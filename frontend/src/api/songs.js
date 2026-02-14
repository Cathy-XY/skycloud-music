import api from './index.js'

export async function getSongs() {
  const { data } = await api.get('/songs')
  return data
}

export async function getSong(id) {
  const { data } = await api.get(`/songs/${id}`)
  return data
}

export function getStreamUrl(id) {
  return `/api/songs/${id}/stream`
}

export async function getStreamSignedUrl(id) {
  const { data } = await api.get(`/songs/${id}/stream-url`)
  return data.url
}

export async function refreshSongs() {
  const { data } = await api.post('/songs/refresh')
  return data
}
