import { createRouter, createWebHistory } from 'vue-router'
import HomePage from './pages/HomePage.vue'
import SongDetailPage from './pages/SongDetailPage.vue'
import ChatPage from './pages/ChatPage.vue'
import LoginPage from './pages/LoginPage.vue'

const routes = [
  { path: '/', component: HomePage },
  { path: '/songs/:id', component: SongDetailPage, props: true },
  { path: '/chat', component: ChatPage },
  { path: '/login', component: LoginPage },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
