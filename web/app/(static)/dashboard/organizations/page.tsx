'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import {
  Building2,
  Users,
  Search,
  ChevronRight,
  CreditCard,
  Calendar,
  Ticket,
  Loader2,
  Filter,
  X
} from 'lucide-react'
import apiClient from '@/lib/api/client'
import { Skeleton } from '@/components/ui/Skeleton'

interface OrganizationSummary {
  id: number
  name: string
  plan_type: string
  max_users: number
  member_count: number
  subscription_status: string
  subscription_end_date: string | null
  billing_email: string | null
  admin_email: string | null
  admin_name: string | null
  created_at: string
}

interface OrganizationMember {
  id: number
  email: string
  full_name: string | null
  role_in_org: string
  subscription_status: string
  ticket_count: number
  last_login: string | null
  created_at: string
}

interface OrganizationDetail extends OrganizationSummary {
  subscription_id: string | null
  admin_id: number | null
  shared_insights_enabled: boolean
  allow_personal_professions: boolean
  members: OrganizationMember[]
  updated_at: string
}

const planColors: Record<string, string> = {
  team: 'bg-blue-500/20 text-blue-400',
  business: 'bg-purple-500/20 text-purple-400',
  enterprise: 'bg-gold-500/20 text-gold-400',
}

const statusColors: Record<string, string> = {
  active: 'bg-emerald-500/20 text-emerald-400',
  trial: 'bg-yellow-500/20 text-yellow-400',
  cancelled: 'bg-red-500/20 text-red-400',
  expired: 'bg-gray-500/20 text-gray-400',
}

function OrganizationCard({
  org,
  onClick,
}: {
  org: OrganizationSummary
  onClick: () => void
}) {
  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    })
  }

  return (
    <div
      onClick={onClick}
      className="bg-premium-card border border-premium-border rounded-xl p-6 hover:border-gold-500/30 transition-colors cursor-pointer"
    >
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center">
          <div className="w-12 h-12 bg-gold-500/20 rounded-lg flex items-center justify-center">
            <Building2 className="h-6 w-6 text-gold-400" />
          </div>
          <div className="ml-4">
            <h3 className="font-medium text-white">{org.name}</h3>
            <p className="text-gray-500 text-sm">{org.billing_email}</p>
          </div>
        </div>
        <ChevronRight className="h-5 w-5 text-gray-500" />
      </div>

      <div className="flex flex-wrap gap-2 mb-4">
        <span className={`px-2 py-1 rounded text-xs font-medium ${planColors[org.plan_type] || 'bg-gray-500/20 text-gray-400'}`}>
          {org.plan_type.charAt(0).toUpperCase() + org.plan_type.slice(1)}
        </span>
        <span className={`px-2 py-1 rounded text-xs font-medium ${statusColors[org.subscription_status] || 'bg-gray-500/20 text-gray-400'}`}>
          {org.subscription_status.charAt(0).toUpperCase() + org.subscription_status.slice(1)}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-4 text-sm">
        <div className="flex items-center text-gray-400">
          <Users className="h-4 w-4 mr-2" />
          {org.member_count} / {org.max_users} members
        </div>
        <div className="flex items-center text-gray-400">
          <Calendar className="h-4 w-4 mr-2" />
          {formatDate(org.created_at)}
        </div>
      </div>

      {org.admin_name && (
        <div className="mt-3 pt-3 border-t border-premium-border">
          <p className="text-xs text-gray-500">
            Admin: <span className="text-gray-300">{org.admin_name}</span>
          </p>
        </div>
      )}
    </div>
  )
}

function OrganizationDetailModal({
  orgId,
  onClose,
}: {
  orgId: number
  onClose: () => void
}) {
  const [org, setOrg] = useState<OrganizationDetail | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const fetchOrg = async () => {
      try {
        const data = await apiClient.get<OrganizationDetail>(`/api/v1/admin/dashboard/organizations/${orgId}`)
        setOrg(data)
      } catch (err) {
        console.error('Failed to fetch organization:', err)
      } finally {
        setIsLoading(false)
      }
    }
    fetchOrg()
  }, [orgId])

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '—'
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="fixed inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-premium-card border border-premium-border rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-premium-border flex items-center justify-between flex-shrink-0">
          <div className="flex items-center">
            <div className="w-12 h-12 bg-gold-500/20 rounded-lg flex items-center justify-center mr-4">
              <Building2 className="h-6 w-6 text-gold-400" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-white">{org?.name || 'Loading...'}</h2>
              <p className="text-gray-500 text-sm">{org?.billing_email}</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 text-gray-400 hover:text-white">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-gold-400" />
            </div>
          ) : org ? (
            <div className="space-y-6">
              {/* Stats */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-premium-surface rounded-lg p-4">
                  <p className="text-gray-500 text-sm">Members</p>
                  <p className="text-2xl font-bold text-white">{org.member_count}</p>
                  <p className="text-xs text-gray-500">of {org.max_users} max</p>
                </div>
                <div className="bg-premium-surface rounded-lg p-4">
                  <p className="text-gray-500 text-sm">Plan</p>
                  <p className="text-2xl font-bold text-white capitalize">{org.plan_type}</p>
                </div>
                <div className="bg-premium-surface rounded-lg p-4">
                  <p className="text-gray-500 text-sm">Status</p>
                  <span className={`inline-block px-2 py-1 rounded text-sm font-medium ${statusColors[org.subscription_status]}`}>
                    {org.subscription_status}
                  </span>
                </div>
                <div className="bg-premium-surface rounded-lg p-4">
                  <p className="text-gray-500 text-sm">Created</p>
                  <p className="text-lg font-medium text-white">{formatDate(org.created_at)}</p>
                </div>
              </div>

              {/* Team Members */}
              <div>
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center">
                  <Users className="h-5 w-5 text-gold-400 mr-2" />
                  Team Members ({org.members.length})
                </h3>

                <div className="bg-premium-surface rounded-xl overflow-hidden">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-premium-border">
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Member</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Role</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Tickets</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Last Login</th>
                      </tr>
                    </thead>
                    <tbody>
                      {org.members.map((member) => (
                        <tr key={member.id} className="border-b border-premium-border hover:bg-premium-card/50">
                          <td className="px-4 py-3">
                            <div>
                              <p className="font-medium text-white">{member.full_name || 'Unnamed'}</p>
                              <p className="text-sm text-gray-500">{member.email}</p>
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <span className={`px-2 py-1 rounded text-xs font-medium ${
                              member.role_in_org === 'admin' ? 'bg-gold-500/20 text-gold-400' : 'bg-gray-500/20 text-gray-400'
                            }`}>
                              {member.role_in_org}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex items-center text-gray-400">
                              <Ticket className="h-4 w-4 mr-1" />
                              {member.ticket_count}
                            </div>
                          </td>
                          <td className="px-4 py-3 text-gray-400 text-sm">
                            {formatDate(member.last_login)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Quick Actions */}
              <div className="flex flex-wrap gap-3">
                <Link
                  href={`/dashboard/organizations/${org.id}/tickets`}
                  className="px-4 py-2 bg-premium-surface border border-premium-border rounded-lg text-white hover:bg-premium-surface/80 transition-colors flex items-center text-sm"
                >
                  <Ticket className="h-4 w-4 mr-2" />
                  View All Tickets
                </Link>
                <button className="px-4 py-2 bg-premium-surface border border-premium-border rounded-lg text-white hover:bg-premium-surface/80 transition-colors flex items-center text-sm">
                  <CreditCard className="h-4 w-4 mr-2" />
                  View Billing
                </button>
              </div>
            </div>
          ) : (
            <p className="text-center text-gray-400">Failed to load organization details</p>
          )}
        </div>
      </div>
    </div>
  )
}

function OrganizationsPageSkeleton() {
  return (
    <div className="space-y-6">
      <div>
        <Skeleton className="h-8 w-48 mb-2" />
        <Skeleton className="h-4 w-72" />
      </div>
      <Skeleton className="h-10 w-full max-w-md rounded-lg" />
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="bg-premium-card border border-premium-border rounded-xl p-6">
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center">
                <Skeleton className="w-12 h-12 rounded-lg" />
                <div className="ml-4">
                  <Skeleton className="h-5 w-32 mb-1" />
                  <Skeleton className="h-4 w-40" />
                </div>
              </div>
            </div>
            <div className="flex gap-2 mb-4">
              <Skeleton className="h-6 w-16 rounded" />
              <Skeleton className="h-6 w-16 rounded" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Skeleton className="h-4 w-20" />
              <Skeleton className="h-4 w-24" />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function OrganizationsPage() {
  const [organizations, setOrganizations] = useState<OrganizationSummary[]>([])
  const [total, setTotal] = useState(0)
  const [isLoading, setIsLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [planFilter, setPlanFilter] = useState<string>('')
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [selectedOrgId, setSelectedOrgId] = useState<number | null>(null)

  const fetchOrganizations = async () => {
    setIsLoading(true)
    try {
      const params = new URLSearchParams()
      if (search) params.append('search', search)
      if (planFilter) params.append('plan_type', planFilter)
      if (statusFilter) params.append('subscription_status', statusFilter)

      const data = await apiClient.get<{ organizations: OrganizationSummary[]; total: number }>(
        `/api/v1/admin/dashboard/organizations?${params.toString()}`
      )
      setOrganizations(data.organizations)
      setTotal(data.total)
    } catch (err) {
      console.error('Failed to fetch organizations:', err)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchOrganizations()
  }, [search, planFilter, statusFilter])

  if (isLoading && organizations.length === 0) {
    return <OrganizationsPageSkeleton />
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Organizations</h1>
        <p className="text-gray-400 mt-1">
          Manage company accounts and their team members
        </p>
      </div>

      {/* Search & Filters */}
      <div className="flex flex-wrap items-center gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
          <input
            type="text"
            placeholder="Search organizations..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-premium-surface border border-premium-border rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-gold-500/50"
          />
        </div>

        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-gray-500" />
          <select
            value={planFilter}
            onChange={(e) => setPlanFilter(e.target.value)}
            className="px-3 py-2 bg-premium-surface border border-premium-border rounded-lg text-white focus:outline-none focus:border-gold-500/50"
          >
            <option value="">All Plans</option>
            <option value="team">Team</option>
            <option value="business">Business</option>
            <option value="enterprise">Enterprise</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 bg-premium-surface border border-premium-border rounded-lg text-white focus:outline-none focus:border-gold-500/50"
          >
            <option value="">All Status</option>
            <option value="active">Active</option>
            <option value="trial">Trial</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>
      </div>

      {/* Stats */}
      <div className="flex items-center text-sm text-gray-400">
        <Building2 className="h-4 w-4 mr-2" />
        {total} organization{total !== 1 ? 's' : ''} found
      </div>

      {/* Organizations Grid */}
      {organizations.length > 0 ? (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {organizations.map((org) => (
            <OrganizationCard
              key={org.id}
              org={org}
              onClick={() => setSelectedOrgId(org.id)}
            />
          ))}
        </div>
      ) : (
        <div className="text-center py-12">
          <Building2 className="h-12 w-12 text-gray-600 mx-auto mb-3" />
          <p className="text-gray-400">No organizations found</p>
          <p className="text-gray-500 text-sm mt-1">
            {search || planFilter || statusFilter
              ? 'Try adjusting your filters'
              : 'Organizations will appear here when companies sign up'}
          </p>
        </div>
      )}

      {/* Detail Modal */}
      {selectedOrgId && (
        <OrganizationDetailModal
          orgId={selectedOrgId}
          onClose={() => setSelectedOrgId(null)}
        />
      )}
    </div>
  )
}
