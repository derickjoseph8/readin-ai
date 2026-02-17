'use client'

import { useState, useMemo } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import {
  Ticket,
  Search,
  Clock,
  AlertTriangle,
  MessageSquare,
  User,
  X,
  Send
} from 'lucide-react'
import { useTickets, useTicket, useTeams } from '@/lib/hooks/useAdmin'
import { usePermissions, TEAM_CATEGORIES } from '@/lib/hooks/usePermissions'
import { adminApi, SupportTicket } from '@/lib/api/admin'

const priorityColors = {
  urgent: 'bg-red-500/20 text-red-400 border-red-500/30',
  high: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  medium: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  low: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
}

const statusColors = {
  open: 'bg-blue-500/20 text-blue-400',
  in_progress: 'bg-purple-500/20 text-purple-400',
  waiting_customer: 'bg-yellow-500/20 text-yellow-400',
  waiting_internal: 'bg-orange-500/20 text-orange-400',
  resolved: 'bg-emerald-500/20 text-emerald-400',
  closed: 'bg-gray-500/20 text-gray-400',
}

function TicketRow({
  ticket,
  onSelect,
  isSelected
}: {
  ticket: SupportTicket
  onSelect: (ticket: SupportTicket) => void
  isSelected: boolean
}) {
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffHours < 1) return 'Just now'
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 7) return `${diffDays}d ago`
    return date.toLocaleDateString()
  }

  return (
    <button
      onClick={() => onSelect(ticket)}
      className={`w-full text-left p-4 border-b border-premium-border hover:bg-premium-surface/50 transition-colors ${
        isSelected ? 'bg-premium-surface' : ''
      }`}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center space-x-2 mb-1">
            <span className="text-xs text-gray-500">{ticket.ticket_number}</span>
            <span className={`text-xs px-2 py-0.5 rounded ${priorityColors[ticket.priority as keyof typeof priorityColors]}`}>
              {ticket.priority}
            </span>
            {ticket.sla_breached && (
              <AlertTriangle className="h-4 w-4 text-red-400" />
            )}
          </div>
          <h3 className="font-medium text-white truncate">{ticket.subject}</h3>
          <div className="flex items-center space-x-3 mt-2 text-sm text-gray-500">
            <span className="flex items-center">
              <User className="h-3.5 w-3.5 mr-1" />
              {ticket.user_name || ticket.user_email}
            </span>
            <span className="flex items-center">
              <MessageSquare className="h-3.5 w-3.5 mr-1" />
              {ticket.message_count}
            </span>
            <span className="flex items-center">
              <Clock className="h-3.5 w-3.5 mr-1" />
              {formatDate(ticket.created_at)}
            </span>
          </div>
        </div>
        <div className="ml-4 flex flex-col items-end space-y-2">
          <span className={`text-xs px-2 py-1 rounded ${statusColors[ticket.status as keyof typeof statusColors]}`}>
            {ticket.status.replace(/_/g, ' ')}
          </span>
          {ticket.assigned_to_name && (
            <span className="text-xs text-gray-500">
              {ticket.assigned_to_name}
            </span>
          )}
        </div>
      </div>
    </button>
  )
}

function TicketDetail({
  ticketId,
  onClose
}: {
  ticketId: number
  onClose: () => void
}) {
  const { ticket, isLoading, refresh } = useTicket(ticketId)
  const { teams } = useTeams()
  const [replyText, setReplyText] = useState('')
  const [isInternal, setIsInternal] = useState(false)
  const [isSending, setIsSending] = useState(false)
  const [showStatusMenu, setShowStatusMenu] = useState(false)

  const handleSendReply = async () => {
    if (!replyText.trim()) return
    setIsSending(true)

    try {
      await adminApi.addTicketMessage(ticketId, {
        message: replyText,
        is_internal: isInternal
      })
      setReplyText('')
      refresh()
    } catch (error) {
      console.error('Failed to send reply:', error)
    } finally {
      setIsSending(false)
    }
  }

  const handleStatusChange = async (status: string) => {
    try {
      await adminApi.updateTicket(ticketId, { status })
      refresh()
      setShowStatusMenu(false)
    } catch (error) {
      console.error('Failed to update status:', error)
    }
  }

  const handleClaim = async () => {
    try {
      await adminApi.claimTicket(ticketId)
      refresh()
    } catch (error) {
      console.error('Failed to claim ticket:', error)
    }
  }

  if (isLoading || !ticket) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-gold-400"></div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-premium-border">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-500">{ticket.ticket_number}</span>
            <span className={`text-xs px-2 py-0.5 rounded ${priorityColors[ticket.priority as keyof typeof priorityColors]}`}>
              {ticket.priority}
            </span>
          </div>
          <button onClick={onClose} className="lg:hidden text-gray-500 hover:text-white">
            <X className="h-5 w-5" />
          </button>
        </div>
        <h2 className="text-lg font-semibold text-white">{ticket.subject}</h2>
        <div className="flex items-center space-x-4 mt-2 text-sm text-gray-500">
          <span>{ticket.user_name || ticket.user_email}</span>
          <span>{ticket.category}</span>
          <span>{new Date(ticket.created_at).toLocaleString()}</span>
        </div>
      </div>

      {/* Actions */}
      <div className="p-4 border-b border-premium-border flex items-center space-x-3">
        <div className="relative">
          <button
            onClick={() => setShowStatusMenu(!showStatusMenu)}
            className={`text-sm px-3 py-1.5 rounded ${statusColors[ticket.status as keyof typeof statusColors]}`}
          >
            {ticket.status.replace(/_/g, ' ')}
          </button>
          {showStatusMenu && (
            <div className="absolute top-full left-0 mt-1 bg-premium-card border border-premium-border rounded-lg shadow-lg z-10 min-w-[150px]">
              {['open', 'in_progress', 'waiting_customer', 'waiting_internal', 'resolved', 'closed'].map((s) => (
                <button
                  key={s}
                  onClick={() => handleStatusChange(s)}
                  className="w-full text-left px-3 py-2 text-sm text-white hover:bg-premium-surface first:rounded-t-lg last:rounded-b-lg"
                >
                  {s.replace(/_/g, ' ')}
                </button>
              ))}
            </div>
          )}
        </div>

        {!ticket.assigned_to_id && (
          <button
            onClick={handleClaim}
            className="text-sm px-3 py-1.5 bg-gold-500/20 text-gold-400 rounded hover:bg-gold-500/30 transition-colors"
          >
            Claim Ticket
          </button>
        )}

        {ticket.assigned_to_name && (
          <span className="text-sm text-gray-500">
            Assigned to: <span className="text-white">{ticket.assigned_to_name}</span>
          </span>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Original description */}
        <div className="bg-premium-surface rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-white">
              {ticket.user_name || 'Customer'}
            </span>
            <span className="text-xs text-gray-500">
              {new Date(ticket.created_at).toLocaleString()}
            </span>
          </div>
          <p className="text-gray-300 whitespace-pre-wrap">{ticket.description}</p>
        </div>

        {/* Messages */}
        {ticket.messages.map((msg) => (
          <div
            key={msg.id}
            className={`rounded-lg p-4 ${
              msg.sender_type === 'agent'
                ? msg.is_internal
                  ? 'bg-yellow-500/10 border border-yellow-500/20'
                  : 'bg-gold-500/10 border border-gold-500/20'
                : 'bg-premium-surface'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center space-x-2">
                <span className="text-sm font-medium text-white">
                  {msg.sender_name || (msg.sender_type === 'agent' ? 'Agent' : 'Customer')}
                </span>
                {msg.is_internal && (
                  <span className="text-xs bg-yellow-500/20 text-yellow-400 px-1.5 py-0.5 rounded">
                    Internal
                  </span>
                )}
              </div>
              <span className="text-xs text-gray-500">
                {new Date(msg.created_at).toLocaleString()}
              </span>
            </div>
            <p className="text-gray-300 whitespace-pre-wrap">{msg.message}</p>
          </div>
        ))}
      </div>

      {/* Reply Box */}
      <div className="p-4 border-t border-premium-border">
        <div className="flex items-center space-x-2 mb-2">
          <label className="flex items-center text-sm text-gray-400">
            <input
              type="checkbox"
              checked={isInternal}
              onChange={(e) => setIsInternal(e.target.checked)}
              className="mr-2"
            />
            Internal note (not visible to customer)
          </label>
        </div>
        <div className="flex space-x-2">
          <textarea
            value={replyText}
            onChange={(e) => setReplyText(e.target.value)}
            placeholder="Type your reply..."
            className="flex-1 px-4 py-2 bg-premium-surface border border-premium-border rounded-lg text-white focus:outline-none focus:border-gold-500 resize-none"
            rows={3}
          />
          <button
            onClick={handleSendReply}
            disabled={!replyText.trim() || isSending}
            className="px-4 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-medium rounded-lg hover:shadow-gold transition-all disabled:opacity-50"
          >
            <Send className="h-5 w-5" />
          </button>
        </div>
      </div>
    </div>
  )
}

export default function TicketsPage() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const { permissions } = usePermissions()
  const [selectedTicket, setSelectedTicket] = useState<SupportTicket | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState(searchParams.get('status') || '')
  const [priorityFilter, setPriorityFilter] = useState('')

  // Permission check - redirect if not allowed
  if (!permissions.canViewAllTickets && !permissions.canViewTechTickets && !permissions.canViewBillingTickets) {
    if (typeof window !== 'undefined') {
      router.push('/dashboard')
    }
    return null
  }

  // Get allowed categories based on team membership
  const allowedCategories = useMemo(() => {
    if (permissions.isAdmin || permissions.isSuperAdmin) {
      // Admins see all categories
      return null // null means no filter
    }

    // Build list from team memberships
    const categories: string[] = []
    if (permissions.canViewTechTickets) {
      categories.push(...TEAM_CATEGORIES['tech-support'])
    }
    if (permissions.canViewBillingTickets) {
      categories.push(...TEAM_CATEGORIES['accounts'])
    }
    return categories.length > 0 ? categories : null
  }, [permissions])

  const { tickets, total, byStatus, byPriority, isLoading, refresh } = useTickets({
    status: statusFilter || undefined,
    priority: priorityFilter || undefined,
    limit: 50
  })

  // Filter tickets by allowed categories and search
  const filteredTickets = useMemo(() => {
    return tickets.filter((t) => {
      // Category filter based on permissions
      if (allowedCategories && !allowedCategories.includes(t.category)) {
        return false
      }
      // Search filter
      if (searchQuery) {
        const query = searchQuery.toLowerCase()
        return (
          t.subject.toLowerCase().includes(query) ||
          t.ticket_number.toLowerCase().includes(query) ||
          (t.user_email && t.user_email.toLowerCase().includes(query))
        )
      }
      return true
    })
  }, [tickets, allowedCategories, searchQuery])

  return (
    <div className="h-[calc(100vh-6rem)]">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Tickets</h1>
          <p className="text-gray-400 mt-1">{filteredTickets.length} tickets</p>
        </div>
      </div>

      <div className="flex h-[calc(100%-4rem)] gap-6">
        {/* Ticket List */}
        <div className="w-full lg:w-1/2 xl:w-2/5 flex flex-col bg-premium-card border border-premium-border rounded-xl overflow-hidden">
          {/* Filters */}
          <div className="p-4 border-b border-premium-border space-y-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-500" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search tickets..."
                className="w-full pl-10 pr-4 py-2 bg-premium-surface border border-premium-border rounded-lg text-white focus:outline-none focus:border-gold-500"
              />
            </div>
            <div className="flex space-x-2">
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="flex-1 px-3 py-2 bg-premium-surface border border-premium-border rounded-lg text-white text-sm focus:outline-none focus:border-gold-500"
              >
                <option value="">All Status</option>
                <option value="open">Open ({byStatus.open || 0})</option>
                <option value="in_progress">In Progress ({byStatus.in_progress || 0})</option>
                <option value="waiting_customer">Waiting Customer ({byStatus.waiting_customer || 0})</option>
                <option value="resolved">Resolved ({byStatus.resolved || 0})</option>
                <option value="closed">Closed ({byStatus.closed || 0})</option>
              </select>
              <select
                value={priorityFilter}
                onChange={(e) => setPriorityFilter(e.target.value)}
                className="flex-1 px-3 py-2 bg-premium-surface border border-premium-border rounded-lg text-white text-sm focus:outline-none focus:border-gold-500"
              >
                <option value="">All Priority</option>
                <option value="urgent">Urgent ({byPriority.urgent || 0})</option>
                <option value="high">High ({byPriority.high || 0})</option>
                <option value="medium">Medium ({byPriority.medium || 0})</option>
                <option value="low">Low ({byPriority.low || 0})</option>
              </select>
            </div>
          </div>

          {/* Ticket List */}
          <div className="flex-1 overflow-y-auto">
            {isLoading ? (
              <div className="flex items-center justify-center h-32">
                <div className="animate-spin rounded-full h-6 w-6 border-t-2 border-b-2 border-gold-400"></div>
              </div>
            ) : filteredTickets.length > 0 ? (
              filteredTickets.map((ticket) => (
                <TicketRow
                  key={ticket.id}
                  ticket={ticket}
                  onSelect={setSelectedTicket}
                  isSelected={selectedTicket?.id === ticket.id}
                />
              ))
            ) : (
              <div className="flex flex-col items-center justify-center h-32 text-gray-500">
                <Ticket className="h-8 w-8 mb-2" />
                <p>No tickets found</p>
              </div>
            )}
          </div>
        </div>

        {/* Ticket Detail */}
        <div className={`flex-1 bg-premium-card border border-premium-border rounded-xl overflow-hidden ${selectedTicket ? '' : 'hidden lg:flex'}`}>
          {selectedTicket ? (
            <TicketDetail
              ticketId={selectedTicket.id}
              onClose={() => setSelectedTicket(null)}
            />
          ) : (
            <div className="flex items-center justify-center h-full text-gray-500">
              <div className="text-center">
                <Ticket className="h-12 w-12 mx-auto mb-3" />
                <p>Select a ticket to view details</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
