import { request } from './request'

// 类型定义
export interface Article {
  id: string
  keyword_id: string
  title: string
  content: string | null
  url: string
  source: string | null
  source_api: string | null
  sentiment_score: number | null
  sentiment_label: string | null
  publish_time: string | null
  collect_time: string
}

export interface ArticleListResponse {
  items: Article[]
  total: number
  page: number
  size: number
}

export interface ArticleListParams {
  page?: number
  size?: number
  keyword_id?: string
  sentiment?: string
  source?: string
  start_date?: string
  end_date?: string
}

// 统计类型
export interface TrendPoint {
  date: string
  count: number
  positive: number
  negative: number
  neutral: number
}

export interface TrendResponse {
  data: TrendPoint[]
}

export interface SourceDistribution {
  source: string
  count: number
}

export interface WordFrequency {
  word: string
  count: number
}

export interface StatsOverview {
  total: number
  today: number
  week: number
  positive_ratio: number
  negative_ratio: number
}

// API
export const articlesApi = {
  list: (params: ArticleListParams) =>
    request.get<ArticleListResponse>('/articles/', { params }),

  get: (id: string) => request.get<Article>(`/articles/${id}`),

  // 统计 API
  getStatsOverview: () => request.get<StatsOverview>('/articles/stats/overview'),

  getTrend: (days = 7, keywordId?: string) =>
    request.get<TrendResponse>('/articles/stats/trend', {
      params: { days, keyword_id: keywordId }
    }),

  getSources: (keywordId?: string, limit = 10) =>
    request.get<SourceDistribution[]>('/articles/stats/sources', {
      params: { keyword_id: keywordId, limit }
    }),

  getWords: (days = 7, keywordId?: string, limit = 50) =>
    request.get<WordFrequency[]>('/articles/stats/words', {
      params: { days, keyword_id: keywordId, limit }
    }),
}
