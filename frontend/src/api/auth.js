import api from './index.js'

export async function loginApi(username, password) {
  const { data } = await api.post('/auth/login', { username, password })
  return data
}

export async function registerApi(username, password, nickname) {
  const { data } = await api.post('/auth/register', { username, password, nickname })
  return data
}

export async function getMeApi() {
  const { data } = await api.get('/auth/me')
  return data
}
