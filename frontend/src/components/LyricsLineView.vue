<template>
  <div class="lyrics-line-view">
    <div v-for="(line, idx) in parsedLines" :key="idx">
      <div
        class="lyric-line"
        :class="{ 'active-line': isActiveLine(line.time), expanded: expandedLine === idx }"
        @click="toggleLine(idx)"
      >
        <span class="lyric-time" v-if="line.time !== null">{{ formatLrcTime(line.time) }}</span>
        <span class="lyric-text">{{ line.text }}</span>
        <span class="lyric-comment-badge" v-if="commentCounts[idx]">
          {{ commentCounts[idx] }} comments
        </span>
        <button
          v-if="userStore.isLoggedIn"
          class="lyric-add-btn"
          @click.stop="toggleLine(idx)"
        >+ Comment</button>
      </div>
      <div v-if="expandedLine === idx" class="line-comments-panel">
        <div v-for="c in lineComments[idx] || []" :key="c.id" class="line-comment-item">
          <span class="line-comment-user">{{ c.nickname }}</span>
          <span class="line-comment-content">{{ c.content }}</span>
          <span class="line-comment-time">{{ c.created_at }}</span>
        </div>
        <p v-if="!lineComments[idx]?.length" class="empty" style="padding:8px;">No comments on this line yet</p>
        <div v-if="userStore.isLoggedIn" class="line-comment-input">
          <input
            v-model="newLineComment"
            @keyup.enter="submitLineComment(idx, line.text)"
            placeholder="Share your thoughts..."
          />
          <button class="btn btn-primary btn-sm" @click="submitLineComment(idx, line.text)" :disabled="!newLineComment.trim()">Post</button>
        </div>
      </div>
    </div>
    <p v-if="parsedLines.length === 0" class="empty">No lyrics available</p>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { usePlayerStore } from '../stores/player.js'
import { useUserStore } from '../stores/user.js'
import { getLineComments, postLineComment, getAllLineComments } from '../api/lyrics.js'

const props = defineProps({
  songId: [Number, String],
  lyricsContent: String
})

const playerStore = usePlayerStore()
const userStore = useUserStore()
const expandedLine = ref(-1)
const lineComments = ref({})
const commentCounts = ref({})
const newLineComment = ref('')

const parsedLines = computed(() => {
  if (!props.lyricsContent) return []
  const lines = props.lyricsContent.split('\n')
  const result = []
  const lrcRegex = /^\[(\d{2}):(\d{2})\.(\d{2,3})\](.*)$/
  for (const raw of lines) {
    const trimmed = raw.trim()
    if (!trimmed) continue
    const match = trimmed.match(lrcRegex)
    if (match) {
      const min = parseInt(match[1])
      const sec = parseInt(match[2])
      const ms = parseInt(match[3])
      const time = min * 60 + sec + ms / (match[3].length === 3 ? 1000 : 100)
      const text = match[4].trim()
      if (text) {
        result.push({ time, text })
      }
    } else if (!trimmed.startsWith('[')) {
      result.push({ time: null, text: trimmed })
    }
  }
  return result
})

function isActiveLine(time) {
  if (time === null) return false
  if (!playerStore.currentSong || playerStore.currentSong.id !== Number(props.songId)) return false
  const cur = playerStore.currentTime
  const idx = parsedLines.value.findIndex(l => l.time === time)
  const nextIdx = idx + 1
  const nextTime = nextIdx < parsedLines.value.length ? parsedLines.value[nextIdx].time : Infinity
  return cur >= time && cur < (nextTime || Infinity)
}

function formatLrcTime(sec) {
  if (sec === null) return ''
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

async function toggleLine(idx) {
  if (expandedLine.value === idx) {
    expandedLine.value = -1
    return
  }
  expandedLine.value = idx
  newLineComment.value = ''
  try {
    lineComments.value[idx] = await getLineComments(props.songId, idx)
  } catch {
    lineComments.value[idx] = []
  }
}

async function submitLineComment(idx, lineText) {
  if (!newLineComment.value.trim()) return
  const comment = await postLineComment(props.songId, idx, newLineComment.value.trim(), lineText)
  if (!lineComments.value[idx]) lineComments.value[idx] = []
  lineComments.value[idx].unshift(comment)
  commentCounts.value[idx] = (commentCounts.value[idx] || 0) + 1
  newLineComment.value = ''
}

async function loadCommentCounts() {
  try {
    const grouped = await getAllLineComments(props.songId)
    const counts = {}
    for (const [idx, comments] of Object.entries(grouped)) {
      counts[idx] = comments.length
    }
    commentCounts.value = counts
  } catch {
    commentCounts.value = {}
  }
}

onMounted(loadCommentCounts)
watch(() => props.songId, loadCommentCounts)
</script>
