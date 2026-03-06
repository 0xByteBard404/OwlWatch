<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Plus,
  Edit,
  Delete,
  Refresh,
  Link,
  VideoPlay,
  Promotion,
} from '@element-plus/icons-vue'
import {
  rssApi,
  keywordsApi,
  type RSSFeed,
  type RSSFeedCreate,
  type RSSFeedUpdate,
  type RSSHubPlatform,
  type Keyword,
} from '@/api'

const feeds = ref<RSSFeed[]>([])
const keywords = ref<Keyword[]>([])
const loading = ref(false)

// 对话框
const dialogVisible = ref(false)
const dialogTitle = ref('添加订阅')
const formLoading = ref(false)
const editingId = ref<string | null>(null)

// 表单
const form = ref<RSSFeedCreate>({
  name: '',
  feed_url: '',
  source_type: 'generic',
  keyword_id: undefined,
  fetch_interval: 300,
})

// RSSHub 快捷创建
const rsshubDialogVisible = ref(false)
const rsshubPlatforms = ref<Record<string, RSSHubPlatform>>({})
const selectedPlatform = ref('')
const selectedRoute = ref('')
const rsshubParams = ref<Record<string, string>>({})
const rsshubLoading = ref(false)
const selectedCategory = ref('')

// 获取所有分类
const categories = computed(() => {
  const cats = new Set<string>()
  Object.values(rsshubPlatforms.value).forEach(p => {
    if (p.category) cats.add(p.category)
  })
  return ['全部', ...Array.from(cats)]
})

// 按分类筛选平台
const filteredPlatforms = computed(() => {
  if (!selectedCategory.value || selectedCategory.value === '全部') {
    return rsshubPlatforms.value
  }
  const filtered: Record<string, RSSHubPlatform> = {}
  Object.entries(rsshubPlatforms.value).forEach(([key, platform]) => {
    if (platform.category === selectedCategory.value) {
      filtered[key] = platform
    }
  })
  return filtered
})

const sourceTypeOptions = [
  // 社交媒体
  { label: '微博', value: 'weibo', icon: '🐦', category: '社交媒体' },
  { label: '知乎', value: 'zhihu', icon: '📘', category: '社交媒体' },
  { label: 'B站', value: 'bilibili', icon: '📺', category: '社交媒体' },
  { label: '小红书', value: 'xiaohongshu', icon: '📕', category: '社交媒体' },
  { label: '抖音', value: 'douyin', icon: '🎵', category: '社交媒体' },
  { label: 'Twitter/X', value: 'twitter', icon: '𝕏', category: '社交媒体' },
  { label: 'Instagram', value: 'instagram', icon: '📸', category: '社交媒体' },
  { label: 'Threads', value: 'threads', icon: '🧵', category: '社交媒体' },
  // 资讯平台
  { label: '微信公众号', value: 'wechat', icon: '💚', category: '资讯平台' },
  { label: '今日头条', value: 'toutiao', icon: '📰', category: '资讯平台' },
  // 视频平台
  { label: 'YouTube', value: 'youtube', icon: '▶️', category: '视频平台' },
  { label: 'TikTok', value: 'tiktok', icon: '🎬', category: '视频平台' },
  // 财经科技
  { label: '36氪', value: '36kr', icon: '💼', category: '财经科技' },
  { label: '华尔街见闻', value: 'wallstreetcn', icon: '📈', category: '财经科技' },
  { label: '财联社', value: 'cls', icon: '💰', category: '财经科技' },
  { label: 'Hacker News', value: 'hackernews', icon: '🔶', category: '财经科技' },
  { label: 'Product Hunt', value: 'producthunt', icon: '🚀', category: '财经科技' },
  // 社区论坛
  { label: '百度贴吧', value: 'tieba', icon: '💬', category: '社区论坛' },
  { label: '豆瓣', value: 'douban', icon: '🎬', category: '社区论坛' },
  { label: 'Reddit', value: 'reddit', icon: '🤖', category: '社区论坛' },
  { label: 'V2EX', value: 'v2ex', icon: '🖥️', category: '社区论坛' },
  // 新闻媒体
  { label: 'BBC', value: 'bbc', icon: '🇬🇧', category: '新闻媒体' },
  { label: 'CNN', value: 'cnn', icon: '🇺🇸', category: '新闻媒体' },
  { label: '纽约时报', value: 'nytimes', icon: '📰', category: '新闻媒体' },
  { label: '澎湃新闻', value: 'thepaper', icon: '🌊', category: '新闻媒体' },
  { label: '凤凰网', value: 'ifeng', icon: '🔴', category: '新闻媒体' },
  { label: '财新网', value: 'caixin', icon: '📊', category: '新闻媒体' },
  // 开发者
  { label: 'GitHub', value: 'github', icon: '🐙', category: '开发者' },
  { label: 'NPM', value: 'npm', icon: '📦', category: '开发者' },
  { label: 'PyPI', value: 'pypi', icon: '🐍', category: '开发者' },
  // 学术
  { label: 'arXiv', value: 'arxiv', icon: '📄', category: '学术' },
  // 设计
  { label: 'Dribbble', value: 'dribbble', icon: '🏀', category: '设计' },
  { label: 'Behance', value: 'behance', icon: '🎨', category: '设计' },
  // 通用
  { label: '通用 RSS', value: 'generic', icon: '📡', category: '其他' },
]

const intervalOptions = [
  { label: '5 分钟', value: 300 },
  { label: '10 分钟', value: 600 },
  { label: '15 分钟', value: 900 },
  { label: '30 分钟', value: 1800 },
  { label: '1 小时', value: 3600 },
]

// 获取当前选中平台的路由
const currentPlatformRoutes = computed(() => {
  if (!selectedPlatform.value || !rsshubPlatforms.value[selectedPlatform.value]) {
    return []
  }
  return rsshubPlatforms.value[selectedPlatform.value]?.routes || []
})

// 获取当前路由需要的参数
const currentRouteParams = computed(() => {
  if (!selectedRoute.value) return []
  const route = currentPlatformRoutes.value.find(r => r.path === selectedRoute.value)
  return route?.params || []
})

const fetchData = async () => {
  loading.value = true
  try {
    feeds.value = await rssApi.list()
  } catch (error) {
    console.error('Failed to fetch RSS feeds:', error)
  } finally {
    loading.value = false
  }
}

const fetchKeywords = async () => {
  try {
    keywords.value = await keywordsApi.list()
  } catch (error) {
    console.error('Failed to fetch keywords:', error)
  }
}

const fetchRSSHubPlatforms = async () => {
  try {
    rsshubPlatforms.value = await rssApi.getPlatforms()
  } catch (error) {
    console.error('Failed to fetch RSSHub platforms:', error)
  }
}

const handleCreate = () => {
  dialogTitle.value = '添加订阅'
  editingId.value = null
  form.value = {
    name: '',
    feed_url: '',
    source_type: 'generic',
    keyword_id: undefined,
    fetch_interval: 300,
  }
  dialogVisible.value = true
}

const handleEdit = (row: RSSFeed) => {
  dialogTitle.value = '编辑订阅'
  editingId.value = row.id
  form.value = {
    name: row.name,
    feed_url: row.feed_url,
    source_type: row.source_type || 'generic',
    keyword_id: row.keyword_id || undefined,
    fetch_interval: row.fetch_interval || 300,
  }
  dialogVisible.value = true
}

const handleSubmit = async () => {
  if (!form.value.name.trim()) {
    ElMessage.warning('请输入订阅名称')
    return
  }
  if (!form.value.feed_url.trim()) {
    ElMessage.warning('请输入 RSS 地址')
    return
  }

  formLoading.value = true
  try {
    if (editingId.value) {
      const updateData: RSSFeedUpdate = { ...form.value }
      await rssApi.update(editingId.value, updateData)
      ElMessage.success('更新成功')
    } else {
      await rssApi.create(form.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchData()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '操作失败')
  } finally {
    formLoading.value = false
  }
}

const handleDelete = async (row: RSSFeed) => {
  try {
    await ElMessageBox.confirm(`确定要删除订阅「${row.name}」吗？`, '确认删除', {
      type: 'warning',
    })
    await rssApi.delete(row.id)
    ElMessage.success('删除成功')
    fetchData()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error?.response?.data?.detail || '删除失败')
    }
  }
}

const handleFetch = async (row: RSSFeed) => {
  try {
    const result = await rssApi.fetch(row.id)
    ElMessage.success(result.message)
    fetchData()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '获取失败')
  }
}

const handleToggleActive = async (row: RSSFeed) => {
  try {
    await rssApi.update(row.id, { is_active: !row.is_active })
    ElMessage.success(row.is_active ? '已暂停' : '已启用')
    fetchData()
  } catch (error: any) {
    ElMessage.error('操作失败')
  }
}

// RSSHub 快捷创建
const openRSSHubDialog = async () => {
  selectedPlatform.value = ''
  selectedRoute.value = ''
  rsshubParams.value = {}
  rsshubDialogVisible.value = true

  if (Object.keys(rsshubPlatforms.value).length === 0) {
    await fetchRSSHubPlatforms()
  }
}

const handlePlatformChange = () => {
  selectedRoute.value = ''
  rsshubParams.value = {}
}

const handleRouteChange = () => {
  // 初始化参数
  const params: Record<string, string> = {}
  currentRouteParams.value.forEach(p => {
    params[p] = ''
  })
  rsshubParams.value = params
}

const buildRSSHubUrl = async () => {
  // 检查参数是否填写完整
  const emptyParams = currentRouteParams.value.filter(p => !rsshubParams.value[p])
  if (emptyParams.length > 0) {
    ElMessage.warning(`请填写参数: ${emptyParams.join(', ')}`)
    return
  }

  rsshubLoading.value = true
  try {
    const result = await rssApi.buildUrl({
      platform: selectedPlatform.value,
      route_path: selectedRoute.value,
      params: rsshubParams.value,
    })

    // 填充表单
    form.value.feed_url = result.url
    form.value.source_type = selectedPlatform.value
    form.value.name = `${rsshubPlatforms.value[selectedPlatform.value]?.name || selectedPlatform.value} - ${result.route_name}`

    rsshubDialogVisible.value = false
    dialogVisible.value = true
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '构建失败')
  } finally {
    rsshubLoading.value = false
  }
}

const getSourceTypeLabel = (type: string | null) => {
  const option = sourceTypeOptions.find(o => o.value === type)
  return option ? `${option.icon} ${option.label}` : '📡 通用 RSS'
}

const getStatusColor = (row: RSSFeed) => {
  if (!row.is_active) return '#8b95a8'
  if (row.fetch_error_count > 3) return '#ff3366'
  return '#00ff88'
}

const openUrl = (url: string) => {
  if (url) {
    window.open(url, '_blank')
  }
}

onMounted(() => {
  fetchData()
  fetchKeywords()
})
</script>

<template>
  <div class="rss-page">
    <!-- Page Header -->
    <div class="page-header">
      <div class="header-left">
        <h3 class="page-title">
          <span class="title-icon">◈</span>
          RSS 订阅
        </h3>
        <span class="subtitle">RSS SUBSCRIPTIONS</span>
      </div>
      <div class="header-actions">
        <button class="btn-rsshub" @click="openRSSHubDialog">
          <el-icon><Promotion /></el-icon>
          <span>RSSHub 快捷订阅</span>
        </button>
        <button class="btn-primary" @click="handleCreate">
          <el-icon><Plus /></el-icon>
          <span>添加订阅</span>
        </button>
      </div>
    </div>

    <!-- Stats -->
    <div class="stats-bar">
      <div class="stat-item">
        <span class="stat-label">订阅总数</span>
        <span class="stat-value data-value">{{ feeds.length }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">活跃订阅</span>
        <span class="stat-value data-value" style="color: var(--neon-green)">
          {{ feeds.filter(f => f.is_active).length }}
        </span>
      </div>
      <div class="stat-item">
        <span class="stat-label">累计条目</span>
        <span class="stat-value data-value" style="color: var(--neon-cyan)">
          {{ feeds.reduce((sum, f) => sum + (f.total_entries || 0), 0) }}
        </span>
      </div>
    </div>

    <!-- Feeds List -->
    <div class="feeds-list cyber-card">
      <el-table :data="feeds" v-loading="loading">
        <el-table-column prop="name" label="订阅名称" min-width="200">
          <template #default="{ row }">
            <div class="feed-name">
              <span class="name-text">{{ row.name }}</span>
              <span v-if="!row.is_active" class="paused-tag">已暂停</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="source_type" label="来源类型" width="140">
          <template #default="{ row }">
            <span class="type-tag">{{ getSourceTypeLabel(row.source_type) }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="feed_url" label="订阅地址" min-width="250">
          <template #default="{ row }">
            <div class="feed-url" @click="openUrl(row.feed_url)">
              <el-icon><Link /></el-icon>
              <span class="url-text">{{ row.feed_url }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="fetch_interval" label="更新间隔" width="100">
          <template #default="{ row }">
            <span class="interval-tag">{{ Math.floor(row.fetch_interval / 60) }}分钟</span>
          </template>
        </el-table-column>

        <el-table-column prop="last_fetched" label="最后获取" width="160">
          <template #default="{ row }">
            <span v-if="row.last_fetched" class="time-text">
              {{ new Date(row.last_fetched).toLocaleString() }}
            </span>
            <span v-else class="time-text" style="color: var(--text-muted)">从未获取</span>
          </template>
        </el-table-column>

        <el-table-column prop="total_entries" label="累计条目" width="100">
          <template #default="{ row }">
            <span class="entries-count data-value">{{ row.total_entries || 0 }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <div class="status-indicator" :style="{ '--status-color': getStatusColor(row) }">
              <span class="status-dot"></span>
              <span>{{ row.is_active ? (row.fetch_error_count > 3 ? '异常' : '正常') : '暂停' }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons">
              <button class="action-btn" @click="handleFetch(row)" title="立即获取">
                <el-icon><Refresh /></el-icon>
              </button>
              <button class="action-btn" @click="handleEdit(row)" title="编辑">
                <el-icon><Edit /></el-icon>
              </button>
              <button
                class="action-btn"
                :class="{ active: row.is_active }"
                @click="handleToggleActive(row)"
                :title="row.is_active ? '暂停' : '启用'"
              >
                <el-icon><VideoPlay /></el-icon>
              </button>
              <button class="action-btn delete" @click="handleDelete(row)" title="删除">
                <el-icon><Delete /></el-icon>
              </button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Create/Edit Dialog -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="600px" class="cyber-dialog">
      <el-form :model="form" label-width="100px" label-position="left">
        <el-form-item label="订阅名称" required>
          <el-input v-model="form.name" placeholder="如：微博-特斯拉关键词" />
        </el-form-item>

        <el-form-item label="RSS 地址" required>
          <el-input v-model="form.feed_url" placeholder="https://rsshub.app/weibo/keyword/特斯拉" />
        </el-form-item>

        <el-form-item label="来源类型">
          <el-select v-model="form.source_type" placeholder="选择来源类型">
            <el-option
              v-for="item in sourceTypeOptions"
              :key="item.value"
              :label="`${item.icon} ${item.label}`"
              :value="item.value"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="关联监控主体">
          <el-select v-model="form.keyword_id" placeholder="可选：关联到监控主体" clearable>
            <el-option
              v-for="item in keywords"
              :key="item.id"
              :label="item.keyword"
              :value="item.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="更新间隔">
          <el-select v-model="form.fetch_interval">
            <el-option
              v-for="item in intervalOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <button class="btn-cancel" @click="dialogVisible = false">取消</button>
          <button class="btn-submit" @click="handleSubmit" :loading="formLoading">
            {{ editingId ? '保存' : '创建' }}
          </button>
        </div>
      </template>
    </el-dialog>

    <!-- RSSHub Quick Create Dialog -->
    <el-dialog v-model="rsshubDialogVisible" title="RSSHub 快捷订阅" width="700px" class="cyber-dialog">
      <div class="rsshub-form">
        <!-- 分类筛选 -->
        <div class="form-group">
          <label class="form-label">选择分类</label>
          <div class="category-tabs">
            <button
              v-for="cat in categories"
              :key="cat"
              class="category-tab"
              :class="{ active: selectedCategory === cat }"
              @click="selectedCategory = cat; selectedPlatform = ''; selectedRoute = ''"
            >
              {{ cat }}
            </button>
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">选择平台</label>
          <el-select v-model="selectedPlatform" placeholder="选择平台" @change="handlePlatformChange" filterable>
            <el-option
              v-for="(platform, key) in filteredPlatforms"
              :key="key"
              :label="`${platform.category ? `[${platform.category}] ` : ''}${platform.name}`"
              :value="key"
            />
          </el-select>
        </div>

        <div class="form-group" v-if="selectedPlatform">
          <label class="form-label">选择订阅类型</label>
          <el-select v-model="selectedRoute" placeholder="选择订阅类型" @change="handleRouteChange">
            <el-option
              v-for="route in currentPlatformRoutes"
              :key="route.path"
              :label="route.name"
              :value="route.path"
            />
          </el-select>
        </div>

        <div class="form-group" v-if="currentRouteParams.length > 0">
          <label class="form-label">填写参数</label>
          <div class="params-grid">
            <div v-for="param in currentRouteParams" :key="param" class="param-item">
              <label>{{ param }}</label>
              <el-input v-model="rsshubParams[param]" :placeholder="`输入 ${param}`" />
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <button class="btn-cancel" @click="rsshubDialogVisible = false">取消</button>
          <button
            class="btn-submit"
            @click="buildRSSHubUrl"
            :loading="rsshubLoading"
            :disabled="!selectedPlatform || !selectedRoute"
          >
            生成订阅
          </button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.rss-page {
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
  color: var(--neon-orange);
  margin-right: 8px;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.btn-primary, .btn-rsshub {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  border-radius: var(--radius-md);
  font-family: var(--font-display);
  font-size: 0.8rem;
  font-weight: 500;
  letter-spacing: 0.05em;
  cursor: pointer;
  transition: all var(--transition-normal);
}

.btn-primary {
  background: linear-gradient(135deg, var(--neon-cyan-dim), var(--neon-cyan));
  border: none;
  color: var(--bg-primary);
}

.btn-primary:hover {
  box-shadow: var(--glow-cyan);
  transform: translateY(-2px);
}

.btn-rsshub {
  background: transparent;
  border: 1px solid var(--neon-orange);
  color: var(--neon-orange);
}

.btn-rsshub:hover {
  background: rgba(255, 107, 44, 0.1);
  box-shadow: 0 0 15px rgba(255, 107, 44, 0.3);
}

/* Stats Bar */
.stats-bar {
  display: flex;
  gap: 32px;
  margin-bottom: 20px;
  padding: 16px 20px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-label {
  font-family: var(--font-display);
  font-size: 0.65rem;
  letter-spacing: 0.1em;
  color: var(--text-muted);
  text-transform: uppercase;
}

.stat-value {
  font-family: var(--font-display);
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary);
}

/* Feeds List */
.feeds-list {
  overflow: hidden;
}

.feed-name {
  display: flex;
  align-items: center;
  gap: 8px;
}

.name-text {
  font-size: 0.85rem;
  color: var(--text-primary);
}

.paused-tag {
  padding: 2px 8px;
  background: rgba(139, 149, 168, 0.2);
  border-radius: 10px;
  font-size: 0.65rem;
  color: var(--text-muted);
}

.type-tag {
  font-size: 0.8rem;
}

.feed-url {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  color: var(--neon-cyan);
  transition: opacity var(--transition-fast);
}

.feed-url:hover {
  opacity: 0.8;
}

.url-text {
  font-size: 0.75rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 200px;
}

.interval-tag {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.time-text {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.entries-count {
  font-family: var(--font-mono);
  font-size: 0.85rem;
  color: var(--neon-cyan);
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.75rem;
  color: var(--status-color);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--status-color);
  box-shadow: 0 0 8px var(--status-color);
}

.action-buttons {
  display: flex;
  gap: 6px;
}

.action-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.action-btn:hover {
  border-color: var(--neon-cyan);
  color: var(--neon-cyan);
}

.action-btn.active {
  border-color: var(--neon-green);
  color: var(--neon-green);
}

.action-btn.delete:hover {
  border-color: var(--neon-red);
  color: var(--neon-red);
}

/* Dialog */
.rsshub-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-label {
  font-family: var(--font-display);
  font-size: 0.75rem;
  letter-spacing: 0.1em;
  color: var(--text-secondary);
}

.params-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.param-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.param-item label {
  font-size: 0.75rem;
  color: var(--text-muted);
  text-transform: capitalize;
}

/* Category Tabs */
.category-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.category-tab {
  padding: 6px 14px;
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

.category-tab:hover {
  border-color: var(--neon-cyan);
  color: var(--neon-cyan);
}

.category-tab.active {
  background: rgba(0, 240, 255, 0.1);
  border-color: var(--neon-cyan);
  color: var(--neon-cyan);
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.btn-cancel, .btn-submit {
  padding: 10px 24px;
  border-radius: var(--radius-sm);
  font-family: var(--font-display);
  font-size: 0.8rem;
  letter-spacing: 0.05em;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-cancel {
  background: transparent;
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
}

.btn-cancel:hover {
  border-color: var(--text-secondary);
  color: var(--text-primary);
}

.btn-submit {
  background: linear-gradient(135deg, var(--neon-cyan-dim), var(--neon-cyan));
  border: none;
  color: var(--bg-primary);
}

.btn-submit:hover {
  box-shadow: var(--glow-cyan);
}

.btn-submit:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Responsive */
@media (max-width: 1200px) {
  .stats-bar {
    flex-wrap: wrap;
  }
}
</style>
