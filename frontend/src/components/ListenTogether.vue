<template>
  <button
    class="btn btn-sm listen-toggle"
    :class="{ active: listenStore.isInRoom }"
    @click="onToggle"
    :title="listenStore.isInRoom
      ? '一起听中 (' + listenStore.peerCount + '人) — 再点退出'
      : '点击开启一起听'"
  >
    🎧 一起听
    <span v-if="listenStore.isInRoom" class="listen-dot"></span>
  </button>
</template>

<script setup>
import { watch, onMounted, onUnmounted } from 'vue'
import { useListenStore } from '../stores/listenTogether.js'
import { usePlayerStore } from '../stores/player.js'
import { useUserStore } from '../stores/user.js'
import { getSocket, connectChat } from '../api/chat.js'

const listenStore = useListenStore()
const playerStore = usePlayerStore()
const userStore = useUserStore()

let fromRemote = false

onMounted(() => {
  const sock = getSocket()
  if (sock) {
    listenStore.setupListeners()
  }
})

onUnmounted(() => {
  listenStore.cleanupListeners()
})

/**
 * 确保 socket 已连接并返回 Promise
 * 关键修复：connectChat 后要等 connect 事件再 emit
 */
function ensureSocket() {
  return new Promise((resolve) => {
    const existing = getSocket()
    if (existing && existing.connected) {
      resolve(existing)
      return
    }
    const token = localStorage.getItem('token')
    if (!token) { resolve(null); return }
    const sock = connectChat(token)
    listenStore.cleanupListeners()
    listenStore.setupListeners()
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
  } else {
    await ensureSocket()
    listenStore.join()
  }
}

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
    playerStore.setPlaylist([state.songData])
    playerStore.playSong(state.songData)
  }

  if (state.isPlaying !== playerStore.isPlaying) {
    playerStore.isPlaying = state.isPlaying
  }

  if (Math.abs((state.position || 0) - playerStore.currentTime) > 2) {
    playerStore.currentTime = state.position || 0
  }

  setTimeout(() => { fromRemote = false }, 100)
}, { deep: true })
</script>
