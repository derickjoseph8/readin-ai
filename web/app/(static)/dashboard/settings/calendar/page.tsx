'use client'

import { useState, useEffect } from 'react'
import {
  Calendar,
  Link2,
  Check,
  X,
  Loader2,
  ExternalLink,
  AlertCircle,
  CalendarDays,
  Video,
  Clock
} from 'lucide-react'
import { calendarApi, CalendarIntegration, CalendarEvent } from '@/lib/api/calendar'

// Provider configurations
const PROVIDERS = [
  {
    id: 'google',
    name: 'Google Calendar',
    description: 'Connect your Google Calendar to see upcoming meetings',
    icon: '/icons/google-calendar.svg',
    color: 'bg-blue-500/20 text-blue-400',
  },
  {
    id: 'microsoft',
    name: 'Microsoft Outlook',
    description: 'Connect your Outlook calendar for Office 365 meetings',
    icon: '/icons/outlook.svg',
    color: 'bg-sky-500/20 text-sky-400',
  },
]

function ProviderCard({
  provider,
  integration,
  onConnect,
  onDisconnect,
  isConnecting,
}: {
  provider: typeof PROVIDERS[0]
  integration: CalendarIntegration | null
  onConnect: () => void
  onDisconnect: () => void
  isConnecting: boolean
}) {
  const isConnected = integration?.connected

  return (
    <div className="bg-premium-card border border-premium-border rounded-xl p-6">
      <div className="flex items-start justify-between">
        <div className="flex items-start">
          <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${provider.color}`}>
            <Calendar className="h-6 w-6" />
          </div>
          <div className="ml-4">
            <h3 className="font-medium text-white">{provider.name}</h3>
            <p className="text-gray-500 text-sm mt-0.5">{provider.description}</p>
            {isConnected && integration?.email && (
              <p className="text-emerald-400 text-sm mt-2 flex items-center">
                <Check className="h-4 w-4 mr-1" />
                Connected as {integration.email}
              </p>
            )}
          </div>
        </div>

        <div>
          {isConnected ? (
            <button
              onClick={onDisconnect}
              disabled={isConnecting}
              className="px-4 py-2 border border-red-500/50 text-red-400 rounded-lg hover:bg-red-500/10 transition-colors text-sm flex items-center disabled:opacity-50"
            >
              {isConnecting ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <X className="h-4 w-4 mr-2" />
              )}
              Disconnect
            </button>
          ) : (
            <button
              onClick={onConnect}
              disabled={isConnecting}
              className="px-4 py-2 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-medium rounded-lg hover:shadow-gold transition-all text-sm flex items-center disabled:opacity-50"
            >
              {isConnecting ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <Link2 className="h-4 w-4 mr-2" />
              )}
              Connect
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

function UpcomingMeetings({ events, isLoading }: { events: CalendarEvent[]; isLoading: boolean }) {
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
    })
  }

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
    })
  }

  if (isLoading) {
    return (
      <div className="bg-premium-card border border-premium-border rounded-xl p-6">
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-gold-400" />
        </div>
      </div>
    )
  }

  if (events.length === 0) {
    return (
      <div className="bg-premium-card border border-premium-border rounded-xl p-6">
        <div className="text-center py-8">
          <CalendarDays className="h-12 w-12 text-gray-600 mx-auto mb-3" />
          <p className="text-gray-400">No upcoming meetings</p>
          <p className="text-gray-500 text-sm mt-1">Connect a calendar to see your meetings</p>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-premium-card border border-premium-border rounded-xl overflow-hidden">
      <div className="px-6 py-4 border-b border-premium-border">
        <h3 className="font-medium text-white flex items-center">
          <CalendarDays className="h-5 w-5 text-gold-400 mr-2" />
          Upcoming Meetings
        </h3>
      </div>

      <div className="divide-y divide-premium-border">
        {events.slice(0, 5).map((event) => {
          const meetingApp = calendarApi.detectMeetingApp(event.meeting_link)

          return (
            <div key={event.id} className="px-6 py-4 hover:bg-premium-surface/50 transition-colors">
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <h4 className="font-medium text-white truncate">{event.title}</h4>
                  <div className="flex items-center mt-1 text-sm text-gray-400">
                    <Clock className="h-4 w-4 mr-1" />
                    {formatDate(event.start_time)} at {formatTime(event.start_time)}
                  </div>
                  {meetingApp && (
                    <div className="flex items-center mt-1 text-sm text-emerald-400">
                      <Video className="h-4 w-4 mr-1" />
                      {meetingApp}
                    </div>
                  )}
                </div>

                {event.meeting_link && (
                  <a
                    href={event.meeting_link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-3 py-1.5 bg-gold-500/20 text-gold-400 rounded-lg hover:bg-gold-500/30 transition-colors text-sm flex items-center ml-4"
                  >
                    Join
                    <ExternalLink className="h-3 w-3 ml-1" />
                  </a>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default function CalendarSettingsPage() {
  const [integrations, setIntegrations] = useState<CalendarIntegration[]>([])
  const [events, setEvents] = useState<CalendarEvent[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isEventsLoading, setIsEventsLoading] = useState(false)
  const [connectingProvider, setConnectingProvider] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const fetchIntegrations = async () => {
    try {
      const data = await calendarApi.getIntegrations()
      setIntegrations(data)
    } catch (err) {
      console.error('Failed to fetch integrations:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const fetchEvents = async () => {
    setIsEventsLoading(true)
    try {
      const data = await calendarApi.getAllEvents(10)
      setEvents(data)
    } catch (err) {
      console.error('Failed to fetch events:', err)
    } finally {
      setIsEventsLoading(false)
    }
  }

  useEffect(() => {
    fetchIntegrations()
  }, [])

  useEffect(() => {
    const hasConnected = integrations.some(i => i.connected)
    if (hasConnected) {
      fetchEvents()
    }
  }, [integrations])

  const handleConnect = async (provider: string) => {
    setConnectingProvider(provider)
    setError(null)

    try {
      const { auth_url } = await calendarApi.getAuthUrl(provider)
      // Open OAuth popup
      const popup = window.open(auth_url, 'calendar-auth', 'width=600,height=700')

      // Poll for popup close and refresh integrations
      const checkPopup = setInterval(() => {
        if (popup?.closed) {
          clearInterval(checkPopup)
          setConnectingProvider(null)
          fetchIntegrations()
        }
      }, 500)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to connect calendar')
      setConnectingProvider(null)
    }
  }

  const handleDisconnect = async (provider: string) => {
    setConnectingProvider(provider)
    setError(null)

    try {
      await calendarApi.disconnect(provider)
      setIntegrations(prev =>
        prev.map(i => (i.provider === provider ? { ...i, connected: false, email: null } : i))
      )
      setEvents(prev => prev.filter(e => e.provider !== provider))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to disconnect calendar')
    } finally {
      setConnectingProvider(null)
    }
  }

  const getIntegrationForProvider = (providerId: string) =>
    integrations.find(i => i.provider === providerId) || null

  return (
    <div className="max-w-3xl space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Calendar Integration</h1>
        <p className="text-gray-400 mt-1">
          Connect your calendars to automatically sync meetings with ReadIn AI
        </p>
      </div>

      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 flex items-center">
          <AlertCircle className="h-5 w-5 mr-2 flex-shrink-0" />
          {error}
        </div>
      )}

      {/* Connected Calendars */}
      <div className="space-y-4">
        <h2 className="text-lg font-semibold text-white">Calendar Providers</h2>

        {isLoading ? (
          <div className="bg-premium-card border border-premium-border rounded-xl p-6">
            <div className="flex items-center justify-center py-4">
              <Loader2 className="h-6 w-6 animate-spin text-gold-400" />
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {PROVIDERS.map(provider => (
              <ProviderCard
                key={provider.id}
                provider={provider}
                integration={getIntegrationForProvider(provider.id)}
                onConnect={() => handleConnect(provider.id)}
                onDisconnect={() => handleDisconnect(provider.id)}
                isConnecting={connectingProvider === provider.id}
              />
            ))}
          </div>
        )}
      </div>

      {/* Upcoming Meetings */}
      <div className="space-y-4">
        <h2 className="text-lg font-semibold text-white">Upcoming Meetings</h2>
        <UpcomingMeetings events={events} isLoading={isEventsLoading} />
      </div>

      {/* Desktop App Integration Info */}
      <div className="bg-premium-card border border-premium-border rounded-xl p-6">
        <h3 className="font-medium text-white mb-3 flex items-center">
          <Video className="h-5 w-5 text-gold-400 mr-2" />
          Desktop App Integration
        </h3>
        <p className="text-gray-400 text-sm">
          Once connected, ReadIn AI can automatically detect when your meetings start and prompt you
          to launch the desktop app. The app will automatically identify which video conferencing
          tool is being used (Zoom, Teams, Meet, etc.) and provide real-time assistance.
        </p>
        <div className="mt-4 flex items-center text-sm text-gray-500">
          <Check className="h-4 w-4 mr-2 text-emerald-400" />
          Automatic meeting detection
        </div>
        <div className="mt-2 flex items-center text-sm text-gray-500">
          <Check className="h-4 w-4 mr-2 text-emerald-400" />
          Video tool auto-detection (Zoom, Teams, Meet)
        </div>
        <div className="mt-2 flex items-center text-sm text-gray-500">
          <Check className="h-4 w-4 mr-2 text-emerald-400" />
          One-click launch for meetings
        </div>
      </div>
    </div>
  )
}
