<template>
  <div class="lyrics-editor">
    <h3>Lyrics</h3>
    <div v-if="!editing" class="lyrics-view">
      <pre v-if="lyrics.content" class="lyrics-text">{{ lyrics.content }}</pre>
      <p v-else class="empty">No lyrics yet</p>
      <div class="lyrics-meta" v-if="lyrics.edited_by_name">
        Last edited by {{ lyrics.edited_by_name }} at {{ lyrics.updated_at }}
      </div>
      <button v-if="userStore.isLoggedIn" class="btn btn-sm" @click="startEdit">
        {{ lyrics.content ? 'Edit Lyrics' : 'Add Lyrics' }}
      </button>
      <p v-else class="login-hint">
        <router-link to="/login">Login</router-link> to edit lyrics
      </p>
    </div>
    <div v-else class="lyrics-edit">
      <textarea v-model="editContent" rows="12" placeholder="Enter lyrics here..."></textarea>
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
