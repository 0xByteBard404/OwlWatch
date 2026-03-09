<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Download,
  Edit,
  Delete,
  Plus,
  Promotion,
  View,
  Link,
} from '@element-plus/icons-vue'
import {
  keywordsApi,
  collectApi,
  rssApi,
  type Keyword,
  type KeywordCreate,
  type AlertConfig,
  DEFAULT_ALERT_CONFIG,
} from '@/api'

const router = useRouter()

const keywords = ref<Keyword[]>([])
const rssFeeds = ref<any[]>([])
const loading = ref(false)

const dialogVisible = ref(false)
const dialogTitle = ref('添加监控主体')
const formLoading = ref(false)

interface FormType extends KeywordCreate {
  data_sources: { rss_ids: string[] }
  alert_config: AlertConfig
}

const form = ref<FormType>({
  keyword: '',
  priority: 'medium',
  platforms: ['bocha', 'tavily'],
  data_sources: { rss_ids: [] },
  fetch_interval: 300,
  alert_config: JSON.parse(JSON.stringify(DEFAULT_ALERT_CONFIG)),
})

const editingId = ref<string | null>(null)

// 自定义敏感词输入（逗号分隔的字符串）
const customKeywordsInput = computed({
  get: () => form.value.alert_config?.sensitive_keyword?.custom_keywords?.join(', ') || '',
  set: (val: string) => {
    if (form.value.alert_config?.sensitive_keyword) {
      form.value.alert_config.sensitive_keyword.custom_keywords = val
        .split(',')
        .map(k => k.trim())
        .filter(k => k.length > 0)
    }
  }
})

// 预警配置计算属性（带默认值）
const alertConfig = computed(() => form.value.alert_config || DEFAULT_ALERT_CONFIG)

// 确保 alert_config 存在
const ensureAlertConfig = () => {
  if (!form.value.alert_config) {
    form.value.alert_config = JSON.parse(JSON.stringify(DEFAULT_ALERT_CONFIG))
  }
}

// 切换函数
const toggleNegativeBurst = () => {
  ensureAlertConfig()
  const nb = form.value.alert_config!.negative_burst
  if (nb) {
    nb.enabled = !nb.enabled
  }
}

const toggleSensitiveKeyword = () => {
  ensureAlertConfig()
  const sk = form.value.alert_config!.sensitive_keyword
  if (sk) {
    sk.enabled = !sk.enabled
  }
}

const toggleUseGlobal = () => {
  ensureAlertConfig()
  const sk = form.value.alert_config!.sensitive_keyword
  if (sk) {
    sk.use_global = !sk.use_global
  }
}

const toggleVolumeSpike = () => {
  ensureAlertConfig()
  const vs = form.value.alert_config!.volume_spike
  if (vs) {
    vs.enabled = !vs.enabled
  }
}

const collectTasks = ref<Map<string, { keyword_id: string; keyword: string; status: string; collected_count: number }>>(
  new Map()
)
const pollingTimers = ref<Map<string, number>>(new Map())
// 跟踪正在刷新的监控主体（防止重复点击）
const refreshingKeywords = ref<Set<string>>(new Set())

const priorityOptions = [
  { label: '高优先级', value: 'high', color: '#ff3366' },
  { label: '中优先级', value: 'medium', color: '#ffd000' },
  { label: '低优先级', value: 'low', color: '#00f0ff' },
]

const platformOptions = [
  { label: '百度搜索', value: 'baidu', color: '#00f0ff' },
  { label: 'Bing 搜索', value: 'bing', color: '#00ff88' },
  { label: '博查 API', value: 'bocha', color: '#ff6b2c' },
  { label: 'Tavily API', value: 'tavily', color: '#a855f7' },
  { label: 'Anspire API', value: 'anspire', color: '#ffd000' },
]

const fetchIntervalOptions = [
  { label: '5 分钟', value: 300 },
  { label: '10 分钟', value: 600 },
  { label: '15 分钟', value: 900 },
  { label: '30 分钟', value: 1800 },
  { label: '1 小时', value: 3600 },
]

// RSS 全选/取消全选
const isAllRssSelected = () => {
  if (rssFeeds.value.length === 0) return false
  return form.value.data_sources.rss_ids.length === rssFeeds.value.length
}

const toggleAllRss = () => {
  if (isAllRssSelected()) {
    // 已全选，取消全选
    form.value.data_sources.rss_ids = []
  } else {
    // 未全选，全选所有
    form.value.data_sources.rss_ids = rssFeeds.value.map(f => f.id)
  }
}

// 采集平台全选/取消全选
const isAllPlatformsSelected = () => {
  return (form.value.platforms?.length ?? 0) === platformOptions.length
}

const toggleAllPlatforms = () => {
  if (isAllPlatformsSelected()) {
    form.value.platforms = []
  } else {
    form.value.platforms = platformOptions.map(p => p.value)
  }
}

const fetchData = async () => {
  loading.value = true
  try {
    const [keywordsRes, rssRes] = await Promise.all([
      keywordsApi.list(),
      rssApi.list(),
    ])
    keywords.value = keywordsRes
    rssFeeds.value = rssRes
  } catch (error) {
    console.error('Failed to fetch data:', error)
  } finally {
    loading.value = false
  }
}

const handleCreate = () => {
  dialogTitle.value = '添加监控主体'
  editingId.value = null
  form.value = {
    keyword: '',
    priority: 'medium',
    platforms: ['bocha', 'tavily'],
    data_sources: { rss_ids: [] },
    fetch_interval: 300,
    alert_config: JSON.parse(JSON.stringify(DEFAULT_ALERT_CONFIG)),
  }
  dialogVisible.value = true
}

const handleEdit = (row: Keyword) => {
  dialogTitle.value = '编辑监控主体'
  editingId.value = row.id
  form.value = {
    keyword: row.keyword,
    priority: row.priority,
    platforms: row.platforms,
    data_sources: { rss_ids: row.data_sources?.rss_ids || [] },
    fetch_interval: row.fetch_interval || 300,
    alert_config: row.alert_config ? JSON.parse(JSON.stringify(row.alert_config)) : JSON.parse(JSON.stringify(DEFAULT_ALERT_CONFIG)),
  }
  dialogVisible.value = true
}

const handleSubmit = async () => {
  if (!form.value.keyword.trim()) {
    ElMessage.warning('请输入主体名称')
    return
  }

  formLoading.value = true
  try {
    if (editingId.value) {
      await keywordsApi.update(editingId.value, form.value)
      ElMessage.success('更新成功')
    } else {
      await keywordsApi.create(form.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchData()
  } catch (error) {
    console.error('Failed to save keyword:', error)
  } finally {
    formLoading.value = false
  }
}

const handleDelete = async (row: Keyword) => {
  try {
    await ElMessageBox.confirm(`确定要删除监控主体「${row.keyword}」吗？`, '确认删除', {
      type: 'warning',
    })
    await keywordsApi.delete(row.id)
    ElMessage.success('删除成功')
    fetchData()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to delete keyword:', error)
    }
  }
}

const viewDetail = (row: Keyword) => {
  router.push(`/keywords/${row.id}`)
}

// 立即刷新（使用默认参数，不需要弹窗配置）
const handleRefresh = async (row: Keyword) => {
  // 防止重复点击：检查是否已经在刷新中
  if (refreshingKeywords.value.has(row.id)) {
    ElMessage.warning(`「${row.keyword}」正在刷新中，请稍候`)
    return
  }

  // 标记为正在刷新
  refreshingKeywords.value.add(row.id)

  try {
    const result = await keywordsApi.refresh(row.id)

    // 检查 task_id 是否有效
    if (!result.task_id) {
      console.error('Refresh response missing task_id:', result)
      ElMessage.error('刷新任务创建失败：无效的任务ID')
      refreshingKeywords.value.delete(row.id)
      return
    }

    collectTasks.value.set(result.task_id, {
      keyword_id: row.id,
      keyword: result.keyword,
      status: 'pending',
      collected_count: 0,
    })

    ElMessage.info(`「${result.keyword}」刷新任务已创建`)
    startPolling(result.task_id, result.keyword)
  } catch (error) {
    console.error('Failed to trigger refresh:', error)
    ElMessage.error('刷新任务创建失败')
    refreshingKeywords.value.delete(row.id)
  }
}

// 格式化更新间隔显示
const formatFetchInterval = (seconds: number | undefined) => {
  const value = seconds || 300
  const option = fetchIntervalOptions.find(o => o.value === value)
  return option?.label || `${value / 60} 分钟`
}

// 格式化最近扫描时间
const formatLastFetched = (lastFetched: string | undefined | null) => {
  if (!lastFetched) {
    return '从未扫描'
  }

  const date = new Date(lastFetched)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) {
    return '刚刚'
  } else if (diffMins < 60) {
    return `${diffMins} 分钟前`
  } else if (diffHours < 24) {
    return `${diffHours} 小时前`
  } else if (diffDays < 7) {
    return `${diffDays} 天前`
  } else {
    return date.toLocaleDateString()
  }
}

const pollTaskStatus = async (taskId: string, keywordText: string) => {
  try {
    const status = await collectApi.getStatus(taskId)

    // 获取当前的 task 信息（包含 keyword_id）
    const currentTask = collectTasks.value.get(taskId)

    collectTasks.value.set(taskId, {
      keyword_id: currentTask?.keyword_id || '',
      keyword: keywordText,
      status: status.status,
      collected_count: status.collected_count,
    })

    if (status.status === 'completed') {
      ElMessage.success(`「${keywordText}」采集完成，新增 ${status.collected_count} 条情报`)
      fetchData()
      stopPolling(taskId, currentTask?.keyword_id)
    } else if (status.status === 'failed') {
      ElMessage.error(`「${keywordText}」采集失败：${status.message}`)
      stopPolling(taskId, currentTask?.keyword_id)
    }
  } catch (error) {
    console.error('Failed to poll status:', error)
    const currentTask = collectTasks.value.get(taskId)
    stopPolling(taskId, currentTask?.keyword_id)
  }
}

const startPolling = (taskId: string, keywordText: string) => {
  pollTaskStatus(taskId, keywordText)
  const timer = window.setInterval(() => {
    pollTaskStatus(taskId, keywordText)
  }, 2000)
  pollingTimers.value.set(taskId, timer)
}

const stopPolling = (taskId: string, keywordId?: string) => {
  const timer = pollingTimers.value.get(taskId)
  if (timer) {
    clearInterval(timer)
    pollingTimers.value.delete(taskId)
  }
  // 移除刷新标记
  if (keywordId) {
    refreshingKeywords.value.delete(keywordId)
  }
  setTimeout(() => {
    collectTasks.value.delete(taskId)
  }, 5000)
}

const getPriorityConfig = (priority: string | undefined | null) => {
  return priorityOptions.find(p => p.value === priority) ?? priorityOptions[1]
}

const getTaskStatusConfig = (status: string) => {
  const map: Record<string, { label: string; color: string }> = {
    pending: { label: '等待中', color: '#ffd000' },
    running: { label: '采集中', color: '#00f0ff' },
    completed: { label: '已完成', color: '#00ff88' },
    failed: { label: '失败', color: '#ff3366' },
  }
  return map[status] || { label: status, color: '#8b95a8' }
}

const getPlatformColor = (platform: string) => {
  return platformOptions.find(p => p.value === platform)?.color || '#8b95a8'
}

const getPlatformLabel = (platform: string) => {
  return platformOptions.find(p => p.value === platform)?.label || platform
}

const getRssCount = (row: any) => {
  return row.data_sources?.rss_ids?.length || 0
}

const hasDataSources = (row: any) => {
  const hasPlatforms = (row.platforms?.length ?? 0) > 0
  const hasRss = getRssCount(row) > 0
  return hasPlatforms || hasRss
}

onUnmounted(() => {
  pollingTimers.value.forEach((timer) => clearInterval(timer))
})

const restoreRunningTasks = async () => {
  try {
    const result = await collectApi.getRunningTasks()
    for (const task of result.tasks) {
      // 跳过无效的 task_id
      if (!task.task_id) {
        console.warn('Skipping task with null task_id:', task)
        continue
      }
      collectTasks.value.set(task.task_id, {
        keyword_id: task.keyword_id || '',
        keyword: task.keyword,
        status: task.status,
        collected_count: task.collected_count,
      })
      // 如果任务正在运行，标记为正在刷新
      if (task.status === 'pending' || task.status === 'running') {
        if (task.keyword_id) {
          refreshingKeywords.value.add(task.keyword_id)
        }
      }
      startPolling(task.task_id, task.keyword)
    }
  } catch (error) {
    console.error('Failed to restore running tasks:', error)
  }
}

onMounted(() => {
  fetchData()
  restoreRunningTasks()
})
</script>

<template>
  <div class="keywords-page">
    <!-- Page Header -->
    <div class="page-header">
      <div class="header-left">
        <h3 class="page-title">
          <span class="title-icon">◈</span>
          监控主体管理
        </h3>
        <span class="subtitle">MONITORING SUBJECTS</span>
      </div>
      <button class="btn-primary" @click="handleCreate">
        <el-icon><Plus /></el-icon>
        <span>添加监控主体</span>
      </button>
    </div>

    <!-- RSS 订阅提示 -->
    <div class="tip-card">
      <div class="tip-content">
        <span class="tip-icon">💡</span>
        <div class="tip-text">
          <span class="tip-title">推荐使用 RSS 订阅采集情报</span>
          <span class="tip-desc">RSS 订阅自动定时获取最新内容，稳定可靠且完全免费。此处的 API 搜索为补充功能。</span>
        </div>
      </div>
      <button class="tip-btn" @click="$router.push('/rss')">
        <el-icon><Promotion /></el-icon>
        前往订阅
      </button>
    </div>

    <!-- Active Tasks -->
    <div v-if="collectTasks.size > 0" class="tasks-panel cyber-card">
      <div class="panel-header">
        <span class="panel-title">
          <span class="status-dot online pulse"></span>
          活动任务
        </span>
      </div>
      <div class="tasks-grid">
        <div v-for="[taskId, task] in collectTasks" :key="taskId" class="task-item">
          <div class="task-info">
            <span class="task-keyword">{{ task.keyword }}</span>
            <span
              class="task-status"
              :style="{ '--status-color': getTaskStatusConfig(task.status).color }"
            >
              {{ getTaskStatusConfig(task.status).label }}
            </span>
          </div>
          <span v-if="task.status === 'completed'" class="task-count">
            +{{ task.collected_count }} 条
          </span>
          <div class="task-progress" v-if="task.status === 'running'">
            <div class="progress-bar"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Keywords Table -->
    <div class="table-container cyber-card">
      <el-table :data="keywords" v-loading="loading">
        <el-table-column prop="keyword" label="主体名称" min-width="180">
          <template #default="{ row }">
            <div class="keyword-cell">
              <span class="keyword-text">{{ row.keyword }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="priority" label="优先级" width="120">
          <template #default="{ row }">
            <span
              class="priority-tag"
              :style="{ '--tag-color': getPriorityConfig(row.priority)?.color }"
            >
              {{ getPriorityConfig(row.priority)?.label }}
            </span>
          </template>
        </el-table-column>

        <el-table-column prop="platforms" label="数据来源" min-width="200">
          <template #default="{ row }">
            <div class="data-source-tags">
              <!-- API 平台标签 -->
              <span
                v-for="p in row.platforms ?? []"
                :key="p"
                class="source-tag api"
                :style="{ '--tag-color': getPlatformColor(p) }"
              >
                {{ getPlatformLabel(p) }}
              </span>
              <!-- RSS 数据源标签 -->
              <span
                v-if="getRssCount(row) > 0"
                class="source-tag rss"
              >
                <el-icon><Link /></el-icon>
                RSS ({{ getRssCount(row) }})
              </span>
              <!-- 无数据源时显示 -->
              <span v-if="!hasDataSources(row)" class="source-tag empty">
                未配置
              </span>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="fetch_interval" label="更新间隔" width="100">
          <template #default="{ row }">
            <span class="interval-text">{{ formatFetchInterval(row.fetch_interval) }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="last_fetched" label="最近扫描" width="160">
          <template #default="{ row }">
            <span class="time-text" :class="{ 'never-scanned': !row.last_fetched }">
              {{ formatLastFetched(row.last_fetched) }}
            </span>
          </template>
        </el-table-column>

        <el-table-column prop="is_active" label="状态" width="100">
          <template #default="{ row }">
            <span class="status-badge" :class="{ active: row.is_active }">
              {{ row.is_active ? '运行中' : '已暂停' }}
            </span>
          </template>
        </el-table-column>

        <el-table-column prop="created_at" label="创建时间" width="160">
          <template #default="{ row }">
            <span class="time-text">{{ new Date(row.created_at).toLocaleDateString() }}</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons">
              <button class="action-btn detail" @click="viewDetail(row)">
                <el-icon><View /></el-icon>
                详情
              </button>
              <button
                class="action-btn refresh"
                :class="{ disabled: refreshingKeywords.has(row.id) }"
                :disabled="refreshingKeywords.has(row.id)"
                @click="handleRefresh(row)"
              >
                <el-icon><Download /></el-icon>
                {{ refreshingKeywords.has(row.id) ? '刷新中...' : '立即更新' }}
              </button>
              <button class="action-btn edit" @click="handleEdit(row)">
                <el-icon><Edit /></el-icon>
              </button>
              <button class="action-btn delete" @click="handleDelete(row)">
                <el-icon><Delete /></el-icon>
              </button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Create/Edit Dialog -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="680px" class="cyber-dialog">
      <div class="dialog-content">
        <!-- 基本信息 -->
        <div class="form-row">
          <div class="form-group flex-2">
            <label class="form-label">主体名称</label>
            <input
              v-model="form.keyword"
              type="text"
              class="cyber-input"
              placeholder="输入要监控的公司/品牌/人名"
            />
          </div>
          <div class="form-group flex-1">
            <label class="form-label">优先级</label>
            <div class="priority-selector">
              <button
                v-for="item in priorityOptions"
                :key="item.value"
                class="priority-option"
                :class="{ active: form.priority === item.value }"
                :style="{ '--option-color': item.color }"
                @click="form.priority = item.value"
              >
                {{ item.label }}
              </button>
            </div>
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">更新间隔</label>
          <div class="interval-selector">
            <button
              v-for="item in fetchIntervalOptions"
              :key="item.value"
              class="interval-option"
              :class="{ active: form.fetch_interval === item.value }"
              @click="form.fetch_interval = item.value"
            >
              {{ item.label }}
            </button>
          </div>
        </div>

        <!-- RSS 数据源（突出显示） -->
        <div class="form-group rss-section" v-if="rssFeeds.length > 0">
          <div class="section-header">
            <label class="form-label">
              <span class="label-icon">📡</span>
              RSS 数据源
              <span class="label-hint">推荐：自动定时获取，稳定可靠</span>
            </label>
            <button
              class="select-all-btn"
              :class="{ active: isAllRssSelected() }"
              @click="toggleAllRss"
            >
              {{ isAllRssSelected() ? '取消全选' : '全选' }}
            </button>
          </div>
          <div class="rss-source-grid">
            <label
              v-for="feed in rssFeeds"
              :key="feed.id"
              class="rss-card"
              :class="{ active: form.data_sources?.rss_ids?.includes(feed.id) }"
            >
              <input
                type="checkbox"
                :value="feed.id"
                v-model="form.data_sources.rss_ids"
                hidden
              />
              <div class="rss-card-content">
                <span class="rss-name">{{ feed.name }}</span>
                <span class="rss-type-tag">{{ feed.source_type }}</span>
              </div>
              <span class="check-icon">✓</span>
            </label>
          </div>
        </div>

        <!-- 采集平台（辅助） -->
        <div class="form-group platform-section">
          <div class="section-header">
            <label class="form-label secondary">
              <span class="label-icon">🔍</span>
              API 搜索采集
              <span class="label-hint">辅助：按需搜索补充</span>
            </label>
            <button
              class="select-all-btn small"
              :class="{ active: isAllPlatformsSelected() }"
              @click="toggleAllPlatforms"
            >
              {{ isAllPlatformsSelected() ? '取消全选' : '全选' }}
            </button>
          </div>
          <div class="platform-grid-compact">
            <label
              v-for="item in platformOptions"
              :key="item.value"
              class="platform-chip"
              :class="{ active: form.platforms?.includes(item.value) }"
              :style="{ '--chip-color': item.color }"
            >
              <input
                type="checkbox"
                :value="item.value"
                v-model="form.platforms"
                hidden
              />
              <span class="chip-label">{{ item.label }}</span>
            </label>
          </div>
        </div>

        <!-- 预警配置 -->
        <div class="form-group alert-section">
          <div class="section-header">
            <label class="form-label">
              <span class="label-icon">🔔</span>
              预警配置
              <span class="label-hint">设置预警触发条件</span>
            </label>
          </div>

          <div class="alert-config-items">
            <!-- 负面情感爆发预警 -->
            <div class="alert-config-item">
              <div class="alert-config-header" @click="toggleNegativeBurst">
                <div class="toggle-switch" :class="{ active: alertConfig.negative_burst?.enabled }">
                  <span class="toggle-knob"></span>
                </div>
                <div class="alert-config-info">
                  <span class="alert-config-title">负面情感爆发</span>
                  <span class="alert-config-desc">当负面情感文章占比超过阈值时触发预警</span>
                </div>
              </div>
              <div v-if="alertConfig.negative_burst?.enabled" class="alert-config-params">
                <div class="param-row">
                  <label>负面占比阈值</label>
                  <div class="param-input-group">
                    <input
                      type="number"
                      v-model.number="alertConfig.negative_burst!.threshold"
                      min="0"
                      max="1"
                      step="0.1"
                      class="cyber-input small"
                    />
                    <span class="param-unit">（{{ Math.round((alertConfig.negative_burst?.threshold ?? 0.3) * 100) }}%）</span>
                  </div>
                </div>
                <div class="param-row">
                  <label>最少文章数</label>
                  <input
                    type="number"
                    v-model.number="alertConfig.negative_burst!.min_count"
                    min="1"
                    class="cyber-input small"
                  />
                </div>
              </div>
            </div>

            <!-- 敏感词预警 -->
            <div class="alert-config-item">
              <div class="alert-config-header" @click="toggleSensitiveKeyword">
                <div class="toggle-switch" :class="{ active: alertConfig.sensitive_keyword?.enabled }">
                  <span class="toggle-knob"></span>
                </div>
                <div class="alert-config-info">
                  <span class="alert-config-title">敏感词预警</span>
                  <span class="alert-config-desc">当文章包含敏感词时触发预警</span>
                </div>
              </div>
              <div v-if="alertConfig.sensitive_keyword?.enabled" class="alert-config-params">
                <div class="param-row">
                  <label>使用全局敏感词库</label>
                  <div class="toggle-switch small" :class="{ active: alertConfig.sensitive_keyword?.use_global }" @click="toggleUseGlobal">
                    <span class="toggle-knob"></span>
                  </div>
                </div>
                <div class="param-row column">
                  <label>自定义敏感词</label>
                  <input
                    type="text"
                    v-model="customKeywordsInput"
                    class="cyber-input"
                    placeholder="输入敏感词，多个用逗号分隔"
                  />
                </div>
              </div>
            </div>

            <!-- 讨论量激增预警 -->
            <div class="alert-config-item">
              <div class="alert-config-header" @click="toggleVolumeSpike">
                <div class="toggle-switch" :class="{ active: alertConfig.volume_spike?.enabled }">
                  <span class="toggle-knob"></span>
                </div>
                <div class="alert-config-info">
                  <span class="alert-config-title">讨论量激增</span>
                  <span class="alert-config-desc">当讨论量相比历史平均值增长超过阈值时触发</span>
                </div>
              </div>
              <div v-if="alertConfig.volume_spike?.enabled" class="alert-config-params">
                <div class="param-row">
                  <label>增长倍数阈值</label>
                  <div class="param-input-group">
                    <input
                      type="number"
                      v-model.number="alertConfig.volume_spike!.threshold"
                      min="1"
                      step="0.5"
                      class="cyber-input small"
                    />
                    <span class="param-unit">倍（{{ Math.round((alertConfig.volume_spike?.threshold ?? 2) * 100 - 100) }}%）</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <button class="btn-secondary" @click="dialogVisible = false">取消</button>
          <button class="btn-primary" :disabled="formLoading" @click="handleSubmit">
            {{ formLoading ? '处理中...' : '确定' }}
          </button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.keywords-page {
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
  color: var(--neon-orange);
  margin-right: 8px;
}

/* Buttons */
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
}

.btn-primary:hover {
  box-shadow: var(--glow-cyan);
  transform: translateY(-2px);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.btn-secondary {
  padding: 12px 24px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  font-family: var(--font-display);
  font-size: 0.8rem;
  letter-spacing: 0.05em;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-normal);
}

.btn-secondary:hover {
  border-color: var(--text-secondary);
  color: var(--text-primary);
}

/* Tasks Panel */
.tasks-panel {
  margin-bottom: 20px;
}

.panel-header {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
}

.panel-title {
  font-family: var(--font-display);
  font-size: 0.75rem;
  font-weight: 500;
  letter-spacing: 0.1em;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 8px;
}

.tasks-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  padding: 16px;
}

.task-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
}

.task-keyword {
  font-weight: 500;
  color: var(--text-primary);
}

.task-status {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: var(--status-color);
}

.task-count {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: var(--neon-green);
}

.task-progress {
  width: 40px;
  height: 3px;
  background: var(--bg-secondary);
  border-radius: 2px;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background: var(--neon-cyan);
  animation: progress 1.5s ease-in-out infinite;
}

@keyframes progress {
  0% { width: 0%; margin-left: 0; }
  50% { width: 60%; margin-left: 20%; }
  100% { width: 0%; margin-left: 100%; }
}

/* Table */
.table-container {
  overflow: hidden;
}

.keyword-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.keyword-text {
  font-weight: 500;
  color: var(--text-primary);
}

.priority-tag {
  display: inline-block;
  padding: 4px 12px;
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: var(--tag-color);
  border: 1px solid var(--tag-color);
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.2);
}

.data-source-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

.source-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  font-family: var(--font-mono);
  font-size: 0.65rem;
  border-radius: 3px;
  background: rgba(0, 0, 0, 0.2);
}

.source-tag.api {
  color: var(--tag-color);
  border: 1px solid var(--tag-color);
}

.source-tag.rss {
  color: #a855f7;
  border: 1px solid #a855f7;
  background: rgba(168, 85, 247, 0.1);
}

.source-tag.rss .el-icon {
  font-size: 0.7rem;
}

.source-tag.empty {
  color: #8b95a8;
  border: 1px dashed #8b95a8;
  font-style: italic;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  font-family: var(--font-mono);
  font-size: 0.7rem;
  border-radius: 12px;
  background: rgba(139, 149, 168, 0.2);
  color: var(--text-secondary);
}

.status-badge.active {
  background: rgba(0, 255, 136, 0.15);
  color: var(--neon-green);
}

.status-badge.active::before {
  content: '';
  width: 6px;
  height: 6px;
  background: var(--neon-green);
  border-radius: 50%;
  animation: pulse 2s infinite;
}

.time-text {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.time-text.never-scanned {
  color: #8b95a8;
  font-style: italic;
}

/* Action Buttons */
.action-buttons {
  display: flex;
  gap: 8px;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
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

.action-btn.detail:hover {
  border-color: #a855f7;
  color: #a855f7;
  box-shadow: 0 0 10px rgba(168, 85, 247, 0.2);
}

.action-btn.refresh:hover {
  border-color: var(--neon-green);
  color: var(--neon-green);
  box-shadow: 0 0 10px rgba(0, 255, 136, 0.2);
}

.action-btn.edit:hover {
  border-color: var(--neon-orange);
  color: var(--neon-orange);
}

.action-btn.delete:hover {
  border-color: var(--neon-red);
  color: var(--neon-red);
}

.action-btn.disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none !important;
}

/* Dialog */
.dialog-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.form-label {
  font-family: var(--font-display);
  font-size: 0.7rem;
  font-weight: 500;
  letter-spacing: 0.1em;
  color: var(--text-secondary);
  text-transform: uppercase;
}

.cyber-input {
  width: 100%;
  padding: 14px 16px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  font-family: var(--font-body);
  font-size: 0.9rem;
  color: var(--text-primary);
  transition: all var(--transition-normal);
}

.cyber-input::placeholder {
  color: var(--text-muted);
}

.cyber-input:focus {
  outline: none;
  border-color: var(--neon-cyan);
  box-shadow: 0 0 15px rgba(0, 240, 255, 0.2);
}

/* Form Row Layout */
.form-row {
  display: flex;
  gap: 16px;
}

.form-row .form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-row .flex-2 {
  flex: 2;
}

.form-row .flex-1 {
  flex: 1;
}

.form-row .priority-selector {
  display: flex;
  gap: 8px;
}

.form-row .priority-option {
  flex: 1;
  padding: 10px 8px;
  font-size: 0.7rem;
}

/* Section Header with Select All */
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.section-header .form-label {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 0;
}

.section-header .form-label.secondary {
  color: var(--text-muted);
}

.label-icon {
  font-size: 1rem;
}

.label-hint {
  font-size: 0.7rem;
  font-weight: 400;
  color: var(--text-muted);
  margin-left: 4px;
}

.select-all-btn {
  padding: 6px 14px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  font-family: var(--font-display);
  font-size: 0.7rem;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.select-all-btn:hover {
  border-color: var(--neon-cyan);
  color: var(--neon-cyan);
}

.select-all-btn.active {
  background: rgba(0, 240, 255, 0.15);
  border-color: var(--neon-cyan);
  color: var(--neon-cyan);
}

.select-all-btn.small {
  padding: 4px 10px;
  font-size: 0.65rem;
}

/* RSS Section - Highlighted */
.rss-section {
  padding: 16px;
  background: linear-gradient(135deg, rgba(0, 240, 255, 0.08), rgba(0, 240, 255, 0.02));
  border: 1px solid rgba(0, 240, 255, 0.3);
  border-radius: var(--radius-md);
  margin-top: 8px;
}

.rss-source-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.rss-card {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.rss-card:hover {
  border-color: var(--neon-cyan);
}

.rss-card.active {
  border-color: var(--neon-cyan);
  background: rgba(0, 240, 255, 0.1);
}

.rss-card-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.rss-card .rss-name {
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--text-primary);
}

.rss-type-tag {
  display: inline-block;
  width: fit-content;
  padding: 2px 8px;
  font-family: var(--font-mono);
  font-size: 0.6rem;
  border-radius: 3px;
  background: rgba(0, 240, 255, 0.15);
  color: var(--neon-cyan);
  text-transform: uppercase;
}

.rss-card .check-icon {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--bg-secondary);
  color: transparent;
  font-size: 0.7rem;
  transition: all var(--transition-fast);
}

.rss-card.active .check-icon {
  background: var(--neon-cyan);
  color: var(--bg-primary);
}

/* Platform Section - Compact */
.platform-section {
  margin-top: 8px;
  padding: 12px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
}

.platform-grid-compact {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.platform-chip {
  padding: 6px 14px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 20px;
  font-size: 0.75rem;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.platform-chip:hover {
  border-color: var(--chip-color);
  color: var(--chip-color);
}

.platform-chip.active {
  background: rgba(0, 0, 0, 0.3);
  border-color: var(--chip-color);
  color: var(--chip-color);
}

.priority-selector {
  display: flex;
  gap: 10px;
}

.priority-option {
  flex: 1;
  padding: 12px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  font-family: var(--font-display);
  font-size: 0.75rem;
  letter-spacing: 0.05em;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-normal);
  text-align: center;
}

.priority-option:hover {
  border-color: var(--option-color);
  color: var(--option-color);
}

.priority-option.active {
  background: rgba(0, 0, 0, 0.3);
  border-color: var(--option-color);
  color: var(--option-color);
  box-shadow: 0 0 15px rgba(0, 0, 0, 0.3);
}

/* Interval Selector */
.interval-selector {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.interval-option {
  padding: 10px 14px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  font-family: var(--font-display);
  font-size: 0.75rem;
  letter-spacing: 0.05em;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-normal);
}

.interval-option:hover {
  border-color: var(--neon-cyan);
  color: var(--neon-cyan);
}

.interval-option.active {
  background: rgba(0, 240, 255, 0.15);
  border-color: var(--neon-cyan);
  color: var(--neon-cyan);
}

.interval-text {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--neon-cyan);
}

.platform-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.platform-option {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-normal);
}

.platform-option:hover {
  border-color: var(--option-color);
}

.platform-option.active {
  border-color: var(--option-color);
  background: rgba(0, 0, 0, 0.2);
}

.platform-option.active .checkbox-indicator {
  background: var(--option-color);
  border-color: var(--option-color);
}

.platform-option.active .checkbox-indicator::after {
  opacity: 1;
}

.checkbox-indicator {
  width: 18px;
  height: 18px;
  border: 2px solid var(--border-color);
  border-radius: 4px;
  position: relative;
  transition: all var(--transition-fast);
}

.checkbox-indicator::after {
  content: '';
  position: absolute;
  left: 5px;
  top: 2px;
  width: 4px;
  height: 8px;
  border: solid var(--bg-primary);
  border-width: 0 2px 2px 0;
  transform: rotate(45deg);
  opacity: 0;
  transition: opacity var(--transition-fast);
}

.option-label {
  font-size: 0.85rem;
  color: var(--text-primary);
}

.time-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.time-option {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.time-option:hover {
  border-color: var(--neon-cyan);
}

.time-option.active {
  border-color: var(--neon-cyan);
  background: rgba(0, 240, 255, 0.1);
}

.radio-indicator {
  width: 16px;
  height: 16px;
  border: 2px solid var(--border-color);
  border-radius: 50%;
  position: relative;
  transition: all var(--transition-fast);
}

.time-option.active .radio-indicator {
  border-color: var(--neon-cyan);
}

.time-option.active .radio-indicator::after {
  content: '';
  position: absolute;
  left: 3px;
  top: 3px;
  width: 6px;
  height: 6px;
  background: var(--neon-cyan);
  border-radius: 50%;
}

.mode-toggle {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 16px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-normal);
}

.mode-toggle:hover {
  border-color: var(--neon-orange);
}

.mode-toggle.active {
  border-color: var(--neon-orange);
  background: rgba(255, 107, 44, 0.1);
}

.toggle-switch {
  width: 44px;
  height: 24px;
  background: var(--bg-secondary);
  border-radius: 12px;
  position: relative;
  transition: all var(--transition-normal);
  flex-shrink: 0;
}

.toggle-switch::after {
  content: '';
  position: absolute;
  left: 3px;
  top: 3px;
  width: 18px;
  height: 18px;
  background: var(--text-secondary);
  border-radius: 50%;
  transition: all var(--transition-normal);
}

.mode-toggle.active .toggle-switch {
  background: var(--neon-orange);
}

.mode-toggle.active .toggle-switch::after {
  left: 23px;
  background: white;
}

.toggle-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.toggle-label {
  font-weight: 500;
  color: var(--text-primary);
}

.toggle-hint {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

/* Tip Card */
.tip-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 20px;
  margin-bottom: 20px;
  background: linear-gradient(135deg, rgba(168, 85, 247, 0.1), rgba(168, 85, 247, 0.03));
  border: 1px solid rgba(168, 85, 247, 0.3);
  border-radius: var(--radius-md);
}

.tip-content {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.tip-icon {
  font-size: 1.2rem;
  line-height: 1;
}

.tip-text {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.tip-title {
  font-family: var(--font-display);
  font-size: 0.85rem;
  font-weight: 600;
  color: #a855f7;
  letter-spacing: 0.05em;
}

.tip-desc {
  font-size: 0.75rem;
  color: var(--text-muted);
  line-height: 1.5;
}

.tip-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 16px;
  background: linear-gradient(135deg, rgba(168, 85, 247, 0.3), rgba(168, 85, 247, 0.15));
  border: 1px solid #a855f7;
  border-radius: var(--radius-md);
  font-family: var(--font-display);
  font-size: 0.75rem;
  font-weight: 500;
  letter-spacing: 0.05em;
  color: #a855f7;
  cursor: pointer;
  transition: all var(--transition-normal);
  text-decoration: none;
  white-space: nowrap;
}

.tip-btn:hover {
  background: rgba(168, 85, 247, 0.3);
  box-shadow: 0 0 15px rgba(168, 85, 247, 0.4);
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(0.9); }
}

/* RSS Source List */
.rss-source-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 200px;
  overflow-y: auto;
  padding-right: 4px;
}

.rss-source-list::-webkit-scrollbar {
  width: 4px;
}

.rss-source-list::-webkit-scrollbar-track {
  background: var(--bg-tertiary);
  border-radius: 2px;
}

.rss-source-list::-webkit-scrollbar-thumb {
  background: var(--border-color);
  border-radius: 2px;
}

.rss-option {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.rss-option:hover {
  border-color: var(--neon-cyan);
}

.rss-option.active {
  border-color: var(--neon-cyan);
  background: rgba(0, 240, 255, 0.1);
}

.rss-option.active .checkbox-indicator {
  background: var(--neon-cyan);
  border-color: var(--neon-cyan);
}

.rss-option.active .checkbox-indicator::after {
  opacity: 1;
}

.rss-name {
  flex: 1;
  font-size: 0.85rem;
  color: var(--text-primary);
}

.rss-type {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  padding: 2px 8px;
  border-radius: 3px;
  background: rgba(0, 240, 255, 0.15);
  color: var(--neon-cyan);
  text-transform: uppercase;
}

/* Alert Configuration Section */
.alert-section {
  padding: 16px;
  background: linear-gradient(135deg, rgba(255, 51, 102, 0.08), rgba(255, 51, 102, 0.02));
  border: 1px solid rgba(255, 51, 102, 0.3);
  border-radius: var(--radius-md);
  margin-top: 8px;
}

.alert-config-items {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.alert-config-item {
  padding: 12px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
}

.alert-config-header {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
}

.alert-config-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.alert-config-title {
  font-family: var(--font-display);
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--text-primary);
}

.alert-config-desc {
  font-size: 0.7rem;
  color: var(--text-muted);
}

.alert-config-params {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.param-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.param-row.column {
  flex-direction: column;
  align-items: stretch;
}

.param-row label {
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.param-input-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.param-unit {
  font-size: 0.7rem;
  color: var(--text-muted);
}

.cyber-input.small {
  width: 80px;
  padding: 8px 12px;
  font-size: 0.85rem;
}

/* Toggle Switch */
.toggle-switch {
  width: 44px;
  height: 24px;
  background: var(--bg-secondary);
  border-radius: 12px;
  position: relative;
  transition: all var(--transition-normal);
  flex-shrink: 0;
}

.toggle-switch.small {
  width: 36px;
  height: 20px;
}

.toggle-knob {
  position: absolute;
  left: 3px;
  top: 3px;
  width: 18px;
  height: 18px;
  background: var(--text-secondary);
  border-radius: 50%;
  transition: all var(--transition-normal);
}

.toggle-switch.small .toggle-knob {
  width: 14px;
  height: 14px;
}

.toggle-switch.active {
  background: var(--neon-cyan);
}

.toggle-switch.active .toggle-knob {
  left: 23px;
  background: var(--bg-primary);
}

.toggle-switch.small.active .toggle-knob {
  left: 19px;
}
</style>
