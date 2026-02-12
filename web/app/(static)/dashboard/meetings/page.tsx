'use client'

import { useState } from 'react'
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
  FileText
} from 'lucide-react'
import { useMeetings } from '@/lib/hooks/useMeetings'
import { meetingsApi, Meeting } from '@/lib/api/meetings'

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
  const { meetings, total, isLoading, totalPages, refresh } = useMeetings(page, 10)

  const filteredMeetings = meetings.filter(
    (m) =>
      (m.title?.toLowerCase().includes(search.toLowerCase()) ?? false) ||
      m.meeting_type.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Meetings</h1>
          <p className="text-gray-400 mt-1">
            View and manage your meeting history
          </p>
        </div>
      </div>

      {/* Search & Filters */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
          <input
            type="text"
            placeholder="Search meetings..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-premium-surface border border-premium-border rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-gold-500/50"
          />
        </div>
      </div>

      {/* Meetings Table */}
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
    </div>
  )
}
