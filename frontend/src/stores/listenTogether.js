import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getSocket } from '../api/chat.js'

export const useListenStore = defineStore('listenTogether', () => {
  const active = ref(false)
  const members = ref([])
  const roomState = ref(null)
  const djInfo = ref(null)  // { nickname, user_id }

  const isInRoom = computed(() => active.value)
  const peerCount = computed(() => members.value.length)
  const isDJ = computed(() => {
    if (!active.value || !djInfo.value) return false
    return djInfo.value._isSelf === true
  })

  function join() {
    const socket = getSocket()
    if (!socket) return
    // 不在这里设 active=true，等服务端 listen_update 确认
    socket.emit('listen_join')
  }

  function leave() {
    const socket = getSocket()
    if (!socket) return
    socket.emit('listen_leave')
    active.value = false
    members.value = []
    roomState.value = null
    djInfo.value = null
  }

  function syncState(data) {
    const socket = getSocket()
    if (!socket || !socket.connected) {
      console.warn('[listen] syncState: no connected socket')
      return
    }
    if (!active.value) return
    socket.emit('listen_sync', data)
  }

  function setupListeners(currentUserId) {
    const socket = getSocket()
    if (!socket) { console.warn('[listen] setupListeners: no socket'); return }

    socket.on('listen_update', (data) => {
      console.log('[listen] listen_update:', data.members?.length, 'members, dj:', data.dj?.nickname)
      members.value = data.members
      // 服务端确认加入成功
      active.value = true
      if (data.state) roomState.value = { ...data.state }
      if (data.dj) {
        djInfo.value = {
          ...data.dj,
          _isSelf: data.dj.user_id === currentUserId,
        }
      } else {
        djInfo.value = null
      }
    })

    socket.on('listen_left', () => {
      active.value = false
      members.value = []
      roomState.value = null
      djInfo.value = null
    })

    socket.on('listen_state', (data) => {
      console.log('[listen] listen_state received:', data.action, data.state?.songId)
      roomState.value = { ...data.state }
    })

    socket.on('listen_error', (data) => {
      alert(data.msg)
    })

    socket.on('listen_dj_change', (data) => {
      console.log('[listen] DJ changed to:', data.nickname)
      djInfo.value = {
        ...data,
        _isSelf: data.user_id === currentUserId,
      }
    })

    // 断线重连：如果之前在房间里，自动重新加入
    socket.on('connect', () => {
      if (active.value) {
        console.log('[listen] reconnected, re-joining listen room')
        socket.emit('listen_join')
      }
    })
  }

  function cleanupListeners() {
    const socket = getSocket()
    if (!socket) return
    socket.off('listen_update')
    socket.off('listen_left')
    socket.off('listen_state')
    socket.off('listen_error')
    socket.off('listen_dj_change')
    // 注意：不移除 connect 监听器，重连处理需要它持续工作
  }

  return {
    active, members, roomState, djInfo, isInRoom, peerCount, isDJ,
    join, leave, syncState, setupListeners, cleanupListeners,
  }
})
