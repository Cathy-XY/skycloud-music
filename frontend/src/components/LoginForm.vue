<template>
  <div class="login-form">
    <h2>{{ isRegister ? 'Register' : 'Login' }}</h2>
    <form @submit.prevent="handleSubmit">
      <div class="form-group">
        <label>Username</label>
        <input v-model="username" type="text" required />
      </div>
      <div class="form-group">
        <label>Password</label>
        <input v-model="password" type="password" required />
      </div>
      <div v-if="isRegister" class="form-group">
        <label>Nickname</label>
        <input v-model="nickname" type="text" placeholder="Optional" />
      </div>
      <p v-if="error" class="error-msg">{{ error }}</p>
      <button type="submit" class="btn btn-primary btn-block">
        {{ isRegister ? 'Register' : 'Login' }}
      </button>
    </form>
    <p class="switch-mode">
      {{ isRegister ? 'Already have an account?' : "Don't have an account?" }}
      <a href="#" @click.prevent="isRegister = !isRegister">
        {{ isRegister ? 'Login' : 'Register' }}
      </a>
    </p>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useUserStore } from '../stores/user.js'
import { useRouter } from 'vue-router'

const userStore = useUserStore()
const router = useRouter()
const isRegister = ref(false)
const username = ref('')
const password = ref('')
const nickname = ref('')
const error = ref('')

async function handleSubmit() {
  error.value = ''
  try {
    if (isRegister.value) {
      await userStore.register(username.value, password.value, nickname.value || username.value)
    } else {
      await userStore.login(username.value, password.value)
    }
    router.push('/')
  } catch (e) {
    error.value = e.response?.data?.error || 'Something went wrong'
  }
}
</script>
