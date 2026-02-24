<template>
  <div class="chat-room">
    <div class="chat-header">
      <h3>Chat Room</h3>
      <span class="online-badge">{{ onlineCount }} online</span>
      <button class="btn-send-mode" @click="toggleSendMode" :title="sendModeHint">
        {{ sendMode === 'enter' ? '⏎ 发送' : 'Ctrl+⏎ 发送' }}
      </button>
    </div>
    <div class="chat-messages" ref="messagesEl">
      <div
        v-for="msg in messages"
        :key="msg.id"
        class="chat-msg"
        :class="{ 'chat-msg-clickable': userStore.isLoggedIn && msg.nickname !== 'System' }"
        :data-msg-id="msg.id"
        @click="onMsgClick(msg, $event)"
      >
        <!-- 引用块 -->
        <div v-if="msg.reply_content || msg.reply_image_url" class="chat-reply-quote" @click.stop="scrollToMessage(msg.reply_to)">
          <span class="reply-nick">{{ msg.reply_nickname }}</span>
          <span class="reply-text">{{ msg.reply_content }}<span v-if="msg.reply_image_url"> [图片]</span></span>
        </div>
        <div v-else-if="msg.reply_to" class="chat-reply-quote chat-reply-deleted" @click.stop>
          <span class="reply-text">[消息已删除]</span>
        </div>
        <div class="chat-msg-header">
          <strong>{{ msg.nickname }}</strong>
          <span class="chat-time">{{ msg.created_at }}</span>
          <span
            v-if="userStore.isLoggedIn && msg.nickname !== 'System'"
            class="reply-hint"
          >↩ 引用</span>
        </div>
        <p v-if="msg.content" class="chat-content">{{ msg.content }}</p>
        <div v-if="msg.image_url" class="chat-image-wrap" @click.stop="lightboxUrl = '/api/uploads/' + msg.image_url">
          <img :src="'/api/uploads/' + msg.image_url" class="chat-image" loading="lazy" />
        </div>
      </div>
      <p v-if="messages.length === 0" class="empty">No messages yet. Start the conversation!</p>
    </div>
    <!-- 引用预览条 -->
    <div v-if="replyTo" class="chat-reply-bar">
      <div class="reply-bar-content">
        <span class="reply-bar-label">回复 <strong>{{ replyTo.nickname }}</strong></span>
        <span class="reply-bar-text">{{ replyTo.content }}</span>
      </div>
      <button class="reply-bar-close" @click="cancelReply">&times;</button>
    </div>
    <div v-if="userStore.isLoggedIn" class="chat-input">
      <div v-if="pendingImage" class="chat-image-preview">
        <img :src="pendingImagePreview" />
        <button class="image-preview-close" @click="clearPendingImage">&times;</button>
      </div>
      <div class="chat-input-row">
        <button class="btn-icon btn-image-pick" @click="imageInput?.click()" title="发送图片">&#128247;</button>
        <input
          ref="imageInput"
          type="file"
          accept="image/jpeg,image/png,image/gif,image/webp"
          style="display: none"
          @change="onImagePicked"
        />
        <textarea
          ref="inputEl"
          v-model="newMsg"
          @keydown="handleKeydown"
          @paste="handlePaste"
          :placeholder="inputPlaceholder"
          rows="1"
        ></textarea>
        <div class="send-area">
          <button class="btn btn-primary" @click="sendMessage" :disabled="(!newMsg.trim() && !pendingImage) || uploading">{{ uploading ? '...' : 'Send' }}</button>
          <span class="shortcut-hint">{{ shortcutHint }}</span>
        </div>
      </div>
    </div>
    <p v-else class="login-hint">
      <router-link to="/login">Login</router-link> to chat
    </p>
    <!-- Lightbox -->
    <div v-if="lightboxUrl" class="chat-lightbox" @click="lightboxUrl = null">
      <img :src="lightboxUrl" @click.stop />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useUserStore } from '../stores/user.js'
import { connectChat, disconnectChat, getMessages, uploadChatImage } from '../api/chat.js'

const userStore = useUserStore()
const messages = ref([])
const newMsg = ref('')
const onlineCount = ref(0)
const messagesEl = ref(null)
const inputEl = ref(null)
const replyTo = ref(null)
const pendingImage = ref(null)
const pendingImagePreview = ref(null)
const lightboxUrl = ref(null)
const uploading = ref(false)
const imageInput = ref(null)
let socket = null

// 发送模式：'enter' = 回车发送，'ctrl+enter' = Ctrl+回车发送
const sendMode = ref(localStorage.getItem('chat-send-mode') || 'enter')

const sendModeHint = computed(() => {
  if (sendMode.value === 'enter') {
    return 'Enter 发送，Shift/Ctrl+Enter 换行\n点击切换为 Ctrl+Enter 发送'
  }
  return 'Ctrl+Enter 发送，Enter 换行\n点击切换为 Enter 发送'
})

const inputPlaceholder = computed(() => {
  return replyTo.value ? `回复 ${replyTo.value.nickname}...` : 'Type a message...'
})

const shortcutHint = computed(() => {
  if (sendMode.value === 'enter') {
    return 'Shift/Ctrl+Enter 换行'
  }
  return 'Enter 换行'
})

function toggleSendMode() {
  sendMode.value = sendMode.value === 'enter' ? 'ctrl+enter' : 'enter'
  localStorage.setItem('chat-send-mode', sendMode.value)
}

function handleKeydown(e) {
  // Esc 取消引用
  if (e.key === 'Escape') {
    if (replyTo.value) {
      cancelReply()
      e.preventDefault()
    }
    return
  }

  if (e.key === 'Enter') {
    if (sendMode.value === 'enter') {
      // Enter 发送模式：Enter 发送，Shift+Enter / Ctrl+Enter 换行
      if (e.shiftKey || e.ctrlKey || e.metaKey) return // 允许换行
      e.preventDefault()
      sendMessage()
    } else {
      // Ctrl+Enter 发送模式：Ctrl/Meta+Enter 发送，Enter 换行
      if (e.ctrlKey || e.metaKey) {
        e.preventDefault()
        sendMessage()
      }
      // 普通 Enter 允许换行，不需要 preventDefault
    }
  }
}

// textarea 自动调整高度
watch(newMsg, () => {
  nextTick(() => {
    if (inputEl.value) {
      inputEl.value.style.height = 'auto'
      inputEl.value.style.height = Math.min(inputEl.value.scrollHeight, 120) + 'px'
    }
  })
})

function scrollToBottom() {
  nextTick(() => {
    if (messagesEl.value) {
      messagesEl.value.scrollTop = messagesEl.value.scrollHeight
    }
  })
}

function setReply(msg) {
  replyTo.value = { id: msg.id, nickname: msg.nickname, content: msg.content }
  nextTick(() => inputEl.value?.focus())
}

function onMsgClick(msg, event) {
  // 只有登录用户点击非系统消息才触发引用
  if (!userStore.isLoggedIn || msg.nickname === 'System') return
  // 如果用户在选中文字，不触发引用
  const selection = window.getSelection()
  if (selection && selection.toString().trim()) return
  setReply(msg)
}

function cancelReply() {
  replyTo.value = null
}

function onImagePicked(e) {
  const file = e.target.files[0]
  if (!file) return
  if (file.size > 2 * 1024 * 1024) {
    alert('图片过大，最大 2MB')
    return
  }
  setPendingImage(file)
  e.target.value = ''
}

function handlePaste(e) {
  const items = e.clipboardData?.items
  if (!items) return
  for (const item of items) {
    if (item.type.startsWith('image/')) {
      e.preventDefault()
      const file = item.getAsFile()
      if (file.size > 2 * 1024 * 1024) {
        alert('图片过大，最大 2MB')
        return
      }
      setPendingImage(file)
      return
    }
  }
}

function setPendingImage(file) {
  pendingImage.value = file
  const reader = new FileReader()
  reader.onload = (e) => { pendingImagePreview.value = e.target.result }
  reader.readAsDataURL(file)
}

function clearPendingImage() {
  pendingImage.value = null
  pendingImagePreview.value = null
}

function scrollToMessage(msgId) {
  if (!messagesEl.value) return
  const el = messagesEl.value.querySelector(`[data-msg-id="${msgId}"]`)
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'center' })
    el.classList.add('chat-msg-highlight')
    setTimeout(() => el.classList.remove('chat-msg-highlight'), 1500)
  }
}

async function loadHistory() {
  const msgs = await getMessages()
  messages.value = msgs.reverse()
  scrollToBottom()
}

async function sendMessage() {
  const hasText = newMsg.value.trim()
  const hasImage = pendingImage.value
  if (!hasText && !hasImage) return
  if (!socket) return

  let image_url = null
  if (hasImage) {
    uploading.value = true
    try {
      const res = await uploadChatImage(pendingImage.value)
      image_url = res.image_url
    } catch (err) {
      alert('图片上传失败: ' + (err.response?.data?.error || err.message))
      uploading.value = false
      return
    }
    uploading.value = false
  }

  const payload = { content: newMsg.value.trim() }
  if (image_url) payload.image_url = image_url
  if (replyTo.value) payload.reply_to = replyTo.value.id

  socket.emit('send_message', payload)
  newMsg.value = ''
  replyTo.value = null
  clearPendingImage()
  nextTick(() => {
    if (inputEl.value) {
      inputEl.value.style.height = 'auto'
    }
  })
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
