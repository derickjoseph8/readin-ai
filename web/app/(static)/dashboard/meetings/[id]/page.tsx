'use client'

import { useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  ArrowLeft,
  Calendar,
  Clock,
  Users,
  MessageSquare,
  FileText,
  Download,
  Trash2,
  Sparkles,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Bot,
  User
} from 'lucide-react'
import { useMeeting } from '@/lib/hooks/useMeetings'
import { meetingsApi, Conversation } from '@/lib/api/meetings'

function ConversationItem({ conversation, index }: { conversation: Conversation; index: number }) {
  const [expanded, setExpanded] = useState(false)

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      second: '2-digit',
    })
  }

  return (
    <div className="border border-premium-border rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-3 flex items-center justify-between bg-premium-surface/50 hover:bg-premium-surface transition-colors"
      >
        <div className="flex items-center">
          <span className="w-6 h-6 rounded-full bg-gold-500/20 text-gold-400 text-xs flex items-center justify-center mr-3">
            {index + 1}
          </span>
          <div className="text-left">
            <p className="text-white font-medium">{conversation.speaker || 'Unknown Speaker'}</p>
            <p className="text-xs text-gray-500">{formatTime(conversation.timestamp)}</p>
          </div>
        </div>
        <div className="flex items-center">
          {conversation.ai_response && (
            <span className="mr-3 px-2 py-1 bg-emerald-500/20 text-emerald-400 text-xs rounded-full flex items-center">
              <Bot className="h-3 w-3 mr-1" />
              AI Response
            </span>
          )}
          {expanded ? (
            <ChevronUp className="h-4 w-4 text-gray-400" />
          ) : (
            <ChevronDown className="h-4 w-4 text-gray-400" />
          )}
        </div>
      </button>

      {expanded && (
        <div className="px-4 py-4 space-y-4">
          {/* Transcript */}
          <div>
            <div className="flex items-center mb-2">
              <User className="h-4 w-4 text-gray-500 mr-2" />
              <span className="text-sm font-medium text-gray-400">Transcript</span>
            </div>
            <p className="text-gray-300 text-sm pl-6">{conversation.transcript}</p>
          </div>

          {/* AI Response */}
          {conversation.ai_response && (
            <div className="border-t border-premium-border pt-4">
              <div className="flex items-center mb-2">
                <Bot className="h-4 w-4 text-gold-400 mr-2" />
                <span className="text-sm font-medium text-gold-400">AI Response</span>
                {conversation.response_time_ms && (
                  <span className="ml-2 text-xs text-gray-500">
                    ({conversation.response_time_ms}ms)
                  </span>
                )}
              </div>
              <p className="text-gray-300 text-sm pl-6 whitespace-pre-wrap">
                {conversation.ai_response}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function MeetingDetailPage() {
  const params = useParams()
  const router = useRouter()
  const meetingId = params.id ? Number(params.id) : null
  const { meeting, isLoading, error } = useMeeting(meetingId)
  const [isGeneratingSummary, setIsGeneratingSummary] = useState(false)

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-US', {
      weekday: 'long',
      month: 'long',
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
    if (!meeting) return
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
  }

  const handleDelete = async () => {
    if (!meeting) return
    if (confirm('Are you sure you want to delete this meeting? This action cannot be undone.')) {
      try {
        await meetingsApi.delete(meeting.id)
        router.push('/dashboard/meetings')
      } catch (error) {
        console.error('Delete failed:', error)
      }
    }
  }

  const handleGenerateSummary = async () => {
    if (!meeting) return
    setIsGeneratingSummary(true)
    try {
      await meetingsApi.generateSummary(meeting.id)
      window.location.reload()
    } catch (error) {
      console.error('Summary generation failed:', error)
    } finally {
      setIsGeneratingSummary(false)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-gold-400"></div>
      </div>
    )
  }

  if (error || !meeting) {
    return (
      <div className="text-center py-20">
        <p className="text-red-400 mb-4">{error || 'Meeting not found'}</p>
        <Link
          href="/dashboard/meetings"
          className="text-gold-400 hover:text-gold-300 flex items-center justify-center"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Meetings
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <Link
            href="/dashboard/meetings"
            className="text-gray-400 hover:text-white flex items-center text-sm mb-3 transition-colors"
          >
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back to Meetings
          </Link>
          <h1 className="text-2xl font-bold text-white">
            {meeting.title || `${meeting.meeting_type} Meeting`}
          </h1>
          <p className="text-gray-400 mt-1">{meeting.meeting_app || 'Unknown app'}</p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => handleExport('markdown')}
            className="px-3 py-2 text-gray-400 hover:text-white hover:bg-premium-surface rounded-lg transition-colors flex items-center text-sm"
          >
            <FileText className="h-4 w-4 mr-2" />
            Export MD
          </button>
          <button
            onClick={() => handleExport('json')}
            className="px-3 py-2 text-gray-400 hover:text-white hover:bg-premium-surface rounded-lg transition-colors flex items-center text-sm"
          >
            <Download className="h-4 w-4 mr-2" />
            Export JSON
          </button>
          <button
            onClick={handleDelete}
            className="px-3 py-2 text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded-lg transition-colors flex items-center text-sm"
          >
            <Trash2 className="h-4 w-4 mr-2" />
            Delete
          </button>
        </div>
      </div>

      {/* Meta Info */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-premium-card border border-premium-border rounded-lg p-4">
          <div className="flex items-center text-gray-500 mb-2">
            <Calendar className="h-4 w-4 mr-2" />
            <span className="text-sm">Date</span>
          </div>
          <p className="text-white font-medium">{formatDate(meeting.started_at)}</p>
          <p className="text-gray-500 text-sm">{formatTime(meeting.started_at)}</p>
        </div>

        <div className="bg-premium-card border border-premium-border rounded-lg p-4">
          <div className="flex items-center text-gray-500 mb-2">
            <Clock className="h-4 w-4 mr-2" />
            <span className="text-sm">Duration</span>
          </div>
          <p className="text-white font-medium">{formatDuration(meeting.duration_seconds)}</p>
        </div>

        <div className="bg-premium-card border border-premium-border rounded-lg p-4">
          <div className="flex items-center text-gray-500 mb-2">
            <Users className="h-4 w-4 mr-2" />
            <span className="text-sm">Participants</span>
          </div>
          <p className="text-white font-medium">{meeting.participant_count}</p>
        </div>

        <div className="bg-premium-card border border-premium-border rounded-lg p-4">
          <div className="flex items-center text-gray-500 mb-2">
            <MessageSquare className="h-4 w-4 mr-2" />
            <span className="text-sm">AI Responses</span>
          </div>
          <p className="text-white font-medium">{meeting.conversation_count}</p>
        </div>
      </div>

      {/* Summary & Key Points */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Summary */}
        <div className="bg-premium-card border border-premium-border rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-white flex items-center">
              <Sparkles className="h-5 w-5 text-gold-400 mr-2" />
              Meeting Summary
            </h2>
            {!meeting.summary && (
              <button
                onClick={handleGenerateSummary}
                disabled={isGeneratingSummary}
                className="px-3 py-1.5 bg-gold-500/20 text-gold-400 text-sm rounded-lg hover:bg-gold-500/30 transition-colors disabled:opacity-50"
              >
                {isGeneratingSummary ? 'Generating...' : 'Generate Summary'}
              </button>
            )}
          </div>
          {meeting.summary ? (
            <p className="text-gray-300 whitespace-pre-wrap">{meeting.summary}</p>
          ) : (
            <p className="text-gray-500 italic">
              No summary available. Click "Generate Summary" to create one.
            </p>
          )}
        </div>

        {/* Key Points & Action Items */}
        <div className="space-y-6">
          {/* Key Points */}
          <div className="bg-premium-card border border-premium-border rounded-xl p-6">
            <h2 className="font-semibold text-white mb-4">Key Points</h2>
            {meeting.key_points && meeting.key_points.length > 0 ? (
              <ul className="space-y-2">
                {meeting.key_points.map((point, i) => (
                  <li key={i} className="flex items-start text-gray-300">
                    <span className="w-1.5 h-1.5 rounded-full bg-gold-400 mt-2 mr-3 flex-shrink-0" />
                    {point}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-gray-500 italic">No key points recorded</p>
            )}
          </div>

          {/* Action Items */}
          <div className="bg-premium-card border border-premium-border rounded-xl p-6">
            <h2 className="font-semibold text-white mb-4">Action Items</h2>
            {meeting.action_items && meeting.action_items.length > 0 ? (
              <ul className="space-y-2">
                {meeting.action_items.map((item, i) => (
                  <li key={i} className="flex items-start text-gray-300">
                    <CheckCircle2 className="h-4 w-4 text-emerald-400 mt-0.5 mr-3 flex-shrink-0" />
                    {item}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-gray-500 italic">No action items recorded</p>
            )}
          </div>
        </div>
      </div>

      {/* Conversations */}
      <div className="bg-premium-card border border-premium-border rounded-xl p-6">
        <h2 className="font-semibold text-white mb-4 flex items-center">
          <MessageSquare className="h-5 w-5 text-gold-400 mr-2" />
          Conversations ({meeting.conversations?.length || 0})
        </h2>

        {meeting.conversations && meeting.conversations.length > 0 ? (
          <div className="space-y-3">
            {meeting.conversations.map((conversation, index) => (
              <ConversationItem
                key={conversation.id}
                conversation={conversation}
                index={index}
              />
            ))}
          </div>
        ) : (
          <p className="text-gray-500 italic text-center py-8">
            No conversations recorded for this meeting
          </p>
        )}
      </div>
    </div>
  )
}
