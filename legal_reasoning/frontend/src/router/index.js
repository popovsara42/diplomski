import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import Reasoning from '@/components/Reasoning.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
            path: '/reasoning-result',
            name: 'reasoning-result',
            component: Reasoning
        }
  ],
})

export default router
