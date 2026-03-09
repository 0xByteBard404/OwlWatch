<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { articlesApi, keywordsApi, type Article, type ArticleListParams, type Keyword } from '@/api'

const route = useRoute()

// 数据
const articles = ref<Article[]>([])
const keywords = ref<Keyword[]>([])
const sources = ref<string[]>([])
const total = ref(0)
const loading = ref(false)

// 分页
const page = ref(1)
const size = ref(20)

// 筛选条件
const filters = ref<ArticleListParams>({
  keyword_id: '',
  sentiment: '',
  source: '',
})

// 详情对话框
const detailVisible = ref(false)
const currentArticle = ref<Article | null>(null)

// 情感选项
const sentimentOptions = [
  { label: '正面', value: 'positive', color: '#00ff88' },
  { label: '中性', value: 'neutral', color: '#8b95a8' },
  { label: '负面', value: 'negative', color: '#ff3366' },
]

// 获取来源列表（从 API）
const sourceOptions = computed(() => {
  return sources.value.map((s) => ({ label: s, value: s }))
})

// 获取来源列表
const fetchSources = async () => {
  try {
    sources.value = await articlesApi.getSourcesList()
  } catch (error) {
    console.error('Failed to fetch sources:', error)
  }
}

// 获取关键词列表
const fetchKeywords = async () => {
  try {
    keywords.value = await keywordsApi.list()
  } catch (error) {
    console.error('Failed to fetch keywords:', error)
  }
}

// 获取文章列表
const fetchData = async () => {
  loading.value = true
  try {
    const params: ArticleListParams = {
      page: page.value,
      size: size.value,
      ...filters.value,
    }
    // 移除空值
    Object.keys(params).forEach((key) => {
      if (!params[key as keyof ArticleListParams]) {
        delete params[key as keyof ArticleListParams]
      }
    })

    const result = await articlesApi.list(params)
    articles.value = result.items
    total.value = result.total
  } catch (error) {
    console.error('Failed to fetch articles:', error)
  } finally {
    loading.value = false
  }
}

// 搜索
const handleSearch = () => {
  page.value = 1
  fetchData()
}

// 重置
const handleReset = () => {
  filters.value = {
    keyword_id: '',
    sentiment: '',
    source: '',
  }
  page.value = 1
  fetchData()
}

// 分页变化
const handlePageChange = (val: number) => {
  page.value = val
  fetchData()
}

const handleSizeChange = (val: number) => {
  size.value = val
  page.value = 1
  fetchData()
}

// 查看详情
const handleDetail = (row: Article) => {
  currentArticle.value = row
  detailVisible.value = true
}

// 获取情感配置
const getSentimentConfig = (label: string | null) => {
  return sentimentOptions.find(s => s.value === label) || { label: '未分析', color: '#4a5568' }
}

// 获取情感分数颜色
const getScoreColor = (score: number | null) => {
  if (score === null) return '#4a5568'
  if (score > 0.3) return '#00ff88'
  if (score < -0.3) return '#ff3366'
  return '#8b95a8'
}

// 获取分数条宽度
const getScoreWidth = (score: number | null) => {
  if (score === null) return 50
  return 50 + score * 50
}

// 获取关键词名称
const getKeywordName = (keywordId: string) => {
  return keywords.value.find((k) => k.id === keywordId)?.keyword || keywordId
}

// 格式化时间（人性化显示）
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

// 剥离 HTML 标签，只保留纯文本（用于标题等需要纯文本显示的场景）
const stripHtml = (html: string | null | undefined): string => {
  if (!html) return ''
  // 使用正则表达式移除所有 HTML 标签
  return html
    .replace(/<br\s*\/?>/gi, ' ')  // 将 <br> 转换为空格
    .replace(/<\/p>/gi, ' ')        // 将 </p> 转换为空格
    .replace(/<[^>]+>/g, '')        // 移除所有其他 HTML 标签
    .replace(/\s+/g, ' ')           // 合并多个空格
    .trim()                         // 移除首尾空格
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

// 打开链接
const openUrl = (url: string) => {
  window.open(url, '_blank')
}

// 根据 ID 打开文章详情（用于从预警跳转）
const openArticleById = async (articleId: string) => {
  try {
    const article = await articlesApi.get(articleId)
    if (article) {
      currentArticle.value = article
      detailVisible.value = true
    }
  } catch (error) {
    console.error('Failed to fetch article:', error)
  }
}

onMounted(() => {
  fetchKeywords()
  fetchSources()
  fetchData()

  // 检查 URL 参数是否有高亮文章 ID
  const highlightId = route.query.highlight as string
  if (highlightId) {
    openArticleById(highlightId)
  }
})
</script>

<template>
  <div class="articles-page">
    <!-- Page Header -->
    <div class="page-header">
      <div class="header-left">
        <h3 class="page-title">
          <span class="title-icon">◈</span>
          情报库
        </h3>
        <span class="subtitle">INTELLIGENCE DATABASE</span>
      </div>
      <div class="header-stats">
        <span class="stat-item">
          <span class="stat-value data-value">{{ total }}</span>
          <span class="stat-label">条情报</span>
        </span>
      </div>
    </div>

    <!-- Filters -->
    <div class="filters-panel cyber-card">
      <div class="filters-grid">
        <div class="filter-group">
          <label class="filter-label">监控主体</label>
          <el-select
            v-model="filters.keyword_id"
            placeholder="全部主体"
            clearable
            class="cyber-select"
          >
            <el-option
              v-for="item in keywords"
              :key="item.id"
              :label="item.keyword"
              :value="item.id"
            />
          </el-select>
        </div>

        <div class="filter-group">
          <label class="filter-label">情感倾向</label>
          <div class="filter-options">
            <button
              v-for="item in sentimentOptions"
              :key="item.value"
              class="filter-btn"
              :class="{ active: filters.sentiment === item.value }"
              :style="{ '--btn-color': item.color }"
              @click="filters.sentiment = filters.sentiment === item.value ? '' : item.value"
            >
              {{ item.label }}
            </button>
          </div>
        </div>

        <div class="filter-group">
          <label class="filter-label">来源</label>
          <el-select
            v-model="filters.source"
            placeholder="全部来源"
            clearable
            class="cyber-select"
          >
            <el-option
              v-for="item in sourceOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </div>

        <div class="filter-actions">
          <button class="btn-search" @click="handleSearch">
            <el-icon><Search /></el-icon>
            搜索
          </button>
          <button class="btn-reset" @click="handleReset">
            <el-icon><RefreshRight /></el-icon>
            重置
          </button>
        </div>
      </div>
    </div>

    <!-- Articles Grid -->
    <div class="articles-grid" v-loading="loading">
      <div
        v-for="(article, index) in articles"
        :key="article.id"
        class="article-card cyber-card fade-in-up"
        :style="{ '--delay': `${index * 0.05}s` }"
        @click="handleDetail(article)"
      >
        <!-- Article Header -->
        <div class="article-header">
          <span class="article-source">{{ article.source || article.source_api || '未知来源' }}</span>
          <span
            class="article-sentiment"
            :style="{ color: getSentimentConfig(article.sentiment_label).color }"
          >
            {{ getSentimentConfig(article.sentiment_label).label }}
          </span>
        </div>

        <!-- Article Title -->
        <h4 class="article-title">{{ stripHtml(article.title) }}</h4>

        <!-- Article Content Preview -->
        <p class="article-excerpt" v-html="sanitizeHtml(article.content, 120, true) || '暂无内容摘要...'"></p>

        <!-- Article Footer -->
        <div class="article-footer">
          <span v-if="article.keyword_id" class="keyword-tag">{{ getKeywordName(article.keyword_id) }}</span>
          <span class="article-time">
            {{ formatTime(article.publish_time) }}
          </span>
        </div>

        <!-- Sentiment Score Bar -->
        <div class="score-bar">
          <div
            class="score-fill"
            :style="{
              width: `${getScoreWidth(article.sentiment_score)}%`,
              background: getScoreColor(article.sentiment_score)
            }"
          ></div>
        </div>

        <!-- Hover Glow -->
        <div class="card-glow"></div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-if="!loading && articles.length === 0" class="empty-state cyber-card">
      <el-icon :size="64"><Document /></el-icon>
      <span>暂无情报数据</span>
      <p>请先添加监控主体并执行采集任务</p>
    </div>

    <!-- Pagination -->
    <div class="pagination-bar" v-if="total > 0">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="size"
        :total="total"
        :page-sizes="[20, 40, 60, 100]"
        layout="total, sizes, prev, pager, next"
        @current-change="handlePageChange"
        @size-change="handleSizeChange"
      />
    </div>

    <!-- Detail Dialog -->
    <el-dialog v-model="detailVisible" title="情报详情" width="700px" class="cyber-dialog">
      <div v-if="currentArticle" class="detail-content">
        <!-- Header -->
        <div class="detail-header">
          <span
            class="detail-sentiment"
            :style="{ color: getSentimentConfig(currentArticle.sentiment_label).color }"
          >
            {{ getSentimentConfig(currentArticle.sentiment_label).label }}
            <span class="sentiment-score">
              {{ currentArticle.sentiment_score?.toFixed(2) || '-' }}
            </span>
          </span>
          <span class="detail-source">{{ currentArticle.source || currentArticle.source_api }}</span>
        </div>

        <!-- Title -->
        <h3 class="detail-title">{{ stripHtml(currentArticle.title) }}</h3>

        <!-- Meta -->
        <div class="detail-meta">
          <div class="meta-item">
            <span class="meta-label">监控主体</span>
            <span class="meta-value">{{ getKeywordName(currentArticle.keyword_id) }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">发布时间</span>
            <span class="meta-value">{{ formatTime(currentArticle.publish_time) }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">采集时间</span>
            <span class="meta-value">{{ formatTime(currentArticle.collect_time) }}</span>
          </div>
        </div>

        <!-- Content -->
        <div class="detail-body">
          <h4 class="body-title">内容摘要</h4>
          <div class="body-content" v-html="sanitizeHtml(currentArticle.content) || '暂无内容'">
          </div>
        </div>

        <!-- Link -->
        <div class="detail-link">
          <button class="btn-link" @click.stop="openUrl(currentArticle.url)">
            <el-icon><Link /></el-icon>
            访问原文
          </button>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<style scoped>
.articles-page {
  max-width: 1400px;
  margin: 0 auto;
}

/* Page Header */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.subtitle {
  font-family: var(--font-display);
  font-size: 0.65rem;
  letter-spacing: 0.2em;
  color: var(--text-muted);
}

.title-icon {
  color: var(--neon-green);
  margin-right: 8px;
}

.header-stats {
  display: flex;
  gap: 24px;
}

.stat-item {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.stat-value {
  font-family: var(--font-display);
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--neon-cyan);
}

.stat-label {
  font-size: 0.8rem;
  color: var(--text-secondary);
}

/* Filters */
.filters-panel {
  margin-bottom: 24px;
}

.filters-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  padding: 20px;
  align-items: flex-end;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.filter-label {
  font-family: var(--font-display);
  font-size: 0.65rem;
  font-weight: 500;
  letter-spacing: 0.15em;
  color: var(--text-muted);
  text-transform: uppercase;
}

.filter-options {
  display: flex;
  gap: 6px;
}

.filter-btn {
  padding: 8px 16px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  font-family: var(--font-display);
  font-size: 0.7rem;
  letter-spacing: 0.05em;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.filter-btn:hover {
  border-color: var(--btn-color);
  color: var(--btn-color);
}

.filter-btn.active {
  background: rgba(0, 0, 0, 0.3);
  border-color: var(--btn-color);
  color: var(--btn-color);
}

.cyber-select {
  width: 160px;
}

.filter-actions {
  display: flex;
  gap: 10px;
  margin-left: auto;
}

.btn-search, .btn-reset {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  border-radius: var(--radius-sm);
  font-family: var(--font-display);
  font-size: 0.75rem;
  letter-spacing: 0.05em;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-search {
  background: var(--neon-cyan);
  border: none;
  color: var(--bg-primary);
}

.btn-search:hover {
  box-shadow: 0 0 15px rgba(0, 240, 255, 0.4);
}

.btn-reset {
  background: transparent;
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
}

.btn-reset:hover {
  border-color: var(--text-secondary);
  color: var(--text-primary);
}

/* Articles Grid */
.articles-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
  margin-bottom: 24px;
}

.article-card {
  padding: 0;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
}

.article-card:hover {
  transform: translateY(-4px);
}

.article-card:hover .card-glow {
  opacity: 1;
}

.card-glow {
  position: absolute;
  inset: 0;
  background: radial-gradient(ellipse at top, rgba(0, 240, 255, 0.1), transparent 60%);
  opacity: 0;
  transition: opacity var(--transition-normal);
  pointer-events: none;
}

.article-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 16px 0;
}

.article-source {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: var(--text-muted);
  text-transform: uppercase;
}

.article-sentiment {
  font-family: var(--font-display);
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.1em;
}

.article-title {
  padding: 12px 16px 8px;
  font-family: var(--font-body);
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.article-excerpt {
  padding: 0 16px;
  font-size: 0.8rem;
  color: var(--text-secondary);
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  flex: 1;
}

.article-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  margin-top: auto;
}

.keyword-tag {
  padding: 4px 10px;
  background: rgba(0, 240, 255, 0.1);
  border: 1px solid rgba(0, 240, 255, 0.3);
  border-radius: 12px;
  font-family: var(--font-mono);
  font-size: 0.65rem;
  color: var(--neon-cyan);
}

.article-time {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: var(--text-muted);
}

.score-bar {
  height: 3px;
  background: var(--bg-tertiary);
  margin-top: auto;
}

.score-fill {
  height: 100%;
  transition: width var(--transition-normal);
}

/* Empty State */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  gap: 12px;
  color: var(--text-muted);
  text-align: center;
}

.empty-state p {
  font-size: 0.85rem;
}

/* Pagination */
.pagination-bar {
  display: flex;
  justify-content: center;
  padding: 20px;
}

/* Detail Dialog */
.detail-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.detail-sentiment {
  font-family: var(--font-display);
  font-size: 0.9rem;
  font-weight: 600;
  letter-spacing: 0.1em;
  display: flex;
  align-items: center;
  gap: 10px;
}

.sentiment-score {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  padding: 2px 8px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 4px;
}

.detail-source {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--text-muted);
  text-transform: uppercase;
}

.detail-title {
  font-family: var(--font-body);
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.5;
}

.detail-meta {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  padding: 16px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-md);
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.meta-label {
  font-family: var(--font-display);
  font-size: 0.6rem;
  letter-spacing: 0.15em;
  color: var(--text-muted);
  text-transform: uppercase;
}

.meta-value {
  font-size: 0.85rem;
  color: var(--text-primary);
}

.detail-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.body-title {
  font-family: var(--font-display);
  font-size: 0.75rem;
  font-weight: 500;
  letter-spacing: 0.1em;
  color: var(--text-secondary);
}

.body-content {
  padding: 16px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-md);
  font-size: 0.9rem;
  color: var(--text-primary);
  line-height: 1.8;
  max-height: 400px;
  overflow-y: auto;
}

.body-content :deep(p) {
  margin: 0 0 12px 0;
  line-height: 1.8;
}

.body-content :deep(img) {
  max-width: 100% !important;
  max-height: 200px !important;
  width: auto !important;
  height: auto !important;
  display: block;
  margin: 12px auto;
  border-radius: var(--radius-sm);
  object-fit: contain;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.body-content :deep(a) {
  color: var(--neon-cyan);
  text-decoration: none;
}

.body-content :deep(a:hover) {
  text-decoration: underline;
}

.body-content :deep(br) {
  display: block;
  margin-bottom: 8px;
}

.detail-link {
  display: flex;
  justify-content: flex-end;
}

.btn-link {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  background: linear-gradient(135deg, var(--neon-cyan-dim), var(--neon-cyan));
  border: none;
  border-radius: var(--radius-md);
  font-family: var(--font-display);
  font-size: 0.8rem;
  font-weight: 500;
  letter-spacing: 0.05em;
  color: var(--bg-primary);
  cursor: pointer;
  transition: all var(--transition-normal);
}

.btn-link:hover {
  box-shadow: var(--glow-cyan);
}

/* Responsive */
@media (max-width: 768px) {
  .articles-grid {
    grid-template-columns: 1fr;
  }

  .detail-meta {
    grid-template-columns: 1fr;
  }

  .filters-grid {
    flex-direction: column;
    align-items: stretch;
  }

  .cyber-select {
    width: 100%;
  }

  .filter-actions {
    margin-left: 0;
    justify-content: flex-end;
  }
}
</style>
