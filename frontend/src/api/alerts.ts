import { request } from './request'

// 类型定义
export interface Alert {
  id: string
  keyword_id: string
  article_id: string | null
  alert_type: string | null
  alert_level: string
  status: string
  message: string | null
  created_at: string
  handled_at: string | null
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

// API
export const alertsApi = {
  list: (params: AlertListParams) =>
    request.get<AlertListResponse>('/alerts/', { params }),

  stats: () => request.get<AlertStatsResponse>('/alerts/stats'),

  handle: (id: string) => request.put(`/alerts/${id}/handle`),

  ignore: (id: string) => request.put(`/alerts/${id}/ignore`),

  batchHandle: (ids: string[]) =>
    request.post('/alerts/batch-handle', { alert_ids: ids }),

  test: (keywordId: string, alertLevel = 'warning', alertType = 'negative_burst') =>
    request.post(`/alerts/test?keyword_id=${keywordId}&alert_level=${alertLevel}&alert_type=${alertType}`),
}
