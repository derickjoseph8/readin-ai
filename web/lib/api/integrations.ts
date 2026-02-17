/**
 * Integrations API client for Slack and Microsoft Teams.
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
