<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, TrendCharts, Document, ChatDotRound, Warning } from '@element-plus/icons-vue'
import { keywordsApi, articlesApi, type Article, type Keyword } from '@/api'

const route = useRoute()
const router = useRouter()

const keyword = ref<Keyword | null>(null)
const positiveArticles = ref<Article[]>([])
const negativeArticles = ref<Article[]>([])
const neutralArticles = ref<Article[]>([])
const loading = ref(true)

const stats = computed(() => ({
  positive: positiveArticles.value.length,
  negative: negativeArticles.value.length,
  neutral: neutralArticles.value.length,
  total: positiveArticles.value.length + negativeArticles.value.length + neutralArticles.value.length,
}))

const positiveRatio = computed(() => {
  if (stats.value.total === 0) return 0
  return Math.round((stats.value.positive / stats.value.total) * 100)
})

const fetchData = async () => {
  const keywordId = route.params.id as string
  if (!keywordId) return

  loading.value = true
  try {
    keyword.value = await keywordsApi.get(keywordId)

    const [positiveRes, negativeRes, neutralRes] = await Promise.all([
      articlesApi.list({ keyword_id: keywordId, sentiment: 'positive', size: 50 }),
      articlesApi.list({ keyword_id: keywordId, sentiment: 'negative', size: 50 }),
      articlesApi.list({ keyword_id: keywordId, sentiment: 'neutral', size: 50 }),
    ])

    positiveArticles.value = positiveRes.items
    negativeArticles.value = negativeRes.items
    neutralArticles.value = neutralRes.items
  } catch (error) {
    console.error('Failed to fetch data:', error)
    ElMessage.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

const goBack = () => {
  router.push('/keywords')
}

const formatTime = (dateStr: string | null | undefined): string => {
  if (!dateStr) return '-'

  const date = new Date(dateStr)
  const now = new Date()

  const hours = date.getHours().toString().padStart(2, '0')
  const minutes = date.getMinutes().toString().padStart(2, '0')
  const timeStr = `${hours}:${minutes}`

  const month = (date.getMonth() + 1).toString().padStart(2, '0')
  const day = date.getDate().toString().padStart(2, '0')

  // 判断是否今天
  const isToday =
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate()

  if (isToday) {
    return `今天 ${timeStr}`
  }

  // 判断是否昨天
  const yesterday = new Date(now)
  yesterday.setDate(yesterday.getDate() - 1)
  const isYesterday =
    date.getFullYear() === yesterday.getFullYear() &&
    date.getMonth() === yesterday.getMonth() &&
    date.getDate() === yesterday.getDate()

  if (isYesterday) {
    return `昨天 ${timeStr}`
  }

  // 同一年：显示 MM-DD HH:mm
  if (date.getFullYear() === now.getFullYear()) {
    return `${month}-${day} ${timeStr}`
  }

  // 不同年：显示 YYYY-MM-DD HH:mm
  return `${date.getFullYear()}-${month}-${day} ${timeStr}`
}

// 清理 HTML 内容 - 移除乱码字符和限制图片
const sanitizeHtml = (html: string | null | undefined, maxLength?: number, removeImages = false): string => {
  if (!html) return ''

  // 移除 Unicode 私有使用区字符 (乱码)
  let cleaned = html.replace(/[\uE000-\uF8FF\uDB80-\uDBFF]/g, '')

  // 如果需要移除图片
  if (removeImages) {
    cleaned = cleaned.replace(/<img[^>]*>/gi, '')
  }

  // 如果指定了最大长度，截取内容
  if (maxLength && cleaned.length > maxLength) {
    cleaned = cleaned.slice(0, maxLength) + '...'
  }

  return cleaned
}

const openUrl = (url: string) => {
  window.open(url, '_blank')
}

const getScoreStyle = (score: number | null) => {
  if (score === null) return { width: '0%', backgroundColor: '#8b95a8' }
  const width = Math.abs(score) * 100
  const color = score > 0 ? '#00ff88' : '#ff3366'
  return { width: `${width}%`, backgroundColor: color }
}

onMounted(() => {
  fetchData()
})
</script>

<template>
  <div class="detail-page" v-loading="loading">
    <!-- Header -->
    <header class="page-header">
      <button class="back-btn" @click="goBack">
        <el-icon><ArrowLeft /></el-icon>
        <span>返回列表</span>
      </button>
      <div class="header-actions">
        <button class="action-btn" @click="fetchData">
          <el-icon><TrendCharts /></el-icon>
          <span>刷新数据</span>
        </button>
      </div>
    </header>

    <!-- Hero Section -->
    <section class="hero-section" v-if="keyword">
      <div class="hero-bg">
        <div class="grid-overlay"></div>
        <div class="glow-orb positive"></div>
        <div class="glow-orb negative"></div>
      </div>

      <div class="hero-content">
        <div class="subject-info">
          <div class="subject-badge">
            <span class="badge-icon">◈</span>
            <span class="badge-text">SUBJECT</span>
          </div>
          <h1 class="subject-name">{{ keyword.keyword }}</h1>
          <p class="subject-desc">
            {{ keyword.is_active ? '监控运行中' : '监控已暂停' }} ·
            优先级: {{ keyword.priority === 'high' ? '高' : keyword.priority === 'low' ? '低' : '中' }}
          </p>
        </div>

        <div class="stats-row">
          <div class="stat-card positive" :class="{ dominant: stats.positive > stats.negative }">
            <div class="stat-value">{{ stats.positive }}</div>
            <div class="stat-label">正面舆论</div>
            <div class="stat-bar">
              <div class="bar-fill" :style="{ width: stats.total > 0 ? (stats.positive / stats.total * 100) + '%' : '0%' }"></div>
            </div>
          </div>

          <div class="stat-divider">
            <div class="divider-line"></div>
            <div class="divider-ratio">{{ positiveRatio }}%</div>
            <div class="divider-label">正面占比</div>
          </div>

          <div class="stat-card negative" :class="{ dominant: stats.negative > stats.positive }">
            <div class="stat-value">{{ stats.negative }}</div>
            <div class="stat-label">负面舆论</div>
            <div class="stat-bar">
              <div class="bar-fill" :style="{ width: stats.total > 0 ? (stats.negative / stats.total * 100) + '%' : '0%' }"></div>
            </div>
          </div>

          <div class="stat-card neutral">
            <div class="stat-value">{{ stats.neutral }}</div>
            <div class="stat-label">中性舆论</div>
            <div class="stat-bar">
              <div class="bar-fill" :style="{ width: stats.total > 0 ? (stats.neutral / stats.total * 100) + '%' : '0%' }"></div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Content Section - Three Column Layout -->
    <section class="content-section" v-if="!loading">
      <div class="three-column-layout">
        <!-- Positive Column (Left) -->
        <div class="sentiment-column positive-column">
          <div class="column-header">
            <span class="column-icon">▲</span>
            <h2 class="column-title">正面舆论</h2>
            <span class="column-count">{{ stats.positive }}</span>
          </div>
          <div class="column-content">
            <div v-if="positiveArticles.length === 0" class="empty-state">
              <el-icon :size="36"><Document /></el-icon>
              <p>暂无正面舆论</p>
            </div>
            <article
              v-for="(article, index) in positiveArticles"
              :key="article.id"
              class="article-card positive"
              :style="{ animationDelay: `${index * 0.03}s` }"
              @click="openUrl(article.url)"
            >
              <div class="card-header">
                <span class="source-tag">{{ article.source || '未知' }}</span>
                <span class="time-tag">{{ formatTime(article.publish_time || article.collect_time) }}</span>
              </div>
              <h3 class="card-title">{{ article.title }}</h3>
              <p class="card-content" v-html="sanitizeHtml(article.content, 100, true) || '暂无摘要...'"></p>
              <div class="card-footer">
                <div class="sentiment-indicator">
                  <div class="score-bar">
                    <div class="score-fill" :style="getScoreStyle(article.sentiment_score)"></div>
                  </div>
                  <span class="score-value">{{ article.sentiment_score?.toFixed(2) || 'N/A' }}</span>
                </div>
              </div>
            </article>
          </div>
        </div>

        <!-- Neutral Column (Center) -->
        <div class="sentiment-column neutral-column">
          <div class="column-header">
            <span class="column-icon">●</span>
            <h2 class="column-title">中性舆论</h2>
            <span class="column-count">{{ stats.neutral }}</span>
          </div>
          <div class="column-content">
            <div v-if="neutralArticles.length === 0" class="empty-state">
              <el-icon :size="36"><ChatDotRound /></el-icon>
              <p>暂无中性舆论</p>
            </div>
            <article
              v-for="(article, index) in neutralArticles"
              :key="article.id"
              class="article-card neutral"
              :style="{ animationDelay: `${index * 0.03}s` }"
              @click="openUrl(article.url)"
            >
              <div class="card-header">
                <span class="source-tag">{{ article.source || '未知' }}</span>
                <span class="time-tag">{{ formatTime(article.publish_time || article.collect_time) }}</span>
              </div>
              <h3 class="card-title">{{ article.title }}</h3>
              <p class="card-content" v-html="sanitizeHtml(article.content, 100, true) || '暂无摘要...'"></p>
              <div class="card-footer">
                <div class="sentiment-indicator">
                  <div class="score-bar">
                    <div class="score-fill" :style="getScoreStyle(article.sentiment_score)"></div>
                  </div>
                  <span class="score-value">{{ article.sentiment_score?.toFixed(2) || 'N/A' }}</span>
                </div>
              </div>
            </article>
          </div>
        </div>

        <!-- Negative Column (Right) -->
        <div class="sentiment-column negative-column">
          <div class="column-header">
            <span class="column-icon">▼</span>
            <h2 class="column-title">负面舆论</h2>
            <span class="column-count">{{ stats.negative }}</span>
          </div>
          <div class="column-content">
            <div v-if="negativeArticles.length === 0" class="empty-state">
              <el-icon :size="36"><Warning /></el-icon>
              <p>暂无负面舆论</p>
            </div>
            <article
              v-for="(article, index) in negativeArticles"
              :key="article.id"
              class="article-card negative"
              :style="{ animationDelay: `${index * 0.03}s` }"
              @click="openUrl(article.url)"
            >
              <div class="card-header">
                <span class="source-tag">{{ article.source || '未知' }}</span>
                <span class="time-tag">{{ formatTime(article.publish_time || article.collect_time) }}</span>
              </div>
              <h3 class="card-title">{{ article.title }}</h3>
              <p class="card-content" v-html="sanitizeHtml(article.content, 100, true) || '暂无摘要...'"></p>
              <div class="card-footer">
                <div class="sentiment-indicator">
                  <div class="score-bar">
                    <div class="score-fill" :style="getScoreStyle(article.sentiment_score)"></div>
                  </div>
                  <span class="score-value">{{ article.sentiment_score?.toFixed(2) || 'N/A' }}</span>
                </div>
              </div>
            </article>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.detail-page {
  max-width: 1400px;
  margin: 0 auto;
  min-height: 100vh;
}

/* Header */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 16px 0;
  margin-bottom: 24px;
}

.back-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  font-family: var(--font-display);
  font-size: 0.8rem;
  letter-spacing: 0.05em;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.3s ease;
}

.back-btn:hover {
  border-color: var(--neon-cyan);
  color: var(--neon-cyan);
  box-shadow: 0 0 15px rgba(0, 240, 255, 0.2);
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  font-family: var(--font-display);
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.3s ease;
  color: var(--text-secondary);
}

.action-btn:hover {
  border-color: var(--text-secondary);
  color: var(--text-primary);
}

/* Hero Section */
.hero-section {
  position: relative;
  padding: 48px;
  background: linear-gradient(135deg, rgba(0, 240, 255, 0.05), rgba(255, 51, 102, 0.05));
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  overflow: hidden;
  margin-bottom: 32px;
}

.hero-bg {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.grid-overlay {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(0, 240, 255, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 240, 255, 0.03) 1px, transparent 1px);
  background-size: 40px 40px;
}

.glow-orb {
  position: absolute;
  width: 300px;
  height: 300px;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.3;
}

.glow-orb.positive {
  top: -100px;
  left: -100px;
  background: var(--neon-green);
}

.glow-orb.negative {
  bottom: -100px;
  right: -100px;
  background: var(--neon-red);
}

.hero-content {
  position: relative;
  z-index: 1;
}

.subject-info {
  margin-bottom: 40px;
}

.subject-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid var(--neon-orange);
  border-radius: 20px;
  margin-bottom: 16px;
}

.badge-icon {
  color: var(--neon-orange);
  font-size: 0.9rem;
}

.badge-text {
  font-family: var(--font-display);
  font-size: 0.65rem;
  letter-spacing: 0.15em;
  color: var(--neon-orange);
}

.subject-name {
  font-family: var(--font-display);
  font-size: 2.5rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 8px 0;
  letter-spacing: 0.02em;
}

.subject-desc {
  font-size: 0.9rem;
  color: var(--text-muted);
  margin: 0;
}

/* Stats Row */
.stats-row {
  display: grid;
  grid-template-columns: 1fr auto 1fr 1fr;
  gap: 24px;
  align-items: center;
}

.stat-card {
  padding: 24px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  text-align: center;
  transition: all 0.3s ease;
}

.stat-card.positive {
  border-color: rgba(0, 255, 136, 0.3);
}

.stat-card.positive.dominant {
  background: rgba(0, 255, 136, 0.1);
  box-shadow: 0 0 30px rgba(0, 255, 136, 0.2);
}

.stat-card.negative {
  border-color: rgba(255, 51, 102, 0.3);
}

.stat-card.negative.dominant {
  background: rgba(255, 51, 102, 0.1);
  box-shadow: 0 0 30px rgba(255, 51, 102, 0.2);
}

.stat-card.neutral {
  border-color: rgba(139, 149, 168, 0.3);
}

.stat-value {
  font-family: var(--font-display);
  font-size: 2.5rem;
  font-weight: 700;
  line-height: 1;
  margin-bottom: 8px;
}

.stat-card.positive .stat-value {
  color: var(--neon-green);
}

.stat-card.negative .stat-value {
  color: var(--neon-red);
}

.stat-label {
  font-family: var(--font-display);
  font-size: 0.7rem;
  letter-spacing: 0.1em;
  color: var(--text-muted);
  text-transform: uppercase;
  margin-bottom: 12px;
}

.stat-bar {
  height: 4px;
  background: var(--bg-secondary);
  border-radius: 2px;
  overflow: hidden;
  margin-top: 12px;
}

.stat-card.positive .bar-fill {
  height: 100%;
  background: var(--neon-green);
  border-radius: 2px;
  transition: width 0.6s ease;
}

.stat-card.negative .bar-fill {
  height: 100%;
  background: var(--neon-red);
  border-radius: 2px;
  transition: width 0.6s ease;
}

.stat-card.neutral .bar-fill {
  height: 100%;
  background: var(--text-muted);
  border-radius: 2px;
  transition: width 0.6s ease;
}

.stat-divider {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0 16px;
}

.divider-line {
  width: 1px;
  height: 40px;
  background: linear-gradient(to bottom, transparent, var(--border-color), transparent);
  margin-bottom: 12px;
}

.divider-ratio {
  font-family: var(--font-display);
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--neon-green);
}

.divider-label {
  font-size: 0.65rem;
  color: var(--text-muted);
  letter-spacing: 0.1em;
}

/* Content Section */
.content-section {
  padding: 24px 0;
}

/* Three Column Layout */
.three-column-layout {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
}

.sentiment-column {
  display: flex;
  flex-direction: column;
  min-height: 500px;
}

.column-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: var(--radius-md) var(--radius-md) 0 0;
  border: 1px solid var(--border-color);
  border-bottom: none;
}

.positive-column .column-header {
  border-color: rgba(0, 255, 136, 0.3);
  background: rgba(0, 255, 136, 0.05);
}

.neutral-column .column-header {
  border-color: rgba(139, 149, 168, 0.3);
  background: rgba(139, 149, 168, 0.05);
}

.negative-column .column-header {
  border-color: rgba(255, 51, 102, 0.3);
  background: rgba(255, 51, 102, 0.05);
}

.column-icon {
  font-size: 1rem;
}

.positive-column .column-icon {
  color: var(--neon-green);
}

.neutral-column .column-icon {
  color: var(--text-muted);
}

.negative-column .column-icon {
  color: var(--neon-red);
}

.column-title {
  flex: 1;
  margin: 0;
  font-family: var(--font-display);
  font-size: 0.9rem;
  font-weight: 600;
  letter-spacing: 0.05em;
}

.positive-column .column-title {
  color: var(--neon-green);
}

.neutral-column .column-title {
  color: var(--text-primary);
}

.negative-column .column-title {
  color: var(--neon-red);
}

.column-count {
  padding: 4px 12px;
  border-radius: 12px;
  font-family: var(--font-mono);
  font-size: 0.8rem;
  font-weight: 600;
}

.positive-column .column-count {
  background: rgba(0, 255, 136, 0.2);
  color: var(--neon-green);
}

.neutral-column .column-count {
  background: rgba(139, 149, 168, 0.2);
  color: var(--text-muted);
}

.negative-column .column-count {
  background: rgba(255, 51, 102, 0.2);
  color: var(--neon-red);
}

.column-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  background: rgba(0, 0, 0, 0.15);
  border: 1px solid var(--border-color);
  border-top: none;
  border-radius: 0 0 var(--radius-md) var(--radius-md);
  max-height: 600px;
  overflow-y: auto;
}

.column-content::-webkit-scrollbar {
  width: 4px;
}

.column-content::-webkit-scrollbar-track {
  background: transparent;
}

.column-content::-webkit-scrollbar-thumb {
  background: var(--border-color);
  border-radius: 2px;
}

/* Articles List */
.articles-container {
  min-height: 400px;
}

.articles-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

.article-card {
  padding: 16px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.3s ease;
  animation: cardFadeIn 0.4s ease forwards;
  opacity: 0;
  transform: translateY(10px);
}

@keyframes cardFadeIn {
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.article-card:hover {
  transform: translateY(-4px);
}

.article-card.positive:hover {
  border-color: var(--neon-green);
  box-shadow: 0 8px 32px rgba(0, 255, 136, 0.15);
}

.article-card.negative:hover {
  border-color: var(--neon-red);
  box-shadow: 0 8px 32px rgba(255, 51, 102, 0.15);
}

.article-card.neutral:hover {
  border-color: var(--text-secondary);
  box-shadow: 0 8px 32px rgba(139, 149, 168, 0.15);
}

.card-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
}

.source-tag {
  padding: 4px 10px;
  border-radius: 4px;
  font-family: var(--font-mono);
  font-size: 0.65rem;
  color: var(--text-muted);
}

.article-card.positive .source-tag {
  color: var(--neon-green);
  background: rgba(0, 255, 136, 0.1);
}

.article-card.negative .source-tag {
  color: var(--neon-red);
  background: rgba(255, 51, 102, 0.1);
}

.article-card.neutral .source-tag {
  color: var(--text-muted);
  background: rgba(139, 149, 168, 0.1);
}

.time-tag {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: var(--text-muted);
}

.card-title {
  font-family: var(--font-display);
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 12px 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-content {
  font-size: 0.85rem;
  color: var(--text-secondary);
  line-height: 1.6;
  margin: 0 0 16px 0;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-footer {
  display: flex;
  justify-content: flex-end;
}

.sentiment-indicator {
  display: flex;
  align-items: center;
  gap: 10px;
}

.score-bar {
  width: 60px;
  height: 4px;
  background: var(--bg-tertiary);
  border-radius: 2px;
  overflow: hidden;
}

.score-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.3s ease;
}

.score-value {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--text-muted);
}

/* Empty State */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: var(--text-muted);
}

.empty-state p {
  margin-top: 12px;
  font-size: 0.85rem;
}

/* Responsive */
@media (max-width: 1200px) {
  .three-column-layout {
    gap: 16px;
  }
  .column-content {
    max-height: 500px;
  }
}

@media (max-width: 900px) {
  .stats-row {
    grid-template-columns: 1fr 1fr 1fr;
    gap: 16px;
    align-items: center;
  }
  .stat-divider {
    grid-column: 1 / -1;
    flex-direction: row;
    gap: 12px;
    padding: 16px 0;
  }
  .three-column-layout {
    grid-template-columns: 1fr 1fr;
    grid-template-rows: auto auto;
  }
  .negative-column {
    grid-column: 1 / -1;
  }
  .column-content {
    max-height: 400px;
  }
}

@media (max-width: 600px) {
  .hero-section {
    padding: 24px;
  }
  .subject-name {
    font-size: 1.8rem;
  }
  .stat-value {
    font-size: 2rem;
  }
  .three-column-layout {
    grid-template-columns: 1fr;
  }
  .negative-column {
    grid-column: 1;
  }
  .column-content {
    max-height: 350px;
  }
}
</style>
