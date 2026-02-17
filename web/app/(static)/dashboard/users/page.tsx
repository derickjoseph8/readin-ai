'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  Users,
  Search,
  Shield,
  MoreVertical,
  UserCog,
  Ban,
  CheckCircle,
  XCircle,
  ChevronLeft,
  ChevronRight
} from 'lucide-react'
import { useAdminUsers } from '@/lib/hooks/useAdmin'
import { usePermissions } from '@/lib/hooks/usePermissions'
import { adminApi, AdminUser } from '@/lib/api/admin'

const subscriptionColors = {
  free: 'bg-gray-500/20 text-gray-400',
  trial: 'bg-blue-500/20 text-blue-400',
  pro: 'bg-gold-500/20 text-gold-400',
  enterprise: 'bg-purple-500/20 text-purple-400',
}

function UserRow({
  user,
  onAction,
  canModify,
}: {
  user: AdminUser
  onAction: (user: AdminUser, action: string) => void
  canModify: boolean
}) {
  const [showMenu, setShowMenu] = useState(false)

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'Never'
    return new Date(dateStr).toLocaleDateString()
  }

  return (
    <tr className="border-b border-premium-border hover:bg-premium-surface/50 transition-colors">
      <td className="px-4 py-4">
        <div className="flex items-center">
          <div className="w-10 h-10 bg-gold-500/20 rounded-full flex items-center justify-center mr-3">
            <span className="text-gold-400 font-medium">
              {user.full_name?.[0] || user.email[0].toUpperCase()}
            </span>
          </div>
          <div>
            <p className="font-medium text-white">{user.full_name || 'No name'}</p>
            <p className="text-sm text-gray-500">{user.email}</p>
          </div>
        </div>
      </td>
      <td className="px-4 py-4">
        <span className={`text-xs px-2 py-1 rounded ${subscriptionColors[user.subscription_tier as keyof typeof subscriptionColors] || subscriptionColors.free}`}>
          {user.subscription_tier || 'free'}
        </span>
      </td>
      <td className="px-4 py-4">
        <div className="flex items-center">
          {user.is_staff ? (
            <Shield className="h-4 w-4 text-gold-400 mr-1" />
          ) : null}
          <span className={`text-sm ${user.is_active ? 'text-emerald-400' : 'text-red-400'}`}>
            {user.is_active ? 'Active' : 'Inactive'}
          </span>
        </div>
      </td>
      <td className="px-4 py-4 text-sm text-gray-400">
        {formatDate(user.last_active)}
      </td>
      <td className="px-4 py-4 text-sm text-gray-400">
        {formatDate(user.created_at)}
      </td>
      <td className="px-4 py-4">
        <div className="relative">
          <button
            onClick={() => setShowMenu(!showMenu)}
            className="p-1 text-gray-500 hover:text-white transition-colors"
          >
            <MoreVertical className="h-5 w-5" />
          </button>
          {showMenu && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setShowMenu(false)} />
              <div className="absolute right-0 top-full mt-1 bg-premium-card border border-premium-border rounded-lg shadow-lg z-20 min-w-[160px]">
                <button
                  onClick={() => {
                    onAction(user, 'view')
                    setShowMenu(false)
                  }}
                  className="w-full text-left px-4 py-2 text-sm text-white hover:bg-premium-surface rounded-t-lg flex items-center"
                >
                  <UserCog className="h-4 w-4 mr-2" />
                  View Details
                </button>
                {canModify && (
                  <>
                    {user.is_active ? (
                      <button
                        onClick={() => {
                          onAction(user, 'deactivate')
                          setShowMenu(false)
                        }}
                        className="w-full text-left px-4 py-2 text-sm text-red-400 hover:bg-premium-surface flex items-center"
                      >
                        <Ban className="h-4 w-4 mr-2" />
                        Deactivate
                      </button>
                    ) : (
                      <button
                        onClick={() => {
                          onAction(user, 'activate')
                          setShowMenu(false)
                        }}
                        className="w-full text-left px-4 py-2 text-sm text-emerald-400 hover:bg-premium-surface flex items-center"
                      >
                        <CheckCircle className="h-4 w-4 mr-2" />
                        Activate
                      </button>
                    )}
                    {!user.is_staff && (
                      <button
                        onClick={() => {
                          onAction(user, 'make_staff')
                          setShowMenu(false)
                        }}
                        className="w-full text-left px-4 py-2 text-sm text-gold-400 hover:bg-premium-surface rounded-b-lg flex items-center"
                      >
                        <Shield className="h-4 w-4 mr-2" />
                        Make Staff
                      </button>
                    )}
                    {user.is_staff && (
                      <button
                        onClick={() => {
                          onAction(user, 'remove_staff')
                          setShowMenu(false)
                        }}
                        className="w-full text-left px-4 py-2 text-sm text-orange-400 hover:bg-premium-surface rounded-b-lg flex items-center"
                      >
                        <XCircle className="h-4 w-4 mr-2" />
                        Remove Staff
                      </button>
                    )}
                  </>
                )}
              </div>
            </>
          )}
        </div>
      </td>
    </tr>
  )
}

function UserDetailModal({
  user,
  onClose,
}: {
  user: AdminUser
  onClose: () => void
}) {
  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'Never'
    return new Date(dateStr).toLocaleString()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="fixed inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-premium-card border border-premium-border rounded-xl shadow-2xl w-full max-w-lg mx-4">
        <div className="p-6 border-b border-premium-border">
          <h2 className="text-xl font-semibold text-white">User Details</h2>
        </div>
        <div className="p-6 space-y-4">
          <div className="flex items-center space-x-4">
            <div className="w-16 h-16 bg-gold-500/20 rounded-full flex items-center justify-center">
              <span className="text-gold-400 font-bold text-2xl">
                {user.full_name?.[0] || user.email[0].toUpperCase()}
              </span>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-white">{user.full_name || 'No name'}</h3>
              <p className="text-gray-400">{user.email}</p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 pt-4">
            <div>
              <p className="text-sm text-gray-500">Status</p>
              <p className={`font-medium ${user.is_active ? 'text-emerald-400' : 'text-red-400'}`}>
                {user.is_active ? 'Active' : 'Inactive'}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Subscription</p>
              <p className="font-medium text-white capitalize">{user.subscription_tier || 'Free'}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Staff Member</p>
              <p className="font-medium text-white">{user.is_staff ? 'Yes' : 'No'}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Staff Role</p>
              <p className="font-medium text-white capitalize">{user.staff_role || 'N/A'}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Created</p>
              <p className="font-medium text-white">{formatDate(user.created_at)}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Last Active</p>
              <p className="font-medium text-white">{formatDate(user.last_active)}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Trial Ends</p>
              <p className="font-medium text-white">{formatDate(user.trial_ends_at)}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Subscription Ends</p>
              <p className="font-medium text-white">{formatDate(user.subscription_ends_at)}</p>
            </div>
          </div>

          {user.stripe_customer_id && (
            <div className="pt-4 border-t border-premium-border">
              <p className="text-sm text-gray-500">Stripe Customer ID</p>
              <p className="font-mono text-sm text-white">{user.stripe_customer_id}</p>
            </div>
          )}
        </div>
        <div className="p-6 border-t border-premium-border flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-premium-surface text-white rounded-lg hover:bg-premium-surface/80 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

export default function UsersPage() {
  const router = useRouter()
  const { permissions } = usePermissions()
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [subscriptionFilter, setSubscriptionFilter] = useState('')
  const [staffFilter, setStaffFilter] = useState('')
  const [page, setPage] = useState(1)
  const [selectedUser, setSelectedUser] = useState<AdminUser | null>(null)
  const limit = 20

  // Permission check - redirect if not allowed
  if (!permissions.canViewAllUsers) {
    if (typeof window !== 'undefined') {
      router.push('/dashboard')
    }
    return null
  }

  const { users, total, isLoading, refresh } = useAdminUsers({
    search: searchQuery || undefined,
    is_active: statusFilter === 'active' ? true : statusFilter === 'inactive' ? false : undefined,
    subscription_tier: subscriptionFilter || undefined,
    is_staff: staffFilter === 'staff' ? true : staffFilter === 'customer' ? false : undefined,
    skip: (page - 1) * limit,
    limit,
  })

  const totalPages = Math.ceil(total / limit)

  const handleAction = async (user: AdminUser, action: string) => {
    switch (action) {
      case 'view':
        setSelectedUser(user)
        break
      case 'deactivate':
        if (confirm(`Are you sure you want to deactivate ${user.email}?`)) {
          try {
            await adminApi.updateUser(user.id, { is_active: false })
            refresh()
          } catch (error) {
            console.error('Failed to deactivate user:', error)
          }
        }
        break
      case 'activate':
        try {
          await adminApi.updateUser(user.id, { is_active: true })
          refresh()
        } catch (error) {
          console.error('Failed to activate user:', error)
        }
        break
      case 'make_staff':
        try {
          await adminApi.updateUser(user.id, { is_staff: true, staff_role: 'agent' })
          refresh()
        } catch (error) {
          console.error('Failed to make staff:', error)
        }
        break
      case 'remove_staff':
        if (confirm(`Are you sure you want to remove staff access from ${user.email}?`)) {
          try {
            await adminApi.updateUser(user.id, { is_staff: false, staff_role: null })
            refresh()
          } catch (error) {
            console.error('Failed to remove staff:', error)
          }
        }
        break
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Users</h1>
          <p className="text-gray-400 mt-1">{total} total users</p>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-premium-card border border-premium-border rounded-xl p-4">
        <div className="flex flex-col lg:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value)
                setPage(1)
              }}
              placeholder="Search by name or email..."
              className="w-full pl-10 pr-4 py-2 bg-premium-surface border border-premium-border rounded-lg text-white focus:outline-none focus:border-gold-500"
            />
          </div>
          <div className="flex gap-3">
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value)
                setPage(1)
              }}
              className="px-3 py-2 bg-premium-surface border border-premium-border rounded-lg text-white text-sm focus:outline-none focus:border-gold-500"
            >
              <option value="">All Status</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
            <select
              value={subscriptionFilter}
              onChange={(e) => {
                setSubscriptionFilter(e.target.value)
                setPage(1)
              }}
              className="px-3 py-2 bg-premium-surface border border-premium-border rounded-lg text-white text-sm focus:outline-none focus:border-gold-500"
            >
              <option value="">All Plans</option>
              <option value="free">Free</option>
              <option value="trial">Trial</option>
              <option value="pro">Pro</option>
              <option value="enterprise">Enterprise</option>
            </select>
            <select
              value={staffFilter}
              onChange={(e) => {
                setStaffFilter(e.target.value)
                setPage(1)
              }}
              className="px-3 py-2 bg-premium-surface border border-premium-border rounded-lg text-white text-sm focus:outline-none focus:border-gold-500"
            >
              <option value="">All Users</option>
              <option value="staff">Staff Only</option>
              <option value="customer">Customers Only</option>
            </select>
          </div>
        </div>
      </div>

      {/* Users Table */}
      <div className="bg-premium-card border border-premium-border rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-premium-surface text-left">
                <th className="px-4 py-3 text-sm font-medium text-gray-400">User</th>
                <th className="px-4 py-3 text-sm font-medium text-gray-400">Subscription</th>
                <th className="px-4 py-3 text-sm font-medium text-gray-400">Status</th>
                <th className="px-4 py-3 text-sm font-medium text-gray-400">Last Active</th>
                <th className="px-4 py-3 text-sm font-medium text-gray-400">Created</th>
                <th className="px-4 py-3 text-sm font-medium text-gray-400"></th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center">
                    <div className="flex items-center justify-center">
                      <div className="animate-spin rounded-full h-6 w-6 border-t-2 border-b-2 border-gold-400"></div>
                    </div>
                  </td>
                </tr>
              ) : users.length > 0 ? (
                users.map((user) => (
                  <UserRow
                    key={user.id}
                    user={user}
                    onAction={handleAction}
                    canModify={permissions.isSuperAdmin || permissions.isAdmin}
                  />
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                    <Users className="h-8 w-8 mx-auto mb-2" />
                    <p>No users found</p>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="px-4 py-3 border-t border-premium-border flex items-center justify-between">
            <p className="text-sm text-gray-500">
              Showing {(page - 1) * limit + 1} to {Math.min(page * limit, total)} of {total}
            </p>
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setPage(page - 1)}
                disabled={page === 1}
                className="p-2 text-gray-400 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="h-5 w-5" />
              </button>
              <span className="text-sm text-white">
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => setPage(page + 1)}
                disabled={page === totalPages}
                className="p-2 text-gray-400 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronRight className="h-5 w-5" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* User Detail Modal */}
      {selectedUser && (
        <UserDetailModal user={selectedUser} onClose={() => setSelectedUser(null)} />
      )}
    </div>
  )
}
