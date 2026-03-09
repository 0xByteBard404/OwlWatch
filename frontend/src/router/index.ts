import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { title: '登录', public: true },
  },
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
    path: '/keywords/:id',
    name: 'KeywordDetail',
    component: () => import('@/views/KeywordDetail.vue'),
    meta: { title: '主体详情' },
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

// 路由守卫
router.beforeEach((to, _from, next) => {
  // 设置页面标题
  document.title = `${to.meta.title || 'OwlWatch'} - OwlWatch 舆情监控`

  // 检查是否需要认证
  const isPublic = to.meta.public === true
  const token = localStorage.getItem('token')

  if (!isPublic && !token) {
    // 需要认证但没有 token，跳转到登录页
    next({
      path: '/login',
      query: { redirect: to.fullPath },
    })
  } else if (to.path === '/login' && token) {
    // 已登录用户访问登录页，跳转到首页
    next('/dashboard')
  } else {
    next()
  }
})

export default router
