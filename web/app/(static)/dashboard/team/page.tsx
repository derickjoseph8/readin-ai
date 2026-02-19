'use client'

import { useState } from 'react'
import {
  Users,
  UserPlus,
  Mail,
  Shield,
  MoreVertical,
  Trash2,
  Crown,
  Building2,
  X
} from 'lucide-react'
import { useAuth } from '@/lib/hooks/useAuth'

interface TeamMember {
  id: number
  name: string
  email: string
  role: 'owner' | 'admin' | 'member'
  status: 'active' | 'pending'
  joinedAt: string
}

// Mock data - in production, this would come from the API
const mockTeamMembers: TeamMember[] = [
  {
    id: 1,
    name: 'John Doe',
    email: 'john@example.com',
    role: 'owner',
    status: 'active',
    joinedAt: '2024-01-15',
  },
]

export default function TeamPage() {
  const { user, status } = useAuth()
  const [showInviteModal, setShowInviteModal] = useState(false)
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteRole, setInviteRole] = useState<'admin' | 'member'>('member')
  const [isInviting, setIsInviting] = useState(false)
  const [teamMembers] = useState<TeamMember[]>([
    {
      id: 1,
      name: user?.full_name || 'You',
      email: user?.email || '',
      role: 'owner',
      status: 'active',
      joinedAt: new Date().toISOString().split('T')[0],
    },
  ])

  const isPremium = status?.subscription.status === 'active' || status?.subscription.status === 'trial'
  const isCompanyAccount = user?.account_type === 'company' || user?.account_type === 'business' || !!user?.organization_id || !!user?.company_name
  const isTeamPlan = isCompanyAccount && isPremium

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsInviting(true)
    try {
      // API call to invite team member
      await new Promise(resolve => setTimeout(resolve, 1000)) // Simulated delay
      alert(`Invitation sent to ${inviteEmail}`)
      setShowInviteModal(false)
      setInviteEmail('')
    } catch (error) {
      console.error('Invite failed:', error)
    } finally {
      setIsInviting(false)
    }
  }

  const getRoleBadge = (role: TeamMember['role']) => {
    const styles = {
      owner: 'bg-gold-500/20 text-gold-400',
      admin: 'bg-blue-500/20 text-blue-400',
      member: 'bg-gray-500/20 text-gray-400',
    }
    return (
      <span className={`px-2 py-1 text-xs rounded-full capitalize ${styles[role]}`}>
        {role}
      </span>
    )
  }

  // Individual accounts need to upgrade to team account
  if (!isCompanyAccount) {
    return (
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-white">Team Management</h1>
          <p className="text-gray-400 mt-1">
            Collaborate with your team on meeting intelligence
          </p>
        </div>

        {/* Upgrade to Team Account Banner */}
        <div className="bg-premium-card border border-premium-border rounded-xl p-8 text-center">
          <div className="w-16 h-16 bg-blue-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <Building2 className="h-8 w-8 text-blue-400" />
          </div>
          <h2 className="text-xl font-semibold text-white mb-2">Individual Account</h2>
          <p className="text-gray-400 mb-6 max-w-md mx-auto">
            You're on an individual account. Upgrade to a Team account to invite members, share meeting insights, and collaborate with your team.
          </p>
          <button
            onClick={() => window.location.href = '/dashboard/settings/billing'}
            className="px-6 py-3 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-medium rounded-lg hover:shadow-gold transition-all"
          >
            Upgrade to Team Account
          </button>
        </div>

        {/* Feature List */}
        <div className="grid md:grid-cols-3 gap-4">
          <div className="bg-premium-card border border-premium-border rounded-xl p-5">
            <UserPlus className="h-8 w-8 text-gold-400 mb-3" />
            <h3 className="font-medium text-white mb-1">Invite Team Members</h3>
            <p className="text-gray-500 text-sm">
              Add up to 10 team members to collaborate on meetings
            </p>
          </div>
          <div className="bg-premium-card border border-premium-border rounded-xl p-5">
            <Building2 className="h-8 w-8 text-gold-400 mb-3" />
            <h3 className="font-medium text-white mb-1">Shared Library</h3>
            <p className="text-gray-500 text-sm">
              Access a shared library of team meeting recordings
            </p>
          </div>
          <div className="bg-premium-card border border-premium-border rounded-xl p-5">
            <Shield className="h-8 w-8 text-gold-400 mb-3" />
            <h3 className="font-medium text-white mb-1">Admin Controls</h3>
            <p className="text-gray-500 text-sm">
              Manage team permissions and billing centrally
            </p>
          </div>
        </div>
      </div>
    )
  }

  if (!isPremium) {
    return (
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-white">Team Management</h1>
          <p className="text-gray-400 mt-1">
            Collaborate with your team on meeting intelligence
          </p>
        </div>

        {/* Upgrade Banner */}
        <div className="bg-premium-card border border-premium-border rounded-xl p-8 text-center">
          <div className="w-16 h-16 bg-gold-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <Users className="h-8 w-8 text-gold-400" />
          </div>
          <h2 className="text-xl font-semibold text-white mb-2">Team Features</h2>
          <p className="text-gray-400 mb-6 max-w-md mx-auto">
            Upgrade to a Team plan to invite members, share meeting insights, and collaborate on action items.
          </p>
          <button
            onClick={() => window.location.href = '/dashboard/settings/billing'}
            className="px-6 py-3 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-medium rounded-lg hover:shadow-gold transition-all"
          >
            Upgrade to Team Plan
          </button>
        </div>

        {/* Feature List */}
        <div className="grid md:grid-cols-3 gap-4">
          <div className="bg-premium-card border border-premium-border rounded-xl p-5">
            <UserPlus className="h-8 w-8 text-gold-400 mb-3" />
            <h3 className="font-medium text-white mb-1">Invite Team Members</h3>
            <p className="text-gray-500 text-sm">
              Add up to 10 team members to collaborate on meetings
            </p>
          </div>
          <div className="bg-premium-card border border-premium-border rounded-xl p-5">
            <Building2 className="h-8 w-8 text-gold-400 mb-3" />
            <h3 className="font-medium text-white mb-1">Shared Library</h3>
            <p className="text-gray-500 text-sm">
              Access a shared library of team meeting recordings
            </p>
          </div>
          <div className="bg-premium-card border border-premium-border rounded-xl p-5">
            <Shield className="h-8 w-8 text-gold-400 mb-3" />
            <h3 className="font-medium text-white mb-1">Admin Controls</h3>
            <p className="text-gray-500 text-sm">
              Manage permissions and control team access
            </p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Team Management</h1>
          <p className="text-gray-400 mt-1">
            Manage your team members and permissions
          </p>
        </div>
        <button
          onClick={() => setShowInviteModal(true)}
          className="px-4 py-2 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-medium rounded-lg hover:shadow-gold transition-all flex items-center"
        >
          <UserPlus className="h-4 w-4 mr-2" />
          Invite Member
        </button>
      </div>

      {/* Team Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-premium-card border border-premium-border rounded-xl p-5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-gray-400 text-sm">Team Members</span>
            <Users className="h-5 w-5 text-gold-400" />
          </div>
          <p className="text-2xl font-bold text-white">
            {teamMembers.filter(m => m.status === 'active').length}
            <span className="text-gray-500 text-sm font-normal"> / 10</span>
          </p>
        </div>
        <div className="bg-premium-card border border-premium-border rounded-xl p-5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-gray-400 text-sm">Pending Invites</span>
            <Mail className="h-5 w-5 text-gold-400" />
          </div>
          <p className="text-2xl font-bold text-white">
            {teamMembers.filter(m => m.status === 'pending').length}
          </p>
        </div>
        <div className="bg-premium-card border border-premium-border rounded-xl p-5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-gray-400 text-sm">Total Meetings</span>
            <Crown className="h-5 w-5 text-gold-400" />
          </div>
          <p className="text-2xl font-bold text-white">24</p>
        </div>
      </div>

      {/* Team Members Table */}
      <div className="bg-premium-card border border-premium-border rounded-xl overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-premium-border bg-premium-surface/50">
              <th className="px-6 py-4 text-left text-sm font-medium text-gray-400">Member</th>
              <th className="px-6 py-4 text-left text-sm font-medium text-gray-400">Role</th>
              <th className="px-6 py-4 text-left text-sm font-medium text-gray-400">Status</th>
              <th className="px-6 py-4 text-left text-sm font-medium text-gray-400">Joined</th>
              <th className="px-6 py-4 w-12"></th>
            </tr>
          </thead>
          <tbody>
            {teamMembers.map((member) => (
              <tr key={member.id} className="border-b border-premium-border hover:bg-premium-surface/50 transition-colors">
                <td className="px-6 py-4">
                  <div className="flex items-center">
                    <div className="w-10 h-10 bg-gold-500/20 rounded-full flex items-center justify-center mr-3">
                      <span className="text-gold-400 font-medium">
                        {member.name[0]}
                      </span>
                    </div>
                    <div>
                      <p className="text-white font-medium">{member.name}</p>
                      <p className="text-gray-500 text-sm">{member.email}</p>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4">
                  {getRoleBadge(member.role)}
                </td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-1 text-xs rounded-full ${
                    member.status === 'active'
                      ? 'bg-emerald-500/20 text-emerald-400'
                      : 'bg-yellow-500/20 text-yellow-400'
                  }`}>
                    {member.status}
                  </span>
                </td>
                <td className="px-6 py-4 text-gray-400 text-sm">
                  {new Date(member.joinedAt).toLocaleDateString('en-US', {
                    month: 'short',
                    day: 'numeric',
                    year: 'numeric',
                  })}
                </td>
                <td className="px-6 py-4">
                  {member.role !== 'owner' && (
                    <button className="p-2 text-gray-500 hover:text-white hover:bg-premium-surface rounded transition-colors">
                      <MoreVertical className="h-4 w-4" />
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {teamMembers.length === 1 && (
          <div className="text-center py-12">
            <Users className="h-12 w-12 text-gray-600 mx-auto mb-3" />
            <p className="text-gray-400">No team members yet</p>
            <p className="text-gray-500 text-sm mt-1">
              Invite your first team member to get started
            </p>
          </div>
        )}
      </div>

      {/* Invite Modal */}
      {showInviteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="fixed inset-0 bg-black/50" onClick={() => setShowInviteModal(false)} />
          <div className="relative bg-premium-card border border-premium-border rounded-xl p-6 w-full max-w-md mx-4">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold text-white">Invite Team Member</h3>
              <button
                onClick={() => setShowInviteModal(false)}
                className="p-1 text-gray-500 hover:text-white transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleInvite} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-400 mb-2">
                  Email Address
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
                  <input
                    type="email"
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    className="w-full pl-10 pr-4 py-2.5 bg-premium-surface border border-premium-border rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-gold-500/50"
                    placeholder="colleague@company.com"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-400 mb-2">
                  Role
                </label>
                <select
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value as 'admin' | 'member')}
                  className="w-full px-4 py-2.5 bg-premium-surface border border-premium-border rounded-lg text-white focus:outline-none focus:border-gold-500/50 appearance-none"
                >
                  <option value="member">Member - Can view and create meetings</option>
                  <option value="admin">Admin - Full access and team management</option>
                </select>
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowInviteModal(false)}
                  className="flex-1 px-4 py-2.5 border border-premium-border text-white rounded-lg hover:bg-premium-surface transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isInviting || !inviteEmail}
                  className="flex-1 px-4 py-2.5 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-medium rounded-lg hover:shadow-gold transition-all disabled:opacity-50"
                >
                  {isInviting ? 'Sending...' : 'Send Invite'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
