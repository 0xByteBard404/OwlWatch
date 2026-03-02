import { request } from './request'

// 类型定义
export interface Keyword {
  id: string
  keyword: string
  priority: string
  platforms: string[]
  is_active: boolean
  created_at: string
}

export interface KeywordCreate {
  keyword: string
  priority?: string
  platforms?: string[]
}

// API
export const keywordsApi = {
  list: () => request.get<Keyword[]>('/keywords/'),

  create: (data: KeywordCreate) => request.post<Keyword>('/keywords/', data),

  update: (id: string, data: KeywordCreate) =>
    request.put<Keyword>(`/keywords/${id}`, data),

  delete: (id: string) => request.delete(`/keywords/${id}`),
}
