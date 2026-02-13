import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const usePlayerStore = defineStore('player', () => {
  const playlist = ref([])
  const currentIndex = ref(-1)
  const isPlaying = ref(false)
  const currentTime = ref(0)
  const duration = ref(0)
  const volume = ref(0.8)

  const currentSong = computed(() => {
    if (currentIndex.value >= 0 && currentIndex.value < playlist.value.length) {
      return playlist.value[currentIndex.value]
    }
    return null
  })

  function setPlaylist(songs) {
    playlist.value = songs
  }

  function playSong(song) {
    const idx = playlist.value.findIndex(s => s.id === song.id)
    if (idx >= 0) {
      currentIndex.value = idx
    } else {
      playlist.value.push(song)
      currentIndex.value = playlist.value.length - 1
    }
    isPlaying.value = true
  }

  function togglePlay() {
    isPlaying.value = !isPlaying.value
  }

  function nextSong() {
    if (playlist.value.length === 0) return
    currentIndex.value = (currentIndex.value + 1) % playlist.value.length
    isPlaying.value = true
  }

  function prevSong() {
    if (playlist.value.length === 0) return
    currentIndex.value = (currentIndex.value - 1 + playlist.value.length) % playlist.value.length
    isPlaying.value = true
  }

  function setVolume(v) {
    volume.value = v
  }

  function seek(time) {
    currentTime.value = time
  }

  return {
    playlist, currentIndex, isPlaying, currentTime, duration, volume,
    currentSong, setPlaylist, playSong, togglePlay, nextSong, prevSong, setVolume, seek
  }
})
