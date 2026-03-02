<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { articlesApi, keywordsApi, type Article, type ArticleListParams, type Keyword } from '@/api'

// 数据
const articles = ref<Article[]>([])
const keywords = ref<Keyword[]>([])
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
  { label: '正面', value: 'positive' },
  { label: '中性', value: 'neutral' },
  { label: '负面', value: 'negative' },
]

// 获取来源列表
const sourceOptions = computed(() => {
  const sources = new Set(articles.value.map((a) => a.source).filter(Boolean))
  return Array.from(sources).map((s) => ({ label: s, value: s }))
})

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

// 获取情感标签类型
const getSentimentType = (label: string | null) => {
  const map: Record<string, string> = {
    positive: 'success',
    neutral: 'info',
    negative: 'danger',
  }
  return map[label || ''] || 'info'
}

const getSentimentLabel = (label: string | null) => {
  const map: Record<string, string> = {
    positive: '正面',
    neutral: '中性',
    negative: '负面',
  }
  return map[label || ''] || '未分析'
}

// 获取情感分数颜色
const getScoreColor = (score: number | null) => {
  if (score === null) return '#909399'
  if (score > 0.3) return '#67c23a'
  if (score < -0.3) return '#f56c6c'
  return '#909399'
}

// 获取关键词名称
const getKeywordName = (keywordId: string) => {
  return keywords.value.find((k) => k.id === keywordId)?.keyword || keywordId
}

// 打开链接
const openUrl = (url: string) => {
  window.open(url, '_blank')
}

onMounted(() => {
  fetchKeywords()
  fetchData()
})
</script>

<template>
  <div class="articles-page">
    <div class="page-header">
      <h3 class="page-title">文章列表</h3>
    </div>

    <!-- 筛选条件 -->
    <el-card class="filter-card">
      <el-form :inline="true" :model="filters">
        <el-form-item label="监控主体">
          <el-select
            v-model="filters.keyword_id"
            placeholder="全部"
            clearable
            style="width: 180px"
          >
            <el-option
              v-for="item in keywords"
              :key="item.id"
              :label="item.keyword"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="情感">
          <el-select
            v-model="filters.sentiment"
            placeholder="全部"
            clearable
            style="width: 120px"
          >
            <el-option
              v-for="item in sentimentOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="来源">
          <el-select
            v-model="filters.source"
            placeholder="全部"
            clearable
            style="width: 140px"
          >
            <el-option
              v-for="item in sourceOptions"
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

    <!-- 文章列表 -->
    <el-card>
      <el-table :data="articles" v-loading="loading" stripe>
        <el-table-column type="index" width="50" />
        <el-table-column prop="title" label="标题" min-width="300">
          <template #default="{ row }">
            <div class="article-title" @click="handleDetail(row)">
              {{ row.title }}
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="keyword_id" label="监控主体" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ getKeywordName(row.keyword_id) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="source" label="来源" width="120">
          <template #default="{ row }">
            {{ row.source || row.source_api || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="sentiment_label" label="情感" width="100">
          <template #default="{ row }">
            <el-tag :type="getSentimentType(row.sentiment_label)" size="small">
              {{ getSentimentLabel(row.sentiment_label) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="sentiment_score" label="情感分数" width="100">
          <template #default="{ row }">
            <span :style="{ color: getScoreColor(row.sentiment_score) }">
              {{ row.sentiment_score?.toFixed(2) || '-' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="publish_time" label="发布时间" width="160">
          <template #default="{ row }">
            {{ row.publish_time ? new Date(row.publish_time).toLocaleString() : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="openUrl(row.url)">
              查看
            </el-button>
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
          @size-change="handleSizeChange"
        />
      </div>
    </el-card>

    <!-- 详情对话框 -->
    <el-dialog v-model="detailVisible" title="文章详情" width="700px">
      <template v-if="currentArticle">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="标题" :span="2">
            {{ currentArticle.title }}
          </el-descriptions-item>
          <el-descriptions-item label="来源">
            {{ currentArticle.source || currentArticle.source_api || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="情感">
            <el-tag :type="getSentimentType(currentArticle.sentiment_label)">
              {{ getSentimentLabel(currentArticle.sentiment_label) }}
            </el-tag>
            <span style="margin-left: 8px; color: #909399">
              分数: {{ currentArticle.sentiment_score?.toFixed(2) || '-' }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="发布时间">
            {{ currentArticle.publish_time ? new Date(currentArticle.publish_time).toLocaleString() : '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="采集时间">
            {{ new Date(currentArticle.collect_time).toLocaleString() }}
          </el-descriptions-item>
          <el-descriptions-item label="链接" :span="2">
            <el-link :href="currentArticle.url" target="_blank" type="primary">
              {{ currentArticle.url }}
            </el-link>
          </el-descriptions-item>
          <el-descriptions-item label="内容" :span="2">
            <div class="article-content">
              {{ currentArticle.content || '无内容' }}
            </div>
          </el-descriptions-item>
        </el-descriptions>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.articles-page {
  padding: 0;
}

.page-header {
  margin-bottom: 20px;
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
}

.filter-card {
  margin-bottom: 20px;
}

.article-title {
  color: #409eff;
  cursor: pointer;
}

.article-title:hover {
  text-decoration: underline;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.article-content {
  max-height: 200px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
