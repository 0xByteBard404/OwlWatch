<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
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
    <div class="page-header">
      <div class="title-section">
        <h3 class="page-title">负面关键词管理</h3>
        <span class="page-desc">用于负面舆情搜索时自动组合的关键词</span>
      </div>
      <div class="action-buttons">
        <el-button @click="handleInitDefaults">
          <el-icon><RefreshRight /></el-icon>
          初始化默认
        </el-button>
        <el-button type="primary" @click="handleCreate">
          <el-icon><Plus /></el-icon>
          添加关键词
        </el-button>
      </div>
    </div>

    <el-card>
      <el-table :data="keywords" v-loading="loading" stripe>
        <el-table-column prop="keyword" label="关键词" min-width="200" />
        <el-table-column prop="is_active" label="状态" width="100">
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
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button
              :type="row.is_active ? 'warning' : 'success'"
              link
              size="small"
              @click="handleToggle(row)"
            >
              {{ row.is_active ? '禁用' : '启用' }}
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
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="450px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="关键词" required>
          <el-input v-model="form.keyword" placeholder="请输入负面关键词" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="formLoading" @click="handleSubmit">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.negative-keywords-page {
  padding: 0;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
}

.title-section {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
}

.page-desc {
  font-size: 12px;
  color: #909399;
}

.action-buttons {
  display: flex;
  gap: 10px;
}
</style>
