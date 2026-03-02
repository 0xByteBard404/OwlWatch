<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

const isCollapse = ref(false)

const menuItems = [
  { path: '/dashboard', icon: 'DataLine', title: '仪表盘' },
  { path: '/keywords', icon: 'Key', title: '监控主体' },
  { path: '/negative-keywords', icon: 'Warning', title: '负面关键词' },
  { path: '/articles', icon: 'Document', title: '文章列表' },
  { path: '/alerts', icon: 'Bell', title: '预警中心' },
]

const handleSelect = (path: string) => {
  router.push(path)
}
</script>

<template>
  <el-container class="layout-container">
    <!-- 侧边栏 -->
    <el-aside :width="isCollapse ? '64px' : '220px'" class="aside">
      <div class="logo">
        <el-icon :size="24"><View /></el-icon>
        <span v-show="!isCollapse" class="logo-text">OwlWatch</span>
      </div>
      <el-menu
        :default-active="route.path"
        :collapse="isCollapse"
        class="el-menu-vertical"
        @select="handleSelect"
      >
        <el-menu-item v-for="item in menuItems" :key="item.path" :index="item.path">
          <el-icon><component :is="item.icon" /></el-icon>
          <template #title>{{ item.title }}</template>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- 主内容区 -->
    <el-container>
      <el-header class="header">
        <div class="header-left">
          <el-icon
            class="collapse-btn"
            :size="20"
            @click="isCollapse = !isCollapse"
          >
            <component :is="isCollapse ? 'Expand' : 'Fold'" />
          </el-icon>
        </div>
        <div class="header-right">
          <span class="title">OwlWatch 舆情监控系统</span>
        </div>
      </el-header>

      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.layout-container {
  height: 100vh;
}

.aside {
  background: linear-gradient(180deg, #1d1e1f 0%, #2d2e2f 100%);
  transition: width 0.3s;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #409eff;
  border-bottom: 1px solid #3d3e3f;
}

.logo-text {
  font-size: 18px;
  font-weight: bold;
}

.el-menu-vertical {
  border-right: none;
  background: transparent;
}

.el-menu-vertical .el-menu-item {
  color: #a0a0a0;
}

.el-menu-vertical .el-menu-item:hover,
.el-menu-vertical .el-menu-item.is-active {
  background: #3d3e3f;
  color: #409eff;
}

.header {
  background: #fff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
}

.header-left {
  display: flex;
  align-items: center;
}

.collapse-btn {
  cursor: pointer;
  color: #606266;
}

.collapse-btn:hover {
  color: #409eff;
}

.header-right .title {
  font-size: 16px;
  color: #303133;
}

.main {
  background: #f5f7fa;
  padding: 20px;
}
</style>
