'use client'

import { useState, useEffect, useRef } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  ArrowLeft,
  Clock,
  CheckCircle,
  Send,
  User,
  Shield,
  MessageSquare,
  AlertCircle
} from 'lucide-react'
import { useMyTicket } from '@/lib/hooks/useAdmin'
import { supportApi } from '@/lib/api/admin'

const statusColors = {
  open: 'bg-blue-500/20 text-blue-400',
  in_progress: 'bg-purple-500/20 text-purple-400',
  waiting_customer: 'bg-yellow-500/20 text-yellow-400',
  waiting_internal: 'bg-orange-500/20 text-orange-400',
  resolved: 'bg-emerald-500/20 text-emerald-400',
  closed: 'bg-gray-500/20 text-gray-400',
}

const statusLabels = {
  open: 'Open',
  in_progress: 'In Progress',
  waiting_customer: 'Awaiting Your Reply',
  waiting_internal: 'Under Review',
  resolved: 'Resolved',
  closed: 'Closed',
}

const priorityColors = {
  urgent: 'bg-red-500/20 text-red-400 border-red-500/30',
  high: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  medium: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  low: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
}

export default function TicketDetailPage() {
  const params = useParams()
  const router = useRouter()
  const ticketId = parseInt(params.id as string)
  const { ticket, isLoading, refresh } = useMyTicket(ticketId)
  const [replyText, setReplyText] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [error, setError] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [ticket?.messages])

  const handleSendReply = async () => {
    if (!replyText.trim()) return
    setError('')
    setIsSending(true)

    try {
      await supportApi.addTicketMessage(ticketId, replyText.trim())
      setReplyText('')
      refresh()
    } catch (err: any) {
      setError(err.message || 'Failed to send message')
    } finally {
      setIsSending(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendReply()
    }
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString()
  }

  const isOpen = ticket && !['resolved', 'closed'].includes(ticket.status)

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-gold-400"></div>
      </div>
    )
  }

  if (!ticket) {
    return (
      <div className="max-w-2xl mx-auto text-center py-12">
        <MessageSquare className="h-12 w-12 mx-auto mb-4 text-gray-600" />
        <h2 className="text-xl font-semibold text-white mb-2">Ticket not found</h2>
        <p className="text-gray-500 mb-6">This ticket doesn't exist or you don't have access to it.</p>
        <Link
          href="/dashboard/support"
          className="inline-flex items-center px-4 py-2 bg-premium-surface text-white rounded-lg hover:bg-premium-surface/80 transition-colors"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Support
        </Link>
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center space-x-4">
          <Link
            href="/dashboard/support"
            className="p-2 text-gray-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <div>
            <div className="flex items-center space-x-2 mb-1">
              <span className="text-sm text-gray-500 font-mono">{ticket.ticket_number}</span>
              <span className={`text-xs px-2 py-0.5 rounded border ${priorityColors[ticket.priority as keyof typeof priorityColors]}`}>
                {ticket.priority}
              </span>
            </div>
            <h1 className="text-xl font-bold text-white">{ticket.subject}</h1>
          </div>
        </div>
        <span className={`text-sm px-3 py-1 rounded ${statusColors[ticket.status as keyof typeof statusColors]}`}>
          {statusLabels[ticket.status as keyof typeof statusLabels] || ticket.status}
        </span>
      </div>

      {/* Ticket Info */}
      <div className="bg-premium-card border border-premium-border rounded-xl p-4">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <p className="text-gray-500">Category</p>
            <p className="text-white capitalize">{ticket.category}</p>
          </div>
          <div>
            <p className="text-gray-500">Created</p>
            <p className="text-white">{formatDate(ticket.created_at)}</p>
          </div>
          <div>
            <p className="text-gray-500">Last Updated</p>
            <p className="text-white">{formatDate(ticket.updated_at)}</p>
          </div>
          {ticket.assigned_to_name && (
            <div>
              <p className="text-gray-500">Assigned To</p>
              <p className="text-white">{ticket.assigned_to_name}</p>
            </div>
          )}
        </div>
      </div>

      {/* Status Banner for waiting_customer */}
      {ticket.status === 'waiting_customer' && (
        <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-4 flex items-center">
          <AlertCircle className="h-5 w-5 text-yellow-400 mr-3 flex-shrink-0" />
          <p className="text-yellow-400">We're waiting for your reply. Please provide the requested information.</p>
        </div>
      )}

      {/* Resolved Banner */}
      {ticket.status === 'resolved' && (
        <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-xl p-4 flex items-center">
          <CheckCircle className="h-5 w-5 text-emerald-400 mr-3 flex-shrink-0" />
          <p className="text-emerald-400">This ticket has been resolved. If you still need help, you can reply to reopen it.</p>
        </div>
      )}

      {/* Messages */}
      <div className="bg-premium-card border border-premium-border rounded-xl overflow-hidden">
        <div className="p-4 border-b border-premium-border">
          <h2 className="font-semibold text-white">Conversation</h2>
        </div>
        <div className="p-4 space-y-4 max-h-[500px] overflow-y-auto">
          {/* Original Description */}
          <div className="bg-premium-surface rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center space-x-2">
                <div className="w-8 h-8 bg-gold-500/20 rounded-full flex items-center justify-center">
                  <User className="h-4 w-4 text-gold-400" />
                </div>
                <span className="text-sm font-medium text-white">You</span>
              </div>
              <span className="text-xs text-gray-500">{formatDate(ticket.created_at)}</span>
            </div>
            <p className="text-gray-300 whitespace-pre-wrap">{ticket.description}</p>
          </div>

          {/* Messages */}
          {ticket.messages.filter(m => !m.is_internal).map((msg) => (
            <div
              key={msg.id}
              className={`rounded-lg p-4 ${
                msg.sender_type === 'agent'
                  ? 'bg-blue-500/10 border border-blue-500/20'
                  : 'bg-premium-surface'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-2">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                    msg.sender_type === 'agent' ? 'bg-blue-500/20' : 'bg-gold-500/20'
                  }`}>
                    {msg.sender_type === 'agent' ? (
                      <Shield className="h-4 w-4 text-blue-400" />
                    ) : (
                      <User className="h-4 w-4 text-gold-400" />
                    )}
                  </div>
                  <span className="text-sm font-medium text-white">
                    {msg.sender_type === 'agent' ? (msg.sender_name || 'Support Team') : 'You'}
                  </span>
                </div>
                <span className="text-xs text-gray-500">{formatDate(msg.created_at)}</span>
              </div>
              <p className="text-gray-300 whitespace-pre-wrap">{msg.message}</p>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Reply Box */}
        {ticket.status !== 'closed' && (
          <div className="p-4 border-t border-premium-border">
            {error && (
              <div className="mb-3 text-sm text-red-400 flex items-center">
                <AlertCircle className="h-4 w-4 mr-2" />
                {error}
              </div>
            )}
            <div className="flex space-x-3">
              <textarea
                value={replyText}
                onChange={(e) => setReplyText(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Type your reply..."
                rows={3}
                className="flex-1 px-4 py-3 bg-premium-surface border border-premium-border rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-gold-500 resize-none"
              />
              <button
                onClick={handleSendReply}
                disabled={!replyText.trim() || isSending}
                className="px-4 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-medium rounded-lg hover:shadow-gold transition-all disabled:opacity-50 self-end h-12"
              >
                {isSending ? (
                  <div className="animate-spin rounded-full h-5 w-5 border-t-2 border-b-2 border-premium-bg"></div>
                ) : (
                  <Send className="h-5 w-5" />
                )}
              </button>
            </div>
            <p className="text-xs text-gray-500 mt-2">Press Enter to send, Shift+Enter for new line</p>
          </div>
        )}

        {ticket.status === 'closed' && (
          <div className="p-4 border-t border-premium-border text-center">
            <p className="text-gray-500">This ticket is closed. <Link href="/dashboard/support/new" className="text-gold-400 hover:underline">Create a new ticket</Link> if you need further assistance.</p>
          </div>
        )}
      </div>
    </div>
  )
}
