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

// 剥离 HTML 标签，只保留纯文本
const stripHtml = (html: string | null | undefined): string => {
  if (!html) return ''
  return html
    .replace(/<br\s*\/?>/gi, ' ')
    .replace(/<\/p>/gi, ' ')
    .replace(/<[^>]+>/g, '')
    .replace(/\s+/g, ' ')
    .trim()
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

    <!-- Compact Hero Section - Horizontal Layout -->
    <section class="hero-compact" v-if="keyword">
      <div class="hero-left">
        <div class="subject-badge">
          <span class="badge-icon">◈</span>
          <span class="badge-text">SUBJECT</span>
        </div>
        <h1 class="subject-name">{{ keyword.keyword }}</h1>
        <span class="status-dot" :class="{ active: keyword.is_active }"></span>
        <span class="subject-status">{{ keyword.is_active ? '运行中' : '已暂停' }}</span>
      </div>

      <div class="hero-divider"></div>

      <div class="hero-stats">
        <div class="stat-item positive">
          <span class="stat-icon">▲</span>
          <span class="stat-num">{{ stats.positive }}</span>
          <span class="stat-label">正面</span>
        </div>
        <div class="stat-item negative">
          <span class="stat-icon">▼</span>
          <span class="stat-num">{{ stats.negative }}</span>
          <span class="stat-label">负面</span>
        </div>
        <div class="stat-item neutral">
          <span class="stat-icon">●</span>
          <span class="stat-num">{{ stats.neutral }}</span>
          <span class="stat-label">中性</span>
        </div>
      </div>

      <div class="hero-divider"></div>

      <div class="hero-ratio">
        <div class="ratio-ring" :style="{ '--ratio': positiveRatio }">
          <svg viewBox="0 0 36 36">
            <path class="ring-bg" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"/>
            <path class="ring-fill" :stroke-dasharray="`${positiveRatio}, 100`" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"/>
          </svg>
          <span class="ratio-value">{{ positiveRatio }}%</span>
        </div>
        <span class="ratio-label">正面占比</span>
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
              <h3 class="card-title">{{ stripHtml(article.title) }}</h3>
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
              <h3 class="card-title">{{ stripHtml(article.title) }}</h3>
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
              <h3 class="card-title">{{ stripHtml(article.title) }}</h3>
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

/* Compact Hero Section - Horizontal Layout */
.hero-compact {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 20px 28px;
  background: rgba(0, 0, 0, 0.25);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  margin-bottom: 24px;
}

.hero-left {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-shrink: 0;
}

.subject-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: rgba(0, 0, 0, 0.4);
  border: 1px solid var(--neon-orange);
  border-radius: 12px;
}

.badge-icon {
  color: var(--neon-orange);
  font-size: 0.75rem;
}

.badge-text {
  font-family: var(--font-display);
  font-size: 0.6rem;
  letter-spacing: 0.12em;
  color: var(--neon-orange);
}

.subject-name {
  font-family: var(--font-display);
  font-size: 1.4rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
  letter-spacing: 0.02em;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--text-muted);
}

.status-dot.active {
  background: var(--neon-green);
  box-shadow: 0 0 8px var(--neon-green);
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.subject-status {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.hero-divider {
  width: 1px;
  height: 40px;
  background: linear-gradient(to bottom, transparent, var(--border-color), transparent);
  flex-shrink: 0;
}

.hero-stats {
  display: flex;
  align-items: center;
  gap: 32px;
  flex: 1;
  justify-content: center;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.stat-icon {
  font-size: 0.7rem;
}

.stat-item.positive .stat-icon {
  color: var(--neon-green);
}

.stat-item.negative .stat-icon {
  color: var(--neon-red);
}

.stat-item.neutral .stat-icon {
  color: var(--text-muted);
}

.stat-num {
  font-family: var(--font-display);
  font-size: 1.5rem;
  font-weight: 700;
  min-width: 32px;
}

.stat-item.positive .stat-num {
  color: var(--neon-green);
}

.stat-item.negative .stat-num {
  color: var(--neon-red);
}

.stat-item.neutral .stat-num {
  color: var(--text-muted);
}

.stat-item .stat-label {
  font-size: 0.7rem;
  color: var(--text-muted);
  letter-spacing: 0.05em;
  margin: 0;
}

.hero-ratio {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.ratio-ring {
  position: relative;
  width: 56px;
  height: 56px;
}

.ratio-ring svg {
  transform: rotate(-90deg);
  width: 100%;
  height: 100%;
}

.ring-bg {
  fill: none;
  stroke: var(--bg-tertiary);
  stroke-width: 3;
}

.ring-fill {
  fill: none;
  stroke: var(--neon-green);
  stroke-width: 3;
  stroke-linecap: round;
  transition: stroke-dasharray 0.6s ease;
}

.ratio-value {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-family: var(--font-display);
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--neon-green);
}

.ratio-label {
  font-size: 0.6rem;
  color: var(--text-muted);
  letter-spacing: 0.1em;
  text-transform: uppercase;
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
  background: rgba(0, 0, 0, 0.25);
  border: 1px solid var(--border-color);
  border-top: none;
  border-radius: 0 0 var(--radius-md) var(--radius-md);
  max-height: calc(100vh - 280px);
  min-height: 400px;
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
  .hero-compact {
    flex-wrap: wrap;
    gap: 16px;
    padding: 16px 20px;
  }
  .hero-left {
    width: 100%;
    justify-content: flex-start;
  }
  .hero-divider {
    display: none;
  }
  .hero-stats {
    width: 100%;
    justify-content: flex-start;
    gap: 24px;
  }
  .hero-ratio {
    flex-direction: row;
    width: 100%;
    justify-content: flex-start;
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
  .hero-compact {
    padding: 14px 16px;
  }
  .subject-name {
    font-size: 1.1rem;
  }
  .stat-num {
    font-size: 1.2rem;
  }
  .ratio-ring {
    width: 44px;
    height: 44px;
  }
  .ratio-value {
    font-size: 0.75rem;
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
