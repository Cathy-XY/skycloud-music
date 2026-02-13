<template>
  <div class="chat-room">
    <div class="chat-header">
      <h3>Chat Room</h3>
      <span class="online-badge">{{ onlineCount }} online</span>
    </div>
    <div class="chat-messages" ref="messagesEl">
      <div v-for="msg in messages" :key="msg.id" class="chat-msg">
        <strong>{{ msg.nickname }}</strong>
        <span class="chat-time">{{ msg.created_at }}</span>
        <p>{{ msg.content }}</p>
      </div>
      <p v-if="messages.length === 0" class="empty">No messages yet. Start the conversation!</p>
    </div>
    <div v-if="userStore.isLoggedIn" class="chat-input">
      <input
        v-model="newMsg"
        @keyup.enter="sendMessage"
        placeholder="Type a message..."
      />
      <button class="btn btn-primary" @click="sendMessage" :disabled="!newMsg.trim()">Send</button>
    </div>
    <p v-else class="login-hint">
      <router-link to="/login">Login</router-link> to chat
    </p>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useUserStore } from '../stores/user.js'
import { connectChat, disconnectChat, getMessages } from '../api/chat.js'

const userStore = useUserStore()
const messages = ref([])
const newMsg = ref('')
const onlineCount = ref(0)
const messagesEl = ref(null)
let socket = null

function scrollToBottom() {
  nextTick(() => {
    if (messagesEl.value) {
      messagesEl.value.scrollTop = messagesEl.value.scrollHeight
    }
  })
}

async function loadHistory() {
  const msgs = await getMessages()
  messages.value = msgs.reverse()
  scrollToBottom()
}

function sendMessage() {
  if (!newMsg.value.trim() || !socket) return
  socket.emit('send_message', { content: newMsg.value.trim() })
  newMsg.value = ''
}

onMounted(async () => {
  await loadHistory()
  if (userStore.isLoggedIn) {
    socket = connectChat(userStore.token)
    socket.on('new_message', (msg) => {
      messages.value.push(msg)
      scrollToBottom()
    })
    socket.on('online_count', (data) => {
      onlineCount.value = data.count
    })
    socket.on('user_joined', (data) => {
      messages.value.push({
        id: Date.now(),
        nickname: 'System',
        content: `${data.nickname} joined the chat`,
        created_at: new Date().toISOString()
      })
      scrollToBottom()
    })
    socket.on('user_left', (data) => {
      messages.value.push({
        id: Date.now(),
        nickname: 'System',
        content: `${data.nickname} left the chat`,
        created_at: new Date().toISOString()
      })
      scrollToBottom()
    })
  }
})

onUnmounted(() => {
  disconnectChat()
})
</script>
