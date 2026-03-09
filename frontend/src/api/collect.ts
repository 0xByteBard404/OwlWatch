import { request } from './request'

export interface CollectTriggerResponse {
  task_id: string
  message: string
  keyword: string
}

export interface CollectStatusResponse {
  task_id: string
  keyword_id?: string
  keyword: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  collected_count: number
  message: string | null
  created_at: string
  finished_at: string | null
}

// 时间范围选项
export const timeRangeOptions = [
  { label: '最近1天', value: 'oneDay' },
  { label: '最近3天', value: 'threeDays' },
  { label: '最近1周', value: 'oneWeek' },
  { label: '最近1个月', value: 'oneMonth' },
  { label: '最近3个月', value: 'threeMonths' },
]

// API
export const collectApi = {
  // 触发异步采集
  trigger: (keywordId: string, timeRange = 'oneDay', negativeMode = false) =>
    request.post<CollectTriggerResponse>(
      `/collect/trigger?keyword_id=${keywordId}&time_range=${timeRange}&negative_mode=${negativeMode}`
    ),

  // 查询任务状态
  getStatus: (taskId: string) =>
    request.get<CollectStatusResponse>(`/collect/status/${taskId}`),

  // 获取正在运行的任务
  getRunningTasks: () =>
    request.get<{ tasks: CollectStatusResponse[] }>('/collect/running'),
}
