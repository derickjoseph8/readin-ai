/**
 * Analytics API
 */

import apiClient from './client'

// =============================================================================
// TYPES
// =============================================================================

export type TimeRange = 'week' | 'month' | 'quarter' | 'year' | 'all_time'

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

export interface MeetingStats {
  total_meetings: number
  total_duration_minutes: number
  avg_duration_minutes: number
  meetings_by_type: Record<string, number>
  meetings_by_app: Record<string, number>
  trend: { date: string; count: number }[]
}

export interface TopicStats {
  total_topics: number
  top_topics: { name: string; frequency: number; category: string }[]
  topic_trends: { date: string; topic: string; count: number }[]
  emerging_topics: { name: string; frequency: number; last_discussed: string }[]
}

export interface ActionItemStats {
  total_created: number
  total_completed: number
  completion_rate: number
  overdue_count: number
  by_priority: Record<string, number>
  by_status: Record<string, number>
  completion_trend: { date: string; completed: number }[]
}

export interface AIUsageStats {
  total_responses: number
  responses_this_period: number
  daily_average: number
  estimated_cost_cents: number
  by_model: Record<string, number>
  usage_trend: { date: string; count: number }[]
}

export interface DashboardOverview {
  period: string
  meetings: MeetingStats
  topics: TopicStats
  action_items: ActionItemStats
  ai_usage: AIUsageStats
  engagement_score: number
}

export interface ProductivityScore {
  score: number
  components: {
    action_completion: number
    meeting_efficiency: number
    commitment_rate: number
  }
  trend: string
  period: string
}

export interface HeatmapData {
  heatmap: number[][]
  days: string[]
  total_meetings: number
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

// =============================================================================
// API
// =============================================================================

export const analyticsApi = {
  // Legacy endpoints for backward compatibility
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

  // New comprehensive endpoints
  async getOverview(timeRange: TimeRange = 'month'): Promise<DashboardOverview> {
    return apiClient.get<DashboardOverview>(`/api/v1/analytics/dashboard/overview?time_range=${timeRange}`)
  },

  async getMeetingStats(timeRange: TimeRange = 'month'): Promise<MeetingStats> {
    return apiClient.get<MeetingStats>(`/api/v1/analytics/dashboard/meetings?time_range=${timeRange}`)
  },

  async getTopicStats(timeRange: TimeRange = 'month'): Promise<TopicStats> {
    return apiClient.get<TopicStats>(`/api/v1/analytics/dashboard/topics?time_range=${timeRange}`)
  },

  async getActionItemStats(timeRange: TimeRange = 'month'): Promise<ActionItemStats> {
    return apiClient.get<ActionItemStats>(`/api/v1/analytics/dashboard/action-items?time_range=${timeRange}`)
  },

  async getAIUsageStats(timeRange: TimeRange = 'month'): Promise<AIUsageStats> {
    return apiClient.get<AIUsageStats>(`/api/v1/analytics/dashboard/ai-usage?time_range=${timeRange}`)
  },

  async getHeatmap(timeRange: TimeRange = 'month'): Promise<HeatmapData> {
    return apiClient.get<HeatmapData>(`/api/v1/analytics/dashboard/heatmap?time_range=${timeRange}`)
  },

  async getProductivityScore(timeRange: TimeRange = 'month'): Promise<ProductivityScore> {
    return apiClient.get<ProductivityScore>(`/api/v1/analytics/dashboard/productivity-score?time_range=${timeRange}`)
  },

  async exportAnalytics(timeRange: TimeRange = 'month', format: 'json' | 'csv' = 'json'): Promise<Blob | object> {
    if (format === 'csv') {
      const response = await fetch(`/api/v1/analytics/dashboard/export?time_range=${timeRange}&format=csv`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      })
      return response.blob()
    }
    return apiClient.get(`/api/v1/analytics/dashboard/export?time_range=${timeRange}&format=json`)
  },
}

export default analyticsApi
