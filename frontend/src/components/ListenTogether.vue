<template>
  <button
    class="btn btn-sm listen-toggle"
    :class="{ active: listenStore.isInRoom }"
    @click="onToggle"
    :title="buttonTitle"
  >
    🎧 一起听
    <span v-if="listenStore.isInRoom" class="listen-dot"></span>
    <span v-if="listenStore.isInRoom && listenStore.isDJ" class="dj-badge">DJ</span>
  </button>
</template>

<script setup>
import { watch, computed, onMounted, onUnmounted } from 'vue'
import { useListenStore } from '../stores/listenTogether.js'
import { usePlayerStore } from '../stores/player.js'
import { useUserStore } from '../stores/user.js'
import { ensureSocket, getSocket } from '../api/chat.js'

const listenStore = useListenStore()
const playerStore = usePlayerStore()
const userStore = useUserStore()

let fromRemote = false
let savedPlayMode = null
let visibilityHandler = null

const buttonTitle = computed(() => {
  if (!listenStore.isInRoom) return '点击开启一起听'
  const djName = listenStore.djInfo?.nickname || '?'
  const djLabel = listenStore.isDJ ? '你是DJ' : `DJ: ${djName}`
  return `一起听中 (${listenStore.peerCount}人, ${djLabel}) — 再点退出`
})

onMounted(() => {
  const sock = getSocket()
  if (sock && userStore.user) {
    listenStore.setupListeners(userStore.user.id)
  }
  // Tab 切回时检测 socket 状态，断了就重连 + rejoin
  visibilityHandler = () => {
    if (document.visibilityState !== 'visible') return
    if (!listenStore.isInRoom) return
    const s = getSocket()
    if (s && s.connected) {
      // socket 还活着，主动 rejoin 刷新状态（服务端幂等）
      s.emit('listen_join')
    } else {
      // socket 断了，重建并等连接后 rejoin
      ensureSocketConnected().then((newSock) => {
        if (newSock) {
          listenStore.cleanupListeners()
          listenStore.setupListeners(userStore.user?.id)
          newSock.emit('listen_join')
        }
      })
    }
  }
  document.addEventListener('visibilitychange', visibilityHandler)
})

onUnmounted(() => {
  listenStore.cleanupListeners()
  if (visibilityHandler) {
    document.removeEventListener('visibilitychange', visibilityHandler)
    visibilityHandler = null
  }
})

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

async function onToggle() {
  if (!userStore.isLoggedIn) {
    alert('请先登录')
    return
  }
  if (listenStore.isInRoom) {
    listenStore.leave()
    // Restore saved play mode when leaving
    if (savedPlayMode) {
      playerStore.playMode = savedPlayMode
      savedPlayMode = null
    }
  } else {
    const sock = await ensureSocketConnected()
    if (!sock) return
    listenStore.cleanupListeners()
    listenStore.setupListeners(userStore.user?.id)
    savedPlayMode = playerStore.playMode
    // Non-DJ will be forced to repeat later via watcher; DJ keeps their mode
    listenStore.join()
  }
}

// When joining the room, set play mode based on DJ status
// DJ: can use any mode (keep current mode)
// Non-DJ: forced to repeat (loop while waiting for DJ's auto-advance)
watch(() => listenStore.isInRoom, (inRoom) => {
  if (!inRoom) return
  if (!listenStore.isDJ) {
    playerStore.playMode = 'repeat'
  }
})

// ---- local -> remote sync ----
watch(() => playerStore.currentSong, (song) => {
  if (!listenStore.isInRoom || fromRemote || !song) return
  listenStore.syncState({
    songId: song.id,
    songData: { id: song.id, title: song.title, artist: song.artist, filename: song.filename, duration: song.duration },
    isPlaying: playerStore.isPlaying,
    position: 0,
    action: 'switch',
  })
})

watch(() => playerStore.isPlaying, (playing) => {
  if (!listenStore.isInRoom || fromRemote) return
  listenStore.syncState({
    isPlaying: playing,
    position: playerStore.currentTime,
    action: playing ? 'play' : 'pause',
  })
})

// ---- remote -> local sync ----
watch(() => listenStore.roomState, (state) => {
  if (!state || !listenStore.isInRoom) return

  fromRemote = true

  if (state.songId && state.songData && playerStore.currentSong?.id !== state.songId) {
    // Don't replace the full playlist — just add the song if missing and jump to it.
    // Replacing with [songData] would destroy the DJ's playlist, making nextSong() unable to advance.
    playerStore.playSong(state.songData)
  }

  if (state.isPlaying !== undefined && state.isPlaying !== playerStore.isPlaying) {
    playerStore.isPlaying = state.isPlaying
  }

  if (state.position !== undefined && Math.abs((state.position || 0) - playerStore.currentTime) > 2) {
    playerStore.currentTime = state.position || 0
  }

  setTimeout(() => { fromRemote = false }, 300)
}, { deep: true })
</script>
