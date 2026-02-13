<template>
  <div class="player-bar" v-if="store.currentSong">
    <audio
      ref="audioEl"
      :src="streamUrl"
      @timeupdate="onTimeUpdate"
      @loadedmetadata="onLoaded"
      @ended="store.nextSong()"
    ></audio>
    <div class="player-info">
      <span class="player-title">{{ store.currentSong.title }}</span>
      <span class="player-artist">{{ store.currentSong.artist }}</span>
    </div>
    <div class="player-controls">
      <button class="btn-icon" @click="store.prevSong()">⏮</button>
      <button class="btn-icon btn-play" @click="togglePlay">
        {{ store.isPlaying ? '⏸' : '▶' }}
      </button>
      <button class="btn-icon" @click="store.nextSong()">⏭</button>
    </div>
    <div class="player-progress">
      <span class="time">{{ formatTime(store.currentTime) }}</span>
      <input
        type="range"
        min="0"
        :max="store.duration"
        :value="store.currentTime"
        @input="onSeek"
        class="progress-bar"
      />
      <span class="time">{{ formatTime(store.duration) }}</span>
    </div>
    <div class="player-volume">
      <span>🔊</span>
      <input
        type="range"
        min="0"
        max="1"
        step="0.01"
        :value="store.volume"
        @input="onVolume"
        class="volume-bar"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed, nextTick } from 'vue'
import { usePlayerStore } from '../stores/player.js'
import { getStreamUrl } from '../api/songs.js'

const store = usePlayerStore()
const audioEl = ref(null)

const streamUrl = computed(() => {
  return store.currentSong ? getStreamUrl(store.currentSong.id) : ''
})

function togglePlay() {
  store.togglePlay()
}

function onTimeUpdate() {
  if (audioEl.value) {
    store.currentTime = audioEl.value.currentTime
  }
}

function onLoaded() {
  if (audioEl.value) {
    store.duration = audioEl.value.duration
  }
}

function onSeek(e) {
  const time = parseFloat(e.target.value)
  if (audioEl.value) {
    audioEl.value.currentTime = time
  }
  store.currentTime = time
}

function onVolume(e) {
  const v = parseFloat(e.target.value)
  store.setVolume(v)
  if (audioEl.value) {
    audioEl.value.volume = v
  }
}

function formatTime(sec) {
  if (!sec || isNaN(sec)) return '0:00'
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

watch(() => store.isPlaying, (playing) => {
  nextTick(() => {
    if (!audioEl.value) return
    if (playing) {
      audioEl.value.play().catch(() => {})
    } else {
      audioEl.value.pause()
    }
  })
})

watch(streamUrl, () => {
  nextTick(() => {
    if (audioEl.value && store.isPlaying) {
      audioEl.value.play().catch(() => {})
    }
  })
})

watch(() => store.volume, (v) => {
  if (audioEl.value) audioEl.value.volume = v
})
</script>
