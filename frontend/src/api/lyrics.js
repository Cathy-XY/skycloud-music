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

export async function getLineComments(songId, lineIndex) {
  const { data } = await api.get(`/songs/${songId}/lyrics/lines/${lineIndex}/comments`)
  return data
}

export async function postLineComment(songId, lineIndex, content, lineText) {
  const { data } = await api.post(`/songs/${songId}/lyrics/lines/${lineIndex}/comments`, { content, line_text: lineText })
  return data
}

export async function getAllLineComments(songId) {
  const { data } = await api.get(`/songs/${songId}/lyrics/line-comments`)
  return data
}
