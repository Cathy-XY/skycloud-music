import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { loginApi, registerApi, getMeApi } from '../api/auth.js'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref(null)
  const isLoggedIn = computed(() => !!token.value)

  async function login(username, password) {
    const res = await loginApi(username, password)
    token.value = res.token
    user.value = res.user
    localStorage.setItem('token', res.token)
  }

  async function register(username, password, nickname) {
    const res = await registerApi(username, password, nickname)
    token.value = res.token
    user.value = res.user
    localStorage.setItem('token', res.token)
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
  }

  async function loadUser() {
    if (!token.value) return
    try {
      const res = await getMeApi()
      user.value = res.user
    } catch {
      logout()
    }
  }

  return { token, user, isLoggedIn, login, register, logout, loadUser }
})
