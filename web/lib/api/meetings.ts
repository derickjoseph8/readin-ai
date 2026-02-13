/**
 * Meetings API
 */

import apiClient from './client'

export interface Meeting {
  id: number
  user_id: number
  meeting_type: string
  title: string | null
  meeting_app: string | null
  started_at: string
  ended_at: string | null
  duration_seconds: number | null
  summary: string | null
  key_points: string[] | null
  action_items: string[] | null
  participant_count: number
  conversation_count: number
}

export interface Conversation {
  id: number
  meeting_id: number
  speaker: string
  transcript: string
  ai_response: string | null
  timestamp: string
  response_time_ms: number | null
}

export interface MeetingDetail extends Meeting {
  conversations: Conversation[]
}

export interface MeetingsResponse {
  meetings: Meeting[]
  total: number
  page: number
  per_page: number
}

export interface MeetingStats {
  total_meetings: number
  total_duration_minutes: number
  total_conversations: number
  average_duration_minutes: number
  meetings_this_week: number
  meetings_this_month: number
}

export const meetingsApi = {
  async list(page = 1, perPage = 10): Promise<MeetingsResponse> {
    return apiClient.get<MeetingsResponse>(
      `/api/v1/meetings?page=${page}&per_page=${perPage}`
    )
  },

  async get(id: number): Promise<MeetingDetail> {
    return apiClient.get<MeetingDetail>(`/api/v1/meetings/${id}`)
  },

  async getStats(): Promise<MeetingStats> {
    return apiClient.get<MeetingStats>('/api/v1/meetings/stats')
  },

  async delete(id: number): Promise<void> {
    return apiClient.delete(`/api/v1/meetings/${id}`)
  },

  async exportMeeting(id: number, format: 'json' | 'markdown' = 'json'): Promise<Blob> {
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL || 'https://www.getreadin.us'}/api/v1/meetings/${id}/export?format=${format}`,
      {
        headers: {
          Authorization: `Bearer ${apiClient.getToken()}`,
        },
      }
    )
    return response.blob()
  },

  async generateSummary(id: number): Promise<Meeting> {
    return apiClient.post<Meeting>(`/api/v1/meetings/${id}/summarize`)
  },
}

export default meetingsApi
