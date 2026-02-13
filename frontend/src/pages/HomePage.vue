<template>
  <div class="page home-page">
    <h2>All Songs</h2>
    <p v-if="loading">Loading...</p>
    <SongList v-else :songs="songs" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getSongs } from '../api/songs.js'
import SongList from '../components/SongList.vue'

const songs = ref([])
const loading = ref(true)

onMounted(async () => {
  songs.value = await getSongs()
  loading.value = false
})
</script>
