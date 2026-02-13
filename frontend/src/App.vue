<template>
  <div class="app">
    <!-- Floating clouds -->
    <div class="cloud cloud-1"></div>
    <div class="cloud cloud-2"></div>
    <div class="cloud cloud-3"></div>
    <div class="cloud cloud-4"></div>
    <div class="cloud cloud-5"></div>
    <div class="cloud cloud-6"></div>

    <header class="app-header">
      <div class="header-left">
        <router-link to="/" class="logo-link">
          <div class="cd-logo">
            <div class="cd-disc">
              <div class="cd-hole"></div>
              <div class="cd-label">Skycloud</div>
              <div class="cd-label cd-label-sub">Music</div>
            </div>
          </div>
          <span class="logo-text">Skycloud Music</span>
        </router-link>
      </div>
      <nav class="header-nav">
        <router-link to="/">Songs</router-link>
        <router-link to="/chat">Chat</router-link>
      </nav>
      <div class="header-right">
        <template v-if="userStore.isLoggedIn">
          <span class="user-name">{{ userStore.user?.nickname }}</span>
          <button class="btn btn-sm" @click="userStore.logout()">Logout</button>
        </template>
        <router-link v-else to="/login" class="btn btn-primary btn-sm">Login</router-link>
      </div>
    </header>
    <main class="app-main">
      <router-view />
    </main>
    <PlayerBar />
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useUserStore } from './stores/user.js'
import PlayerBar from './components/PlayerBar.vue'

const userStore = useUserStore()

onMounted(() => {
  userStore.loadUser()
})
</script>
