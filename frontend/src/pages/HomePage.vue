<template>
  <div class="page home-page">
    <div class="home-header">
      <h2>All Songs</h2>
      <div class="home-header-actions">
        <ListenTogether />
        <button class="btn-refresh" @click="onRefresh" :disabled="refreshing">
          {{ refreshing ? 'Scanning...' : '🔄 Refresh' }}
        </button>
      </div>
    </div>
    <p v-if="loading">Loading...</p>
    <SongList v-else :songs="songs" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getSongs, refreshSongs } from '../api/songs.js'
import SongList from '../components/SongList.vue'
import ListenTogether from '../components/ListenTogether.vue'

const songs = ref([])
const loading = ref(true)
const refreshing = ref(false)

onMounted(async () => {
  songs.value = await getSongs()
  loading.value = false
})

async function onRefresh() {
  refreshing.value = true
  try {
    await refreshSongs()
    songs.value = await getSongs()
  } finally {
    refreshing.value = false
  }
}
</script>
