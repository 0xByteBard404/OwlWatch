<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  RefreshRight,
  Plus,
  Edit,
  Delete,
  CircleCheck,
  CircleClose,
} from '@element-plus/icons-vue'
import { sentimentKeywordsApi, type SentimentKeyword, type SentimentKeywordCreate, type SentimentKeywordUpdate } from '@/api'

// 数据列表
const keywords = ref<SentimentKeyword[]>([])
const categories = ref<string[]>([])
const loading = ref(false)

// 筛选
const activeType = ref<'positive' | 'negative'>('positive')
const selectedCategory = ref<string>('')

// 对话框
const dialogVisible = ref(false)
const dialogTitle = ref('添加情感关键词')
const formLoading = ref(false)

// 表单数据
const form = ref<SentimentKeywordCreate & { id?: string }>({
  keyword: '',
  sentiment_type: 'positive',
  category: '',
})

const editingId = ref<string | null>(null)

// 计算属性：根据类型和分类筛选
const filteredKeywords = computed(() => {
  let result = keywords.value.filter(k => k.sentiment_type === activeType.value)
  if (selectedCategory.value) {
    result = result.filter(k => k.category === selectedCategory.value)
  }
  return result
})

// 获取分类列表
const fetchCategories = async () => {
  try {
    categories.value = await sentimentKeywordsApi.getCategories()
  } catch (error) {
    console.error('Failed to fetch categories:', error)
  }
}

// 获取列表
const fetchData = async () => {
  loading.value = true
  try {
    keywords.value = await sentimentKeywordsApi.list()
    await fetchCategories()
  } catch (error) {
    console.error('Failed to fetch sentiment keywords:', error)
  } finally {
    loading.value = false
  }
}

// 切换类型 Tab
const handleTypeChange = () => {
  selectedCategory.value = ''
}

// 打开创建对话框
const handleCreate = () => {
  dialogTitle.value = '添加情感关键词'
  editingId.value = null
  form.value = {
    keyword: '',
    sentiment_type: activeType.value,
    category: '',
  }
  dialogVisible.value = true
}

// 打开编辑对话框
const handleEdit = (row: SentimentKeyword) => {
  dialogTitle.value = '编辑情感关键词'
  editingId.value = row.id
  form.value = {
    id: row.id,
    keyword: row.keyword,
    sentiment_type: row.sentiment_type,
    category: row.category || '',
  }
  dialogVisible.value = true
}

// 提交表单
const handleSubmit = async () => {
  if (!form.value.keyword.trim()) {
    ElMessage.warning('请输入关键词')
    return
  }

  formLoading.value = true
  try {
    if (editingId.value) {
      const updateData: SentimentKeywordUpdate = {
        keyword: form.value.keyword,
        sentiment_type: form.value.sentiment_type,
        category: form.value.category || undefined,
      }
      await sentimentKeywordsApi.update(editingId.value, updateData)
      ElMessage.success('更新成功')
    } else {
      const createData: SentimentKeywordCreate = {
        keyword: form.value.keyword,
        sentiment_type: form.value.sentiment_type,
        category: form.value.category || undefined,
      }
      await sentimentKeywordsApi.create(createData)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchData()
  } catch (error: any) {
    if (error?.response?.data?.detail) {
      ElMessage.error(error.response.data.detail)
    }
    console.error('Failed to save sentiment keyword:', error)
  } finally {
    formLoading.value = false
  }
}

// 切换状态
const handleToggle = async (row: SentimentKeyword) => {
  try {
    const result = await sentimentKeywordsApi.toggle(row.id)
    ElMessage.success(result.message)
    fetchData()
  } catch (error) {
    console.error('Failed to toggle sentiment keyword:', error)
  }
}

// 删除
const handleDelete = async (row: SentimentKeyword) => {
  try {
    await ElMessageBox.confirm(`确定要删除关键词「${row.keyword}」吗？`, '确认删除', {
      type: 'warning',
    })
    await sentimentKeywordsApi.delete(row.id)
    ElMessage.success('删除成功')
    fetchData()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to delete sentiment keyword:', error)
    }
  }
}

onMounted(() => {
  fetchData()
})
</script>

<template>
  <div class="sentiment-keywords-page">
    <!-- Page Header -->
    <div class="page-header">
      <div class="header-left">
        <h3 class="page-title">
          <span class="title-icon">◈</span>
          情感词库
        </h3>
        <span class="subtitle">SENTIMENT KEYWORDS</span>
      </div>
      <div class="header-actions">
        <button class="btn-secondary" @click="fetchData">
          <el-icon><RefreshRight /></el-icon>
          <span>刷新</span>
        </button>
        <button class="btn-primary" @click="handleCreate">
          <el-icon><Plus /></el-icon>
          <span>添加关键词</span>
        </button>
      </div>
    </div>

    <!-- Type Tabs & Category Filter -->
    <div class="filter-bar">
      <div class="type-tabs">
        <button
          class="type-tab positive"
          :class="{ active: activeType === 'positive' }"
          @click="activeType = 'positive'; handleTypeChange()"
        >
          <span class="tab-icon">+</span>
          正面关键词
          <span class="tab-count">{{ keywords.filter(k => k.sentiment_type === 'positive').length }}</span>
        </button>
        <button
          class="type-tab negative"
          :class="{ active: activeType === 'negative' }"
          @click="activeType = 'negative'; handleTypeChange()"
        >
          <span class="tab-icon">-</span>
          负面关键词
          <span class="tab-count">{{ keywords.filter(k => k.sentiment_type === 'negative').length }}</span>
        </button>
      </div>
      <div class="category-filter">
        <select v-model="selectedCategory" class="cyber-select">
          <option value="">全部分类</option>
          <option v-for="cat in categories" :key="cat" :value="cat">{{ cat }}</option>
        </select>
      </div>
    </div>

    <!-- Keywords Table -->
    <div class="table-container cyber-card">
      <el-table :data="filteredKeywords" v-loading="loading">
        <el-table-column prop="keyword" label="关键词" min-width="200">
          <template #default="{ row }">
            <span class="keyword-text" :class="row.sentiment_type">{{ row.keyword }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="category" label="分类" width="120">
          <template #default="{ row }">
            <span class="category-badge" v-if="row.category">{{ row.category }}</span>
            <span class="category-badge empty" v-else>未分类</span>
          </template>
        </el-table-column>

        <el-table-column prop="is_active" label="状态" width="120">
          <template #default="{ row }">
            <span class="status-badge" :class="{ active: row.is_active }">
              <el-icon v-if="row.is_active"><CircleCheck /></el-icon>
              <el-icon v-else><CircleClose /></el-icon>
              {{ row.is_active ? '启用' : '禁用' }}
            </span>
          </template>
        </el-table-column>

        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            <span class="time-text">{{ new Date(row.created_at).toLocaleString() }}</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons">
              <button
                class="action-btn"
                :class="row.is_active ? 'disable' : 'enable'"
                @click="handleToggle(row)"
              >
                <el-icon><component :is="row.is_active ? 'CircleClose' : 'CircleCheck'" /></el-icon>
                {{ row.is_active ? '禁用' : '启用' }}
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
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="450px" class="cyber-dialog">
      <div class="dialog-content">
        <div class="form-group">
          <label class="form-label">关键词</label>
          <input
            v-model="form.keyword"
            type="text"
            class="cyber-input"
            placeholder="请输入关键词"
          />
        </div>

        <div class="form-group">
          <label class="form-label">情感类型</label>
          <div class="type-selector">
            <button
              class="type-btn positive"
              :class="{ active: form.sentiment_type === 'positive' }"
              @click="form.sentiment_type = 'positive'"
            >
              正面
            </button>
            <button
              class="type-btn negative"
              :class="{ active: form.sentiment_type === 'negative' }"
              @click="form.sentiment_type = 'negative'"
            >
              负面
            </button>
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">分类（可选）</label>
          <input
            v-model="form.category"
            type="text"
            class="cyber-input"
            placeholder="如：法律、财务、经营、技术"
          />
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
.sentiment-keywords-page {
  max-width: 1200px;
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
  color: var(--neon-cyan);
  margin-right: 8px;
}

.header-actions {
  display: flex;
  gap: 12px;
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
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  font-family: var(--font-display);
  font-size: 0.8rem;
  font-weight: 500;
  letter-spacing: 0.05em;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-normal);
}

.btn-secondary:hover {
  border-color: var(--neon-orange);
  color: var(--neon-orange);
  box-shadow: 0 0 15px rgba(255, 107, 44, 0.2);
}

/* Filter Bar */
.filter-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  gap: 20px;
}

.type-tabs {
  display: flex;
  gap: 12px;
}

.type-tab {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: rgba(20, 27, 45, 0.6);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  font-family: var(--font-display);
  font-size: 0.8rem;
  font-weight: 500;
  letter-spacing: 0.05em;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-normal);
}

.type-tab .tab-icon {
  font-size: 1rem;
  font-weight: 700;
}

.type-tab.positive:hover,
.type-tab.positive.active {
  border-color: var(--neon-green);
  color: var(--neon-green);
  background: rgba(0, 255, 136, 0.1);
  box-shadow: 0 0 15px rgba(0, 255, 136, 0.2);
}

.type-tab.negative:hover,
.type-tab.negative.active {
  border-color: var(--neon-red);
  color: var(--neon-red);
  background: rgba(255, 51, 102, 0.1);
  box-shadow: 0 0 15px rgba(255, 51, 102, 0.2);
}

.tab-count {
  padding: 2px 8px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  font-size: 0.7rem;
}

.type-tab.active .tab-count {
  background: rgba(255, 255, 255, 0.2);
}

.category-filter {
  flex-shrink: 0;
}

.cyber-select {
  padding: 10px 16px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  font-family: var(--font-body);
  font-size: 0.85rem;
  color: var(--text-primary);
  cursor: pointer;
  transition: all var(--transition-normal);
  min-width: 140px;
}

.cyber-select:focus {
  outline: none;
  border-color: var(--neon-cyan);
}

/* Table */
.table-container {
  overflow: hidden;
}

.keyword-text {
  font-family: var(--font-mono);
  font-size: 0.9rem;
  color: var(--text-primary);
}

.keyword-text.positive {
  color: var(--neon-green);
}

.keyword-text.negative {
  color: var(--neon-red);
}

.category-badge {
  display: inline-block;
  padding: 4px 10px;
  font-family: var(--font-mono);
  font-size: 0.7rem;
  border-radius: 10px;
  background: rgba(0, 240, 255, 0.15);
  color: var(--neon-cyan);
}

.category-badge.empty {
  background: rgba(139, 149, 168, 0.2);
  color: var(--text-muted);
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 12px;
  font-family: var(--font-mono);
  font-size: 0.7rem;
  border-radius: 12px;
  background: rgba(139, 149, 168, 0.2);
  color: var(--text-muted);
}

.status-badge.active {
  background: rgba(0, 255, 136, 0.15);
  color: var(--neon-green);
}

.status-badge .el-icon {
  font-size: 12px;
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

.action-btn.enable:hover {
  border-color: var(--neon-green);
  color: var(--neon-green);
  box-shadow: 0 0 10px rgba(0, 255, 136, 0.2);
}

.action-btn.disable:hover {
  border-color: var(--neon-orange);
  color: var(--neon-orange);
}

.action-btn.edit:hover {
  border-color: var(--neon-cyan);
  color: var(--neon-cyan);
}

.action-btn.delete:hover {
  border-color: var(--neon-red);
  color: var(--neon-red);
}

/* Dialog */
.dialog-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
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

.type-selector {
  display: flex;
  gap: 10px;
}

.type-btn {
  flex: 1;
  padding: 12px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  font-family: var(--font-display);
  font-size: 0.85rem;
  font-weight: 500;
  letter-spacing: 0.05em;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-normal);
}

.type-btn.positive:hover,
.type-btn.positive.active {
  border-color: var(--neon-green);
  color: var(--neon-green);
  background: rgba(0, 255, 136, 0.1);
}

.type-btn.negative:hover,
.type-btn.negative.active {
  border-color: var(--neon-red);
  color: var(--neon-red);
  background: rgba(255, 51, 102, 0.1);
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>
