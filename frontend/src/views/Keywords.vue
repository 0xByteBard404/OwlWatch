<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { keywordsApi, collectApi, type Keyword, type KeywordCreate } from '@/api'

// 数据列表
const keywords = ref<Keyword[]>([])
const loading = ref(false)

// 对话框
const dialogVisible = ref(false)
const dialogTitle = ref('添加监控主体')
const formLoading = ref(false)

// 表单数据
const form = ref<KeywordCreate>({
  keyword: '',
  priority: 'medium',
  platforms: ['baidu'],
})

const editingId = ref<string | null>(null)

// 采集对话框
const collectDialogVisible = ref(false)
const collectKeyword = ref<Keyword | null>(null)
const collectTimeRange = ref('oneDay')
const collectNegativeMode = ref(false)
const collectLoading = ref(false)

// 采集任务状态
const collectTasks = ref<Map<string, { keyword: string; status: string; collected_count: number }>>(new Map())
const pollingTimers = ref<Map<string, number>>(new Map())

// 优先级选项
const priorityOptions = [
  { label: '高', value: 'high' },
  { label: '中', value: 'medium' },
  { label: '低', value: 'low' },
]

// 平台选项
const platformOptions = [
  { label: '百度（推荐）', value: 'baidu' },
  { label: 'Bing', value: 'bing' },
  { label: '博查 API', value: 'bocha' },
  { label: 'Tavily API', value: 'tavily' },
  { label: 'Anspire API', value: 'anspire' },
]

// 时间范围选项
const timeRangeOptions = [
  { label: '最近1天', value: 'oneDay' },
  { label: '最近3天', value: 'threeDays' },
  { label: '最近1周', value: 'oneWeek' },
  { label: '最近1个月', value: 'oneMonth' },
  { label: '最近3个月', value: 'threeMonths' },
]

// 获取列表
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

// 打开创建对话框
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

// 打开编辑对话框
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

// 提交表单
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

// 删除
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

// 打开采集对话框
const openCollectDialog = (row: Keyword) => {
  collectKeyword.value = row
  collectTimeRange.value = 'oneDay'
  collectNegativeMode.value = false
  collectDialogVisible.value = true
}

// 轮询任务状态
const pollTaskStatus = async (taskId: string, keywordText: string) => {
  try {
    const status = await collectApi.getStatus(taskId)

    collectTasks.value.set(taskId, {
      keyword: keywordText,
      status: status.status,
      collected_count: status.collected_count,
    })

    if (status.status === 'completed') {
      ElMessage.success(`「${keywordText}」采集完成，新增 ${status.collected_count} 条文章`)
      fetchData()
      stopPolling(taskId)
    } else if (status.status === 'failed') {
      ElMessage.error(`「${keywordText}」采集失败：${status.message}`)
      stopPolling(taskId)
    }
    // 如果是 pending 或 running，继续轮询
  } catch (error) {
    console.error('Failed to poll status:', error)
    stopPolling(taskId)
  }
}

// 开始轮询
const startPolling = (taskId: string, keywordText: string) => {
  // 立即查询一次
  pollTaskStatus(taskId, keywordText)

  // 每2秒轮询一次
  const timer = window.setInterval(() => {
    pollTaskStatus(taskId, keywordText)
  }, 2000)

  pollingTimers.value.set(taskId, timer)
}

// 停止轮询
const stopPolling = (taskId: string) => {
  const timer = pollingTimers.value.get(taskId)
  if (timer) {
    clearInterval(timer)
    pollingTimers.value.delete(taskId)
  }
  // 5秒后从列表中移除
  setTimeout(() => {
    collectTasks.value.delete(taskId)
  }, 5000)
}

// 执行采集
const handleCollect = async () => {
  if (!collectKeyword.value) return

  collectLoading.value = true
  try {
    const result = await collectApi.trigger(
      collectKeyword.value.id,
      collectTimeRange.value,
      collectNegativeMode.value
    )

    // 添加到任务列表
    collectTasks.value.set(result.task_id, {
      keyword: result.keyword,
      status: 'pending',
      collected_count: 0,
    })

    ElMessage.info(`「${result.keyword}」采集任务已创建`)

    // 开始轮询状态
    startPolling(result.task_id, result.keyword)

    collectDialogVisible.value = false
  } catch (error) {
    console.error('Failed to trigger collect:', error)
  } finally {
    collectLoading.value = false
  }
}

// 获取优先级标签类型
const getPriorityType = (priority: string) => {
  const map: Record<string, string> = {
    high: 'danger',
    medium: 'warning',
    low: 'info',
  }
  return map[priority] || 'info'
}

const getPriorityLabel = (priority: string) => {
  const map: Record<string, string> = {
    high: '高',
    medium: '中',
    low: '低',
  }
  return map[priority] || priority
}

// 获取任务状态样式
const getTaskStatusType = (status: string) => {
  const map: Record<string, string> = {
    pending: 'info',
    running: 'warning',
    completed: 'success',
    failed: 'danger',
  }
  return map[status] || 'info'
}

const getTaskStatusLabel = (status: string) => {
  const map: Record<string, string> = {
    pending: '等待中',
    running: '采集中',
    completed: '已完成',
    failed: '失败',
  }
  return map[status] || status
}

// 清理所有轮询
onUnmounted(() => {
  pollingTimers.value.forEach((timer) => clearInterval(timer))
})

// 恢复正在运行的任务
const restoreRunningTasks = async () => {
  try {
    const result = await collectApi.getRunningTasks()
    for (const task of result.tasks) {
      // 添加到任务列表
      collectTasks.value.set(task.task_id, {
        keyword: task.keyword,
        status: task.status,
        collected_count: task.collected_count,
      })
      // 开始轮询
      startPolling(task.task_id, task.keyword)
    }
    if (result.tasks.length > 0) {
      console.log(`Restored ${result.tasks.length} running tasks`)
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
    <div class="page-header">
      <h3 class="page-title">监控主体</h3>
      <el-button type="primary" @click="handleCreate">
        <el-icon><Plus /></el-icon>
        添加监控主体
      </el-button>
    </div>

    <!-- 采集任务状态 -->
    <el-card v-if="collectTasks.size > 0" class="tasks-card">
      <template #header>
        <span>采集任务</span>
      </template>
      <div class="task-list">
        <div v-for="[taskId, task] in collectTasks" :key="taskId" class="task-item">
          <span class="task-keyword">{{ task.keyword }}</span>
          <el-tag :type="getTaskStatusType(task.status)" size="small">
            {{ getTaskStatusLabel(task.status) }}
          </el-tag>
          <span v-if="task.status === 'completed'" class="task-count">
            +{{ task.collected_count }} 条
          </span>
        </div>
      </div>
    </el-card>

    <el-card>
      <el-table :data="keywords" v-loading="loading" stripe>
        <el-table-column prop="keyword" label="主体名称" min-width="150" />
        <el-table-column prop="priority" label="优先级" width="100">
          <template #default="{ row }">
            <el-tag :type="getPriorityType(row.priority)" size="small">
              {{ getPriorityLabel(row.priority) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="platforms" label="采集平台" width="200">
          <template #default="{ row }">
            <el-tag
              v-for="p in row.platforms"
              :key="p"
              size="small"
              style="margin-right: 4px"
            >
              {{ p }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ new Date(row.created_at).toLocaleString() }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="openCollectDialog(row)">
              采集
            </el-button>
            <el-button type="primary" link size="small" @click="handleEdit(row)">
              编辑
            </el-button>
            <el-button type="danger" link size="small" @click="handleDelete(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 创建/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="500px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="主体名称" required>
          <el-input v-model="form.keyword" placeholder="请输入要监控的公司/品牌/人名" />
        </el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="form.priority" style="width: 100%">
            <el-option
              v-for="item in priorityOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="采集平台">
          <el-checkbox-group v-model="form.platforms">
            <el-checkbox
              v-for="item in platformOptions"
              :key="item.value"
              :value="item.value"
            >
              {{ item.label }}
            </el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="formLoading" @click="handleSubmit">
          确定
        </el-button>
      </template>
    </el-dialog>

    <!-- 采集设置对话框 -->
    <el-dialog v-model="collectDialogVisible" title="采集设置" width="450px">
      <div class="collect-dialog-content">
        <p class="collect-keyword">
          监控主体：<strong>{{ collectKeyword?.keyword }}</strong>
        </p>
        <el-form label-width="100px">
          <el-form-item label="时间范围">
            <el-radio-group v-model="collectTimeRange">
              <el-radio
                v-for="item in timeRangeOptions"
                :key="item.value"
                :value="item.value"
                style="margin-bottom: 10px"
              >
                {{ item.label }}
              </el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="搜索模式">
            <el-checkbox v-model="collectNegativeMode">
              负面舆情模式
            </el-checkbox>
            <div class="mode-tip" v-if="collectNegativeMode">
              将自动添加"违规、违法、投诉、通报"等负面关键词
            </div>
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="collectDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="collectLoading" @click="handleCollect">
          开始采集
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.keywords-page {
  padding: 0;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
}

.tasks-card {
  margin-bottom: 20px;
}

.task-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.task-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 4px;
}

.task-keyword {
  font-weight: 500;
}

.task-count {
  color: #67c23a;
  font-size: 12px;
}

.collect-dialog-content {
  padding: 10px 0;
}

.collect-keyword {
  margin-bottom: 20px;
  color: #606266;
}

.collect-keyword strong {
  color: #409eff;
  font-size: 16px;
}

.el-radio-group {
  display: flex;
  flex-direction: column;
}

.mode-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
}
</style>
