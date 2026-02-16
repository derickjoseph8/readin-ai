'use client'

import { useState } from 'react'
import Link from 'next/link'
import {
  Ticket,
  Plus,
  Clock,
  CheckCircle,
  AlertTriangle,
  MessageSquare,
  Search,
  ChevronRight,
  HelpCircle
} from 'lucide-react'
import { useMyTickets } from '@/lib/hooks/useAdmin'
import { SupportTicket } from '@/lib/api/admin'

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
  urgent: 'text-red-400',
  high: 'text-orange-400',
  medium: 'text-yellow-400',
  low: 'text-gray-400',
}

function TicketCard({ ticket }: { ticket: SupportTicket }) {
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
    <Link
      href={`/dashboard/support/${ticket.id}`}
      className="block bg-premium-card border border-premium-border rounded-xl p-5 hover:border-gold-500/30 transition-colors"
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center space-x-2 mb-2">
            <span className="text-xs text-gray-500 font-mono">{ticket.ticket_number}</span>
            <span className={`text-xs px-2 py-0.5 rounded ${statusColors[ticket.status as keyof typeof statusColors]}`}>
              {statusLabels[ticket.status as keyof typeof statusLabels] || ticket.status}
            </span>
          </div>
          <h3 className="font-medium text-white truncate">{ticket.subject}</h3>
          <div className="flex items-center space-x-4 mt-3 text-sm text-gray-500">
            <span className="flex items-center">
              <Clock className="h-3.5 w-3.5 mr-1" />
              {formatDate(ticket.created_at)}
            </span>
            <span className="flex items-center">
              <MessageSquare className="h-3.5 w-3.5 mr-1" />
              {ticket.message_count} {ticket.message_count === 1 ? 'reply' : 'replies'}
            </span>
            <span className={`capitalize ${priorityColors[ticket.priority as keyof typeof priorityColors]}`}>
              {ticket.priority}
            </span>
          </div>
        </div>
        <ChevronRight className="h-5 w-5 text-gray-500 flex-shrink-0 ml-4" />
      </div>
    </Link>
  )
}

export default function SupportPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const { tickets, isLoading } = useMyTickets({
    status: statusFilter || undefined,
  })

  const filteredTickets = tickets.filter(
    (t) =>
      !searchQuery ||
      t.subject.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.ticket_number.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const openCount = tickets.filter((t) => ['open', 'in_progress', 'waiting_customer', 'waiting_internal'].includes(t.status)).length
  const resolvedCount = tickets.filter((t) => ['resolved', 'closed'].includes(t.status)).length

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Support</h1>
          <p className="text-gray-400 mt-1">Get help with ReadIn AI</p>
        </div>
        <Link
          href="/dashboard/support/new"
          className="flex items-center px-4 py-2 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-medium rounded-lg hover:shadow-gold transition-all"
        >
          <Plus className="h-5 w-5 mr-2" />
          New Ticket
        </Link>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-premium-card border border-premium-border rounded-xl p-4">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-blue-500/20 rounded-lg flex items-center justify-center">
              <Ticket className="h-5 w-5 text-blue-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{tickets.length}</p>
              <p className="text-sm text-gray-500">Total Tickets</p>
            </div>
          </div>
        </div>
        <div className="bg-premium-card border border-premium-border rounded-xl p-4">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-yellow-500/20 rounded-lg flex items-center justify-center">
              <Clock className="h-5 w-5 text-yellow-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{openCount}</p>
              <p className="text-sm text-gray-500">Open</p>
            </div>
          </div>
        </div>
        <div className="bg-premium-card border border-premium-border rounded-xl p-4">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-emerald-500/20 rounded-lg flex items-center justify-center">
              <CheckCircle className="h-5 w-5 text-emerald-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{resolvedCount}</p>
              <p className="text-sm text-gray-500">Resolved</p>
            </div>
          </div>
        </div>
        <Link
          href="/dashboard/support/new"
          className="bg-premium-card border border-premium-border rounded-xl p-4 hover:border-gold-500/30 transition-colors"
        >
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gold-500/20 rounded-lg flex items-center justify-center">
              <HelpCircle className="h-5 w-5 text-gold-400" />
            </div>
            <div>
              <p className="text-sm font-medium text-white">Need Help?</p>
              <p className="text-sm text-gray-500">Create a ticket</p>
            </div>
          </div>
        </Link>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search tickets..."
            className="w-full pl-10 pr-4 py-2 bg-premium-surface border border-premium-border rounded-lg text-white focus:outline-none focus:border-gold-500"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-3 py-2 bg-premium-surface border border-premium-border rounded-lg text-white text-sm focus:outline-none focus:border-gold-500"
        >
          <option value="">All Status</option>
          <option value="open">Open</option>
          <option value="in_progress">In Progress</option>
          <option value="waiting_customer">Awaiting Reply</option>
          <option value="resolved">Resolved</option>
          <option value="closed">Closed</option>
        </select>
      </div>

      {/* Tickets List */}
      <div className="space-y-4">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-gold-400"></div>
          </div>
        ) : filteredTickets.length > 0 ? (
          filteredTickets.map((ticket) => <TicketCard key={ticket.id} ticket={ticket} />)
        ) : (
          <div className="bg-premium-card border border-premium-border rounded-xl p-12 text-center">
            <Ticket className="h-12 w-12 mx-auto mb-4 text-gray-600" />
            <h3 className="text-lg font-medium text-white mb-2">No tickets found</h3>
            <p className="text-gray-500 mb-6">
              {searchQuery || statusFilter
                ? "Try adjusting your filters"
                : "You haven't created any support tickets yet"}
            </p>
            <Link
              href="/dashboard/support/new"
              className="inline-flex items-center px-4 py-2 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-medium rounded-lg hover:shadow-gold transition-all"
            >
              <Plus className="h-5 w-5 mr-2" />
              Create Your First Ticket
            </Link>
          </div>
        )}
      </div>
    </div>
  )
}
