import { request } from './request'

// 类型定义
export interface RSSFeed {
  id: string
  name: string
  feed_url: string
  source_type: string | null
  keyword_id: string | null
  is_active: boolean
  last_fetched: string | null
  fetch_error_count: number
  last_error: string | null
  fetch_interval: number
  total_entries: number
  created_at: string
}

export interface RSSFeedCreate {
  name: string
  feed_url: string
  source_type?: string
  keyword_id?: string
  fetch_interval?: number
}

export interface RSSFeedUpdate {
  name?: string
  feed_url?: string
  source_type?: string
  keyword_id?: string
  fetch_interval?: number
  is_active?: boolean
}

export interface RSSFeedTestResponse {
  success: boolean
  message: string
  entry_count: number
  sample_titles: string[]
}

export interface RSSHubPlatform {
  name: string
  routes: Array<{
    path: string
    name: string
    params: string[]
  }>
}

export interface RSSHubBuildRequest {
  platform: string
  params: Record<string, string>
}

export interface RSSHubBuildResponse {
  url: string
  platform: string
  route_name: string
}

// API
export const rssApi = {
  // 订阅管理
  list: (params?: { is_active?: boolean; source_type?: string }) =>
    request.get<RSSFeed[]>('/rss/', { params }),

  get: (id: string) => request.get<RSSFeed>(`/rss/${id}`),

  create: (data: RSSFeedCreate) => request.post<RSSFeed>('/rss/', data),

  update: (id: string, data: RSSFeedUpdate) =>
    request.put<RSSFeed>(`/rss/${id}`, data),

  delete: (id: string) => request.delete(`/rss/${id}`),

  // 测试和手动获取
  test: (id: string) =>
    request.post<RSSFeedTestResponse>(`/rss/${id}/test`),

  fetch: (id: string) =>
    request.post<{ message: string }>(`/rss/${id}/fetch`),

  // RSSHub 辅助
  getPlatforms: () =>
    request.get<Record<string, RSSHubPlatform>>('/rss/rsshub/platforms'),

  buildUrl: (data: RSSHubBuildRequest) =>
    request.post<RSSHubBuildResponse>('/rss/rsshub/build', data),
}
