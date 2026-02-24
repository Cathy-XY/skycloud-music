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

export async function uploadChatImage(file) {
  const formData = new FormData()
  formData.append('image', file)
  const { data } = await api.post('/chat/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
  return data
}
