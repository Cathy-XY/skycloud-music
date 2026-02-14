<template>
  <div class="song-list">
    <div
      v-for="song in songs"
      :key="song.id"
      class="song-item"
      :class="{ active: playerStore.currentSong?.id === song.id }"
    >
      <div class="song-cover">♪</div>
      <div class="song-info" @click="goDetail(song)">
        <span class="song-title">{{ song.title }}</span>
        <span class="song-artist">{{ song.artist }}</span>
      </div>
      <span class="song-duration">{{ formatDuration(song.duration) }}</span>
      <button class="btn-icon song-play-btn" :class="{ 'is-paused': playerStore.currentSong?.id === song.id && playerStore.isPlaying }" @click="play(song)"></button>
    </div>
  </div>
</template>

<script setup>
import { usePlayerStore } from '../stores/player.js'
import { useRouter } from 'vue-router'

const props = defineProps({ songs: Array })
const playerStore = usePlayerStore()
const router = useRouter()

function play(song) {
  if (playerStore.currentSong?.id === song.id) {
    playerStore.togglePlay()
  } else {
    playerStore.setPlaylist(props.songs)
    playerStore.playSong(song)
  }
}

function goDetail(song) {
  router.push(`/songs/${song.id}`)
}

function formatDuration(sec) {
  if (!sec) return '-'
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}
</script>
