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
  {
    path: '/negative-keywords',
    name: 'NegativeKeywords',
    component: () => import('@/views/NegativeKeywords.vue'),
    meta: { title: '负面关键词' },
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
