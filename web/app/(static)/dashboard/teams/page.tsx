'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  Users,
  Plus,
  Trash2,
  UserPlus,
  ChevronRight,
  X
} from 'lucide-react'
import { useTeams, useTeamMembers } from '@/lib/hooks/useAdmin'
import { usePermissions } from '@/lib/hooks/usePermissions'
import { adminApi, SupportTeam, TeamMember } from '@/lib/api/admin'

function TeamCard({
  team,
  onSelect,
  isSelected
}: {
  team: SupportTeam
  onSelect: (team: SupportTeam) => void
  isSelected: boolean
}) {
  return (
    <button
      onClick={() => onSelect(team)}
      className={`w-full text-left p-4 rounded-xl border transition-colors ${
        isSelected
          ? 'bg-gold-500/10 border-gold-500/30'
          : 'bg-premium-card border-premium-border hover:border-gold-500/20'
      }`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div
            className="w-10 h-10 rounded-lg flex items-center justify-center"
            style={{ backgroundColor: `${team.color}20` }}
          >
            <Users className="h-5 w-5" style={{ color: team.color }} />
          </div>
          <div>
            <h3 className="font-medium text-white">{team.name}</h3>
            <p className="text-sm text-gray-500">{team.member_count} members</p>
          </div>
        </div>
        <ChevronRight className={`h-5 w-5 text-gray-500 transition-transform ${isSelected ? 'rotate-90' : ''}`} />
      </div>
      {team.description && (
        <p className="text-sm text-gray-400 mt-2 line-clamp-2">{team.description}</p>
      )}
      <div className="flex items-center space-x-2 mt-3">
        {team.accepts_tickets && (
          <span className="text-xs bg-blue-500/20 text-blue-400 px-2 py-0.5 rounded">Tickets</span>
        )}
        {team.accepts_chat && (
          <span className="text-xs bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded">Chat</span>
        )}
        {!team.is_active && (
          <span className="text-xs bg-red-500/20 text-red-400 px-2 py-0.5 rounded">Inactive</span>
        )}
      </div>
    </button>
  )
}

function MemberRow({
  member,
  onRemove,
  onRoleChange,
  canManage
}: {
  member: TeamMember
  onRemove: () => void
  onRoleChange: (role: string) => void
  canManage: boolean
}) {
  const [showRoleMenu, setShowRoleMenu] = useState(false)

  const roleColors = {
    admin: 'text-gold-400 bg-gold-500/20',
    manager: 'text-purple-400 bg-purple-500/20',
    agent: 'text-blue-400 bg-blue-500/20',
  }

  return (
    <div className="flex items-center justify-between py-3 border-b border-premium-border last:border-0">
      <div className="flex items-center space-x-3">
        <div className="w-8 h-8 bg-premium-surface rounded-full flex items-center justify-center">
          <span className="text-sm text-white font-medium">
            {(member.user_name || member.user_email || 'U')[0].toUpperCase()}
          </span>
        </div>
        <div>
          <p className="text-sm font-medium text-white">{member.user_name || 'Unnamed'}</p>
          <p className="text-xs text-gray-500">{member.user_email}</p>
        </div>
      </div>
      <div className="flex items-center space-x-2">
        <div className="relative">
          <button
            onClick={() => canManage && setShowRoleMenu(!showRoleMenu)}
            className={`text-xs px-2 py-1 rounded capitalize ${roleColors[member.role as keyof typeof roleColors] || 'text-gray-400 bg-gray-500/20'} ${canManage ? 'cursor-pointer' : 'cursor-default'}`}
          >
            {member.role}
          </button>
          {showRoleMenu && canManage && (
            <div className="absolute right-0 mt-1 bg-premium-card border border-premium-border rounded-lg shadow-lg z-10 min-w-[100px]">
              {['admin', 'manager', 'agent'].map((role) => (
                <button
                  key={role}
                  onClick={() => {
                    onRoleChange(role)
                    setShowRoleMenu(false)
                  }}
                  className="w-full text-left px-3 py-2 text-sm text-white hover:bg-premium-surface capitalize first:rounded-t-lg last:rounded-b-lg"
                >
                  {role}
                </button>
              ))}
            </div>
          )}
        </div>
        {canManage && (
          <button
            onClick={onRemove}
            className="p-1 text-gray-500 hover:text-red-400 transition-colors"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  )
}

function InviteModal({
  teamId,
  teamName,
  onClose,
  onInvited
}: {
  teamId: number
  teamName: string
  onClose: () => void
  onInvited: () => void
}) {
  const [email, setEmail] = useState('')
  const [role, setRole] = useState('agent')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError('')

    try {
      await adminApi.inviteTeamMember({ email, role, team_id: teamId })
      onInvited()
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send invitation')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-premium-card border border-premium-border rounded-xl p-6 w-full max-w-md mx-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white">Invite to {teamName}</h3>
          <button onClick={onClose} className="text-gray-500 hover:text-white">
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Email Address</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-2 bg-premium-surface border border-premium-border rounded-lg text-white focus:outline-none focus:border-gold-500"
              placeholder="Enter email address"
              required
            />
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1">Role</label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="w-full px-4 py-2 bg-premium-surface border border-premium-border rounded-lg text-white focus:outline-none focus:border-gold-500"
            >
              <option value="agent">Agent</option>
              <option value="manager">Manager</option>
              <option value="admin">Admin</option>
            </select>
          </div>

          {error && (
            <p className="text-red-400 text-sm">{error}</p>
          )}

          <div className="flex justify-end space-x-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-400 hover:text-white transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="px-4 py-2 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-medium rounded-lg hover:shadow-gold transition-all disabled:opacity-50"
            >
              {isLoading ? 'Sending...' : 'Send Invitation'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function CreateTeamModal({
  onClose,
  onCreated
}: {
  onClose: () => void
  onCreated: () => void
}) {
  const [name, setName] = useState('')
  const [slug, setSlug] = useState('')
  const [description, setDescription] = useState('')
  const [color, setColor] = useState('#3B82F6')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

  const handleNameChange = (value: string) => {
    setName(value)
    setSlug(value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, ''))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError('')

    try {
      await adminApi.createTeam({ name, slug, description, color })
      onCreated()
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create team')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-premium-card border border-premium-border rounded-xl p-6 w-full max-w-md mx-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white">Create Team</h3>
          <button onClick={onClose} className="text-gray-500 hover:text-white">
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Team Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => handleNameChange(e.target.value)}
              className="w-full px-4 py-2 bg-premium-surface border border-premium-border rounded-lg text-white focus:outline-none focus:border-gold-500"
              placeholder="e.g., Technical Support"
              required
            />
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1">Slug</label>
            <input
              type="text"
              value={slug}
              onChange={(e) => setSlug(e.target.value)}
              className="w-full px-4 py-2 bg-premium-surface border border-premium-border rounded-lg text-white focus:outline-none focus:border-gold-500"
              placeholder="e.g., tech-support"
              pattern="^[a-z0-9-]+$"
              required
            />
            <p className="text-xs text-gray-500 mt-1">Lowercase letters, numbers, and hyphens only</p>
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-4 py-2 bg-premium-surface border border-premium-border rounded-lg text-white focus:outline-none focus:border-gold-500"
              placeholder="What does this team do?"
              rows={2}
            />
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1">Color</label>
            <div className="flex items-center space-x-2">
              <input
                type="color"
                value={color}
                onChange={(e) => setColor(e.target.value)}
                className="w-10 h-10 rounded cursor-pointer"
              />
              <input
                type="text"
                value={color}
                onChange={(e) => setColor(e.target.value)}
                className="flex-1 px-4 py-2 bg-premium-surface border border-premium-border rounded-lg text-white focus:outline-none focus:border-gold-500"
                pattern="^#[0-9A-Fa-f]{6}$"
              />
            </div>
          </div>

          {error && (
            <p className="text-red-400 text-sm">{error}</p>
          )}

          <div className="flex justify-end space-x-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-400 hover:text-white transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="px-4 py-2 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-medium rounded-lg hover:shadow-gold transition-all disabled:opacity-50"
            >
              {isLoading ? 'Creating...' : 'Create Team'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function TeamsPage() {
  const router = useRouter()
  const { permissions } = usePermissions()
  const { teams, isLoading, refresh } = useTeams()
  const [selectedTeam, setSelectedTeam] = useState<SupportTeam | null>(null)
  const { members, refresh: refreshMembers } = useTeamMembers(selectedTeam?.id || 0)
  const [showInviteModal, setShowInviteModal] = useState(false)
  const [showCreateModal, setShowCreateModal] = useState(false)

  // Permission check - redirect if not allowed
  if (!permissions.canManageTeams && !permissions.isStaff) {
    if (typeof window !== 'undefined') {
      router.push('/dashboard')
    }
    return null
  }

  const handleRemoveMember = async (memberId: number) => {
    if (!selectedTeam || !permissions.canManageTeams) return
    if (!confirm('Are you sure you want to remove this member?')) return

    try {
      await adminApi.removeTeamMember(selectedTeam.id, memberId)
      refreshMembers()
      refresh()
    } catch (error) {
      console.error('Failed to remove member:', error)
    }
  }

  const handleRoleChange = async (memberId: number, role: string) => {
    if (!selectedTeam || !permissions.canManageTeams) return

    try {
      await adminApi.updateMemberRole(selectedTeam.id, memberId, role)
      refreshMembers()
    } catch (error) {
      console.error('Failed to update role:', error)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-gold-400"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Teams</h1>
          <p className="text-gray-400 mt-1">Manage support teams and members</p>
        </div>
        {permissions.canManageTeams && (
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center px-4 py-2 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-medium rounded-lg hover:shadow-gold transition-all"
          >
            <Plus className="h-4 w-4 mr-2" />
            Create Team
          </button>
        )}
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Teams List */}
        <div className="space-y-3">
          {teams.length > 0 ? (
            teams.map((team) => (
              <TeamCard
                key={team.id}
                team={team}
                onSelect={setSelectedTeam}
                isSelected={selectedTeam?.id === team.id}
              />
            ))
          ) : (
            <div className="bg-premium-card border border-premium-border rounded-xl p-8 text-center">
              <Users className="h-12 w-12 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-400">No teams yet</p>
              <p className="text-gray-500 text-sm mt-1">Create your first team to get started</p>
            </div>
          )}
        </div>

        {/* Team Details */}
        <div className="lg:col-span-2">
          {selectedTeam ? (
            <div className="bg-premium-card border border-premium-border rounded-xl p-6">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center space-x-3">
                  <div
                    className="w-12 h-12 rounded-lg flex items-center justify-center"
                    style={{ backgroundColor: `${selectedTeam.color}20` }}
                  >
                    <Users className="h-6 w-6" style={{ color: selectedTeam.color }} />
                  </div>
                  <div>
                    <h2 className="text-xl font-semibold text-white">{selectedTeam.name}</h2>
                    <p className="text-gray-500 text-sm">{selectedTeam.slug}</p>
                  </div>
                </div>
                {permissions.canManageTeams && (
                  <button
                    onClick={() => setShowInviteModal(true)}
                    className="flex items-center px-4 py-2 bg-premium-surface border border-premium-border rounded-lg text-white hover:bg-premium-surface/80 transition-colors"
                  >
                    <UserPlus className="h-4 w-4 mr-2" />
                    Invite Member
                  </button>
                )}
              </div>

              {selectedTeam.description && (
                <p className="text-gray-400 mb-6">{selectedTeam.description}</p>
              )}

              <div className="border-t border-premium-border pt-6">
                <h3 className="font-semibold text-white mb-4">
                  Members ({members.length})
                </h3>

                {members.length > 0 ? (
                  <div>
                    {members.map((member) => (
                      <MemberRow
                        key={member.id}
                        member={member}
                        onRemove={() => handleRemoveMember(member.id)}
                        onRoleChange={(role) => handleRoleChange(member.id, role)}
                        canManage={permissions.canManageTeams}
                      />
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <UserPlus className="h-12 w-12 text-gray-600 mx-auto mb-3" />
                    <p className="text-gray-400">No members yet</p>
                    <p className="text-gray-500 text-sm mt-1">Invite team members to get started</p>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="bg-premium-card border border-premium-border rounded-xl p-8 text-center h-full flex items-center justify-center">
              <div>
                <Users className="h-12 w-12 text-gray-600 mx-auto mb-3" />
                <p className="text-gray-400">Select a team to view details</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Modals */}
      {showInviteModal && selectedTeam && (
        <InviteModal
          teamId={selectedTeam.id}
          teamName={selectedTeam.name}
          onClose={() => setShowInviteModal(false)}
          onInvited={() => {
            refreshMembers()
            refresh()
          }}
        />
      )}

      {showCreateModal && (
        <CreateTeamModal
          onClose={() => setShowCreateModal(false)}
          onCreated={refresh}
        />
      )}
    </div>
  )
}
