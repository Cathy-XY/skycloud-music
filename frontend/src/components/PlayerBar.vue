<template>
  <div class="player-bar" v-if="store.currentSong">
    <audio
      ref="audioEl"
      :src="audioSrc"
      @timeupdate="onTimeUpdate"
      @loadedmetadata="onLoaded"
      @ended="onEnded"
      @error="onError"
    ></audio>
    <div class="player-cover">♪</div>
    <div class="player-info">
      <span class="player-title">{{ store.currentSong.title }}</span>
      <span class="player-artist">{{ store.currentSong.artist }}</span>
    </div>
    <div class="player-controls">
      <button class="btn-icon btn-mode" @click="store.toggleMode()" :title="modeTitle" :disabled="listenStore.isInRoom && !listenStore.isDJ" :class="{ 'btn-disabled': listenStore.isInRoom && !listenStore.isDJ }">
        {{ modeIcon }}
      </button>
      <button class="btn-icon" @click="store.prevSong()">⏮</button>
      <button class="btn-icon btn-play" :class="{ 'is-paused': store.isPlaying }" @click="togglePlay"></button>
      <button class="btn-icon" @click="store.nextSong()">⏭</button>
    </div>
    <div class="player-progress">
      <span class="time">{{ formatTime(store.currentTime) }}</span>
      <input
        type="range"
        min="0"
        :max="store.duration"
        :value="store.currentTime"
        @input="onSeek"
        class="progress-bar"
      />
      <span class="time">{{ formatTime(store.duration) }}</span>
    </div>
    <div class="player-volume">
      <span>🔊</span>
      <input
        type="range"
        min="0"
        max="1"
        step="0.01"
        :value="store.volume"
        @input="onVolume"
        class="volume-bar"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed, nextTick, onBeforeUnmount, onMounted } from 'vue'
import { usePlayerStore } from '../stores/player.js'
import { useListenStore } from '../stores/listenTogether.js'
import { useUserStore } from '../stores/user.js'
import { getStreamSignedUrl, getStreamUrl } from '../api/songs.js'
import { ensureSocket, getSocket } from '../api/chat.js'

const store = usePlayerStore()
const listenStore = useListenStore()
const userStore = useUserStore()
const audioEl = ref(null)
const audioSrc = ref('')

// 用于清理 canplay 监听器，防止事件泄漏
let cleanupCanplay = null
// 记录当前 audioSrc 对应的 songId，用于检测后台切歌后 src 是否过期
let loadedSongId = null

// ---- 一起听：同步相关变量 ----
let fromRemoteAt = 0
let heartbeatTimer = null

function isFromRemote() {
  return performance.now() - fromRemoteAt < 300
}

const modeIcon = computed(() => {
  const icons = { sequence: '🔁', repeat: '🔂', shuffle: '🔀' }
  return icons[store.playMode] || '🔁'
})

const modeTitle = computed(() => {
  const titles = { sequence: '顺序播放', repeat: '单曲循环', shuffle: '随机播放' }
  return titles[store.playMode] || '顺序播放'
})

function togglePlay() {
  store.togglePlay()
}

function onEnded() {
  if (listenStore.isInRoom) {
    if (listenStore.isDJ) {
      // DJ controls auto-advance based on their play mode
      if (store.playMode === 'repeat') {
        if (audioEl.value) {
          audioEl.value.currentTime = 0
          audioEl.value.play().catch(() => {})
        }
      } else {
        // sequence or shuffle — DJ advances, sync will broadcast to others
        const prevSong = store.currentSong
        store.nextSong()
        // playlist 只有 1 首歌时 nextSong 不会切歌，手动重播
        if (store.currentSong === prevSong && audioEl.value) {
          audioEl.value.currentTime = 0
          audioEl.value.play().catch(() => {})
        }
      }
    } else {
      // Non-DJ: loop current song while waiting for DJ's next-song sync
      if (audioEl.value) {
        audioEl.value.currentTime = 0
        audioEl.value.play().catch(() => {})
      }
    }
  } else if (store.playMode === 'repeat') {
    if (audioEl.value) {
      audioEl.value.currentTime = 0
      audioEl.value.play().catch(() => {})
    }
  } else {
    store.nextSong()
  }
}

function onTimeUpdate() {
  if (audioEl.value) {
    store.currentTime = audioEl.value.currentTime
  }
}

function onLoaded() {
  if (audioEl.value) {
    store.duration = audioEl.value.duration
  }
}

function onError() {
  // 签名 URL 失败时，回退到代理流式接口
  const song = store.currentSong
  if (!song) return
  const fallback = getStreamUrl(song.id)
  if (audioSrc.value !== fallback) {
    console.warn('Signed URL failed, falling back to proxy stream')
    audioSrc.value = fallback
  }
}

function onSeek(e) {
  const time = parseFloat(e.target.value)
  if (audioEl.value) {
    audioEl.value.currentTime = time
  }
  store.currentTime = time
  // 一起听：拖进度条同步给房间
  if (listenStore.isInRoom) {
    listenStore.syncState({
      position: time,
      isPlaying: store.isPlaying,
      action: '拖动进度',
    })
  }
}

function onVolume(e) {
  const v = parseFloat(e.target.value)
  store.setVolume(v)
  if (audioEl.value) {
    audioEl.value.volume = v
  }
}

function formatTime(sec) {
  if (!sec || isNaN(sec)) return '0:00'
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

/**
 * 安全地播放 audio 元素，处理 canplay 竞态
 * 关键修复：用 { once: true } + 清理函数，避免事件泄漏和竞态
 */
function safePlay(el) {
  // 先清理上一次的 canplay 监听
  if (cleanupCanplay) {
    cleanupCanplay()
    cleanupCanplay = null
  }

  if (el.readyState >= 3) {
    // 数据已经足够播放，直接 play
    el.play().catch(() => {})
  } else {
    // 数据还没准备好，等 canplay 事件
    const handler = () => {
      el.play().catch(() => {})
      cleanupCanplay = null
    }
    el.addEventListener('canplay', handler, { once: true })
    cleanupCanplay = () => el.removeEventListener('canplay', handler)

    // 兜底：5 秒后如果还没 canplay，强制尝试播放
    const timeout = setTimeout(() => {
      el.removeEventListener('canplay', handler)
      cleanupCanplay = null
      if (el.readyState >= 2) {
        el.play().catch(() => {})
      }
    }, 5000)

    const origCleanup = cleanupCanplay
    cleanupCanplay = () => {
      origCleanup()
      clearTimeout(timeout)
    }
  }
}

// ---- DJ 心跳 ----
function startHeartbeat() {
  stopHeartbeat()
  heartbeatTimer = setInterval(() => {
    if (!listenStore.isInRoom || !listenStore.isDJ) { stopHeartbeat(); return }
    listenStore.syncState({
      position: store.currentTime,
      isPlaying: store.isPlaying,
      action: 'heartbeat',
    })
  }, 5000)
}

function stopHeartbeat() {
  if (heartbeatTimer) { clearInterval(heartbeatTimer); heartbeatTimer = null }
}

/**
 * 确保 socket 已连接并返回 Promise
 */
function ensureSocketConnected() {
  return new Promise((resolve) => {
    const token = localStorage.getItem('token')
    if (!token) { resolve(null); return }
    const sock = ensureSocket(token)
    if (!sock) { resolve(null); return }
    if (sock.connected) {
      resolve(sock)
    } else {
      sock.once('connect', () => resolve(sock))
    }
  })
}

// ---- audio 播放控制 watchers ----

watch(() => store.isPlaying, (playing) => {
  nextTick(() => {
    if (!audioEl.value) return
    if (playing) {
      safePlay(audioEl.value)
    } else {
      audioEl.value.pause()
    }
  })
})

watch(() => store.currentSong, async (song) => {
  // 清理旧的 canplay 监听
  if (cleanupCanplay) {
    cleanupCanplay()
    cleanupCanplay = null
  }

  if (!song) { audioSrc.value = ''; loadedSongId = null; return }

  loadedSongId = song.id
  try {
    const url = await getStreamSignedUrl(song.id)
    audioSrc.value = url
  } catch (e) {
    console.warn('Failed to get signed URL, using proxy stream:', e)
    audioSrc.value = getStreamUrl(song.id)
  }

  await nextTick()
  if (audioEl.value) {
    audioEl.value.load()
    if (store.isPlaying) {
      safePlay(audioEl.value)
    }
  }
})

watch(() => store.volume, (v) => {
  if (audioEl.value) audioEl.value.volume = v
})

// ---- 一起听：local -> remote sync ----

watch(() => store.currentSong, (song) => {
  if (!listenStore.isInRoom || isFromRemote() || !song) return
  listenStore.syncState({
    songId: song.id,
    songData: { id: song.id, title: song.title, artist: song.artist, filename: song.filename, duration: song.duration },
    isPlaying: store.isPlaying,
    position: 0,
    action: 'switch',
  })
})

watch(() => store.isPlaying, (playing) => {
  if (!listenStore.isInRoom || isFromRemote()) return
  listenStore.syncState({
    isPlaying: playing,
    position: store.currentTime,
    action: playing ? 'play' : 'pause',
  })
})

// ---- 一起听：remote -> local sync ----

watch(() => listenStore.roomState, (state) => {
  if (!state || !listenStore.isInRoom) return

  fromRemoteAt = performance.now()

  if (state.songId && state.songData && store.currentSong?.id !== state.songId) {
    store.playSong(state.songData)
  }

  if (state.isPlaying !== undefined && state.isPlaying !== store.isPlaying) {
    store.isPlaying = state.isPlaying
  }

  if (state.position !== undefined && Math.abs((state.position || 0) - store.currentTime) > 2) {
    store.currentTime = state.position || 0
  }
}, { deep: true })

// 一起听：远端状态同步到 audio 元素（位置 + 确保播放状态一致）
watch(() => listenStore.roomState, (state) => {
  if (!listenStore.isInRoom || !state || !audioEl.value) return
  // 位置纠偏
  if (state.position != null && Math.abs(state.position - audioEl.value.currentTime) > 2) {
    audioEl.value.currentTime = state.position
  }
  // 如果 store 认为在播放但 audio 实际暂停了（后台 autoplay 被拒），重新播放
  if (store.isPlaying && audioEl.value.paused) {
    safePlay(audioEl.value)
  }
}, { deep: true })

// DJ 心跳 watcher
watch([() => listenStore.isInRoom, () => listenStore.isDJ], ([inRoom, isDJ]) => {
  if (inRoom && isDJ) {
    startHeartbeat()
  } else {
    stopHeartbeat()
  }
})

// 加入房间时，非 DJ 强制 repeat 模式
watch(() => listenStore.isInRoom, (inRoom) => {
  if (!inRoom) return
  if (!listenStore.isDJ) {
    store.playMode = 'repeat'
  }
})

// ---- onMounted: setup socket listeners + visibility handler ----

let _visHandler = null

onMounted(() => {
  // 初始化一起听 socket listeners（如果 socket 已连接且用户已登录）
  const sock = getSocket()
  if (sock && userStore.user) {
    listenStore.setupListeners(userStore.user.id)
  }

  // visibilitychange：回前台时 rejoin + 确保 audio 正确
  _visHandler = async () => {
    if (document.visibilityState !== 'visible') return
    if (!listenStore.isInRoom) return

    // 1) Socket rejoin：刷新房间状态
    const s = getSocket()
    if (s && s.connected) {
      s.emit('listen_join')
    } else {
      const newSock = await ensureSocketConnected()
      if (newSock) {
        listenStore.cleanupListeners()
        listenStore.setupListeners(userStore.user?.id)
        newSock.emit('listen_join')
      }
    }

    // 2) Audio 恢复：确保加载了正确的歌曲并播放
    if (!audioEl.value || !store.currentSong) return

    if (loadedSongId !== store.currentSong.id) {
      loadedSongId = store.currentSong.id
      try {
        audioSrc.value = await getStreamSignedUrl(store.currentSong.id)
      } catch {
        audioSrc.value = getStreamUrl(store.currentSong.id)
      }
      await nextTick()
      if (audioEl.value) {
        audioEl.value.load()
      }
    }

    await nextTick()
    if (!audioEl.value) return
    const state = listenStore.roomState
    if (state?.position != null && Math.abs(state.position - audioEl.value.currentTime) > 2) {
      audioEl.value.currentTime = state.position
    }
    if (store.isPlaying && audioEl.value.paused) {
      safePlay(audioEl.value)
    }
  }
  document.addEventListener('visibilitychange', _visHandler)
})

onBeforeUnmount(() => {
  if (cleanupCanplay) {
    cleanupCanplay()
    cleanupCanplay = null
  }
  stopHeartbeat()
  listenStore.cleanupListeners()
  if (_visHandler) {
    document.removeEventListener('visibilitychange', _visHandler)
    _visHandler = null
  }
})
</script>
