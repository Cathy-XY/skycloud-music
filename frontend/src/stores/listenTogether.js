import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getSocket } from '../api/chat.js'

export const useListenStore = defineStore('listenTogether', () => {
  const active = ref(false)
  const members = ref([])
  const roomState = ref(null)

  const isInRoom = computed(() => active.value)
  const peerCount = computed(() => members.value.length)

  let _ignoreNextState = false

  function join() {
    const socket = getSocket()
    if (!socket) return
    socket.emit('listen_join')
    active.value = true
  }

  function leave() {
    const socket = getSocket()
    if (!socket) return
    socket.emit('listen_leave')
    active.value = false
    members.value = []
    roomState.value = null
  }

  function syncState(data) {
    const socket = getSocket()
    if (!socket) return
    _ignoreNextState = true
    socket.emit('listen_sync', data)
  }

  function setupListeners() {
    const socket = getSocket()
    if (!socket) return

    socket.on('listen_update', (data) => {
      members.value = data.members
      roomState.value = data.state
    })

    socket.on('listen_left', () => {
      active.value = false
      members.value = []
      roomState.value = null
    })

    socket.on('listen_state', (data) => {
      if (_ignoreNextState) {
        _ignoreNextState = false
        roomState.value = data.state
        return
      }
      roomState.value = data.state
    })

    socket.on('listen_error', (data) => {
      alert(data.msg)
    })
  }

  function cleanupListeners() {
    const socket = getSocket()
    if (!socket) return
    socket.off('listen_update')
    socket.off('listen_left')
    socket.off('listen_state')
    socket.off('listen_error')
  }

  return {
    active, members, roomState, isInRoom, peerCount,
    join, leave, syncState, setupListeners, cleanupListeners,
  }
})
