<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Hide,
  Check,
  Search,
  Refresh,
  Close,
  Document,
} from '@element-plus/icons-vue'
import {
  alertsApi,
  keywordsApi,
  type Alert,
  type AlertDetail,
  type AlertListParams,
  type AlertStatsResponse,
  type Keyword,
  type ArticleBrief,
} from '@/api'

const alerts = ref<Alert[]>([])
const keywords = ref<Keyword[]>([])
const stats = ref<AlertStatsResponse | null>(null)
const total = ref(0)
const loading = ref(false)

const page = ref(1)
const size = ref(20)

const filters = ref<AlertListParams>({
  status: '',
  alert_level: '',
  alert_type: '',
})

const selectedIds = ref<string[]>([])

// 预警详情弹窗
const detailVisible = ref(false)
const detailLoading = ref(false)
const currentAlert = ref<AlertDetail | null>(null)
const relatedArticles = ref<ArticleBrief[]>([])

// 处理备注弹窗
const handleDialogVisible = ref(false)
const handleNote = ref('')
const handlingAlertId = ref<string | null>(null)

const statusOptions = [
  { label: '待处理', value: 'pending', color: '#ffd000' },
  { label: '已处理', value: 'handled', color: '#00ff88' },
  { label: '已忽略', value: 'ignored', color: '#8b95a8' },
  { label: '误报', value: 'false_positive', color: '#ff3366' },
]

const levelOptions = [
  { label: '信息', value: 'info', color: '#00f0ff' },
  { label: '警告', value: 'warning', color: '#ffd000' },
  { label: '严重', value: 'critical', color: '#ff3366' },
]

const typeOptions = [
  { label: '负面爆发', value: 'negative_burst', icon: '⚠' },
  { label: '敏感词', value: 'sensitive_keyword', icon: '🔍' },
  { label: '讨论量激增', value: 'volume_spike', icon: '📈' },
]

const fetchKeywords = async () => {
  try {
    keywords.value = await keywordsApi.list()
  } catch (error) {
    console.error('Failed to fetch keywords:', error)
  }
}

const fetchStats = async () => {
  try {
    stats.value = await alertsApi.stats()
  } catch (error) {
    console.error('Failed to fetch alert stats:', error)
  }
}

const fetchData = async () => {
  loading.value = true
  try {
    const params: AlertListParams = {
      page: page.value,
      size: size.value,
      ...filters.value,
    }
    Object.keys(params).forEach((key) => {
      if (!params[key as keyof AlertListParams]) {
        delete params[key as keyof AlertListParams]
      }
    })

    const result = await alertsApi.list(params)
    alerts.value = result.items
    total.value = result.total
  } catch (error) {
    console.error('Failed to fetch alerts:', error)
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  page.value = 1
  fetchData()
}

const handleReset = () => {
  filters.value = {
    status: '',
    alert_level: '',
    alert_type: '',
  }
  page.value = 1
  fetchData()
}

const handlePageChange = (val: number) => {
  page.value = val
  fetchData()
}

// 查看预警详情
const viewDetail = async (row: Alert) => {
  detailLoading.value = true
  detailVisible.value = true
  try {
    currentAlert.value = await alertsApi.detail(row.id)
    relatedArticles.value = currentAlert.value?.related_articles || []
  } catch (error) {
    console.error('Failed to fetch alert detail:', error)
    ElMessage.error('获取预警详情失败')
  } finally {
    detailLoading.value = false
  }
}

// 打开处理弹窗
const openHandleDialog = (row: Alert) => {
  handlingAlertId.value = row.id
  handleNote.value = ''
  handleDialogVisible.value = true
}

// 确认处理
const confirmHandle = async () => {
  if (!handlingAlertId.value) return
  try {
    await alertsApi.handle(handlingAlertId.value, { note: handleNote.value })
    ElMessage.success('已处理')
    handleDialogVisible.value = false
    fetchData()
    fetchStats()
  } catch (error) {
    console.error('Failed to handle alert:', error)
    ElMessage.error('处理失败')
  }
}

// 快速处理（无备注）
const quickHandle = async (row: Alert) => {
  try {
    await alertsApi.handle(row.id)
    ElMessage.success('已处理')
    fetchData()
    fetchStats()
  } catch (error) {
    console.error('Failed to handle alert:', error)
  }
}

// 忽略
const ignoreAlert = async (row: Alert) => {
  try {
    await alertsApi.ignore(row.id)
    ElMessage.success('已忽略')
    fetchData()
    fetchStats()
  } catch (error) {
    console.error('Failed to ignore alert:', error)
  }
}

// 标记误报
const markFalsePositive = async (row: Alert) => {
  try {
    await ElMessageBox.confirm('确定要将此预警标记为误报吗？', '确认', {
      type: 'warning',
    confirmButtonText: '标记误报',
      cancelButtonText: '取消',
    })
    await alertsApi.markFalsePositive(row.id)
    ElMessage.success('已标记为误报')
    fetchData()
    fetchStats()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to mark false positive:', error)
    }
  }
}

// 批量处理
const handleBatch = async () => {
  if (selectedIds.value.length === 0) {
    ElMessage.warning('请选择要处理的预警')
    return
  }

  try {
    await ElMessageBox.confirm(`确定要处理选中的 ${selectedIds.value.length} 条预警吗？`, '确认', {
      type: 'warning',
    })
    await alertsApi.batchHandle(selectedIds.value)
    ElMessage.success('批量处理成功')
    selectedIds.value = []
    fetchData()
    fetchStats()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to batch handle:', error)
    }
  }
}

const handleSelectionChange = (selection: Alert[]) => {
  selectedIds.value = selection.map((a) => a.id)
}

const getStatusConfig = (status: string | undefined | null) => {
  return statusOptions.find(s => s.value === status) ?? statusOptions[0]
}

const getLevelConfig = (level: string | undefined | null) => {
  return levelOptions.find(l => l.value === level) ?? levelOptions[0]
}

const getTypeConfig = (type: string | null) => {
  return typeOptions.find(t => t.value === type) || { label: type || '-', icon: '📌' }
}

const getKeywordName = (keywordId: string) => {
  return keywords.value.find((k) => k.id === keywordId)?.keyword || keywordId
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

// 跳转到文章详情
const goToArticle = (article: ArticleBrief) => {
  if (article?.url) {
    window.open(article.url, '_blank')
  }
}

const statCards = computed(() => {
  if (!stats.value) return []
  return [
    { label: '预警总量', value: stats.value.total, color: '#00f0ff', icon: 'Bell' },
    { label: '待处理', value: stats.value.pending, color: '#ff3366', icon: 'Warning', urgent: true },
    { label: '已处理', value: stats.value.handled, color: '#00ff88', icon: 'CircleCheck' },
    { label: '误报', value: stats.value.false_positive || 0, color: '#8b95a8', icon: 'Close' },
  ]
})

onMounted(() => {
  fetchKeywords()
  fetchStats()
  fetchData()
})
</script>

<template>
  <div class="alerts-page">
    <!-- Page Header -->
    <div class="page-header">
      <div class="header-left">
        <h3 class="page-title">
          <span class="title-icon">◈</span>
          预警中心
        </h3>
        <span class="subtitle">ALERT CENTER</span>
      </div>
      <button
        class="btn-primary"
        :class="{ disabled: selectedIds.length === 0 }"
        :disabled="selectedIds.length === 0"
        @click="handleBatch"
      >
        <el-icon><Check /></el-icon>
        <span>批量处理</span>
        <span v-if="selectedIds.length > 0" class="badge">{{ selectedIds.length }}</span>
      </button>
    </div>

    <!-- Stats Grid -->
    <div class="stats-grid" v-if="stats">
      <div
        v-for="(card, index) in statCards"
        :key="card.label"
        class="stat-card cyber-card fade-in-up"
        :class="{ urgent: card.urgent && card.value > 0 }"
        :style="{ '--card-color': card.color, '--delay': `${index * 0.1}s` }"
      >
        <div class="stat-icon">
          <el-icon :size="24"><component :is="card.icon" /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value data-value">{{ card.value }}</div>
          <div class="stat-label">{{ card.label }}</div>
        </div>
        <div class="stat-glow" v-if="card.urgent && card.value > 0"></div>
      </div>
    </div>

    <!-- Filters -->
    <div class="filters-panel cyber-card">
      <div class="filters-grid">
        <div class="filter-group">
          <label class="filter-label">状态</label>
          <div class="filter-options">
            <button
              v-for="item in statusOptions"
              :key="item.value"
              class="filter-btn"
              :class="{ active: filters.status === item.value }"
              :style="{ '--btn-color': item.color }"
              @click="filters.status = filters.status === item.value ? '' : item.value"
            >
              {{ item.label }}
            </button>
          </div>
        </div>

        <div class="filter-group">
          <label class="filter-label">级别</label>
          <div class="filter-options">
            <button
              v-for="item in levelOptions"
              :key="item.value"
              class="filter-btn"
              :class="{ active: filters.alert_level === item.value }"
              :style="{ '--btn-color': item.color }"
              @click="filters.alert_level = filters.alert_level === item.value ? '' : item.value"
            >
              {{ item.label }}
            </button>
          </div>
        </div>

        <div class="filter-group">
          <label class="filter-label">类型</label>
          <div class="filter-options">
            <button
              v-for="item in typeOptions"
              :key="item.value"
              class="filter-btn type-btn"
              :class="{ active: filters.alert_type === item.value }"
              @click="filters.alert_type = filters.alert_type === item.value ? '' : item.value"
            >
              <span class="type-icon">{{ item.icon }}</span>
              {{ item.label }}
            </button>
          </div>
        </div>

        <div class="filter-actions">
          <button class="btn-search" @click="handleSearch">
            <el-icon><Search /></el-icon>
            搜索
          </button>
          <button class="btn-reset" @click="handleReset">
            <el-icon><Refresh /></el-icon>
            重置
          </button>
        </div>
      </div>
    </div>

    <!-- Alerts List -->
    <div class="alerts-list cyber-card">
      <el-table
        :data="alerts"
        v-loading="loading"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="50" />

        <el-table-column prop="alert_level" label="级别" width="90">
          <template #default="{ row }">
            <div class="level-badge" :style="{ '--level-color': getLevelConfig(row.alert_level)?.color }">
              <span class="level-dot"></span>
              {{ getLevelConfig(row.alert_level)?.label }}
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="alert_type" label="类型" width="120">
          <template #default="{ row }">
            <span class="type-tag">
              <span class="type-icon">{{ getTypeConfig(row.alert_type).icon }}</span>
              {{ getTypeConfig(row.alert_type).label }}
            </span>
          </template>
        </el-table-column>

        <el-table-column prop="message" label="预警信息" min-width="280">
          <template #default="{ row }">
            <div class="alert-message clickable" @click="viewDetail(row)">
              <span class="message-text">{{ row.message }}</span>
              <span class="link-hint">查看详情</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="keyword_id" label="监控主体" width="140">
          <template #default="{ row }">
            <span class="keyword-tag">{{ getKeywordName(row.keyword_id) }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <span
              class="status-badge"
              :style="{ '--status-color': getStatusConfig(row.status)?.color }"
            >
              {{ getStatusConfig(row.status)?.label }}
            </span>
          </template>
        </el-table-column>

        <el-table-column prop="created_at" label="时间" width="160">
          <template #default="{ row }">
            <span class="time-text">{{ new Date(row.created_at).toLocaleString() }}</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons" v-if="row.status === 'pending'">
              <button class="action-btn handle" @click="quickHandle(row)">
                <el-icon><Check /></el-icon>
                处理
              </button>
              <button class="action-btn detail" @click="viewDetail(row)">
                <el-icon><Document /></el-icon>
              </button>
              <button class="action-btn false-positive" @click="markFalsePositive(row)">
                <el-icon><Close /></el-icon>
              </button>
            </div>
            <span v-else class="handled-text">
              <span v-if="row.handler_name" class="handler-info">处理人: {{ row.handler_name }}</span>
              <span v-else>已完结</span>
            </span>
          </template>
        </el-table-column>
      </el-table>

      <!-- Pagination -->
      <div class="pagination-bar">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="size"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @current-change="handlePageChange"
        />
      </div>
    </div>

    <!-- 预警详情弹窗 -->
    <el-dialog
      v-model="detailVisible"
      title="预警详情"
      width="700px"
      class="cyber-dialog"
    >
      <div v-loading="detailLoading" class="detail-content">
        <template v-if="currentAlert">
          <!-- 基本信息 -->
          <div class="detail-section">
            <div class="detail-row">
              <span class="detail-label">预警级别</span>
              <span
                class="level-badge"
                :style="{ '--level-color': getLevelConfig(currentAlert.alert_level)?.color }"
              >
                <span class="level-dot"></span>
                {{ getLevelConfig(currentAlert.alert_level)?.label }}
              </span>
            </div>
            <div class="detail-row">
              <span class="detail-label">预警类型</span>
              <span class="type-tag">
                <span class="type-icon">{{ getTypeConfig(currentAlert.alert_type).icon }}</span>
                {{ getTypeConfig(currentAlert.alert_type).label }}
              </span>
            </div>
            <div class="detail-row">
              <span class="detail-label">监控主体</span>
              <span class="keyword-tag">{{ currentAlert.keyword_name || currentAlert.keyword_id }}</span>
            </div>
            <div class="detail-row full">
              <span class="detail-label">预警内容</span>
              <span class="detail-value">{{ currentAlert.message }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">创建时间</span>
              <span class="detail-value time">{{ new Date(currentAlert.created_at).toLocaleString() }}</span>
            </div>
          </div>

          <!-- 关联文章 -->
          <div class="detail-section" v-if="relatedArticles.length > 0">
            <div class="section-title">
              <el-icon><Document /></el-icon>
              关联文章 ({{ relatedArticles.length }})
            </div>
            <div class="articles-list">
              <div
                v-for="article in relatedArticles"
                :key="article.id"
                class="article-item"
                @click="goToArticle(article)"
              >
                <div class="article-header">
                  <span class="article-title">{{ stripHtml(article.title) }}</span>
                  <span
                    class="article-sentiment"
                    :class="article.sentiment_label"
                  >
                    {{ article.sentiment_label === 'positive' ? '正面' : article.sentiment_label === 'negative' ? '负面' : '中性' }}
                  </span>
                </div>
                <div class="article-meta">
                  <span class="article-source">{{ article.source || '未知来源' }}</span>
                  <span class="article-time" v-if="article.publish_time">
                    {{ new Date(article.publish_time).toLocaleDateString() }}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <!-- 处理记录 -->
          <div class="detail-section" v-if="currentAlert.status !== 'pending'">
            <div class="section-title">
              <el-icon><Check /></el-icon>
              处理记录
            </div>
            <div class="detail-row">
              <span class="detail-label">处理状态</span>
              <span
                class="status-badge"
                :style="{ '--status-color': getStatusConfig(currentAlert.status)?.color }"
              >
                {{ getStatusConfig(currentAlert.status)?.label }}
              </span>
            </div>
            <div class="detail-row" v-if="currentAlert.handler_name">
              <span class="detail-label">处理人</span>
              <span class="detail-value">{{ currentAlert.handler_name }}</span>
            </div>
            <div class="detail-row" v-if="currentAlert.handle_note">
              <span class="detail-label">处理备注</span>
              <span class="detail-value note">{{ currentAlert.handle_note }}</span>
            </div>
            <div class="detail-row" v-if="currentAlert.handled_at">
              <span class="detail-label">处理时间</span>
              <span class="detail-value time">{{ new Date(currentAlert.handled_at).toLocaleString() }}</span>
            </div>
          </div>

          <!-- 操作按钮 -->
          <div class="detail-actions" v-if="currentAlert.status === 'pending'">
            <button class="btn-action handle" @click="openHandleDialog(currentAlert); detailVisible = false">
              <el-icon><Check /></el-icon>
              处理（带备注）
            </button>
            <button class="btn-action ignore" @click="ignoreAlert(currentAlert); detailVisible = false">
              <el-icon><Hide /></el-icon>
              忽略
            </button>
            <button class="btn-action false-positive" @click="markFalsePositive(currentAlert); detailVisible = false">
              <el-icon><Close /></el-icon>
              标记误报
            </button>
          </div>
        </template>
      </div>
    </el-dialog>

    <!-- 处理备注弹窗 -->
    <el-dialog
      v-model="handleDialogVisible"
      title="处理预警"
      width="500px"
      class="cyber-dialog"
    >
      <div class="handle-dialog-content">
        <div class="form-group">
          <label class="form-label">处理备注（可选）</label>
          <textarea
            v-model="handleNote"
            class="cyber-textarea"
            placeholder="请输入处理说明或备注..."
            rows="4"
          ></textarea>
        </div>
      </div>
      <template #footer>
        <div class="dialog-footer">
          <button class="btn-secondary" @click="handleDialogVisible = false">取消</button>
          <button class="btn-primary" @click="confirmHandle">
            <el-icon><Check /></el-icon>
            确认处理
          </button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.alerts-page {
  max-width: 1500px;
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
  color: var(--neon-red);
  margin-right: 8px;
}

.btn-primary {
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
  position: relative;
}

.btn-primary:hover:not(.disabled) {
  box-shadow: var(--glow-cyan);
  transform: translateY(-2px);
}

.btn-primary.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.badge {
  position: absolute;
  top: -8px;
  right: -8px;
  min-width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-mono);
  font-size: 0.65rem;
  font-weight: 600;
  background: var(--neon-red);
  color: white;
  border-radius: 10px;
  padding: 0 6px;
  animation: pulse-glow 2s infinite;
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  position: relative;
  overflow: hidden;
}

.stat-card.urgent {
  animation: urgent-pulse 2s infinite;
}

@keyframes urgent-pulse {
  0%, 100% { border-color: var(--border-color); }
  50% { border-color: var(--neon-red); }
}

.stat-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, rgba(0, 240, 255, 0.1), rgba(0, 240, 255, 0.05));
  border: 1px solid var(--card-color);
  border-radius: 12px;
  color: var(--card-color);
}

.stat-value {
  font-family: var(--font-display);
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--text-primary);
}

.stat-label {
  font-size: 0.75rem;
  color: var(--text-secondary);
  letter-spacing: 0.1em;
}

.stat-glow {
  position: absolute;
  inset: 0;
  background: radial-gradient(ellipse at center, rgba(255, 51, 102, 0.1), transparent 70%);
  pointer-events: none;
}

/* Filters Panel */
.filters-panel {
  margin-bottom: 20px;
}

.filters-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 24px;
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

.filter-btn.type-btn {
  display: flex;
  align-items: center;
  gap: 6px;
}

.type-icon {
  font-size: 0.9rem;
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

/* Alerts List */
.alerts-list {
  overflow: hidden;
}

.level-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--level-color);
}

.level-dot {
  width: 8px;
  height: 8px;
  background: var(--level-color);
  border-radius: 50%;
  box-shadow: 0 0 8px var(--level-color);
}

.type-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.8rem;
  color: var(--text-primary);
}

.alert-message {
  max-width: 100%;
}

.alert-message.clickable {
  cursor: pointer;
  transition: all var(--transition-fast);
}

.alert-message.clickable:hover {
  color: var(--neon-cyan);
}

.alert-message.clickable:hover .link-hint {
  opacity: 1;
}

.message-text {
  font-size: 0.85rem;
  color: var(--text-primary);
  word-break: break-word;
}

.link-hint {
  display: block;
  font-size: 0.7rem;
  color: var(--neon-cyan);
  margin-top: 4px;
  opacity: 0;
  transition: opacity var(--transition-fast);
}

.keyword-tag {
  display: inline-block;
  padding: 4px 10px;
  background: rgba(0, 240, 255, 0.1);
  border: 1px solid rgba(0, 240, 255, 0.3);
  border-radius: 12px;
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: var(--neon-cyan);
}

.status-badge {
  display: inline-block;
  padding: 4px 12px;
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid var(--status-color);
  border-radius: 12px;
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: var(--status-color);
}

.time-text {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--text-muted);
}

.action-buttons {
  display: flex;
  gap: 6px;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  font-family: var(--font-display);
  font-size: 0.7rem;
  letter-spacing: 0.05em;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.action-btn:hover {
  transform: translateY(-1px);
}

.action-btn.handle:hover {
  border-color: var(--neon-green);
  color: var(--neon-green);
}

.action-btn.detail:hover {
  border-color: var(--neon-cyan);
  color: var(--neon-cyan);
}

.action-btn.false-positive:hover {
  border-color: var(--neon-red);
  color: var(--neon-red);
}

.action-btn.ignore:hover {
  border-color: var(--text-muted);
  color: var(--text-muted);
}

.handled-text {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: var(--text-muted);
}

.handler-info {
  color: var(--neon-green);
}

/* Pagination */
.pagination-bar {
  display: flex;
  justify-content: flex-end;
  padding: 20px;
  border-top: 1px solid var(--border-color);
}

/* Detail Dialog */
.detail-content {
  padding: 10px 0;
}

.detail-section {
  margin-bottom: 24px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--border-color);
}

.detail-section:last-child {
  border-bottom: none;
  margin-bottom: 0;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-display);
  font-size: 0.8rem;
  font-weight: 500;
  letter-spacing: 0.1em;
  color: var(--text-primary);
  margin-bottom: 16px;
}

.detail-row {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 12px;
}

.detail-row.full {
  flex-direction: column;
  gap: 8px;
}

.detail-label {
  min-width: 80px;
  font-family: var(--font-display);
  font-size: 0.7rem;
  font-weight: 500;
  letter-spacing: 0.1em;
  color: var(--text-muted);
}

.detail-value {
  font-size: 0.85rem;
  color: var(--text-primary);
}

.detail-value.time {
  font-family: var(--font-mono);
  color: var(--text-secondary);
}

.detail-value.note {
  background: var(--bg-tertiary);
  padding: 10px 14px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
  white-space: pre-wrap;
  word-break: break-word;
}

/* Articles List in Detail */
.articles-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 300px;
  overflow-y: auto;
}

.article-item {
  padding: 14px 16px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.article-item:hover {
  border-color: var(--neon-cyan);
  background: rgba(0, 240, 255, 0.05);
}

.article-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 8px;
}

.article-title {
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--text-primary);
  flex: 1;
  line-height: 1.4;
}

.article-sentiment {
  padding: 2px 8px;
  font-family: var(--font-mono);
  font-size: 0.65rem;
  border-radius: 10px;
  flex-shrink: 0;
}

.article-sentiment.positive {
  background: rgba(0, 255, 136, 0.15);
  color: var(--neon-green);
}

.article-sentiment.negative {
  background: rgba(255, 51, 102, 0.15);
  color: var(--neon-red);
}

.article-sentiment.neutral {
  background: rgba(139, 149, 168, 0.15);
  color: var(--text-secondary);
}

.article-meta {
  display: flex;
  gap: 12px;
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: var(--text-muted);
}

/* Detail Actions */
.detail-actions {
  display: flex;
  gap: 12px;
  padding-top: 20px;
}

.btn-action {
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

.btn-action.handle {
  background: rgba(0, 255, 136, 0.15);
  border: 1px solid var(--neon-green);
  color: var(--neon-green);
}

.btn-action.handle:hover {
  background: rgba(0, 255, 136, 0.25);
}

.btn-action.ignore {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
}

.btn-action.ignore:hover {
  border-color: var(--text-secondary);
}

.btn-action.false-positive {
  background: rgba(255, 51, 102, 0.1);
  border: 1px solid var(--neon-red);
  color: var(--neon-red);
}

.btn-action.false-positive:hover {
  background: rgba(255, 51, 102, 0.2);
}

/* Handle Dialog */
.handle-dialog-content {
  padding: 10px 0;
}

.form-group {
  margin-bottom: 16px;
}

.form-label {
  display: block;
  font-family: var(--font-display);
  font-size: 0.7rem;
  font-weight: 500;
  letter-spacing: 0.1em;
  color: var(--text-muted);
  margin-bottom: 8px;
}

.cyber-textarea {
  width: 100%;
  padding: 12px 14px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  font-family: var(--font-body);
  font-size: 0.85rem;
  color: var(--text-primary);
  resize: vertical;
  transition: all var(--transition-normal);
}

.cyber-textarea:focus {
  outline: none;
  border-color: var(--neon-cyan);
  box-shadow: 0 0 15px rgba(0, 240, 255, 0.2);
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.btn-secondary {
  padding: 10px 20px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  font-family: var(--font-display);
  font-size: 0.75rem;
  letter-spacing: 0.05em;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-secondary:hover {
  border-color: var(--text-secondary);
  color: var(--text-primary);
}

/* Responsive */
@media (max-width: 1200px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .filters-grid {
    flex-direction: column;
    align-items: stretch;
  }

  .filter-actions {
    margin-left: 0;
    justify-content: flex-end;
  }
}
</style>
