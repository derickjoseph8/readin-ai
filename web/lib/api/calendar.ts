/**
 * Calendar Integration API
 */

import apiClient from './client'

export interface CalendarIntegration {
  provider: string
  connected: boolean
  email: string | null
  connected_at: string | null
}

export interface CalendarAuthResponse {
  auth_url: string
  state: string
}

export interface CalendarEvent {
  id: string
  title: string
  description: string | null
  start_time: string
  end_time: string
  location: string | null
  attendees: string[]
  meeting_link: string | null
  provider: string
}

export interface CalendarEventsResponse {
  events: CalendarEvent[]
  count: number
}

export const calendarApi = {
  /**
   * Get list of available calendar providers
   */
  async getProviders(): Promise<{ providers: string[] }> {
    return apiClient.get('/calendar/providers')
  },

  /**
   * Get user's calendar integrations
   */
  async getIntegrations(): Promise<CalendarIntegration[]> {
    return apiClient.get('/calendar/integrations')
  },

  /**
   * Get OAuth authorization URL for a provider
   */
  async getAuthUrl(provider: string): Promise<CalendarAuthResponse> {
    return apiClient.get(`/calendar/auth/${provider}`)
  },

  /**
   * Disconnect a calendar integration
   */
  async disconnect(provider: string): Promise<{ status: string; message: string }> {
    return apiClient.delete(`/calendar/${provider}`)
  },

  /**
   * Get upcoming events from a provider
   */
  async getEvents(provider: string, maxResults: number = 10): Promise<CalendarEventsResponse> {
    return apiClient.get(`/calendar/${provider}/events?max_results=${maxResults}`)
  },

  /**
   * Get all events from all connected calendars
   */
  async getAllEvents(maxResults: number = 20): Promise<CalendarEvent[]> {
    try {
      const integrations = await this.getIntegrations()
      const connectedProviders = integrations.filter(i => i.connected).map(i => i.provider)

      const allEvents: CalendarEvent[] = []

      for (const provider of connectedProviders) {
        try {
          const response = await this.getEvents(provider, maxResults)
          allEvents.push(...response.events)
        } catch (err) {
          console.error(`Failed to fetch events from ${provider}:`, err)
        }
      }

      // Sort by start time
      return allEvents.sort((a, b) =>
        new Date(a.start_time).getTime() - new Date(b.start_time).getTime()
      )
    } catch (err) {
      console.error('Failed to fetch all events:', err)
      return []
    }
  },

  /**
   * Detect meeting app from meeting link
   */
  detectMeetingApp(link: string | null): string | null {
    if (!link) return null

    if (link.includes('zoom.us')) return 'Zoom'
    if (link.includes('meet.google.com')) return 'Google Meet'
    if (link.includes('teams.microsoft.com')) return 'Microsoft Teams'
    if (link.includes('webex.com')) return 'Webex'
    if (link.includes('discord.gg')) return 'Discord'
    if (link.includes('whereby.com')) return 'Whereby'
    if (link.includes('around.co')) return 'Around'
    if (link.includes('tuple.app')) return 'Tuple'

    return 'Video Call'
  }
}

export default calendarApi
