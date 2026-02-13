<template>
  <div class="page song-detail-page" v-if="song">
    <div class="song-header">
      <button class="btn-icon btn-back" @click="$router.push('/')">←</button>
      <div>
        <h2>{{ song.title }}</h2>
        <p class="artist">{{ song.artist }}</p>
      </div>
      <button class="btn btn-sm btn-primary" @click="playSong">
        {{ playerStore.currentSong?.id === song.id && playerStore.isPlaying ? '⏸ Pause' : '▶ Play' }}
      </button>
    </div>
    <div class="song-detail-layout">
      <LyricsEditor :songId="song.id" />
      <CommentSection :songId="song.id" />
    </div>
  </div>
  <div v-else class="page">
    <p>Loading...</p>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getSong } from '../api/songs.js'
import { usePlayerStore } from '../stores/player.js'
import LyricsEditor from '../components/LyricsEditor.vue'
import CommentSection from '../components/CommentSection.vue'

const route = useRoute()
const playerStore = usePlayerStore()
const song = ref(null)

function playSong() {
  if (!song.value) return
  if (playerStore.currentSong?.id === song.value.id) {
    playerStore.togglePlay()
  } else {
    playerStore.playSong(song.value)
  }
}

onMounted(async () => {
  song.value = await getSong(route.params.id)
})
</script>
