import api from './index.js'

export async function getComments(songId, page = 1) {
  const { data } = await api.get(`/songs/${songId}/comments`, { params: { page } })
  return data
}

export async function postComment(songId, content) {
  const { data } = await api.post(`/songs/${songId}/comments`, { content })
  return data
}

export async function deleteComment(commentId) {
  const { data } = await api.delete(`/comments/${commentId}`)
  return data
}
