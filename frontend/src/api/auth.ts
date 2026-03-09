import { request } from './request'

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  expires_in: number
}

export interface UserInfo {
  id: string
  username: string
  email: string
  full_name: string | null
  role: string
  is_active: boolean
  tenant_id: string
  created_at: string
}

// 登录
export async function login(data: LoginRequest): Promise<LoginResponse> {
  // OAuth2 要求使用 form-data 格式
  const formData = new URLSearchParams()
  formData.append('username', data.username)
  formData.append('password', data.password)

  const response = await fetch('/api/v1/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: formData.toString(),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: '登录失败' }))
    throw new Error(error.detail || '登录失败')
  }

  return response.json()
}

// 获取当前用户信息
export async function getCurrentUser(): Promise<UserInfo> {
  return request.get<UserInfo>('/auth/me')
}

// 验证 token
export async function verifyToken(): Promise<{ valid: boolean; user_id: string; username: string; role: string }> {
  return request.post('/auth/verify')
}
