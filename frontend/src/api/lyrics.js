import api from './index.js'

export async function getLyrics(songId) {
  const { data } = await api.get(`/songs/${songId}/lyrics`)
  return data
}

export async function saveLyrics(songId, content) {
  const { data } = await api.put(`/songs/${songId}/lyrics`, { content })
  return data
}

export async function getLyricsHistory(songId) {
  const { data } = await api.get(`/songs/${songId}/lyrics/history`)
  return data
}
