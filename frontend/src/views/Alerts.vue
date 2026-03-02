<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { alertsApi, keywordsApi, type Alert, type AlertListParams, type AlertStatsResponse, type Keyword } from '@/api'

// 数据
const alerts = ref<Alert[]>([])
const keywords = ref<Keyword[]>([])
const stats = ref<AlertStatsResponse | null>(null)
const total = ref(0)
const loading = ref(false)

// 分页
const page = ref(1)
const size = ref(20)

// 筛选条件
const filters = ref<AlertListParams>({
  status: '',
  alert_level: '',
  alert_type: '',
})

// 选中的预警
const selectedIds = ref<string[]>([])

// 状态选项
const statusOptions = [
  { label: '待处理', value: 'pending' },
  { label: '已处理', value: 'handled' },
  { label: '已忽略', value: 'ignored' },
]

// 级别选项
const levelOptions = [
  { label: '信息', value: 'info' },
  { label: '警告', value: 'warning' },
  { label: '严重', value: 'critical' },
]

// 类型选项
const typeOptions = [
  { label: '负面爆发', value: 'negative_burst' },
  { label: '敏感词', value: 'sensitive_keyword' },
  { label: '讨论量激增', value: 'volume_spike' },
]

// 获取关键词列表
const fetchKeywords = async () => {
  try {
    keywords.value = await keywordsApi.list()
  } catch (error) {
    console.error('Failed to fetch keywords:', error)
  }
}

// 获取预警统计
const fetchStats = async () => {
  try {
    stats.value = await alertsApi.stats()
  } catch (error) {
    console.error('Failed to fetch alert stats:', error)
  }
}

// 获取预警列表
const fetchData = async () => {
  loading.value = true
  try {
    const params: AlertListParams = {
      page: page.value,
      size: size.value,
      ...filters.value,
    }
    // 移除空值
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

// 搜索
const handleSearch = () => {
  page.value = 1
  fetchData()
}

// 重置
const handleReset = () => {
  filters.value = {
    status: '',
    alert_level: '',
    alert_type: '',
  }
  page.value = 1
  fetchData()
}

// 分页变化
const handlePageChange = (val: number) => {
  page.value = val
  fetchData()
}

// 处理预警
const handleAlert = async (row: Alert) => {
  try {
    await alertsApi.handle(row.id)
    ElMessage.success('已处理')
    fetchData()
    fetchStats()
  } catch (error) {
    console.error('Failed to handle alert:', error)
  }
}

// 忽略预警
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

// 选择变化
const handleSelectionChange = (selection: Alert[]) => {
  selectedIds.value = selection.map((a) => a.id)
}

// 获取状态标签类型
const getStatusType = (status: string) => {
  const map: Record<string, string> = {
    pending: 'warning',
    handled: 'success',
    ignored: 'info',
  }
  return map[status] || 'info'
}

const getStatusLabel = (status: string) => {
  const map: Record<string, string> = {
    pending: '待处理',
    handled: '已处理',
    ignored: '已忽略',
  }
  return map[status] || status
}

// 获取级别标签类型
const getLevelType = (level: string) => {
  const map: Record<string, string> = {
    info: 'info',
    warning: 'warning',
    critical: 'danger',
  }
  return map[level] || 'info'
}

const getLevelLabel = (level: string) => {
  const map: Record<string, string> = {
    info: '信息',
    warning: '警告',
    critical: '严重',
  }
  return map[level] || level
}

// 获取类型标签
const getTypeLabel = (type: string | null) => {
  const map: Record<string, string> = {
    negative_burst: '负面爆发',
    sensitive_keyword: '敏感词',
    volume_spike: '讨论量激增',
  }
  return map[type || ''] || type || '-'
}

// 获取关键词名称
const getKeywordName = (keywordId: string) => {
  return keywords.value.find((k) => k.id === keywordId)?.keyword || keywordId
}

// 统计卡片数据
const statCards = computed(() => {
  if (!stats.value) return []
  return [
    { label: '预警总数', value: stats.value.total, color: '#409eff' },
    { label: '待处理', value: stats.value.pending, color: '#e6a23c' },
    { label: '已处理', value: stats.value.handled, color: '#67c23a' },
    { label: '已忽略', value: stats.value.ignored, color: '#909399' },
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
    <div class="page-header">
      <h3 class="page-title">预警中心</h3>
      <el-button
        type="primary"
        :disabled="selectedIds.length === 0"
        @click="handleBatch"
      >
        批量处理 ({{ selectedIds.length }})
      </el-button>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="16" class="stats-row" v-if="stats">
      <el-col :xs="12" :sm="6" v-for="item in statCards" :key="item.label">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-value" :style="{ color: item.color }">{{ item.value }}</div>
          <div class="stat-label">{{ item.label }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 筛选条件 -->
    <el-card class="filter-card">
      <el-form :inline="true" :model="filters">
        <el-form-item label="状态">
          <el-select
            v-model="filters.status"
            placeholder="全部"
            clearable
            style="width: 120px"
          >
            <el-option
              v-for="item in statusOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="级别">
          <el-select
            v-model="filters.alert_level"
            placeholder="全部"
            clearable
            style="width: 120px"
          >
            <el-option
              v-for="item in levelOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="类型">
          <el-select
            v-model="filters.alert_type"
            placeholder="全部"
            clearable
            style="width: 140px"
          >
            <el-option
              v-for="item in typeOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 预警列表 -->
    <el-card>
      <el-table
        :data="alerts"
        v-loading="loading"
        stripe
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="50" />
        <el-table-column prop="alert_level" label="级别" width="80">
          <template #default="{ row }">
            <el-tag :type="getLevelType(row.alert_level)" size="small">
              {{ getLevelLabel(row.alert_level) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="alert_type" label="类型" width="110">
          <template #default="{ row }">
            {{ getTypeLabel(row.alert_type) }}
          </template>
        </el-table-column>
        <el-table-column prop="message" label="预警信息" min-width="250">
          <template #default="{ row }">
            <div class="alert-message">{{ row.message }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="keyword_id" label="监控主体" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ getKeywordName(row.keyword_id) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160">
          <template #default="{ row }">
            {{ new Date(row.created_at).toLocaleString() }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <template v-if="row.status === 'pending'">
              <el-button type="success" link size="small" @click="handleAlert(row)">
                处理
              </el-button>
              <el-button type="info" link size="small" @click="ignoreAlert(row)">
                忽略
              </el-button>
            </template>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="size"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.alerts-page {
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

.stats-row {
  margin-bottom: 20px;
}

.stat-card {
  text-align: center;
  padding: 10px 0;
}

.stat-value {
  font-size: 28px;
  font-weight: 600;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 4px;
}

.filter-card {
  margin-bottom: 20px;
}

.alert-message {
  white-space: pre-wrap;
  word-break: break-all;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.text-muted {
  color: #c0c4cc;
}
</style>
