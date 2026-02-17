/**
 * Integrations API client for Slack, Microsoft Teams, and Video Platforms.
 *
 * VIDEO PLATFORM INTEGRATIONS (STEALTH MODE):
 * - NO bots join meetings (completely invisible to other participants)
 * - Local audio capture only via desktop app
 * - Calendar sync for meeting detection
 * - Per-user OAuth tokens (data isolation)
 */

import { apiClient } from './client'

export interface IntegrationStatus {
  provider: string
  display_name: string
  is_configured: boolean
  is_connected: boolean
  workspace_name?: string
  user_name?: string
  default_channel?: string
  connected_at?: string
  notifications_enabled: boolean
  meeting_summaries_enabled: boolean
  action_item_reminders_enabled: boolean
}

export interface VideoPlatformStatus {
  provider: string
  display_name: string
  is_configured: boolean
  is_connected: boolean
  email?: string
  display_name_user?: string
  connected_at?: string
  stealth_mode: boolean
  privacy_note: string
}

export interface Meeting {
  id: string
  topic: string
  start_time: string
  duration: number
  join_url?: string
  platform: string
  organizer?: string
  attendees?: string[]
}

export interface IntegrationSettings {
  notifications_enabled: boolean
  meeting_summaries_enabled: boolean
  action_item_reminders_enabled: boolean
  briefing_notifications_enabled: boolean
  default_channel_id?: string
}

export interface Channel {
  id: string
  name: string
  is_private?: boolean
  is_member?: boolean
  description?: string
  membership_type?: string
}

export interface Team {
  id: string
  name: string
  description?: string
}

// Get status of all integrations
export async function getIntegrationsStatus(): Promise<{ integrations: IntegrationStatus[] }> {
  return apiClient.get('/api/v1/integrations/status')
}

// Slack OAuth
export async function getSlackAuthUrl(): Promise<{ authorization_url: string }> {
  return apiClient.get('/api/v1/integrations/slack/authorize')
}

export async function getSlackChannels(): Promise<{ channels: Channel[] }> {
  return apiClient.get('/api/v1/integrations/slack/channels')
}

export async function disconnectSlack(): Promise<{ message: string }> {
  return apiClient.delete('/api/v1/integrations/slack')
}

// Teams OAuth
export async function getTeamsAuthUrl(): Promise<{ authorization_url: string }> {
  return apiClient.get('/api/v1/integrations/teams/authorize')
}

export async function getTeamsList(): Promise<{ teams: Team[] }> {
  return apiClient.get('/api/v1/integrations/teams/teams')
}

export async function getTeamsChannels(teamId: string): Promise<{ channels: Channel[] }> {
  return apiClient.get(`/api/v1/integrations/teams/channels/${teamId}`)
}

export async function disconnectTeams(): Promise<{ message: string }> {
  return apiClient.delete('/api/v1/integrations/teams')
}

// Update settings for any integration
export async function updateIntegrationSettings(
  provider: 'slack' | 'teams',
  settings: IntegrationSettings
): Promise<{ message: string }> {
  return apiClient.put(`/api/v1/integrations/${provider}/settings`, settings)
}

// Send test notification
export async function sendTestNotification(
  provider: 'slack' | 'teams',
  channelId: string
): Promise<{ message: string }> {
  return apiClient.post(`/api/v1/integrations/${provider}/test`, { channel_id: channelId })
}

// =============================================================================
// VIDEO PLATFORM INTEGRATIONS (STEALTH MODE)
// =============================================================================

// Get status of all video platform integrations
export async function getVideoPlatformsStatus(): Promise<{
  video_platforms: VideoPlatformStatus[]
  stealth_mode_explanation: string
}> {
  return apiClient.get('/api/v1/integrations/video-platforms/status')
}

// Zoom
export async function getZoomAuthUrl(): Promise<{ authorization_url: string }> {
  return apiClient.get('/api/v1/integrations/zoom/authorize')
}

export async function disconnectZoom(): Promise<{ message: string }> {
  return apiClient.delete('/api/v1/integrations/zoom')
}

export async function getZoomMeetings(): Promise<{ meetings: Meeting[], platform: string }> {
  return apiClient.get('/api/v1/integrations/zoom/meetings')
}

// Google Meet
export async function getGoogleMeetAuthUrl(): Promise<{ authorization_url: string }> {
  return apiClient.get('/api/v1/integrations/google-meet/authorize')
}

export async function disconnectGoogleMeet(): Promise<{ message: string }> {
  return apiClient.delete('/api/v1/integrations/google-meet')
}

export async function getGoogleMeetMeetings(): Promise<{ meetings: Meeting[], platform: string }> {
  return apiClient.get('/api/v1/integrations/google-meet/meetings')
}

// Microsoft Teams Meetings (Calendar sync)
export async function getTeamsMeetingAuthUrl(): Promise<{ authorization_url: string }> {
  return apiClient.get('/api/v1/integrations/teams-meeting/authorize')
}

export async function disconnectTeamsMeeting(): Promise<{ message: string }> {
  return apiClient.delete('/api/v1/integrations/teams-meeting')
}

export async function getTeamsMeetings(): Promise<{ meetings: Meeting[], platform: string }> {
  return apiClient.get('/api/v1/integrations/teams-meeting/meetings')
}

// Webex
export async function getWebexAuthUrl(): Promise<{ authorization_url: string }> {
  return apiClient.get('/api/v1/integrations/webex/authorize')
}

export async function disconnectWebex(): Promise<{ message: string }> {
  return apiClient.delete('/api/v1/integrations/webex')
}

export async function getWebexMeetings(): Promise<{ meetings: Meeting[], platform: string }> {
  return apiClient.get('/api/v1/integrations/webex/meetings')
}

// Unified meeting endpoints
export async function getAllUpcomingMeetings(): Promise<{
  meetings: Meeting[]
  stealth_mode: boolean
  privacy_note: string
}> {
  return apiClient.get('/api/v1/integrations/meetings/upcoming')
}

export async function checkActiveMeeting(): Promise<{
  active_meeting: Meeting | null
  is_in_meeting: boolean
  stealth_mode: boolean
}> {
  return apiClient.get('/api/v1/integrations/meetings/active')
}
