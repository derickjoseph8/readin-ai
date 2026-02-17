'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import {
  Calendar,
  Clock,
  MessageSquare,
  Search,
  ChevronLeft,
  ChevronRight,
  MoreVertical,
  Trash2,
  Download,
  FileText,
  Video,
  Users,
  ExternalLink,
  CalendarDays,
  History
} from 'lucide-react'
import { useMeetings } from '@/lib/hooks/useMeetings'
import { meetingsApi, Meeting } from '@/lib/api/meetings'
import { calendarApi, CalendarEvent } from '@/lib/api/calendar'
import { MeetingsPageSkeleton } from '@/components/ui/Skeleton'

// Meeting app icons/colors
const meetingAppStyles: Record<string, { bg: string; text: string }> = {
  'Zoom': { bg: 'bg-blue-500/20', text: 'text-blue-400' },
  'Google Meet': { bg: 'bg-green-500/20', text: 'text-green-400' },
  'Microsoft Teams': { bg: 'bg-purple-500/20', text: 'text-purple-400' },
  'Webex': { bg: 'bg-teal-500/20', text: 'text-teal-400' },
  'Discord': { bg: 'bg-indigo-500/20', text: 'text-indigo-400' },
  'Video Call': { bg: 'bg-gray-500/20', text: 'text-gray-400' },
}

function UpcomingEventCard({ event }: { event: CalendarEvent }) {
  const meetingApp = calendarApi.detectMeetingApp(event.meeting_link)
  const appStyle = meetingAppStyles[meetingApp || 'Video Call'] || meetingAppStyles['Video Call']

  const formatEventTime = (startTime: string, endTime: string) => {
    const start = new Date(startTime)
    const end = new Date(endTime)
    const now = new Date()

    const isToday = start.toDateString() === now.toDateString()
    const isTomorrow = start.toDateString() === new Date(now.getTime() + 86400000).toDateString()

    const dateStr = isToday ? 'Today' : isTomorrow ? 'Tomorrow' : start.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })
    const timeStr = `${start.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })} - ${end.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}`

    return { dateStr, timeStr }
  }

  const { dateStr, timeStr } = formatEventTime(event.start_time, event.end_time)

  return (
    <div className="bg-premium-card border border-premium-border rounded-xl p-5 hover:border-gold-500/30 transition-colors">
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center space-x-2 mb-2">
            <span className={`text-xs px-2 py-0.5 rounded ${appStyle.bg} ${appStyle.text}`}>
              {meetingApp || 'Meeting'}
            </span>
            <span className="text-xs px-2 py-0.5 rounded bg-gold-500/20 text-gold-400">
              {dateStr}
            </span>
          </div>
          <h3 className="font-medium text-white truncate">{event.title}</h3>
          <div className="flex items-center space-x-4 mt-3 text-sm text-gray-500">
            <span className="flex items-center">
              <Clock className="h-3.5 w-3.5 mr-1" />
              {timeStr}
            </span>
            {event.attendees.length > 0 && (
              <span className="flex items-center">
                <Users className="h-3.5 w-3.5 mr-1" />
                {event.attendees.length} attendees
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center space-x-2 ml-4">
          {event.meeting_link && (
            <a
              href={event.meeting_link}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center px-3 py-1.5 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg text-sm font-medium rounded-lg hover:shadow-gold transition-all"
            >
              <Video className="h-4 w-4 mr-1.5" />
              Join
            </a>
          )}
        </div>
      </div>
    </div>
  )
}

function MeetingRow({ meeting, onDelete }: { meeting: Meeting; onDelete: () => void }) {
  const [menuOpen, setMenuOpen] = useState(false)

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    })
  }

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
    })
  }

  const formatDuration = (seconds: number | null) => {
    if (!seconds) return '—'
    const mins = Math.floor(seconds / 60)
    const hrs = Math.floor(mins / 60)
    if (hrs > 0) return `${hrs}h ${mins % 60}m`
    return `${mins}m`
  }

  const handleExport = async (format: 'json' | 'markdown') => {
    try {
      const blob = await meetingsApi.exportMeeting(meeting.id, format)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `meeting-${meeting.id}.${format === 'markdown' ? 'md' : 'json'}`
      a.click()
      URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Export failed:', error)
    }
    setMenuOpen(false)
  }

  const handleDelete = async () => {
    if (confirm('Are you sure you want to delete this meeting?')) {
      try {
        await meetingsApi.delete(meeting.id)
        onDelete()
      } catch (error) {
        console.error('Delete failed:', error)
      }
    }
    setMenuOpen(false)
  }

  return (
    <tr className="border-b border-premium-border hover:bg-premium-surface/50 transition-colors">
      <td className="px-4 py-4">
        <Link href={`/dashboard/meetings/${meeting.id}`} className="block">
          <p className="font-medium text-white hover:text-gold-400 transition-colors">
            {meeting.title || `${meeting.meeting_type} Meeting`}
          </p>
          <p className="text-sm text-gray-500 mt-0.5">{meeting.meeting_app || 'Unknown app'}</p>
        </Link>
      </td>
      <td className="px-4 py-4 text-gray-400">
        <div className="flex items-center">
          <Calendar className="h-4 w-4 mr-2 text-gray-500" />
          {formatDate(meeting.started_at)}
        </div>
        <p className="text-sm text-gray-500 mt-0.5">{formatTime(meeting.started_at)}</p>
      </td>
      <td className="px-4 py-4 text-gray-400">
        <div className="flex items-center">
          <Clock className="h-4 w-4 mr-2 text-gray-500" />
          {formatDuration(meeting.duration_seconds)}
        </div>
      </td>
      <td className="px-4 py-4">
        <div className="flex items-center text-gray-400">
          <MessageSquare className="h-4 w-4 mr-2 text-gray-500" />
          {meeting.conversation_count}
        </div>
      </td>
      <td className="px-4 py-4">
        <div className="relative">
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className="p-1.5 text-gray-500 hover:text-white hover:bg-premium-surface rounded transition-colors"
          >
            <MoreVertical className="h-4 w-4" />
          </button>

          {menuOpen && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} />
              <div className="absolute right-0 mt-1 w-48 bg-premium-card border border-premium-border rounded-lg shadow-xl z-20 py-1">
                <button
                  onClick={() => handleExport('markdown')}
                  className="w-full px-4 py-2 text-left text-sm text-gray-300 hover:bg-premium-surface flex items-center"
                >
                  <FileText className="h-4 w-4 mr-2" />
                  Export as Markdown
                </button>
                <button
                  onClick={() => handleExport('json')}
                  className="w-full px-4 py-2 text-left text-sm text-gray-300 hover:bg-premium-surface flex items-center"
                >
                  <Download className="h-4 w-4 mr-2" />
                  Export as JSON
                </button>
                <hr className="my-1 border-premium-border" />
                <button
                  onClick={handleDelete}
                  className="w-full px-4 py-2 text-left text-sm text-red-400 hover:bg-red-500/10 flex items-center"
                >
                  <Trash2 className="h-4 w-4 mr-2" />
                  Delete
                </button>
              </div>
            </>
          )}
        </div>
      </td>
    </tr>
  )
}

export default function MeetingsPage() {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [activeTab, setActiveTab] = useState<'upcoming' | 'past'>('upcoming')
  const [upcomingEvents, setUpcomingEvents] = useState<CalendarEvent[]>([])
  const [eventsLoading, setEventsLoading] = useState(true)
  const [hasCalendarConnected, setHasCalendarConnected] = useState(false)

  const { meetings, total, isLoading, totalPages, refresh } = useMeetings(page, 10)

  // Fetch calendar events
  useEffect(() => {
    const fetchCalendarEvents = async () => {
      try {
        setEventsLoading(true)
        const integrations = await calendarApi.getIntegrations()
        const hasConnected = integrations.some(i => i.connected)
        setHasCalendarConnected(hasConnected)

        if (hasConnected) {
          const events = await calendarApi.getAllEvents(20)
          // Filter to only future events
          const futureEvents = events.filter(e => new Date(e.start_time) > new Date())
          setUpcomingEvents(futureEvents)
        }
      } catch (err) {
        console.error('Failed to fetch calendar events:', err)
      } finally {
        setEventsLoading(false)
      }
    }

    fetchCalendarEvents()
  }, [])

  const filteredMeetings = meetings.filter(
    (m) =>
      (m.title?.toLowerCase().includes(search.toLowerCase()) ?? false) ||
      m.meeting_type.toLowerCase().includes(search.toLowerCase())
  )

  const filteredUpcoming = upcomingEvents.filter(
    (e) =>
      !search ||
      e.title.toLowerCase().includes(search.toLowerCase())
  )

  // Show skeleton loading on initial load
  if ((activeTab === 'past' && isLoading && meetings.length === 0) ||
      (activeTab === 'upcoming' && eventsLoading)) {
    return <MeetingsPageSkeleton />
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Meetings</h1>
          <p className="text-gray-400 mt-1">
            View upcoming meetings and past sessions
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex space-x-1 bg-premium-surface p-1 rounded-lg w-fit">
        <button
          onClick={() => setActiveTab('upcoming')}
          className={`flex items-center px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            activeTab === 'upcoming'
              ? 'bg-premium-card text-white'
              : 'text-gray-400 hover:text-white'
          }`}
        >
          <CalendarDays className="h-4 w-4 mr-2" />
          Upcoming
          {upcomingEvents.length > 0 && (
            <span className="ml-2 px-1.5 py-0.5 text-xs bg-gold-500/20 text-gold-400 rounded">
              {upcomingEvents.length}
            </span>
          )}
        </button>
        <button
          onClick={() => setActiveTab('past')}
          className={`flex items-center px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            activeTab === 'past'
              ? 'bg-premium-card text-white'
              : 'text-gray-400 hover:text-white'
          }`}
        >
          <History className="h-4 w-4 mr-2" />
          Past Sessions
        </button>
      </div>

      {/* Search & Filters */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
          <input
            type="text"
            placeholder={activeTab === 'upcoming' ? 'Search events...' : 'Search meetings...'}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-premium-surface border border-premium-border rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-gold-500/50"
          />
        </div>
      </div>

      {/* Content */}
      {activeTab === 'upcoming' ? (
        /* Upcoming Events */
        <div className="space-y-4">
          {!hasCalendarConnected ? (
            <div className="bg-premium-card border border-premium-border rounded-xl p-8 text-center">
              <Calendar className="h-12 w-12 text-gray-600 mx-auto mb-3" />
              <p className="text-white font-medium mb-2">Connect Your Calendar</p>
              <p className="text-gray-500 text-sm mb-4">
                Connect Google Calendar or Outlook to see your upcoming meetings
              </p>
              <Link
                href="/dashboard/settings/calendar"
                className="inline-flex items-center px-4 py-2 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-medium rounded-lg hover:shadow-gold transition-all"
              >
                <Calendar className="h-4 w-4 mr-2" />
                Connect Calendar
              </Link>
            </div>
          ) : filteredUpcoming.length > 0 ? (
            filteredUpcoming.map((event) => (
              <UpcomingEventCard key={event.id} event={event} />
            ))
          ) : (
            <div className="bg-premium-card border border-premium-border rounded-xl p-8 text-center">
              <CalendarDays className="h-12 w-12 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-400">No upcoming meetings</p>
              <p className="text-gray-500 text-sm mt-1">
                {search ? 'Try a different search term' : 'Your upcoming calendar events will appear here'}
              </p>
            </div>
          )}
        </div>
      ) : (
        /* Past Meetings Table */
        <div className="bg-premium-card border border-premium-border rounded-xl overflow-hidden">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-gold-400"></div>
            </div>
          ) : filteredMeetings.length > 0 ? (
            <table className="w-full">
              <thead>
                <tr className="border-b border-premium-border bg-premium-surface/50">
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">
                    Meeting
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">
                    Date
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">
                    Duration
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">
                    Responses
                  </th>
                  <th className="px-4 py-3 w-12"></th>
                </tr>
              </thead>
              <tbody>
                {filteredMeetings.map((meeting) => (
                  <MeetingRow key={meeting.id} meeting={meeting} onDelete={refresh} />
                ))}
              </tbody>
            </table>
          ) : (
            <div className="text-center py-12">
              <Calendar className="h-12 w-12 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-400">No meetings found</p>
              <p className="text-gray-500 text-sm mt-1">
                {search ? 'Try a different search term' : 'Start using ReadIn AI in your meetings'}
              </p>
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-premium-border">
              <p className="text-sm text-gray-500">
                Showing {(page - 1) * 10 + 1} to {Math.min(page * 10, total)} of {total}
              </p>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPage(page - 1)}
                  disabled={page === 1}
                  className="p-2 text-gray-400 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <span className="text-sm text-gray-400">
                  Page {page} of {totalPages}
                </span>
                <button
                  onClick={() => setPage(page + 1)}
                  disabled={page === totalPages}
                  className="p-2 text-gray-400 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
