<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login } from '@/api/auth'

const router = useRouter()

const form = ref({
  username: '',
  password: '',
})

const loading = ref(false)
const showPassword = ref(false)

async function handleLogin() {
  if (!form.value.username || !form.value.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }

  loading.value = true

  try {
    const response = await login({
      username: form.value.username,
      password: form.value.password,
    })

    // 存储 token 和用户名
    localStorage.setItem('token', response.access_token)
    localStorage.setItem('username', form.value.username)

    ElMessage.success('登录成功')

    // 跳转到首页
    router.push('/dashboard')
  } catch (error: any) {
    ElMessage.error(error.message || '登录失败，请检查用户名和密码')
  } finally {
    loading.value = false
  }
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter') {
    handleLogin()
  }
}
</script>

<template>
  <div class="login-container">
    <!-- 背景效果 -->
    <div class="bg-grid"></div>
    <div class="glow-orb orb-1"></div>
    <div class="glow-orb orb-2"></div>

    <!-- 登录卡片 -->
    <div class="login-card">
      <!-- Logo -->
      <div class="login-header">
        <div class="logo">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10" />
            <circle cx="12" cy="12" r="3" />
            <line x1="12" y1="2" x2="12" y2="5" />
            <line x1="12" y1="19" x2="12" y2="22" />
            <line x1="2" y1="12" x2="5" y2="12" />
            <line x1="19" y1="12" x2="22" y2="12" />
          </svg>
        </div>
        <h1 class="title">OWLWATCH</h1>
        <p class="subtitle">舆情监控指挥中心</p>
      </div>

      <!-- 表单 -->
      <form class="login-form" @submit.prevent="handleLogin" @keydown="handleKeydown">
        <div class="form-group">
          <label class="form-label">用户名</label>
          <div class="input-wrapper">
            <el-icon class="input-icon"><User /></el-icon>
            <input
              v-model="form.username"
              type="text"
              class="form-input"
              placeholder="请输入用户名"
              autocomplete="username"
            />
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">密码</label>
          <div class="input-wrapper">
            <el-icon class="input-icon"><Lock /></el-icon>
            <input
              v-model="form.password"
              :type="showPassword ? 'text' : 'password'"
              class="form-input"
              placeholder="请输入密码"
              autocomplete="current-password"
            />
            <button
              type="button"
              class="toggle-password"
              @click="showPassword = !showPassword"
            >
              <el-icon>
                <View v-if="!showPassword" />
                <Hide v-else />
              </el-icon>
            </button>
          </div>
        </div>

        <button type="submit" class="login-btn" :disabled="loading">
          <span v-if="!loading">登录系统</span>
          <span v-else class="loading-text">
            <el-icon class="is-loading"><Loading /></el-icon>
            验证中...
          </span>
        </button>
      </form>

      <!-- 底部信息 -->
      <div class="login-footer">
        <p>OwlWatch 舆情监控系统 v1.0</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #0a0e17 0%, #151d2e 50%, #0a0e17 100%);
  position: relative;
  overflow: hidden;
}

/* 背景网格 */
.bg-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(0, 240, 255, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 240, 255, 0.03) 1px, transparent 1px);
  background-size: 50px 50px;
  pointer-events: none;
}

/* 发光球体 */
.glow-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  pointer-events: none;
  animation: float 20s ease-in-out infinite;
}

.orb-1 {
  width: 400px;
  height: 400px;
  background: rgba(0, 240, 255, 0.1);
  top: -100px;
  right: -100px;
}

.orb-2 {
  width: 300px;
  height: 300px;
  background: rgba(255, 107, 44, 0.08);
  bottom: -50px;
  left: -50px;
  animation-delay: -10s;
}

@keyframes float {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(30px, 30px); }
}

/* 登录卡片 */
.login-card {
  width: 100%;
  max-width: 420px;
  padding: 48px 40px;
  background: rgba(15, 21, 32, 0.9);
  border: 1px solid rgba(0, 240, 255, 0.2);
  border-radius: 16px;
  backdrop-filter: blur(20px);
  position: relative;
  z-index: 1;
}

.login-card::before {
  content: '';
  position: absolute;
  inset: -1px;
  border-radius: 16px;
  padding: 1px;
  background: linear-gradient(135deg, rgba(0, 240, 255, 0.3), transparent 50%, rgba(255, 107, 44, 0.2));
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  pointer-events: none;
}

/* 头部 */
.login-header {
  text-align: center;
  margin-bottom: 40px;
}

.logo {
  width: 64px;
  height: 64px;
  margin: 0 auto 16px;
  color: var(--neon-cyan, #00f0ff);
  filter: drop-shadow(0 0 20px rgba(0, 240, 255, 0.5));
}

.logo svg {
  width: 100%;
  height: 100%;
}

.title {
  font-family: var(--font-display, 'Orbitron', sans-serif);
  font-size: 1.75rem;
  font-weight: 700;
  letter-spacing: 0.3em;
  color: var(--neon-cyan, #00f0ff);
  text-shadow: 0 0 30px rgba(0, 240, 255, 0.5);
  margin: 0 0 8px;
}

.subtitle {
  font-size: 0.875rem;
  color: var(--text-secondary, #8b9ab8);
  margin: 0;
  letter-spacing: 0.1em;
}

/* 表单 */
.login-form {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-label {
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--text-secondary, #8b9ab8);
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.input-icon {
  position: absolute;
  left: 16px;
  color: var(--text-muted, #4a5568);
  font-size: 18px;
  pointer-events: none;
}

.form-input {
  width: 100%;
  padding: 14px 16px 14px 48px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(0, 240, 255, 0.15);
  border-radius: 8px;
  color: var(--text-primary, #e2e8f0);
  font-size: 1rem;
  transition: all 0.3s ease;
}

.form-input::placeholder {
  color: var(--text-muted, #4a5568);
}

.form-input:focus {
  outline: none;
  border-color: var(--neon-cyan, #00f0ff);
  box-shadow: 0 0 0 3px rgba(0, 240, 255, 0.1);
}

.toggle-password {
  position: absolute;
  right: 12px;
  background: none;
  border: none;
  color: var(--text-muted, #4a5568);
  cursor: pointer;
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: color 0.3s ease;
}

.toggle-password:hover {
  color: var(--neon-cyan, #00f0ff);
}

/* 登录按钮 */
.login-btn {
  width: 100%;
  padding: 16px;
  margin-top: 8px;
  background: linear-gradient(135deg, var(--neon-cyan, #00f0ff), rgba(0, 200, 255, 0.8));
  border: none;
  border-radius: 8px;
  color: #0a0e17;
  font-family: var(--font-display, 'Orbitron', sans-serif);
  font-size: 0.875rem;
  font-weight: 600;
  letter-spacing: 0.15em;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.login-btn::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  transform: translateX(-100%);
  transition: transform 0.5s ease;
}

.login-btn:hover:not(:disabled)::before {
  transform: translateX(100%);
}

.login-btn:hover:not(:disabled) {
  box-shadow: 0 0 30px rgba(0, 240, 255, 0.4);
  transform: translateY(-2px);
}

.login-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.loading-text {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.is-loading {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* 底部 */
.login-footer {
  margin-top: 32px;
  text-align: center;
}

.login-footer p {
  font-size: 0.75rem;
  color: var(--text-muted, #4a5568);
  margin: 0;
}
</style>
