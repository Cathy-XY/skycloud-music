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
import { ref, watch, computed, nextTick, onBeforeUnmount } from 'vue'
import { usePlayerStore } from '../stores/player.js'
import { useListenStore } from '../stores/listenTogether.js'
import { getStreamSignedUrl, getStreamUrl } from '../api/songs.js'

const store = usePlayerStore()
const listenStore = useListenStore()
const audioEl = ref(null)
const audioSrc = ref('')

// 用于清理 canplay 监听器，防止事件泄漏
let cleanupCanplay = null

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

  if (!song) { audioSrc.value = ''; return }

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

// 一起听：远端 seek 同步到 audio 元素
watch(() => listenStore.roomState?.position, (pos) => {
  if (!listenStore.isInRoom || pos == null || !audioEl.value) return
  if (Math.abs(pos - audioEl.value.currentTime) > 2) {
    audioEl.value.currentTime = pos
  }
})

onBeforeUnmount(() => {
  if (cleanupCanplay) {
    cleanupCanplay()
    cleanupCanplay = null
  }
})
</script>
