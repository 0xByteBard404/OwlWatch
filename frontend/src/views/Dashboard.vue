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
import { PieChart as PieIcon, DataLine } from '@element-plus/icons-vue'
import { keywordsApi, articlesApi, alertsApi } from '@/api'
import type { TrendPoint, WordFrequency, SourceDistribution } from '@/api/articles'

// 注册 ECharts 组件
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

const trendData = ref<TrendPoint[]>([])
const sourceData = ref<SourceDistribution[]>([])
const wordData = ref<WordFrequency[]>([])
const loading = ref(true)
const trendLoading = ref(false)
const trendDays = ref(7)

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

const fetchSources = async () => {
  try {
    sourceData.value = await articlesApi.getSources(undefined, 8)
  } catch (error) {
    console.error('Failed to fetch sources:', error)
  }
}

const fetchWords = async () => {
  try {
    wordData.value = await articlesApi.getWords(7, undefined, 80)
  } catch (error) {
    console.error('Failed to fetch words:', error)
  }
}

const handleDaysChange = () => {
  fetchTrend()
}

// Stat cards config
const statCards = computed(() => [
  {
    key: 'keywords',
    value: stats.value.keywords,
    label: '监控主体',
    icon: 'Key',
    color: '#00f0ff',
    trend: '+2',
  },
  {
    key: 'articles',
    value: stats.value.articles,
    label: '情报总量',
    icon: 'Document',
    color: '#00ff88',
    trend: '+15%',
  },
  {
    key: 'today',
    value: stats.value.today,
    label: '今日采集',
    icon: 'Calendar',
    color: '#a855f7',
    trend: null,
  },
  {
    key: 'week',
    value: stats.value.week,
    label: '本周采集',
    icon: 'TrendCharts',
    color: '#ffd000',
    trend: null,
  },
  {
    key: 'alerts',
    value: stats.value.alerts,
    label: '预警总数',
    icon: 'Bell',
    color: '#ff6b2c',
    trend: null,
  },
  {
    key: 'pendingAlerts',
    value: stats.value.pendingAlerts,
    label: '待处理',
    icon: 'Warning',
    color: '#ff3366',
    trend: stats.value.pendingAlerts > 0 ? '!' : null,
  },
])

// Chart options with cyberpunk theme
const sentimentOption = computed(() => ({
  tooltip: {
    trigger: 'item',
    backgroundColor: 'rgba(15, 21, 32, 0.95)',
    borderColor: 'rgba(0, 240, 255, 0.3)',
    textStyle: { color: '#e4e8f1' },
  },
  legend: {
    bottom: '5%',
    left: 'center',
    textStyle: { color: '#8b95a8' },
  },
  series: [
    {
      type: 'pie',
      radius: ['45%', '75%'],
      avoidLabelOverlap: false,
      itemStyle: {
        borderRadius: 6,
        borderColor: '#0a0e17',
        borderWidth: 3,
      },
      label: { show: false },
      emphasis: {
        label: {
          show: true,
          fontSize: 14,
          fontWeight: 'bold',
          color: '#e4e8f1',
        },
      },
      data: [
        {
          value: Math.round(stats.value.positiveRatio * stats.value.articles),
          name: '正面',
          itemStyle: { color: '#00ff88' },
        },
        {
          value: Math.round(stats.value.negativeRatio * stats.value.articles),
          name: '负面',
          itemStyle: { color: '#ff3366' },
        },
        {
          value: Math.round((1 - stats.value.positiveRatio - stats.value.negativeRatio) * stats.value.articles),
          name: '中性',
          itemStyle: { color: '#4a5568' },
        },
      ],
    },
  ],
}))

const trendOption = computed(() => ({
  tooltip: {
    trigger: 'axis',
    backgroundColor: 'rgba(15, 21, 32, 0.95)',
    borderColor: 'rgba(0, 240, 255, 0.3)',
    textStyle: { color: '#e4e8f1' },
    axisPointer: {
      type: 'cross',
      lineStyle: { color: 'rgba(0, 240, 255, 0.3)' },
    },
  },
  legend: {
    data: ['情报量', '正面', '负面'],
    bottom: 0,
    textStyle: { color: '#8b95a8' },
  },
  grid: {
    left: '3%',
    right: '4%',
    bottom: '15%',
    top: '10%',
    containLabel: true,
  },
  xAxis: {
    type: 'category',
    data: trendData.value.map((d) => d.date.slice(5)),
    axisLine: { lineStyle: { color: 'rgba(0, 240, 255, 0.2)' } },
    axisLabel: { color: '#8b95a8' },
  },
  yAxis: {
    type: 'value',
    splitLine: { lineStyle: { color: 'rgba(0, 240, 255, 0.1)' } },
    axisLabel: { color: '#8b95a8' },
  },
  series: [
    {
      name: '情报量',
      type: 'line',
      smooth: true,
      data: trendData.value.map((d) => d.count),
      lineStyle: { color: '#00f0ff', width: 3 },
      itemStyle: { color: '#00f0ff' },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(0, 240, 255, 0.4)' },
            { offset: 1, color: 'rgba(0, 240, 255, 0.02)' },
          ],
        },
      },
    },
    {
      name: '正面',
      type: 'line',
      smooth: true,
      data: trendData.value.map((d) => d.positive),
      lineStyle: { color: '#00ff88', width: 2 },
      itemStyle: { color: '#00ff88' },
    },
    {
      name: '负面',
      type: 'line',
      smooth: true,
      data: trendData.value.map((d) => d.negative),
      lineStyle: { color: '#ff3366', width: 2 },
      itemStyle: { color: '#ff3366' },
    },
  ],
}))

const sourceOption = computed(() => ({
  tooltip: {
    trigger: 'axis',
    backgroundColor: 'rgba(15, 21, 32, 0.95)',
    borderColor: 'rgba(0, 240, 255, 0.3)',
    textStyle: { color: '#e4e8f1' },
    axisPointer: { type: 'shadow' },
  },
  grid: {
    left: '3%',
    right: '8%',
    bottom: '3%',
    top: '3%',
    containLabel: true,
  },
  xAxis: {
    type: 'value',
    splitLine: { lineStyle: { color: 'rgba(0, 240, 255, 0.1)' } },
    axisLabel: { color: '#8b95a8' },
  },
  yAxis: {
    type: 'category',
    data: sourceData.value.map((d) => d.source).reverse(),
    axisLine: { lineStyle: { color: 'rgba(0, 240, 255, 0.2)' } },
    axisLabel: { color: '#8b95a8' },
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
            { offset: 0, color: '#00f0ff' },
            { offset: 1, color: '#ff6b2c' },
          ],
        },
        borderRadius: [0, 4, 4, 0],
      },
      barWidth: 12,
    },
  ],
}))

// 词云颜色配置
const wordColors = [
  '#00f0ff', // 青色
  '#a855f7', // 紫色
  '#ff6b2c', // 橙色
  '#00ff88', // 绿色
  '#ffd000', // 黄色
  '#ff3366', // 红色
  '#4ecdc4', // 青绿
  '#f39c12', // 金色
]

// 热词云暂停状态
const cloudPaused = ref(false)

// 黄金角度（斐波那契螺旋的数学基础）
const GOLDEN_ANGLE = Math.PI * (3 - Math.sqrt(5)) // ≈ 137.5°

// 计算词云数据 - 斐波那契球面均匀分布（热门词汇在赤道位置）
const wordCloudData = computed(() => {
  if (wordData.value.length === 0) return []

  const maxCount = Math.max(...wordData.value.map(w => w.count))
  const minCount = Math.min(...wordData.value.map(w => w.count))
  const total = Math.min(wordData.value.length, 50)

  return wordData.value.slice(0, total).map((word, index) => {
    // 根据频率计算字体大小 (10px - 26px)
    const sizeRange = 16
    const normalizedSize = (word.count - minCount) / (maxCount - minCount || 1)
    const fontSize = 10 + normalizedSize * sizeRange

    // 热门程度：0（最热）到 1（最冷）
    const hotness = index / (total - 1 || 1)

    // 斐波那契球面分布 - 经度使用黄金角度递增，避免螺旋线
    const theta = index * GOLDEN_ANGLE

    // 纬度：热门词在赤道，冷门词在两极
    // 使用 y 分布从 1（北极）到 -1（南极），热门词接近 0（赤道）
    // hotness 越小（越热门），y 越接近 0
    const maxLatitude = Math.PI * 0.4 // 最大纬度范围 ±72度
    const latitude = maxLatitude * Math.pow(hotness, 0.6) * (index % 2 === 0 ? 1 : -1)
    const phi = Math.PI / 2 + latitude

    const radius = 120
    const rx = (phi - Math.PI / 2) * (180 / Math.PI)
    const ry = theta * (180 / Math.PI)
    const rz = radius

    return {
      word: word.word,
      count: word.count,
      fontSize: Math.round(fontSize),
      color: wordColors[index % wordColors.length],
      rx: Math.round(rx),
      ry: Math.round(ry) % 360, // 保持在 0-360 范围
      rz,
    }
  })
})

// 搜索热词
const searchWord = (word: { word: string }) => {
  window.open(`/articles?search=${encodeURIComponent(word.word)}`, '_blank')
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
    <!-- Stats Grid -->
    <div class="stats-grid">
      <div
        v-for="(card, index) in statCards"
        :key="card.key"
        class="stat-card cyber-card fade-in-up"
        :class="`stagger-${index + 1}`"
        :style="{ '--card-color': card.color }"
      >
        <div class="stat-icon">
          <el-icon :size="28"><component :is="card.icon" /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value data-value">{{ card.value }}</div>
          <div class="stat-label">{{ card.label }}</div>
        </div>
        <div class="stat-trend" v-if="card.trend" :class="{ warning: card.trend === '!' }">
          {{ card.trend }}
        </div>
        <div class="stat-glow"></div>
      </div>
    </div>

    <!-- Charts Row 1 -->
    <div class="charts-row">
      <div class="chart-container chart-large cyber-card fade-in-up stagger-3">
        <div class="chart-header">
          <div class="chart-title">
            <span class="title-decorator">◈</span>
            舆情趋势分析
          </div>
          <div class="chart-actions">
            <button
              v-for="days in [7, 14, 30]"
              :key="days"
              class="time-btn"
              :class="{ active: trendDays === days }"
              @click="trendDays = days; handleDaysChange()"
            >
              {{ days }}天
            </button>
          </div>
        </div>
        <div class="chart-body">
          <v-chart
            v-if="trendData.length > 0"
            class="chart"
            :option="trendOption"
            :loading="trendLoading"
            autoresize
          />
          <div v-else class="empty-state">
            <el-icon :size="48"><TrendCharts /></el-icon>
            <span>暂无趋势数据</span>
          </div>
        </div>
      </div>

      <div class="chart-container cyber-card fade-in-up stagger-4">
        <div class="chart-header">
          <div class="chart-title">
            <span class="title-decorator">◈</span>
            情感分布
          </div>
        </div>
        <div class="chart-body">
          <v-chart
            v-if="stats.articles > 0"
            class="chart"
            :option="sentimentOption"
            autoresize
          />
          <div v-else class="empty-state">
            <el-icon :size="48"><PieIcon /></el-icon>
            <span>暂无数据</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Charts Row 2 -->
    <div class="charts-row">
      <div class="chart-container cyber-card fade-in-up stagger-5">
        <div class="chart-header">
          <div class="chart-title">
            <span class="title-decorator">◈</span>
            来源分布
          </div>
        </div>
        <div class="chart-body">
          <v-chart
            v-if="sourceData.length > 0"
            class="chart"
            :option="sourceOption"
            autoresize
          />
          <div v-else class="empty-state">
            <el-icon :size="48"><DataLine /></el-icon>
            <span>暂无数据</span>
          </div>
        </div>
      </div>

      <!-- 热词云 -->
      <div class="chart-container cyber-card fade-in-up stagger-6">
        <div class="chart-header">
          <div class="chart-title">
            <span class="title-decorator">◈</span>
            热词云
          </div>
        </div>
        <div class="chart-body word-cloud-body">
          <div
            v-if="wordCloudData.length > 0"
            class="word-cloud-3d"
            :class="{ paused: cloudPaused }"
            @mouseenter="cloudPaused = true"
            @mouseleave="cloudPaused = false"
          >
            <div class="cloud-sphere">
              <span
                v-for="(word, index) in wordCloudData"
                :key="index"
                class="word-item-3d"
                :style="{
                  fontSize: word.fontSize + 'px',
                  color: word.color,
                  textShadow: `0 0 ${word.fontSize / 2}px ${word.color}`,
                  '--rx': word.rx + 'deg',
                  '--ry': word.ry + 'deg',
                  '--rz': word.rz + 'px',
                }"
                @click="searchWord(word)"
              >
                {{ word.word }}
              </span>
            </div>
          </div>
          <div v-else class="empty-state">
            <el-icon :size="48"><Histogram /></el-icon>
            <span>暂无数据</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Quick Actions -->
    <div class="quick-actions cyber-card fade-in-up stagger-6">
      <div class="chart-header">
        <div class="chart-title">
          <span class="title-decorator">◈</span>
          快速操作
        </div>
      </div>
      <div class="actions-grid">
        <button class="action-btn action-rss" @click="$router.push('/rss')">
          <el-icon :size="24"><Promotion /></el-icon>
          <span>RSS 订阅</span>
          <span class="action-hint">主力采集</span>
        </button>
        <button class="action-btn action-primary" @click="$router.push('/keywords')">
          <el-icon :size="24"><Plus /></el-icon>
          <span>添加监控主体</span>
        </button>
        <button class="action-btn action-warning" @click="$router.push('/alerts')">
          <el-icon :size="24"><Bell /></el-icon>
          <span>查看预警</span>
          <span v-if="stats.pendingAlerts > 0" class="badge">{{ stats.pendingAlerts }}</span>
        </button>
        <button class="action-btn action-default" @click="$router.push('/articles')">
          <el-icon :size="24"><Document /></el-icon>
          <span>浏览情报库</span>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dashboard {
  max-width: 1600px;
  margin: 0 auto;
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  position: relative;
  overflow: hidden;
}

.stat-icon {
  width: 56px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, rgba(0, 240, 255, 0.1), rgba(0, 240, 255, 0.05));
  border: 1px solid var(--card-color);
  border-radius: 12px;
  color: var(--card-color);
  flex-shrink: 0;
  position: relative;
}

.stat-icon::after {
  content: '';
  position: absolute;
  inset: -1px;
  border-radius: 12px;
  background: linear-gradient(135deg, var(--card-color), transparent);
  opacity: 0.1;
}

.stat-content {
  flex: 1;
  min-width: 0;
}

.stat-value {
  font-family: var(--font-display);
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.2;
}

.stat-label {
  font-size: 0.75rem;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-top: 4px;
}

.stat-trend {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--neon-green);
  padding: 2px 8px;
  background: rgba(0, 255, 136, 0.1);
  border-radius: 4px;
}

.stat-trend.warning {
  color: var(--neon-red);
  background: rgba(255, 51, 102, 0.1);
  animation: pulse-glow 1s infinite;
}

.stat-glow {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--card-color), transparent);
  opacity: 0;
  transition: opacity var(--transition-normal);
}

.stat-card:hover .stat-glow {
  opacity: 1;
}

/* Charts */
.charts-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  margin-bottom: 20px;
}

.chart-container {
  overflow: hidden;
}

.chart-large {
  grid-column: span 1;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
}

.chart-title {
  font-family: var(--font-display);
  font-size: 0.85rem;
  font-weight: 600;
  letter-spacing: 0.1em;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 10px;
}

.title-decorator {
  color: var(--neon-cyan);
  font-size: 0.7rem;
}

.chart-actions {
  display: flex;
  gap: 4px;
}

.time-btn {
  padding: 6px 14px;
  font-family: var(--font-display);
  font-size: 0.7rem;
  font-weight: 500;
  letter-spacing: 0.05em;
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.time-btn:hover {
  border-color: var(--neon-cyan);
  color: var(--neon-cyan);
}

.time-btn.active {
  background: var(--neon-cyan);
  border-color: var(--neon-cyan);
  color: var(--bg-primary);
}

.chart-body {
  padding: 16px;
  height: 320px;
}

/* 3D 词云样式 */
.word-cloud-body {
  display: flex;
  align-items: center;
  justify-content: center;
  perspective: 600px;
  perspective-origin: 50% 50%;
  overflow: hidden;
}

.word-cloud-3d {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.cloud-sphere {
  position: relative;
  width: 260px;
  height: 260px;
  transform-style: preserve-3d;
  animation: cloud-rotate 25s linear infinite;
}

.word-cloud-3d.paused .cloud-sphere {
  animation-play-state: paused;
}

@keyframes cloud-rotate {
  from {
    transform: rotateY(0deg) rotateX(-15deg);
  }
  to {
    transform: rotateY(360deg) rotateX(-15deg);
  }
}

.word-item-3d {
  position: absolute;
  left: 50%;
  top: 50%;
  font-family: var(--font-display);
  font-weight: 600;
  letter-spacing: 0.02em;
  cursor: pointer;
  white-space: nowrap;
  transform-style: preserve-3d;
  /* CSS transform 从右到左执行：先 translateZ 移到球面，再 rotateY 设经度，最后 rotateX 设纬度 */
  transform: rotateX(var(--rx)) rotateY(var(--ry)) translateZ(var(--rz));
  transition: transform 0.3s ease, text-shadow 0.3s ease;
}

.word-item-3d:hover {
  text-shadow: 0 0 20px currentColor, 0 0 40px currentColor !important;
  z-index: 100;
}

.chart {
  width: 100%;
  height: 100%;
}

.empty-state {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--text-muted);
}

/* Quick Actions */
.quick-actions {
  margin-top: 4px;
}

.actions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  padding: 20px;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-normal);
  position: relative;
  overflow: hidden;
}

.action-btn span {
  font-family: var(--font-display);
  font-size: 0.8rem;
  font-weight: 500;
  letter-spacing: 0.05em;
}

.action-btn:hover {
  border-color: var(--neon-cyan);
  color: var(--neon-cyan);
  transform: translateY(-2px);
}

.action-btn.action-primary {
  background: linear-gradient(135deg, rgba(0, 240, 255, 0.15), rgba(0, 240, 255, 0.05));
  border-color: rgba(0, 240, 255, 0.3);
  color: var(--neon-cyan);
}

.action-btn.action-primary:hover {
  box-shadow: var(--glow-cyan);
}

.action-btn.action-warning {
  background: linear-gradient(135deg, rgba(255, 107, 44, 0.15), rgba(255, 107, 44, 0.05));
  border-color: rgba(255, 107, 44, 0.3);
  color: var(--neon-orange);
}

.action-btn.action-warning:hover {
  box-shadow: var(--glow-orange);
}

.action-btn.action-rss {
  background: linear-gradient(135deg, rgba(168, 85, 247, 0.2), rgba(168, 85, 247, 0.08));
  border-color: rgba(168, 85, 247, 0.4);
  color: #a855f7;
}

.action-btn.action-rss:hover {
  box-shadow: 0 0 20px rgba(168, 85, 247, 0.4);
  border-color: #a855f7;
}

.action-hint {
  position: absolute;
  top: 8px;
  right: 10px;
  font-size: 0.6rem;
  padding: 2px 6px;
  background: rgba(168, 85, 247, 0.3);
  border-radius: 4px;
  color: #a855f7;
  letter-spacing: 0.05em;
}

.badge {
  position: absolute;
  top: 10px;
  right: 10px;
  min-width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-mono);
  font-size: 0.65rem;
  font-weight: 600;
  background: var(--neon-red);
  color: white;
  border-radius: 10px;
  padding: 0 6px;
  animation: pulse-glow 2s infinite;
}

/* Responsive */
@media (max-width: 1200px) {
  .charts-row {
    grid-template-columns: 1fr;
  }

  .chart-large {
    grid-column: span 1;
  }
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .actions-grid {
    grid-template-columns: 1fr;
  }
}
</style>
