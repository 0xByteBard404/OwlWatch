<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { PieChart, LineChart, BarChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
} from 'echarts/components'
import VChart from 'vue-echarts'
import 'echarts-wordcloud'
import { keywordsApi, articlesApi, alertsApi } from '@/api'
import type { TrendPoint, WordFrequency, SourceDistribution } from '@/api/articles'

use([
  CanvasRenderer,
  PieChart,
  LineChart,
  BarChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
])

// 统计数据
const stats = ref({
  keywords: 0,
  articles: 0,
  today: 0,
  week: 0,
  alerts: 0,
  pendingAlerts: 0,
  positiveRatio: 0,
  negativeRatio: 0,
})

// 趋势数据
const trendData = ref<TrendPoint[]>([])

// 来源分布
const sourceData = ref<SourceDistribution[]>([])

// 词云数据
const wordData = ref<WordFrequency[]>([])

// 加载状态
const loading = ref(true)
const trendLoading = ref(false)

// 趋势天数
const trendDays = ref(7)

// 获取统计数据
const fetchStats = async () => {
  loading.value = true
  try {
    const [keywords, overview, alertStats] = await Promise.all([
      keywordsApi.list(),
      articlesApi.getStatsOverview(),
      alertsApi.stats(),
    ])

    stats.value = {
      keywords: keywords.length,
      articles: overview.total,
      today: overview.today,
      week: overview.week,
      alerts: alertStats.total,
      pendingAlerts: alertStats.pending,
      positiveRatio: overview.positive_ratio,
      negativeRatio: overview.negative_ratio,
    }
  } catch (error) {
    console.error('Failed to fetch stats:', error)
  } finally {
    loading.value = false
  }
}

// 获取趋势数据
const fetchTrend = async () => {
  trendLoading.value = true
  try {
    const result = await articlesApi.getTrend(trendDays.value)
    trendData.value = result.data
  } catch (error) {
    console.error('Failed to fetch trend:', error)
  } finally {
    trendLoading.value = false
  }
}

// 获取来源分布
const fetchSources = async () => {
  try {
    sourceData.value = await articlesApi.getSources(undefined, 8)
  } catch (error) {
    console.error('Failed to fetch sources:', error)
  }
}

// 获取词云数据
const fetchWords = async () => {
  try {
    wordData.value = await articlesApi.getWords(7, undefined, 80)
  } catch (error) {
    console.error('Failed to fetch words:', error)
  }
}

// 情感分布图表配置
const sentimentOption = computed(() => ({
  tooltip: {
    trigger: 'item',
    formatter: '{b}: {c} ({d}%)',
  },
  legend: {
    bottom: '5%',
    left: 'center',
  },
  series: [
    {
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      itemStyle: {
        borderRadius: 10,
        borderColor: '#fff',
        borderWidth: 2,
      },
      label: {
        show: false,
      },
      emphasis: {
        label: {
          show: true,
          fontSize: 14,
          fontWeight: 'bold',
        },
      },
      data: [
        {
          value: Math.round(stats.value.positiveRatio * stats.value.articles),
          name: '正面',
          itemStyle: { color: '#67c23a' },
        },
        {
          value: Math.round(stats.value.negativeRatio * stats.value.articles),
          name: '负面',
          itemStyle: { color: '#f56c6c' },
        },
        {
          value: Math.round((1 - stats.value.positiveRatio - stats.value.negativeRatio) * stats.value.articles),
          name: '中性',
          itemStyle: { color: '#909399' },
        },
      ],
    },
  ],
}))

// 趋势图表配置
const trendOption = computed(() => ({
  tooltip: {
    trigger: 'axis',
    axisPointer: { type: 'cross' },
  },
  legend: {
    data: ['文章数', '正面', '负面'],
    bottom: 0,
  },
  grid: {
    left: '3%',
    right: '4%',
    bottom: '15%',
    containLabel: true,
  },
  xAxis: {
    type: 'category',
    data: trendData.value.map((d) => d.date.slice(5)), // 只显示月-日
  },
  yAxis: { type: 'value' },
  series: [
    {
      name: '文章数',
      type: 'line',
      smooth: true,
      data: trendData.value.map((d) => d.count),
      itemStyle: { color: '#409eff' },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(64,158,255,0.3)' },
            { offset: 1, color: 'rgba(64,158,255,0.05)' },
          ],
        },
      },
    },
    {
      name: '正面',
      type: 'line',
      smooth: true,
      data: trendData.value.map((d) => d.positive),
      itemStyle: { color: '#67c23a' },
    },
    {
      name: '负面',
      type: 'line',
      smooth: true,
      data: trendData.value.map((d) => d.negative),
      itemStyle: { color: '#f56c6c' },
    },
  ],
}))

// 来源分布图表配置
const sourceOption = computed(() => ({
  tooltip: {
    trigger: 'axis',
    axisPointer: { type: 'shadow' },
  },
  grid: {
    left: '3%',
    right: '4%',
    bottom: '3%',
    containLabel: true,
  },
  xAxis: { type: 'value' },
  yAxis: {
    type: 'category',
    data: sourceData.value.map((d) => d.source).reverse(),
  },
  series: [
    {
      type: 'bar',
      data: sourceData.value.map((d) => d.count).reverse(),
      itemStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 1, y2: 0,
          colorStops: [
            { offset: 0, color: '#409eff' },
            { offset: 1, color: '#67c23a' },
          ],
        },
        borderRadius: [0, 4, 4, 0],
      },
    },
  ],
}))

// 词云配置
const wordCloudOption = computed(() => {
  const colors = ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#909399']
  return {
    series: [
      {
        type: 'wordCloud',
        shape: 'circle',
        left: 'center',
        top: 'center',
        width: '90%',
        height: '90%',
        sizeRange: [14, 48],
        rotationRange: [-45, 45],
        rotationStep: 15,
        gridSize: 8,
        drawOutOfBound: false,
        textStyle: {
          fontFamily: 'sans-serif',
          fontWeight: 'bold',
          color: () => colors[Math.floor(Math.random() * colors.length)],
        },
        data: wordData.value.map((w) => ({
          name: w.word,
          value: w.count,
        })),
      },
    ],
  }
})

// 监听天数变化
const handleDaysChange = () => {
  fetchTrend()
}

onMounted(async () => {
  await Promise.all([
    fetchStats(),
    fetchTrend(),
    fetchSources(),
    fetchWords(),
  ])
})
</script>

<template>
  <div class="dashboard" v-loading="loading">
    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :xs="12" :sm="8" :md="4">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-content">
            <div class="stat-icon" style="background: #409eff">
              <el-icon :size="24"><Key /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.keywords }}</div>
              <div class="stat-label">监控主体</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="8" :md="4">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-content">
            <div class="stat-icon" style="background: #67c23a">
              <el-icon :size="24"><Document /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.articles }}</div>
              <div class="stat-label">文章总数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="8" :md="4">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-content">
            <div class="stat-icon" style="background: #00d4aa">
              <el-icon :size="24"><Calendar /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.today }}</div>
              <div class="stat-label">今日采集</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="8" :md="4">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-content">
            <div class="stat-icon" style="background: #e6a23c">
              <el-icon :size="24"><Bell /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.alerts }}</div>
              <div class="stat-label">预警总数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="8" :md="4">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-content">
            <div class="stat-icon" style="background: #f56c6c">
              <el-icon :size="24"><Warning /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.pendingAlerts }}</div>
              <div class="stat-label">待处理预警</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="8" :md="4">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-content">
            <div class="stat-icon" style="background: #8b5cf6">
              <el-icon :size="24"><TrendCharts /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ (stats.negativeRatio * 100).toFixed(1) }}%</div>
              <div class="stat-label">负面占比</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区域 - 第一行 -->
    <el-row :gutter="20">
      <el-col :xs="24" :lg="16">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span class="card-title">舆情趋势</span>
              <el-radio-group v-model="trendDays" size="small" @change="handleDaysChange">
                <el-radio-button :value="7">7天</el-radio-button>
                <el-radio-button :value="14">14天</el-radio-button>
                <el-radio-button :value="30">30天</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <v-chart
            v-if="trendData.length > 0"
            class="chart chart-large"
            :option="trendOption"
            :loading="trendLoading"
            autoresize
          />
          <el-empty v-else description="暂无趋势数据" />
        </el-card>
      </el-col>
      <el-col :xs="24" :lg="8">
        <el-card class="chart-card">
          <template #header>
            <span class="card-title">情感分布</span>
          </template>
          <v-chart
            v-if="stats.articles > 0"
            class="chart"
            :option="sentimentOption"
            autoresize
          />
          <el-empty v-else description="暂无数据" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区域 - 第二行 -->
    <el-row :gutter="20" class="mt-20">
      <el-col :xs="24" :lg="12">
        <el-card class="chart-card">
          <template #header>
            <span class="card-title">来源分布</span>
          </template>
          <v-chart
            v-if="sourceData.length > 0"
            class="chart"
            :option="sourceOption"
            autoresize
          />
          <el-empty v-else description="暂无数据" />
        </el-card>
      </el-col>
      <el-col :xs="24" :lg="12">
        <el-card class="chart-card">
          <template #header>
            <span class="card-title">热词云</span>
          </template>
          <v-chart
            v-if="wordData.length > 0"
            class="chart"
            :option="wordCloudOption"
            autoresize
          />
          <el-empty v-else description="暂无数据" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 快速操作 -->
    <el-row :gutter="20" class="mt-20">
      <el-col :span="24">
        <el-card>
          <template #header>
            <span class="card-title">快速操作</span>
          </template>
          <div class="quick-actions">
            <el-button type="primary" @click="$router.push('/keywords')">
              <el-icon><Plus /></el-icon>
              添加关键词
            </el-button>
            <el-button type="warning" @click="$router.push('/alerts')">
              <el-icon><Bell /></el-icon>
              查看预警
            </el-button>
            <el-button @click="$router.push('/articles')">
              <el-icon><Document /></el-icon>
              浏览文章
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.dashboard {
  padding: 0;
}

.stats-row {
  margin-bottom: 20px;
}

.stat-card {
  margin-bottom: 20px;
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 12px;
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.stat-label {
  font-size: 13px;
  color: #909399;
  margin-top: 2px;
}

.chart-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  font-size: 16px;
  font-weight: 500;
}

.chart {
  height: 280px;
}

.chart-large {
  height: 320px;
}

.mt-20 {
  margin-top: 0;
}

.quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}
</style>
