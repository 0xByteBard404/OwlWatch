import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/dashboard',
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('@/views/Dashboard.vue'),
    meta: { title: '仪表盘' },
  },
  {
    path: '/keywords',
    name: 'Keywords',
    component: () => import('@/views/Keywords.vue'),
    meta: { title: '监控主体' },
  },
  {
    path: '/sentiment-keywords',
    name: 'SentimentKeywords',
    component: () => import('@/views/SentimentKeywords.vue'),
    meta: { title: '情感词库' },
  },
  {
    path: '/rss',
    name: 'RSS',
    component: () => import('@/views/RSS.vue'),
    meta: { title: 'RSS 订阅' },
  },
  {
    path: '/articles',
    name: 'Articles',
    component: () => import('@/views/Articles.vue'),
    meta: { title: '文章列表' },
  },
  {
    path: '/alerts',
    name: 'Alerts',
    component: () => import('@/views/Alerts.vue'),
    meta: { title: '预警中心' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  document.title = `${to.meta.title || 'OwlWatch'} - OwlWatch 舆情监控`
})

export default router
