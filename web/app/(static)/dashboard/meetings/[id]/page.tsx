'use client'

import { useState, useRef, useEffect } from 'react'
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
  ChevronLeft,
  ChevronRight,
  Bot,
  User,
  MoreHorizontal
} from 'lucide-react'
import { useMeeting } from '@/lib/hooks/useMeetings'
import { meetingsApi, Conversation } from '@/lib/api/meetings'

function ConversationItem({ conversation, index, isActive, onSwipeLeft, onSwipeRight }: {
  conversation: Conversation
  index: number
  isActive?: boolean
  onSwipeLeft?: () => void
  onSwipeRight?: () => void
}) {
  const [expanded, setExpanded] = useState(false)
  const touchStartX = useRef(0)
  const touchEndX = useRef(0)

  const handleTouchStart = (e: React.TouchEvent) => {
    touchStartX.current = e.targetTouches[0].clientX
  }

  const handleTouchMove = (e: React.TouchEvent) => {
    touchEndX.current = e.targetTouches[0].clientX
  }

  const handleTouchEnd = () => {
    const swipeThreshold = 50
    const diff = touchStartX.current - touchEndX.current

    if (Math.abs(diff) > swipeThreshold) {
      if (diff > 0 && onSwipeLeft) {
        onSwipeLeft()
      } else if (diff < 0 && onSwipeRight) {
        onSwipeRight()
      }
    }
  }

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      second: '2-digit',
    })
  }

  return (
    <div
      className="border border-premium-border rounded-xl sm:rounded-lg overflow-hidden touch-manipulation"
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-4 sm:py-3 flex items-center justify-between bg-premium-surface/50 hover:bg-premium-surface transition-colors min-h-[64px] sm:min-h-[56px]"
      >
        <div className="flex items-center flex-1 min-w-0">
          <span className="w-7 h-7 sm:w-6 sm:h-6 rounded-full bg-gold-500/20 text-gold-400 text-xs flex items-center justify-center mr-3 flex-shrink-0">
            {index + 1}
          </span>
          <div className="text-left min-w-0">
            <p className="text-white font-medium text-sm sm:text-base truncate">{conversation.speaker || 'Unknown Speaker'}</p>
            <p className="text-xs text-gray-500">{formatTime(conversation.timestamp)}</p>
          </div>
        </div>
        <div className="flex items-center flex-shrink-0 ml-2">
          {conversation.ai_response && (
            <span className="mr-2 sm:mr-3 px-2 py-1 bg-emerald-500/20 text-emerald-400 text-xs rounded-full flex items-center">
              <Bot className="h-3 w-3 sm:mr-1" />
              <span className="hidden sm:inline">AI Response</span>
            </span>
          )}
          {expanded ? (
            <ChevronUp className="h-5 w-5 text-gray-400" />
          ) : (
            <ChevronDown className="h-5 w-5 text-gray-400" />
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
            <p className="text-gray-300 text-sm sm:pl-6 leading-relaxed">{conversation.transcript}</p>
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
              <p className="text-gray-300 text-sm sm:pl-6 whitespace-pre-wrap leading-relaxed">
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
  const [showMobileActions, setShowMobileActions] = useState(false)
  const [activeConversationIndex, setActiveConversationIndex] = useState(0)

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

  const handleNextConversation = () => {
    if (meeting?.conversations && activeConversationIndex < meeting.conversations.length - 1) {
      setActiveConversationIndex(activeConversationIndex + 1)
    }
  }

  const handlePrevConversation = () => {
    if (activeConversationIndex > 0) {
      setActiveConversationIndex(activeConversationIndex - 1)
    }
  }

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <Link
            href="/dashboard/meetings"
            className="text-gray-400 hover:text-white flex items-center text-sm mb-3 transition-colors min-h-[44px] touch-manipulation"
          >
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back to Meetings
          </Link>
          <h1 className="text-xl sm:text-2xl font-bold text-white line-clamp-2">
            {meeting.title || `${meeting.meeting_type} Meeting`}
          </h1>
          <p className="text-gray-400 mt-1 text-sm sm:text-base">{meeting.meeting_app || 'Unknown app'}</p>
        </div>

        {/* Desktop Actions */}
        <div className="hidden sm:flex items-center gap-2">
          <button
            onClick={() => handleExport('markdown')}
            className="px-3 py-2 text-gray-400 hover:text-white hover:bg-premium-surface rounded-lg transition-colors flex items-center text-sm min-h-[44px]"
          >
            <FileText className="h-4 w-4 mr-2" />
            Export MD
          </button>
          <button
            onClick={() => handleExport('json')}
            className="px-3 py-2 text-gray-400 hover:text-white hover:bg-premium-surface rounded-lg transition-colors flex items-center text-sm min-h-[44px]"
          >
            <Download className="h-4 w-4 mr-2" />
            Export JSON
          </button>
          <button
            onClick={handleDelete}
            className="px-3 py-2 text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded-lg transition-colors flex items-center text-sm min-h-[44px]"
          >
            <Trash2 className="h-4 w-4 mr-2" />
            Delete
          </button>
        </div>

        {/* Mobile Actions Menu */}
        <div className="sm:hidden relative">
          <button
            onClick={() => setShowMobileActions(!showMobileActions)}
            className="p-3 text-gray-400 hover:text-white hover:bg-premium-surface rounded-lg transition-colors min-w-[44px] min-h-[44px] flex items-center justify-center touch-manipulation"
            aria-label="More actions"
          >
            <MoreHorizontal className="h-5 w-5" />
          </button>

          {showMobileActions && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setShowMobileActions(false)} />
              <div className="absolute right-0 top-full mt-1 w-56 bg-premium-card border border-premium-border rounded-xl shadow-xl z-20 py-2">
                <button
                  onClick={() => { handleExport('markdown'); setShowMobileActions(false); }}
                  className="w-full px-4 py-3 text-left text-sm text-gray-300 hover:bg-premium-surface flex items-center min-h-[48px] touch-manipulation"
                >
                  <FileText className="h-4 w-4 mr-3" />
                  Export as Markdown
                </button>
                <button
                  onClick={() => { handleExport('json'); setShowMobileActions(false); }}
                  className="w-full px-4 py-3 text-left text-sm text-gray-300 hover:bg-premium-surface flex items-center min-h-[48px] touch-manipulation"
                >
                  <Download className="h-4 w-4 mr-3" />
                  Export as JSON
                </button>
                <hr className="my-2 border-premium-border" />
                <button
                  onClick={() => { handleDelete(); setShowMobileActions(false); }}
                  className="w-full px-4 py-3 text-left text-sm text-red-400 hover:bg-red-500/10 flex items-center min-h-[48px] touch-manipulation"
                >
                  <Trash2 className="h-4 w-4 mr-3" />
                  Delete Meeting
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Meta Info - Swipeable on mobile */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <div className="bg-premium-card border border-premium-border rounded-xl sm:rounded-lg p-3 sm:p-4">
          <div className="flex items-center text-gray-500 mb-2">
            <Calendar className="h-4 w-4 mr-2 flex-shrink-0" />
            <span className="text-xs sm:text-sm">Date</span>
          </div>
          <p className="text-white font-medium text-sm sm:text-base">{formatDate(meeting.started_at)}</p>
          <p className="text-gray-500 text-xs sm:text-sm">{formatTime(meeting.started_at)}</p>
        </div>

        <div className="bg-premium-card border border-premium-border rounded-xl sm:rounded-lg p-3 sm:p-4">
          <div className="flex items-center text-gray-500 mb-2">
            <Clock className="h-4 w-4 mr-2 flex-shrink-0" />
            <span className="text-xs sm:text-sm">Duration</span>
          </div>
          <p className="text-white font-medium text-sm sm:text-base">{formatDuration(meeting.duration_seconds)}</p>
        </div>

        <div className="bg-premium-card border border-premium-border rounded-xl sm:rounded-lg p-3 sm:p-4">
          <div className="flex items-center text-gray-500 mb-2">
            <Users className="h-4 w-4 mr-2 flex-shrink-0" />
            <span className="text-xs sm:text-sm">Participants</span>
          </div>
          <p className="text-white font-medium text-sm sm:text-base">{meeting.participant_count}</p>
        </div>

        <div className="bg-premium-card border border-premium-border rounded-xl sm:rounded-lg p-3 sm:p-4">
          <div className="flex items-center text-gray-500 mb-2">
            <MessageSquare className="h-4 w-4 mr-2 flex-shrink-0" />
            <span className="text-xs sm:text-sm">AI Responses</span>
          </div>
          <p className="text-white font-medium text-sm sm:text-base">{meeting.conversation_count}</p>
        </div>
      </div>

      {/* Summary & Key Points */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
        {/* Summary */}
        <div className="bg-premium-card border border-premium-border rounded-xl p-4 sm:p-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-4 gap-3">
            <h2 className="font-semibold text-white flex items-center text-sm sm:text-base">
              <Sparkles className="h-5 w-5 text-gold-400 mr-2 flex-shrink-0" />
              Meeting Summary
            </h2>
            {!meeting.summary && (
              <button
                onClick={handleGenerateSummary}
                disabled={isGeneratingSummary}
                className="w-full sm:w-auto px-4 py-2.5 bg-gold-500/20 text-gold-400 text-sm rounded-lg hover:bg-gold-500/30 transition-colors disabled:opacity-50 min-h-[44px] touch-manipulation"
              >
                {isGeneratingSummary ? 'Generating...' : 'Generate Summary'}
              </button>
            )}
          </div>
          {meeting.summary ? (
            <p className="text-gray-300 whitespace-pre-wrap text-sm sm:text-base leading-relaxed">{meeting.summary}</p>
          ) : (
            <p className="text-gray-500 italic text-sm">
              No summary available. Click "Generate Summary" to create one.
            </p>
          )}
        </div>

        {/* Key Points & Action Items */}
        <div className="space-y-4 sm:space-y-6">
          {/* Key Points */}
          <div className="bg-premium-card border border-premium-border rounded-xl p-4 sm:p-6">
            <h2 className="font-semibold text-white mb-3 sm:mb-4 text-sm sm:text-base">Key Points</h2>
            {meeting.key_points && meeting.key_points.length > 0 ? (
              <ul className="space-y-2.5 sm:space-y-2">
                {meeting.key_points.map((point, i) => (
                  <li key={i} className="flex items-start text-gray-300 text-sm">
                    <span className="w-1.5 h-1.5 rounded-full bg-gold-400 mt-2 mr-3 flex-shrink-0" />
                    {point}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-gray-500 italic text-sm">No key points recorded</p>
            )}
          </div>

          {/* Action Items */}
          <div className="bg-premium-card border border-premium-border rounded-xl p-4 sm:p-6">
            <h2 className="font-semibold text-white mb-3 sm:mb-4 text-sm sm:text-base">Action Items</h2>
            {meeting.action_items && meeting.action_items.length > 0 ? (
              <ul className="space-y-2.5 sm:space-y-2">
                {meeting.action_items.map((item, i) => (
                  <li key={i} className="flex items-start text-gray-300 text-sm">
                    <CheckCircle2 className="h-4 w-4 text-emerald-400 mt-0.5 mr-3 flex-shrink-0" />
                    {item}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-gray-500 italic text-sm">No action items recorded</p>
            )}
          </div>
        </div>
      </div>

      {/* Conversations */}
      <div className="bg-premium-card border border-premium-border rounded-xl p-4 sm:p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-white flex items-center text-sm sm:text-base">
            <MessageSquare className="h-5 w-5 text-gold-400 mr-2 flex-shrink-0" />
            Conversations ({meeting.conversations?.length || 0})
          </h2>

          {/* Mobile swipe navigation indicator */}
          {meeting.conversations && meeting.conversations.length > 1 && (
            <div className="flex items-center gap-2 sm:hidden">
              <button
                onClick={handlePrevConversation}
                disabled={activeConversationIndex === 0}
                className="p-2 text-gray-400 hover:text-white disabled:opacity-30 min-w-[40px] min-h-[40px] flex items-center justify-center touch-manipulation rounded-lg hover:bg-premium-surface"
                aria-label="Previous conversation"
              >
                <ChevronLeft className="h-5 w-5" />
              </button>
              <span className="text-xs text-gray-500">
                {activeConversationIndex + 1}/{meeting.conversations.length}
              </span>
              <button
                onClick={handleNextConversation}
                disabled={activeConversationIndex === meeting.conversations.length - 1}
                className="p-2 text-gray-400 hover:text-white disabled:opacity-30 min-w-[40px] min-h-[40px] flex items-center justify-center touch-manipulation rounded-lg hover:bg-premium-surface"
                aria-label="Next conversation"
              >
                <ChevronRight className="h-5 w-5" />
              </button>
            </div>
          )}
        </div>

        {meeting.conversations && meeting.conversations.length > 0 ? (
          <div className="space-y-3">
            {meeting.conversations.map((conversation, index) => (
              <ConversationItem
                key={conversation.id}
                conversation={conversation}
                index={index}
                isActive={index === activeConversationIndex}
                onSwipeLeft={handleNextConversation}
                onSwipeRight={handlePrevConversation}
              />
            ))}
          </div>
        ) : (
          <p className="text-gray-500 italic text-center py-6 sm:py-8 text-sm">
            No conversations recorded for this meeting
          </p>
        )}

        {/* Mobile swipe hint */}
        {meeting.conversations && meeting.conversations.length > 1 && (
          <p className="text-center text-xs text-gray-600 mt-4 sm:hidden">
            Swipe left/right to navigate conversations
          </p>
        )}
      </div>
    </div>
  )
}
