import { request } from './request'

// 类型定义
export interface SentimentKeyword {
  id: string
  keyword: string
  sentiment_type: 'positive' | 'negative'
  category: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface SentimentKeywordCreate {
  keyword: string
  sentiment_type: 'positive' | 'negative'
  category?: string
}

export interface SentimentKeywordUpdate {
  keyword?: string
  sentiment_type?: 'positive' | 'negative'
  category?: string
  is_active?: boolean
}

// API
export const sentimentKeywordsApi = {
  list: (sentimentType?: 'positive' | 'negative', category?: string) => {
    const params: Record<string, string> = {}
    if (sentimentType) params.sentiment_type = sentimentType
    if (category) params.category = category
    return request.get<SentimentKeyword[]>('/sentiment-keywords', { params })
  },

  create: (data: SentimentKeywordCreate) =>
    request.post<SentimentKeyword>('/sentiment-keywords', data),

  update: (id: string, data: SentimentKeywordUpdate) =>
    request.put<SentimentKeyword>(`/sentiment-keywords/${id}`, data),

  toggle: (id: string) =>
    request.put<{ message: string; is_active: boolean }>(`/sentiment-keywords/${id}/toggle`),

  delete: (id: string) =>
    request.delete(`/sentiment-keywords/${id}`),

  getCategories: () =>
    request.get<string[]>('/sentiment-keywords/categories'),
}
