/**
 * Analytics API
 */

import apiClient from './client'

export interface UsageStats {
  daily_usage: number
  daily_limit: number | null
  weekly_usage: number
  monthly_usage: number
  total_usage: number
}

export interface MeetingTrend {
  date: string
  count: number
  duration_minutes: number
}

export interface TopicFrequency {
  topic: string
  count: number
  percentage: number
}

export interface AnalyticsDashboard {
  usage: UsageStats
  meeting_trends: MeetingTrend[]
  top_topics: TopicFrequency[]
  response_quality: {
    average_rating: number
    total_ratings: number
  }
  time_saved_minutes: number
}

export const analyticsApi = {
  async getDashboard(): Promise<AnalyticsDashboard> {
    return apiClient.get<AnalyticsDashboard>('/api/v1/analytics/dashboard')
  },

  async getUsage(): Promise<UsageStats> {
    return apiClient.get<UsageStats>('/api/v1/analytics/usage')
  },

  async getMeetingTrends(days = 30): Promise<MeetingTrend[]> {
    return apiClient.get<MeetingTrend[]>(`/api/v1/analytics/trends?days=${days}`)
  },

  async getTopTopics(limit = 10): Promise<TopicFrequency[]> {
    return apiClient.get<TopicFrequency[]>(`/api/v1/analytics/topics?limit=${limit}`)
  },
}

export default analyticsApi
