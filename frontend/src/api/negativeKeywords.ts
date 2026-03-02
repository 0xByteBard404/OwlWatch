import { request } from './request'

// 类型定义
export interface NegativeKeyword {
  id: string
  keyword: string
  is_active: boolean
  created_at: string
}

export interface NegativeKeywordCreate {
  keyword: string
}

// API
export const negativeKeywordsApi = {
  list: (isActive?: boolean) => {
    const params = isActive !== undefined ? { is_active: isActive } : {}
    return request.get<NegativeKeyword[]>('/negative-keywords/', { params })
  },

  create: (data: NegativeKeywordCreate) =>
    request.post<NegativeKeyword>('/negative-keywords/', data),

  update: (id: string, data: NegativeKeywordCreate) =>
    request.put<NegativeKeyword>(`/negative-keywords/${id}`, data),

  toggle: (id: string) =>
    request.put<{ message: string; is_active: boolean }>(`/negative-keywords/${id}/toggle`),

  delete: (id: string) =>
    request.delete(`/negative-keywords/${id}`),

  initDefaults: () =>
    request.post<{ message: string }>('/negative-keywords/init-defaults'),
}
