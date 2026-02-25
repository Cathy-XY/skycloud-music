import { io } from 'socket.io-client'
import api from './index.js'

let socket = null

/**
 * 返回已连接的 socket，如果不存在或已断开则创建新的。
 * 不会销毁已连接的 socket —— 这是获取 socket 的唯一入口。
 */
export function ensureSocket(token) {
  if (socket && socket.connected) return socket
  // socket 存在但已断开，清理后重建
  if (socket) {
    socket.removeAllListeners()
    socket.disconnect()
    socket = null
  }
  if (!token) token = localStorage.getItem('token')
  if (!token) return null
  socket = io('/', { auth: { token } })
  return socket
}

/**
 * 强制断开并清空 socket。仅在登出时调用。
 */
export function disconnectChat() {
  if (socket) {
    socket.removeAllListeners()
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
