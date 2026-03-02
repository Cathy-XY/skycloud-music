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
import { computed } from 'vue'
import { useListenStore } from '../stores/listenTogether.js'
import { usePlayerStore } from '../stores/player.js'
import { useUserStore } from '../stores/user.js'
import { ensureSocket } from '../api/chat.js'

const listenStore = useListenStore()
const playerStore = usePlayerStore()
const userStore = useUserStore()

let savedPlayMode = null

const buttonTitle = computed(() => {
  if (!listenStore.isInRoom) return '点击开启一起听'
  const djName = listenStore.djInfo?.nickname || '?'
  const djLabel = listenStore.isDJ ? '你是DJ' : `DJ: ${djName}`
  return `一起听中 (${listenStore.peerCount}人, ${djLabel}) — 再点退出`
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
    // 确保 listeners 已注册（PlayerBar 的 onMounted 可能已做过，这里幂等地重做一次）
    listenStore.cleanupListeners()
    listenStore.setupListeners(userStore.user?.id)
    savedPlayMode = playerStore.playMode
    listenStore.join()
  }
}
</script>
