<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  RefreshRight,
  Plus,
  Edit,
  Delete,
  CircleCheck,
  CircleClose,
} from '@element-plus/icons-vue'
import { negativeKeywordsApi, type NegativeKeyword, type NegativeKeywordCreate } from '@/api'

// 数据列表
const keywords = ref<NegativeKeyword[]>([])
const loading = ref(false)

// 对话框
const dialogVisible = ref(false)
const dialogTitle = ref('添加负面关键词')
const formLoading = ref(false)

// 表单数据
const form = ref<NegativeKeywordCreate>({
  keyword: '',
})

const editingId = ref<string | null>(null)

// 获取列表
const fetchData = async () => {
  loading.value = true
  try {
    keywords.value = await negativeKeywordsApi.list()
  } catch (error) {
    console.error('Failed to fetch negative keywords:', error)
  } finally {
    loading.value = false
  }
}

// 初始化默认关键词
const handleInitDefaults = async () => {
  try {
    await ElMessageBox.confirm('确定要初始化默认负面关键词吗？已存在的关键词不会被重复添加。', '确认初始化', {
      type: 'info',
    })
    const result = await negativeKeywordsApi.initDefaults()
    ElMessage.success(result.message)
    fetchData()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to init defaults:', error)
    }
  }
}

// 打开创建对话框
const handleCreate = () => {
  dialogTitle.value = '添加负面关键词'
  editingId.value = null
  form.value = { keyword: '' }
  dialogVisible.value = true
}

// 打开编辑对话框
const handleEdit = (row: NegativeKeyword) => {
  dialogTitle.value = '编辑负面关键词'
  editingId.value = row.id
  form.value = { keyword: row.keyword }
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
      await negativeKeywordsApi.update(editingId.value, form.value)
      ElMessage.success('更新成功')
    } else {
      await negativeKeywordsApi.create(form.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchData()
  } catch (error) {
    console.error('Failed to save negative keyword:', error)
  } finally {
    formLoading.value = false
  }
}

// 切换状态
const handleToggle = async (row: NegativeKeyword) => {
  try {
    const result = await negativeKeywordsApi.toggle(row.id)
    ElMessage.success(result.message)
    fetchData()
  } catch (error) {
    console.error('Failed to toggle negative keyword:', error)
  }
}

// 删除
const handleDelete = async (row: NegativeKeyword) => {
  try {
    await ElMessageBox.confirm(`确定要删除负面关键词「${row.keyword}」吗？`, '确认删除', {
      type: 'warning',
    })
    await negativeKeywordsApi.delete(row.id)
    ElMessage.success('删除成功')
    fetchData()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to delete negative keyword:', error)
    }
  }
}

onMounted(() => {
  fetchData()
})
</script>

<template>
  <div class="negative-keywords-page">
    <!-- Page Header -->
    <div class="page-header">
      <div class="header-left">
        <h3 class="page-title">
          <span class="title-icon">◈</span>
          负面词库
        </h3>
        <span class="subtitle">NEGATIVE KEYWORDS</span>
      </div>
      <div class="header-actions">
        <button class="btn-secondary" @click="handleInitDefaults">
          <el-icon><RefreshRight /></el-icon>
          <span>初始化默认</span>
        </button>
        <button class="btn-primary" @click="handleCreate">
          <el-icon><Plus /></el-icon>
          <span>添加关键词</span>
        </button>
      </div>
    </div>

    <!-- Keywords Table -->
    <div class="table-container cyber-card">
      <el-table :data="keywords" v-loading="loading">
        <el-table-column prop="keyword" label="关键词" min-width="200">
          <template #default="{ row }">
            <span class="keyword-text">{{ row.keyword }}</span>
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
            placeholder="请输入负面关键词"
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
.negative-keywords-page {
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
  color: var(--neon-orange);
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

/* Table */
.table-container {
  overflow: hidden;
}

.keyword-text {
  font-family: var(--font-mono);
  font-size: 0.9rem;
  color: var(--text-primary);
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

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>
