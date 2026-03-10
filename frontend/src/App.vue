<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()
const route = useRoute()

const isCollapse = ref(false)
const currentTime = ref(new Date().toLocaleString('zh-CN'))
const username = ref(localStorage.getItem('username') || 'admin')

// Update time every second
setInterval(() => {
  currentTime.value = new Date().toLocaleString('zh-CN')
}, 1000)

const menuItems = [
  { path: '/dashboard', icon: 'DataLine', title: '仪表盘', color: '#00f0ff' },
  { path: '/rss', icon: 'Promotion', title: 'RSS 订阅', color: '#a855f7' },
  { path: '/keywords', icon: 'Key', title: '监控主体', color: '#ff6b2c' },
  { path: '/articles', icon: 'Document', title: '情报库', color: '#00ff88' },
  { path: '/alerts', icon: 'Bell', title: '预警中心', color: '#ff3366' },
  { path: '/sentiment-keywords', icon: 'TrendCharts', title: '情感词库', color: '#ffd000' },
]

const handleSelect = (path: string) => {
  router.push(path)
}

// 登出
async function handleLogout() {
  try {
    await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })

    // 清除 token 和用户信息
    localStorage.removeItem('token')
    localStorage.removeItem('username')

    ElMessage.success('已退出登录')

    // 跳转到登录页
    router.push('/login')
  } catch {
    // 用户取消
  }
}

// 检查登录状态
onMounted(() => {
  const token = localStorage.getItem('token')
  if (!token && route.path !== '/login') {
    router.push('/login')
  }
})
</script>

<template>
  <div class="cyber-layout">
    <!-- Ambient Glow Effects -->
    <div class="ambient-glow glow-1"></div>
    <div class="ambient-glow glow-2"></div>

    <!-- Sidebar -->
    <aside class="cyber-sidebar" :class="{ collapsed: isCollapse }">
      <!-- Logo -->
      <div class="sidebar-logo">
        <div class="logo-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <circle cx="12" cy="12" r="3"/>
            <line x1="12" y1="2" x2="12" y2="5"/>
            <line x1="12" y1="19" x2="12" y2="22"/>
            <line x1="2" y1="12" x2="5" y2="12"/>
            <line x1="19" y1="12" x2="22" y2="12"/>
          </svg>
        </div>
        <transition name="fade">
          <span v-if="!isCollapse" class="logo-text">OWLWATCH</span>
        </transition>
      </div>

      <!-- Navigation -->
      <nav class="sidebar-nav">
        <div
          v-for="item in menuItems"
          :key="item.path"
          class="nav-item"
          :class="{ active: route.path === item.path }"
          :style="{ '--accent-color': item.color }"
          @click="handleSelect(item.path)"
        >
          <div class="nav-indicator" :class="{ visible: route.path === item.path }"></div>
          <el-icon class="nav-icon" :size="20">
            <component :is="item.icon" />
          </el-icon>
          <transition name="fade">
            <span v-if="!isCollapse" class="nav-text">{{ item.title }}</span>
          </transition>
          <div class="nav-glow" v-if="route.path === item.path"></div>
        </div>
      </nav>

      <!-- Collapse Toggle -->
      <div class="sidebar-footer">
        <button class="collapse-btn" @click="isCollapse = !isCollapse">
          <el-icon :size="18">
            <component :is="isCollapse ? 'Expand' : 'Fold'" />
          </el-icon>
        </button>
      </div>
    </aside>

    <!-- Main Content -->
    <div class="cyber-main" :style="{ marginLeft: isCollapse ? '72px' : '220px' }">
      <!-- Header -->
      <header class="cyber-header">
        <div class="header-left">
          <div class="status-indicator">
            <span class="status-dot online pulse"></span>
            <span class="status-text">SYSTEM ONLINE</span>
          </div>
        </div>

        <div class="header-center">
          <h1 class="header-title">
            <span class="title-icon">◈</span>
            舆情监控指挥中心
            <span class="title-icon">◈</span>
          </h1>
        </div>

        <div class="header-right">
          <div class="system-time">
            <span class="time-label">SYSTEM TIME</span>
            <span class="time-value data-value">{{ currentTime }}</span>
          </div>
          <div class="user-menu">
            <el-icon class="user-icon"><User /></el-icon>
            <span class="user-name">{{ username }}</span>
            <button class="logout-btn" @click="handleLogout" title="退出登录">
              <el-icon><SwitchButton /></el-icon>
            </button>
          </div>
        </div>
      </header>

      <!-- Page Content -->
      <main class="cyber-content">
        <router-view v-slot="{ Component }">
          <transition name="page" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<style scoped>
/* Layout Container */
.cyber-layout {
  display: flex;
  min-height: 100vh;
  position: relative;
}

/* Ambient Glow Effects */
.ambient-glow {
  position: fixed;
  border-radius: 50%;
  filter: blur(100px);
  pointer-events: none;
  z-index: 0;
}

.glow-1 {
  width: 400px;
  height: 400px;
  background: rgba(0, 240, 255, 0.08);
  top: -100px;
  left: -100px;
  animation: float 20s ease-in-out infinite;
}

.glow-2 {
  width: 300px;
  height: 300px;
  background: rgba(255, 107, 44, 0.05);
  bottom: -50px;
  right: -50px;
  animation: float 15s ease-in-out infinite reverse;
}

@keyframes float {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(30px, 30px); }
}

/* Sidebar */
.cyber-sidebar {
  width: 220px;
  background: linear-gradient(180deg, rgba(10, 14, 23, 0.98) 0%, rgba(15, 21, 32, 0.95) 100%);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  position: fixed;
  top: 0;
  left: 0;
  height: 100vh;
  z-index: 100;
  transition: width var(--transition-normal);
}

.cyber-sidebar.collapsed {
  width: 72px;
}

.cyber-sidebar::before {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  width: 1px;
  background: linear-gradient(180deg, var(--neon-cyan), transparent 50%, var(--neon-orange));
  opacity: 0.3;
}

/* Logo */
.sidebar-logo {
  height: 70px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 0 16px;
  border-bottom: 1px solid var(--border-color);
  position: relative;
}

.sidebar-logo::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 20%;
  right: 20%;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--neon-cyan), transparent);
}

.logo-icon {
  width: 36px;
  height: 36px;
  color: var(--neon-cyan);
  filter: drop-shadow(0 0 8px var(--neon-cyan));
  flex-shrink: 0;
}

.logo-icon svg {
  width: 100%;
  height: 100%;
}

.logo-text {
  font-family: var(--font-display);
  font-size: 1rem;
  font-weight: 700;
  letter-spacing: 0.2em;
  color: var(--neon-cyan);
  text-shadow: 0 0 15px var(--neon-cyan);
  white-space: nowrap;
}

/* Navigation */
.sidebar-nav {
  flex: 1;
  padding: 16px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border-radius: var(--radius-md);
  cursor: pointer;
  position: relative;
  transition: all var(--transition-normal);
  border: 1px solid transparent;
}

.nav-item:hover {
  background: rgba(0, 240, 255, 0.05);
  border-color: rgba(0, 240, 255, 0.2);
}

.nav-item.active {
  background: rgba(0, 240, 255, 0.1);
  border-color: var(--accent-color);
}

.nav-indicator {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 0;
  background: var(--accent-color);
  border-radius: 0 2px 2px 0;
  transition: height var(--transition-normal);
  box-shadow: 0 0 10px var(--accent-color);
}

.nav-indicator.visible {
  height: 60%;
}

.nav-icon {
  color: var(--text-secondary);
  transition: all var(--transition-normal);
  flex-shrink: 0;
}

.nav-item:hover .nav-icon,
.nav-item.active .nav-icon {
  color: var(--accent-color);
  filter: drop-shadow(0 0 6px var(--accent-color));
}

.nav-text {
  font-family: var(--font-display);
  font-size: 0.75rem;
  font-weight: 500;
  letter-spacing: 0.1em;
  color: var(--text-secondary);
  white-space: nowrap;
  transition: color var(--transition-normal);
}

.nav-item:hover .nav-text,
.nav-item.active .nav-text {
  color: var(--text-primary);
}

.nav-glow {
  position: absolute;
  inset: 0;
  background: radial-gradient(ellipse at center, var(--accent-color), transparent 70%);
  opacity: 0.1;
  pointer-events: none;
}

/* Sidebar Footer */
.sidebar-footer {
  padding: 16px;
  border-top: 1px solid var(--border-color);
}

.collapse-btn {
  width: 100%;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-normal);
}

.collapse-btn:hover {
  border-color: var(--neon-cyan);
  color: var(--neon-cyan);
  box-shadow: 0 0 15px rgba(0, 240, 255, 0.2);
}

/* Main Area */
.cyber-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  position: relative;
  z-index: 1;
  transition: margin-left var(--transition-normal);
}

/* Header */
.cyber-header {
  height: 70px;
  background: rgba(10, 14, 23, 0.9);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  position: relative;
  backdrop-filter: blur(10px);
}

.cyber-header::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--neon-cyan), var(--neon-orange), transparent);
  opacity: 0.5;
}

.header-left, .header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-center {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
}

/* Status Indicator */
.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: rgba(0, 255, 136, 0.1);
  border: 1px solid rgba(0, 255, 136, 0.3);
  border-radius: 20px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--neon-green);
  box-shadow: 0 0 10px var(--neon-green);
}

.status-dot.pulse {
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(0.9); }
}

.status-text {
  font-family: var(--font-display);
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.15em;
  color: var(--neon-green);
}

/* Header Title */
.header-title {
  font-family: var(--font-display);
  font-size: 1.1rem;
  font-weight: 600;
  letter-spacing: 0.2em;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 16px;
}

.title-icon {
  color: var(--neon-cyan);
  font-size: 0.8rem;
}

/* System Time */
.system-time {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
}

.time-label {
  font-family: var(--font-display);
  font-size: 0.6rem;
  font-weight: 500;
  letter-spacing: 0.2em;
  color: var(--text-muted);
}

.time-value {
  font-family: var(--font-mono);
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--neon-cyan);
  text-shadow: 0 0 10px var(--neon-cyan);
}

/* Content Area */
.cyber-content {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
  position: relative;
}

/* Transitions */
.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--transition-normal);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.page-enter-active,
.page-leave-active {
  transition: all 0.3s ease;
}

.page-enter-from {
  opacity: 0;
  transform: translateY(20px);
}

.page-leave-to {
  opacity: 0;
  transform: translateY(-20px);
}

/* User Menu */
.user-menu {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: rgba(0, 240, 255, 0.05);
  border: 1px solid rgba(0, 240, 255, 0.2);
  border-radius: 20px;
}

.user-icon {
  color: var(--neon-cyan);
  font-size: 16px;
}

.user-name {
  font-family: var(--font-display);
  font-size: 0.75rem;
  color: var(--text-primary);
  letter-spacing: 0.05em;
}

.logout-btn {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
  border-radius: 4px;
}

.logout-btn:hover {
  color: var(--neon-orange);
  background: rgba(255, 107, 44, 0.1);
}
</style>
