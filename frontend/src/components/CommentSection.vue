<template>
  <div class="comment-section">
    <h3>Comments</h3>
    <div v-if="userStore.isLoggedIn" class="comment-form">
      <textarea v-model="newComment" placeholder="Write a comment..." rows="2"></textarea>
      <button class="btn btn-primary" @click="submit" :disabled="!newComment.trim()">Post</button>
    </div>
    <p v-else class="login-hint">
      <router-link to="/login">Login</router-link> to leave a comment
    </p>
    <div class="comment-list">
      <div v-for="c in comments" :key="c.id" class="comment-item">
        <div class="comment-header">
          <strong>{{ c.nickname }}</strong>
          <span class="comment-time">{{ c.created_at }}</span>
          <button
            v-if="c.user_id === userStore.user?.id"
            class="btn-icon btn-delete"
            @click="remove(c.id)"
          >✕</button>
        </div>
        <p class="comment-body">{{ c.content }}</p>
      </div>
      <p v-if="comments.length === 0" class="empty">No comments yet</p>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useUserStore } from '../stores/user.js'
import { getComments, postComment, deleteComment } from '../api/comments.js'

const props = defineProps({ songId: [Number, String] })
const userStore = useUserStore()
const comments = ref([])
const newComment = ref('')

async function load() {
  comments.value = await getComments(props.songId)
}

async function submit() {
  if (!newComment.value.trim()) return
  const c = await postComment(props.songId, newComment.value.trim())
  comments.value.unshift(c)
  newComment.value = ''
}

async function remove(id) {
  await deleteComment(id)
  comments.value = comments.value.filter(c => c.id !== id)
}

onMounted(load)
watch(() => props.songId, load)
</script>
