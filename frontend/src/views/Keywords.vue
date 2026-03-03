<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Download,
  Edit,
  Delete,
  Plus,
} from '@element-plus/icons-vue'
import {
  keywordsApi,
  collectApi,
  type Keyword,
  type KeywordCreate,
} from '@/api'

const keywords = ref<Keyword[]>([])
const loading = ref(false)

const dialogVisible = ref(false)
const dialogTitle = ref('添加监控主体')
const formLoading = ref(false)

const form = ref<KeywordCreate>({
  keyword: '',
  priority: 'medium',
  platforms: ['baidu'],
})

const editingId = ref<string | null>(null)

const collectDialogVisible = ref(false)
const collectKeyword = ref<Keyword | null>(null)
const collectTimeRange = ref('oneDay')
const collectNegativeMode = ref(false)
const collectLoading = ref(false)

const collectTasks = ref<Map<string, { keyword: string; status: string; collected_count: number }>>(
  new Map()
)
const pollingTimers = ref<Map<string, number>>(new Map())

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

const timeRangeOptions = [
  { label: '最近 24 小时', value: 'oneDay' },
  { label: '最近 3 天', value: 'threeDays' },
  { label: '最近 1 周', value: 'oneWeek' },
  { label: '最近 1 个月', value: 'oneMonth' },
  { label: '最近 3 个月', value: 'threeMonths' },
]

const fetchData = async () => {
  loading.value = true
  try {
    keywords.value = await keywordsApi.list()
  } catch (error) {
    console.error('Failed to fetch keywords:', error)
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

const openCollectDialog = (row: Keyword) => {
  collectKeyword.value = row
  collectTimeRange.value = 'oneDay'
  collectNegativeMode.value = false
  collectDialogVisible.value = true
}

const pollTaskStatus = async (taskId: string, keywordText: string) => {
  try {
    const status = await collectApi.getStatus(taskId)

    collectTasks.value.set(taskId, {
      keyword: keywordText,
      status: status.status,
      collected_count: status.collected_count,
    })

    if (status.status === 'completed') {
      ElMessage.success(`「${keywordText}」采集完成，新增 ${status.collected_count} 条情报`)
      fetchData()
      stopPolling(taskId)
    } else if (status.status === 'failed') {
      ElMessage.error(`「${keywordText}」采集失败：${status.message}`)
      stopPolling(taskId)
    }
  } catch (error) {
    console.error('Failed to poll status:', error)
    stopPolling(taskId)
  }
}

const startPolling = (taskId: string, keywordText: string) => {
  pollTaskStatus(taskId, keywordText)
  const timer = window.setInterval(() => {
    pollTaskStatus(taskId, keywordText)
  }, 2000)
  pollingTimers.value.set(taskId, timer)
}

const stopPolling = (taskId: string) => {
  const timer = pollingTimers.value.get(taskId)
  if (timer) {
    clearInterval(timer)
    pollingTimers.value.delete(taskId)
  }
  setTimeout(() => {
    collectTasks.value.delete(taskId)
  }, 5000)
}

const handleCollect = async () => {
  if (!collectKeyword.value) return

  collectLoading.value = true
  try {
    const result = await collectApi.trigger(
      collectKeyword.value.id,
      collectTimeRange.value,
      collectNegativeMode.value
    )

    collectTasks.value.set(result.task_id, {
      keyword: result.keyword,
      status: 'pending',
      collected_count: 0,
    })

    ElMessage.info(`「${result.keyword}」采集任务已创建`)
    startPolling(result.task_id, result.keyword)
    collectDialogVisible.value = false
  } catch (error) {
    console.error('Failed to trigger collect:', error)
  } finally {
    collectLoading.value = false
  }
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

onUnmounted(() => {
  pollingTimers.value.forEach((timer) => clearInterval(timer))
})

const restoreRunningTasks = async () => {
  try {
    const result = await collectApi.getRunningTasks()
    for (const task of result.tasks) {
      collectTasks.value.set(task.task_id, {
        keyword: task.keyword,
        status: task.status,
        collected_count: task.collected_count,
      })
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

        <el-table-column prop="platforms" label="采集平台" width="260">
          <template #default="{ row }">
            <div class="platform-tags">
              <span
                v-for="p in row.platforms ?? []"
                :key="p"
                class="platform-tag"
                :style="{ '--tag-color': getPlatformColor(p) }"
              >
                {{ p }}
              </span>
            </div>
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

        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons">
              <button class="action-btn collect" @click="openCollectDialog(row)">
                <el-icon><Download /></el-icon>
                采集
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
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="500px" class="cyber-dialog">
      <div class="dialog-content">
        <div class="form-group">
          <label class="form-label">主体名称</label>
          <input
            v-model="form.keyword"
            type="text"
            class="cyber-input"
            placeholder="输入要监控的公司/品牌/人名"
          />
        </div>

        <div class="form-group">
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

        <div class="form-group">
          <label class="form-label">采集平台</label>
          <div class="platform-grid">
            <label
              v-for="item in platformOptions"
              :key="item.value"
              class="platform-option"
              :class="{ active: form.platforms?.includes(item.value) }"
              :style="{ '--option-color': item.color }"
            >
              <input
                type="checkbox"
                :value="item.value"
                v-model="form.platforms"
                hidden
              />
              <span class="checkbox-indicator"></span>
              <span class="option-label">{{ item.label }}</span>
            </label>
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

    <!-- Collect Dialog -->
    <el-dialog v-model="collectDialogVisible" title="采集配置" width="450px" class="cyber-dialog">
      <div class="dialog-content">
        <div class="collect-target">
          <span class="label">监控主体</span>
          <span class="value">{{ collectKeyword?.keyword }}</span>
        </div>

        <div class="form-group">
          <label class="form-label">时间范围</label>
          <div class="time-options">
            <label
              v-for="item in timeRangeOptions"
              :key="item.value"
              class="time-option"
              :class="{ active: collectTimeRange === item.value }"
            >
              <input type="radio" :value="item.value" v-model="collectTimeRange" hidden />
              <span class="radio-indicator"></span>
              <span>{{ item.label }}</span>
            </label>
          </div>
        </div>

        <div class="form-group">
          <label class="mode-toggle" :class="{ active: collectNegativeMode }">
            <input type="checkbox" v-model="collectNegativeMode" />
            <span class="toggle-switch"></span>
            <div class="toggle-info">
              <span class="toggle-label">负面舆情模式</span>
              <span class="toggle-hint">自动添加"违规、违法、投诉"等负面关键词组合搜索</span>
            </div>
          </label>
        </div>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <button class="btn-secondary" @click="collectDialogVisible = false">取消</button>
          <button class="btn-primary" :disabled="collectLoading" @click="handleCollect">
            {{ collectLoading ? '启动中...' : '开始采集' }}
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

.platform-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.platform-tag {
  padding: 2px 8px;
  font-family: var(--font-mono);
  font-size: 0.65rem;
  color: var(--tag-color);
  border: 1px solid var(--tag-color);
  border-radius: 3px;
  background: rgba(0, 0, 0, 0.2);
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

.action-btn.collect:hover {
  border-color: var(--neon-cyan);
  color: var(--neon-cyan);
  box-shadow: 0 0 10px rgba(0, 240, 255, 0.2);
}

.action-btn.edit:hover {
  border-color: var(--neon-orange);
  color: var(--neon-orange);
}

.action-btn.delete:hover {
  border-color: var(--neon-red);
  color: var(--neon-red);
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

.collect-target {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 16px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
}

.collect-target .label {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.collect-target .value {
  font-family: var(--font-display);
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--neon-cyan);
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

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(0.9); }
}
</style>
