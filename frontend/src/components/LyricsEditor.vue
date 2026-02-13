<template>
  <div class="lyrics-editor">
    <div class="lyrics-header" style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;">
      <h3 style="margin:0;">Lyrics</h3>
      <div>
        <button v-if="userStore.isLoggedIn && !editing" class="btn btn-sm" @click="startEdit">
          {{ lyrics.content ? 'Edit' : 'Add Lyrics' }}
        </button>
      </div>
    </div>
    <div v-if="!editing" class="lyrics-view">
      <LyricsLineView v-if="lyrics.content" :songId="songId" :lyricsContent="lyrics.content" />
      <p v-else class="empty">No lyrics yet</p>
      <div class="lyrics-meta" v-if="lyrics.edited_by_name">
        Last edited by {{ lyrics.edited_by_name }} at {{ lyrics.updated_at }}
      </div>
      <p v-if="!userStore.isLoggedIn && !lyrics.content" class="login-hint">
        <router-link to="/login">Login</router-link> to add lyrics
      </p>
    </div>
    <div v-else class="lyrics-edit">
      <textarea v-model="editContent" rows="15" placeholder="Paste LRC lyrics or plain text..."></textarea>
      <div class="lyrics-actions">
        <button class="btn btn-primary" @click="save">Save</button>
        <button class="btn" @click="cancelEdit">Cancel</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useUserStore } from '../stores/user.js'
import { getLyrics, saveLyrics } from '../api/lyrics.js'
import LyricsLineView from './LyricsLineView.vue'

const props = defineProps({ songId: [Number, String] })
const userStore = useUserStore()
const lyrics = ref({ content: '', edited_by_name: null, updated_at: null })
const editing = ref(false)
const editContent = ref('')

async function load() {
  lyrics.value = await getLyrics(props.songId)
  editing.value = false
}

function startEdit() {
  editContent.value = lyrics.value.content || ''
  editing.value = true
}

function cancelEdit() {
  editing.value = false
}

async function save() {
  await saveLyrics(props.songId, editContent.value)
  await load()
}

onMounted(load)
watch(() => props.songId, load)
</script>
