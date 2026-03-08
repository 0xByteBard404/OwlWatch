import { request } from './request'

// 数据源配置类型
export interface DataSources {
  rss_ids?: string[]
  search_apis?: string[]
}

// 类型定义
export interface Keyword {
  id: string
  keyword: string
  priority: string
  platforms: string[]
  data_sources?: DataSources
  is_active: boolean
  created_at: string
}

export interface KeywordCreate {
  keyword: string
  priority?: string
  platforms?: string[]
  data_sources?: DataSources
}

// API
export const keywordsApi = {
  list: () => request.get<Keyword[]>('/keywords/'),

  get: (id: string) => request.get<Keyword>(`/keywords/${id}`),

  create: (data: KeywordCreate) => request.post<Keyword>('/keywords/', data),

  update: (id: string, data: KeywordCreate) =>
    request.put<Keyword>(`/keywords/${id}`, data),

  delete: (id: string) => request.delete(`/keywords/${id}`),
}
