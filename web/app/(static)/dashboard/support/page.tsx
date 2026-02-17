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
  HelpCircle,
  MessagesSquare,
  Wrench,
  CreditCard,
  Building2,
  X,
  Users
} from 'lucide-react'
import { useMyTickets } from '@/lib/hooks/useAdmin'
import { usePermissions } from '@/lib/hooks/usePermissions'
import { SupportTicket } from '@/lib/api/admin'

const supportCategories = [
  {
    id: 'technical',
    name: 'Technical Support',
    description: 'Help with app issues, bugs, or technical problems',
    icon: Wrench,
    color: 'bg-blue-500/20 text-blue-400',
  },
  {
    id: 'billing',
    name: 'Billing & Subscription',
    description: 'Questions about payments, plans, or invoices',
    icon: CreditCard,
    color: 'bg-emerald-500/20 text-emerald-400',
  },
  {
    id: 'enterprise',
    name: 'Enterprise Inquiry',
    description: 'Custom solutions, volume licensing, or partnerships',
    icon: Building2,
    color: 'bg-purple-500/20 text-purple-400',
  },
]

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

function TicketCard({ ticket, showCreator = false }: { ticket: SupportTicket; showCreator?: boolean }) {
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
            {showCreator && ticket.user_name && (
              <span className="text-xs px-2 py-0.5 rounded bg-purple-500/20 text-purple-400">
                By: {ticket.user_name}
              </span>
            )}
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
  const { permissions } = usePermissions()
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [showSupportOptions, setShowSupportOptions] = useState(false)
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const [viewOrgTickets, setViewOrgTickets] = useState(false)

  // Fetch tickets - my tickets or org tickets based on toggle
  const { tickets, isLoading } = useMyTickets({
    status: statusFilter || undefined,
    orgTickets: viewOrgTickets && permissions.isOrgAdmin,
  })

  const filteredTickets = tickets.filter(
    (t) =>
      !searchQuery ||
      t.subject.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.ticket_number.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const openCount = tickets.filter((t) => ['open', 'in_progress', 'waiting_customer', 'waiting_internal'].includes(t.status)).length
  const resolvedCount = tickets.filter((t) => ['resolved', 'closed'].includes(t.status)).length

  const handleGetSupport = () => {
    setShowSupportOptions(true)
    setSelectedCategory(null)
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Support Options Modal */}
      {showSupportOptions && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
          <div className="bg-premium-card border border-premium-border rounded-2xl max-w-2xl w-full p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-white">
                {selectedCategory ? 'Choose Support Method' : 'How can we help?'}
              </h2>
              <button
                onClick={() => setShowSupportOptions(false)}
                className="p-2 text-gray-400 hover:text-white transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {!selectedCategory ? (
              <div className="space-y-3">
                <p className="text-gray-400 mb-4">Select the type of support you need:</p>
                {supportCategories.map((category) => (
                  <button
                    key={category.id}
                    onClick={() => setSelectedCategory(category.id)}
                    className="w-full flex items-center p-4 bg-premium-surface border border-premium-border rounded-xl hover:border-gold-500/30 transition-colors text-left"
                  >
                    <div className={`w-12 h-12 rounded-lg flex items-center justify-center mr-4 ${category.color}`}>
                      <category.icon className="h-6 w-6" />
                    </div>
                    <div>
                      <h3 className="font-medium text-white">{category.name}</h3>
                      <p className="text-sm text-gray-400">{category.description}</p>
                    </div>
                    <ChevronRight className="h-5 w-5 text-gray-500 ml-auto" />
                  </button>
                ))}
              </div>
            ) : (
              <div className="space-y-4">
                <button
                  onClick={() => setSelectedCategory(null)}
                  className="text-sm text-gold-400 hover:text-gold-300 flex items-center"
                >
                  ← Back to categories
                </button>

                <div className="grid md:grid-cols-2 gap-4">
                  {/* Create Ticket Option */}
                  <Link
                    href={`/dashboard/support/new?category=${selectedCategory}`}
                    onClick={() => setShowSupportOptions(false)}
                    className="flex flex-col items-center p-6 bg-premium-surface border border-premium-border rounded-xl hover:border-gold-500/30 transition-colors text-center"
                  >
                    <div className="w-16 h-16 bg-gold-500/20 rounded-xl flex items-center justify-center mb-4">
                      <Ticket className="h-8 w-8 text-gold-400" />
                    </div>
                    <h3 className="font-semibold text-white mb-2">Create a Ticket</h3>
                    <p className="text-sm text-gray-400">
                      Submit a detailed request and get a response within 24 hours
                    </p>
                  </Link>

                  {/* Live Chat Option */}
                  <button
                    onClick={() => {
                      setShowSupportOptions(false)
                      // Open chat widget or navigate to chat
                      window.open(`mailto:support@getreadin.ai?subject=${encodeURIComponent(
                        supportCategories.find(c => c.id === selectedCategory)?.name || 'Support'
                      )}`, '_blank')
                    }}
                    className="flex flex-col items-center p-6 bg-premium-surface border border-premium-border rounded-xl hover:border-gold-500/30 transition-colors text-center"
                  >
                    <div className="w-16 h-16 bg-emerald-500/20 rounded-xl flex items-center justify-center mb-4">
                      <MessagesSquare className="h-8 w-8 text-emerald-400" />
                    </div>
                    <h3 className="font-semibold text-white mb-2">Start a Chat</h3>
                    <p className="text-sm text-gray-400">
                      Get instant help from our support team (Business hours)
                    </p>
                  </button>
                </div>

                {selectedCategory === 'enterprise' && (
                  <div className="mt-4 p-4 bg-purple-500/10 border border-purple-500/20 rounded-xl">
                    <p className="text-sm text-purple-300">
                      For enterprise inquiries, you can also reach us directly at{' '}
                      <a href="mailto:enterprise@getreadin.ai" className="text-purple-400 hover:underline">
                        enterprise@getreadin.ai
                      </a>
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Support</h1>
          <p className="text-gray-400 mt-1">Get help with ReadIn AI</p>
        </div>
        <button
          onClick={handleGetSupport}
          className="flex items-center px-4 py-2 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-medium rounded-lg hover:shadow-gold transition-all"
        >
          <Plus className="h-5 w-5 mr-2" />
          Get Support
        </button>
      </div>

      {/* Org Admin Tabs */}
      {permissions.isOrgAdmin && (
        <div className="flex space-x-1 bg-premium-surface p-1 rounded-lg w-fit">
          <button
            onClick={() => setViewOrgTickets(false)}
            className={`flex items-center px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              !viewOrgTickets
                ? 'bg-premium-card text-white'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            <Ticket className="h-4 w-4 mr-2" />
            My Tickets
          </button>
          <button
            onClick={() => setViewOrgTickets(true)}
            className={`flex items-center px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              viewOrgTickets
                ? 'bg-premium-card text-white'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            <Users className="h-4 w-4 mr-2" />
            Company Tickets
          </button>
        </div>
      )}

      {/* Quick Support Options */}
      <div className="grid md:grid-cols-3 gap-4">
        {supportCategories.map((category) => (
          <button
            key={category.id}
            onClick={() => {
              setShowSupportOptions(true)
              setSelectedCategory(category.id)
            }}
            className="bg-premium-card border border-premium-border rounded-xl p-4 hover:border-gold-500/30 transition-colors text-left"
          >
            <div className="flex items-center space-x-3">
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${category.color}`}>
                <category.icon className="h-5 w-5" />
              </div>
              <div>
                <p className="font-medium text-white text-sm">{category.name}</p>
                <p className="text-xs text-gray-500">Get help</p>
              </div>
            </div>
          </button>
        ))}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
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
          filteredTickets.map((ticket) => (
            <TicketCard key={ticket.id} ticket={ticket} showCreator={viewOrgTickets} />
          ))
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
