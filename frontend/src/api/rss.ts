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
  category?: string
  routes: Array<{
    path: string
    name: string
    params: string[]
    help?: string
  }>
}

export interface RSSHubBuildRequest {
  platform: string
  route_path: string
  params: Record<string, string>
}

export interface RSSHubBuildResponse {
  url: string
  platform: string
  route_name: string
}

// RSSHub 配置相关
export interface RSSHubConfig {
  id: string
  platform: string
  display_name: string
  config_type: string
  config_value: string
  description: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface RSSHubConfigCreate {
  platform: string
  display_name: string
  config_type: string
  config_value: string
  description?: string
}

export interface RSSHubConfigTemplate {
  display_name: string
  config_type: string
  description: string
  env_key: string
}

export interface InitFeedsResponse {
  added_count: number
  skipped_count: number
  added_feeds: string[]
  message: string
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

  // 初始化默认订阅
  initDefault: () =>
    request.post<InitFeedsResponse>('/rss/init-default'),

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

  // RSSHub 配置管理
  getConfigTemplates: () =>
    request.get<Record<string, RSSHubConfigTemplate>>('/rss/configs/templates'),

  getConfigs: () =>
    request.get<RSSHubConfig[]>('/rss/configs'),

  createConfig: (data: RSSHubConfigCreate) =>
    request.post<RSSHubConfig>('/rss/configs', data),

  deleteConfig: (id: string) =>
    request.delete(`/rss/configs/${id}`),

  testConfig: (id: string) =>
    request.post<{ success: boolean; message: string }>(`/rss/configs/${id}/test`),
}
