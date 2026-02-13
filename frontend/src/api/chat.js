import { io } from 'socket.io-client'
import api from './index.js'

let socket = null

export function connectChat(token) {
  if (socket) socket.disconnect()
  socket = io('/', { auth: { token } })
  return socket
}

export function disconnectChat() {
  if (socket) {
    socket.disconnect()
    socket = null
  }
}

export function getSocket() {
  return socket
}

export async function getMessages(page = 1) {
  const { data } = await api.get('/messages', { params: { page } })
  return data
}
