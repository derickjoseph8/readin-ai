'use client'

import { useState, useEffect } from 'react'
import {
  ClipboardCheck,
  Search,
  Filter,
  Star,
  MessageSquare,
  Clock,
  Bot,
  User as UserIcon,
  X,
  Loader2,
  BarChart3,
  Check,
  AlertCircle
} from 'lucide-react'
import apiClient from '@/lib/api/client'
import { Skeleton } from '@/components/ui/Skeleton'

interface ChatSessionSummary {
  id: number
  user_id: number
  user_name: string | null
  user_email: string | null
  agent_id: number | null
  agent_name: string | null
  team_name: string | null
  status: string
  is_ai_handled: boolean
  ai_resolution_status: string | null
  message_count: number
  started_at: string
  ended_at: string | null
  duration_minutes: number | null
  has_qa_review: boolean
}

interface ChatMessage {
  id: number
  sender_type: string
  sender_name: string
  message: string
  message_type: string
  created_at: string
}

interface QAReview {
  id: number
  session_id: number
  reviewer_id: number
  reviewer_name: string | null
  overall_score: number
  response_time_score: number | null
  resolution_score: number | null
  professionalism_score: number | null
  notes: string | null
  tags: string[]
  reviewed_at: string
}

interface QAMetrics {
  total_sessions: number
  reviewed_sessions: number
  review_rate: number
  avg_overall_score: number
  avg_response_time_score: number
  avg_resolution_score: number
  avg_professionalism_score: number
  ai_handled_count: number
  ai_resolved_count: number
  ai_transferred_count: number
  agent_handled_count: number
}

function MetricsCard({ metrics, isLoading }: { metrics: QAMetrics | null; isLoading: boolean }) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="bg-premium-card border border-premium-border rounded-xl p-4">
            <Skeleton className="h-4 w-24 mb-2" />
            <Skeleton className="h-8 w-16" />
          </div>
        ))}
      </div>
    )
  }

  if (!metrics) return null

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      <div className="bg-premium-card border border-premium-border rounded-xl p-4">
        <p className="text-gray-500 text-sm">Review Rate</p>
        <p className="text-2xl font-bold text-white">{metrics.review_rate.toFixed(1)}%</p>
        <p className="text-xs text-gray-500">{metrics.reviewed_sessions} of {metrics.total_sessions}</p>
      </div>
      <div className="bg-premium-card border border-premium-border rounded-xl p-4">
        <p className="text-gray-500 text-sm">Avg Score</p>
        <div className="flex items-center">
          <p className="text-2xl font-bold text-white">{metrics.avg_overall_score.toFixed(1)}</p>
          <Star className="h-5 w-5 text-gold-400 ml-1" />
        </div>
      </div>
      <div className="bg-premium-card border border-premium-border rounded-xl p-4">
        <p className="text-gray-500 text-sm">AI Resolved</p>
        <p className="text-2xl font-bold text-emerald-400">{metrics.ai_resolved_count}</p>
        <p className="text-xs text-gray-500">{metrics.ai_transferred_count} transferred</p>
      </div>
      <div className="bg-premium-card border border-premium-border rounded-xl p-4">
        <p className="text-gray-500 text-sm">Agent Handled</p>
        <p className="text-2xl font-bold text-blue-400">{metrics.agent_handled_count}</p>
      </div>
    </div>
  )
}

function SessionCard({
  session,
  onClick,
}: {
  session: ChatSessionSummary
  onClick: () => void
}) {
  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    })
  }

  return (
    <div
      onClick={onClick}
      className="bg-premium-card border border-premium-border rounded-xl p-4 hover:border-gold-500/30 transition-colors cursor-pointer"
    >
      <div className="flex items-start justify-between mb-3">
        <div>
          <p className="font-medium text-white">{session.user_name || session.user_email}</p>
          <p className="text-sm text-gray-500">{formatDate(session.started_at)}</p>
        </div>
        <div className="flex items-center gap-2">
          {session.is_ai_handled ? (
            <span className="px-2 py-1 bg-purple-500/20 text-purple-400 text-xs rounded flex items-center">
              <Bot className="h-3 w-3 mr-1" />
              Novah
            </span>
          ) : (
            <span className="px-2 py-1 bg-blue-500/20 text-blue-400 text-xs rounded flex items-center">
              <UserIcon className="h-3 w-3 mr-1" />
              {session.agent_name || 'Agent'}
            </span>
          )}
          {session.has_qa_review && (
            <span className="px-2 py-1 bg-emerald-500/20 text-emerald-400 text-xs rounded flex items-center">
              <Check className="h-3 w-3 mr-1" />
              Reviewed
            </span>
          )}
        </div>
      </div>

      <div className="flex items-center gap-4 text-sm text-gray-400">
        <span className="flex items-center">
          <MessageSquare className="h-4 w-4 mr-1" />
          {session.message_count} msgs
        </span>
        {session.duration_minutes && (
          <span className="flex items-center">
            <Clock className="h-4 w-4 mr-1" />
            {session.duration_minutes}m
          </span>
        )}
        {session.ai_resolution_status && (
          <span className={`flex items-center ${
            session.ai_resolution_status === 'resolved_by_ai' ? 'text-emerald-400' : 'text-yellow-400'
          }`}>
            {session.ai_resolution_status === 'resolved_by_ai' ? 'AI Resolved' : 'Transferred'}
          </span>
        )}
      </div>
    </div>
  )
}

function TranscriptModal({
  sessionId,
  onClose,
  onReviewSubmitted,
}: {
  sessionId: number
  onClose: () => void
  onReviewSubmitted: () => void
}) {
  const [transcript, setTranscript] = useState<{ session: ChatSessionSummary; messages: ChatMessage[] } | null>(null)
  const [existingReview, setExistingReview] = useState<QAReview | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [showReviewForm, setShowReviewForm] = useState(false)
  const [reviewForm, setReviewForm] = useState({
    overall_score: 0,
    response_time_score: 0,
    resolution_score: 0,
    professionalism_score: 0,
    notes: '',
    tags: [] as string[],
  })
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [transcriptData, reviewData] = await Promise.all([
          apiClient.get<{ session: ChatSessionSummary; messages: ChatMessage[] }>(
            `/api/v1/admin/qa/sessions/${sessionId}/transcript`
          ),
          apiClient.get<QAReview | null>(`/api/v1/admin/qa/sessions/${sessionId}/review`),
        ])
        setTranscript(transcriptData)
        setExistingReview(reviewData)
      } catch (err) {
        console.error('Failed to fetch transcript:', err)
      } finally {
        setIsLoading(false)
      }
    }
    fetchData()
  }, [sessionId])

  const handleSubmitReview = async () => {
    if (reviewForm.overall_score === 0) {
      setError('Please provide an overall score')
      return
    }

    setIsSubmitting(true)
    setError(null)

    try {
      await apiClient.post(`/api/v1/admin/qa/sessions/${sessionId}/review`, {
        overall_score: reviewForm.overall_score,
        response_time_score: reviewForm.response_time_score || null,
        resolution_score: reviewForm.resolution_score || null,
        professionalism_score: reviewForm.professionalism_score || null,
        notes: reviewForm.notes || null,
        tags: reviewForm.tags.length > 0 ? reviewForm.tags : null,
      })
      onReviewSubmitted()
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit review')
    } finally {
      setIsSubmitting(false)
    }
  }

  const StarRating = ({
    label,
    value,
    onChange,
  }: {
    label: string
    value: number
    onChange: (value: number) => void
  }) => (
    <div className="flex items-center justify-between">
      <span className="text-gray-400 text-sm">{label}</span>
      <div className="flex gap-1">
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            type="button"
            onClick={() => onChange(star)}
            className="focus:outline-none"
          >
            <Star
              className={`h-5 w-5 ${
                star <= value ? 'text-gold-400 fill-gold-400' : 'text-gray-600'
              }`}
            />
          </button>
        ))}
      </div>
    </div>
  )

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="fixed inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-premium-card border border-premium-border rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-premium-border flex items-center justify-between flex-shrink-0">
          <div>
            <h2 className="text-lg font-semibold text-white">Chat Transcript</h2>
            {transcript && (
              <p className="text-sm text-gray-500">
                {transcript.session.user_name || transcript.session.user_email}
              </p>
            )}
          </div>
          <button onClick={onClose} className="p-2 text-gray-400 hover:text-white">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden flex">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-gold-400" />
              </div>
            ) : transcript ? (
              transcript.messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex ${msg.sender_type === 'customer' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[80%] rounded-lg px-4 py-2 ${
                      msg.sender_type === 'customer'
                        ? 'bg-gold-500/20 text-white'
                        : msg.sender_type === 'bot'
                        ? 'bg-purple-500/20 text-white'
                        : msg.sender_type === 'agent'
                        ? 'bg-blue-500/20 text-white'
                        : 'bg-gray-500/20 text-gray-400 text-sm'
                    }`}
                  >
                    <p className="text-xs text-gray-500 mb-1">{msg.sender_name}</p>
                    <p className="whitespace-pre-wrap">{msg.message}</p>
                    <p className="text-xs text-gray-500 mt-1">
                      {new Date(msg.created_at).toLocaleTimeString()}
                    </p>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-center text-gray-400">Failed to load transcript</p>
            )}
          </div>

          {/* Review Panel */}
          <div className="w-80 border-l border-premium-border p-4 flex-shrink-0 overflow-y-auto">
            <h3 className="font-medium text-white mb-4 flex items-center">
              <ClipboardCheck className="h-5 w-5 text-gold-400 mr-2" />
              QA Review
            </h3>

            {existingReview ? (
              <div className="space-y-4">
                <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-lg p-3">
                  <p className="text-emerald-400 text-sm flex items-center">
                    <Check className="h-4 w-4 mr-2" />
                    Already reviewed
                  </p>
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-gray-400 text-sm">Overall</span>
                    <div className="flex">
                      {[1, 2, 3, 4, 5].map((star) => (
                        <Star
                          key={star}
                          className={`h-4 w-4 ${
                            star <= existingReview.overall_score
                              ? 'text-gold-400 fill-gold-400'
                              : 'text-gray-600'
                          }`}
                        />
                      ))}
                    </div>
                  </div>
                  {existingReview.notes && (
                    <p className="text-gray-400 text-sm mt-2">{existingReview.notes}</p>
                  )}
                </div>

                <p className="text-xs text-gray-500">
                  Reviewed by {existingReview.reviewer_name} on{' '}
                  {new Date(existingReview.reviewed_at).toLocaleDateString()}
                </p>
              </div>
            ) : showReviewForm ? (
              <div className="space-y-4">
                {error && (
                  <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm flex items-center">
                    <AlertCircle className="h-4 w-4 mr-2" />
                    {error}
                  </div>
                )}

                <StarRating
                  label="Overall Score *"
                  value={reviewForm.overall_score}
                  onChange={(v) => setReviewForm({ ...reviewForm, overall_score: v })}
                />
                <StarRating
                  label="Response Time"
                  value={reviewForm.response_time_score}
                  onChange={(v) => setReviewForm({ ...reviewForm, response_time_score: v })}
                />
                <StarRating
                  label="Resolution"
                  value={reviewForm.resolution_score}
                  onChange={(v) => setReviewForm({ ...reviewForm, resolution_score: v })}
                />
                <StarRating
                  label="Professionalism"
                  value={reviewForm.professionalism_score}
                  onChange={(v) => setReviewForm({ ...reviewForm, professionalism_score: v })}
                />

                <div>
                  <label className="block text-sm text-gray-400 mb-2">Notes</label>
                  <textarea
                    value={reviewForm.notes}
                    onChange={(e) => setReviewForm({ ...reviewForm, notes: e.target.value })}
                    className="w-full px-3 py-2 bg-premium-surface border border-premium-border rounded-lg text-white text-sm focus:outline-none focus:border-gold-500/50 resize-none"
                    rows={3}
                    placeholder="Optional notes..."
                  />
                </div>

                <div className="flex gap-2">
                  <button
                    onClick={() => setShowReviewForm(false)}
                    className="flex-1 px-3 py-2 bg-premium-surface border border-premium-border rounded-lg text-white text-sm hover:bg-premium-surface/80"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSubmitReview}
                    disabled={isSubmitting}
                    className="flex-1 px-3 py-2 bg-gold-500 text-premium-bg font-medium rounded-lg text-sm hover:bg-gold-400 disabled:opacity-50 flex items-center justify-center"
                  >
                    {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Submit'}
                  </button>
                </div>
              </div>
            ) : (
              <button
                onClick={() => setShowReviewForm(true)}
                className="w-full px-4 py-2 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-medium rounded-lg hover:shadow-gold transition-all text-sm"
              >
                Add Review
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default function ChatQAPage() {
  const [sessions, setSessions] = useState<ChatSessionSummary[]>([])
  const [metrics, setMetrics] = useState<QAMetrics | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [selectedSessionId, setSelectedSessionId] = useState<number | null>(null)
  const [search, setSearch] = useState('')
  const [filterAI, setFilterAI] = useState<string>('')
  const [filterReviewed, setFilterReviewed] = useState<string>('')

  const fetchData = async () => {
    try {
      const params = new URLSearchParams()
      if (filterAI === 'ai') params.append('is_ai_handled', 'true')
      if (filterAI === 'agent') params.append('is_ai_handled', 'false')
      if (filterReviewed === 'yes') params.append('has_review', 'true')
      if (filterReviewed === 'no') params.append('has_review', 'false')

      const [sessionsData, metricsData] = await Promise.all([
        apiClient.get<{ sessions: ChatSessionSummary[]; total: number }>(
          `/api/v1/admin/qa/sessions?${params.toString()}`
        ),
        apiClient.get<QAMetrics>('/api/v1/admin/qa/metrics'),
      ])

      setSessions(sessionsData.sessions)
      setMetrics(metricsData)
    } catch (err) {
      console.error('Failed to fetch QA data:', err)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [filterAI, filterReviewed])

  const filteredSessions = sessions.filter((s) => {
    if (!search) return true
    const searchLower = search.toLowerCase()
    return (
      s.user_name?.toLowerCase().includes(searchLower) ||
      s.user_email?.toLowerCase().includes(searchLower) ||
      s.agent_name?.toLowerCase().includes(searchLower)
    )
  })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center">
          <ClipboardCheck className="h-7 w-7 text-gold-400 mr-3" />
          Chat QA
        </h1>
        <p className="text-gray-400 mt-1">Review chat sessions and assess quality</p>
      </div>

      {/* Metrics */}
      <MetricsCard metrics={metrics} isLoading={isLoading && !metrics} />

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
          <input
            type="text"
            placeholder="Search by user or agent..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-premium-surface border border-premium-border rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-gold-500/50"
          />
        </div>

        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-gray-500" />
          <select
            value={filterAI}
            onChange={(e) => setFilterAI(e.target.value)}
            className="px-3 py-2 bg-premium-surface border border-premium-border rounded-lg text-white focus:outline-none focus:border-gold-500/50"
          >
            <option value="">All Handlers</option>
            <option value="ai">Novah AI</option>
            <option value="agent">Human Agent</option>
          </select>

          <select
            value={filterReviewed}
            onChange={(e) => setFilterReviewed(e.target.value)}
            className="px-3 py-2 bg-premium-surface border border-premium-border rounded-lg text-white focus:outline-none focus:border-gold-500/50"
          >
            <option value="">All Status</option>
            <option value="no">Needs Review</option>
            <option value="yes">Reviewed</option>
          </select>
        </div>
      </div>

      {/* Sessions Grid */}
      {isLoading ? (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="bg-premium-card border border-premium-border rounded-xl p-4">
              <Skeleton className="h-5 w-32 mb-2" />
              <Skeleton className="h-4 w-24 mb-3" />
              <div className="flex gap-4">
                <Skeleton className="h-4 w-16" />
                <Skeleton className="h-4 w-12" />
              </div>
            </div>
          ))}
        </div>
      ) : filteredSessions.length > 0 ? (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredSessions.map((session) => (
            <SessionCard
              key={session.id}
              session={session}
              onClick={() => setSelectedSessionId(session.id)}
            />
          ))}
        </div>
      ) : (
        <div className="text-center py-12">
          <MessageSquare className="h-12 w-12 text-gray-600 mx-auto mb-3" />
          <p className="text-gray-400">No chat sessions found</p>
          <p className="text-gray-500 text-sm mt-1">
            {search || filterAI || filterReviewed
              ? 'Try adjusting your filters'
              : 'Completed chat sessions will appear here'}
          </p>
        </div>
      )}

      {/* Transcript Modal */}
      {selectedSessionId && (
        <TranscriptModal
          sessionId={selectedSessionId}
          onClose={() => setSelectedSessionId(null)}
          onReviewSubmitted={fetchData}
        />
      )}
    </div>
  )
}
