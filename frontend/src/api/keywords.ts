import { request } from './request'

// 数据源配置类型
export interface DataSources {
  rss_ids?: string[]
  search_apis?: string[]
}

// 预警配置类型
export interface NegativeBurstConfig {
  enabled: boolean
  threshold: number  // 负面情感占比阈值 (0-1)
  min_count: number   // 最少文章数
}

export interface SensitiveKeywordConfig {
  enabled: boolean
  use_global: boolean       // 使用全局敏感词库
  custom_keywords: string[]  // 自定义敏感词
}

export interface VolumeSpikeConfig {
  enabled: boolean
  threshold: number  // 增长倍数阈值
}

export interface AlertConfig {
  negative_burst?: NegativeBurstConfig
  sensitive_keyword?: SensitiveKeywordConfig
  volume_spike?: VolumeSpikeConfig
  notifications?: string[]  // 通知渠道: email, webhook, wechat
}

// 类型定义
export interface Keyword {
  id: string
  keyword: string
  priority: string
  platforms: string[]
  data_sources?: DataSources
  alert_config?: AlertConfig
  fetch_interval?: number  // 更新间隔（秒）
  last_fetched?: string    // 最近扫描时间
  is_active: boolean
  created_at: string
}

export interface KeywordCreate {
  keyword: string
  priority?: string
  platforms?: string[]
  data_sources?: DataSources
  alert_config?: AlertConfig
  fetch_interval?: number  // 更新间隔（秒）
}

export interface KeywordUpdate {
  keyword?: string
  priority?: string
  platforms?: string[]
  data_sources?: DataSources
  alert_config?: AlertConfig
  fetch_interval?: number
  is_active?: boolean
}

export interface RefreshResponse {
  task_id: string
  message: string
  keyword: string
}

// 默认预警配置
export const DEFAULT_ALERT_CONFIG: AlertConfig = {
  negative_burst: {
    enabled: true,
    threshold: 0.3,
    min_count: 3,
  },
  sensitive_keyword: {
    enabled: true,
    use_global: true,
    custom_keywords: [],
  },
  volume_spike: {
    enabled: true,
    threshold: 2.0,
  },
  notifications: ['email', 'webhook'],
}

// API
export const keywordsApi = {
  list: () => request.get<Keyword[]>('/keywords/'),

  get: (id: string) => request.get<Keyword>(`/keywords/${id}`),

  create: (data: KeywordCreate) => request.post<Keyword>('/keywords/', data),

  update: (id: string, data: KeywordUpdate) =>
    request.put<Keyword>(`/keywords/${id}`, data),

  delete: (id: string) => request.delete(`/keywords/${id}`),

  // 立即刷新数据
  refresh: (id: string) => request.post<RefreshResponse>(`/keywords/${id}/refresh`),
}
