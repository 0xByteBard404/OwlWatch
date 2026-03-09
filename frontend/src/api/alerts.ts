import { request } from './request'

// 类型定义
export interface Alert {
  id: string
  keyword_id: string
  keyword_name?: string | null
  article_id: string | null
  related_article_ids: string[]
  alert_type: string | null
  alert_level: string
  status: string
  message: string | null
  // 处理信息
  handler_id: string | null
  handler_name: string | null
  handle_note: string | null
  is_false_positive: boolean
  // 时间
  created_at: string
  handled_at: string | null
}

export interface ArticleBrief {
  id: string
  title: string
  url: string
  source: string | null
  sentiment_score: number | null
  sentiment_label: string | null
  publish_time: string | null
}

export interface AlertDetail extends Alert {
  keyword_name: string | null
  related_article_ids: string[]
  related_articles: ArticleBrief[]
}

export interface AlertListResponse {
  items: Alert[]
  total: number
}

export interface AlertStatsResponse {
  total: number
  pending: number
  handled: number
  ignored: number
  false_positive: number
  by_level: Record<string, number>
  by_type: Record<string, number>
}

export interface AlertListParams {
  page?: number
  size?: number
  status?: string
  alert_level?: string
  alert_type?: string
  keyword_id?: string
}

export interface HandleParams {
  note?: string
}

export interface FalsePositiveParams {
  reason?: string
}

// API
export const alertsApi = {
  list: (params: AlertListParams) =>
    request.get<AlertListResponse>('/alerts/', { params }),

  stats: () => request.get<AlertStatsResponse>('/alerts/stats'),

  detail: (id: string) =>
    request.get<AlertDetail>(`/alerts/${id}`),

  handle: (id: string, params?: HandleParams) =>
    request.put(`/alerts/${id}/handle`, params || {}),

  ignore: (id: string) =>
    request.put(`/alerts/${id}/ignore`),

  markFalsePositive: (id: string, params?: FalsePositiveParams) =>
    request.put(`/alerts/${id}/false-positive`, params || {}),

  batchHandle: (ids: string[], note?: string) =>
    request.post('/alerts/batch-handle', { alert_ids: ids, note }),
}
