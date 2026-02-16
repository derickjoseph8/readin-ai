/**
 * Authentication API
 */

import apiClient from './client'

export interface User {
  id: number
  email: string
  full_name: string | null
  profession: string | null
  company: string | null
  subscription_status: string
  trial_ends_at: string | null
  created_at: string
  account_type?: string
  company_name?: string | null
  organization_id?: number | null
}

export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  email: string
  password: string
  full_name?: string
  account_type?: string
  company_name?: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: User
}

export interface UserStatus {
  user: User
  subscription: {
    status: string
    trial_days_remaining: number
    is_active: boolean
    current_period_end?: string | null
  }
  usage: {
    daily_count: number
    daily_limit: number | null
  }
}

export const authApi = {
  async login(data: LoginRequest): Promise<AuthResponse> {
    const response = await apiClient.post<{ access_token: string }>('/api/v1/auth/login', data)
    apiClient.setToken(response.access_token)
    // Fetch user info after login
    const user = await this.getMe()
    return { ...response, token_type: 'bearer', user }
  },

  async register(data: RegisterRequest): Promise<AuthResponse> {
    const response = await apiClient.post<{ access_token: string }>('/api/v1/auth/register', data)
    apiClient.setToken(response.access_token)
    const user = await this.getMe()
    return { ...response, token_type: 'bearer', user }
  },

  async getMe(): Promise<User> {
    return apiClient.get<User>('/user/me')
  },

  async getStatus(): Promise<UserStatus> {
    const user = await this.getMe()
    const status = await apiClient.get<{
      is_active: boolean
      subscription_status: string
      trial_days_remaining: number | null
      daily_usage: number
      daily_limit: number | null
      can_use: boolean
    }>('/user/status')

    return {
      user,
      subscription: {
        status: status.subscription_status,
        trial_days_remaining: status.trial_days_remaining || 0,
        is_active: status.is_active,
      },
      usage: {
        daily_count: status.daily_usage,
        daily_limit: status.daily_limit,
      },
    }
  },

  async updateProfile(data: { full_name?: string; profession?: string; company?: string }): Promise<User> {
    return apiClient.patch<User>('/user/me', data)
  },

  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    return apiClient.post('/api/v1/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    })
  },

  logout() {
    apiClient.clearToken()
  },

  isAuthenticated(): boolean {
    return !!apiClient.getToken()
  },
}

export default authApi
