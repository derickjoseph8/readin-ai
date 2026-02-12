'use client';

import { useState } from 'react';
import { Users, UserPlus, Mail, MoreVertical, Shield, User, Eye, Trash2 } from 'lucide-react';
import { useTranslations } from 'next-intl';

interface TeamMember {
  id: number;
  name: string;
  email: string;
  role: 'admin' | 'member' | 'viewer';
  status: 'active' | 'pending';
  avatar?: string;
}

const mockMembers: TeamMember[] = [
  { id: 1, name: 'John Doe', email: 'john@example.com', role: 'admin', status: 'active' },
  { id: 2, name: 'Jane Smith', email: 'jane@example.com', role: 'member', status: 'active' },
  { id: 3, name: 'Bob Wilson', email: 'bob@example.com', role: 'viewer', status: 'pending' },
];

function RoleBadge({ role }: { role: string }) {
  const colors = {
    admin: 'bg-gold-500/20 text-gold-400',
    member: 'bg-blue-500/20 text-blue-400',
    viewer: 'bg-gray-500/20 text-gray-400',
  };

  return (
    <span className={`px-2 py-0.5 rounded-full text-xs ${colors[role as keyof typeof colors]}`}>
      {role.charAt(0).toUpperCase() + role.slice(1)}
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs ${
      status === 'active' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-yellow-500/20 text-yellow-400'
    }`}>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}

export default function TeamPage() {
  const [members, setMembers] = useState<TeamMember[]>(mockMembers);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState<'member' | 'viewer'>('member');
  const [showInvite, setShowInvite] = useState(false);
  const [menuOpen, setMenuOpen] = useState<number | null>(null);
  const t = useTranslations('team');

  const handleInvite = (e: React.FormEvent) => {
    e.preventDefault();
    const newMember: TeamMember = {
      id: Date.now(),
      name: inviteEmail.split('@')[0],
      email: inviteEmail,
      role: inviteRole,
      status: 'pending',
    };
    setMembers([...members, newMember]);
    setInviteEmail('');
    setShowInvite(false);
  };

  const handleRemove = (id: number) => {
    setMembers(members.filter(m => m.id !== id));
    setMenuOpen(null);
  };

  const handleRoleChange = (id: number, newRole: 'admin' | 'member' | 'viewer') => {
    setMembers(members.map(m => m.id === id ? { ...m, role: newRole } : m));
    setMenuOpen(null);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">{t('title')}</h1>
          <p className="text-gray-400 mt-1">{t('subtitle')}</p>
        </div>

        <button
          onClick={() => setShowInvite(true)}
          className="flex items-center px-4 py-2.5 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-semibold rounded-lg hover:shadow-gold transition-all"
        >
          <UserPlus className="h-5 w-5 mr-2" />
          {t('invite')}
        </button>
      </div>

      {/* Invite Modal */}
      {showInvite && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-premium-card border border-premium-border rounded-xl p-6 w-full max-w-md">
            <h2 className="text-lg font-semibold text-white mb-4">{t('invite')}</h2>

            <form onSubmit={handleInvite} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Email Address
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-500" />
                  <input
                    type="email"
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    className="w-full pl-10 pr-4 py-3 bg-premium-surface border border-premium-border rounded-lg focus:border-gold-500 focus:outline-none text-white"
                    placeholder="colleague@company.com"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  {t('role')}
                </label>
                <select
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value as 'member' | 'viewer')}
                  className="w-full px-4 py-3 bg-premium-surface border border-premium-border rounded-lg focus:border-gold-500 focus:outline-none text-white"
                >
                  <option value="member">{t('member')} - Can use AI features</option>
                  <option value="viewer">{t('viewer')} - View only access</option>
                </select>
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowInvite(false)}
                  className="flex-1 px-4 py-2.5 bg-premium-surface border border-premium-border rounded-lg text-gray-400 hover:text-white transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2.5 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-semibold rounded-lg hover:shadow-gold transition-all"
                >
                  Send Invite
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Members List */}
      <div className="bg-premium-card border border-premium-border rounded-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-premium-border">
          <h2 className="font-semibold text-white flex items-center">
            <Users className="h-5 w-5 text-gold-400 mr-2" />
            {t('members')} ({members.length})
          </h2>
        </div>

        <div className="divide-y divide-premium-border">
          {members.map((member) => (
            <div key={member.id} className="px-6 py-4 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 bg-gold-500/20 rounded-full flex items-center justify-center">
                  <span className="text-gold-400 font-medium">
                    {member.name.charAt(0).toUpperCase()}
                  </span>
                </div>
                <div>
                  <p className="font-medium text-white">{member.name}</p>
                  <p className="text-sm text-gray-500">{member.email}</p>
                </div>
              </div>

              <div className="flex items-center gap-4">
                <RoleBadge role={member.role} />
                <StatusBadge status={member.status} />

                <div className="relative">
                  <button
                    onClick={() => setMenuOpen(menuOpen === member.id ? null : member.id)}
                    className="p-2 text-gray-500 hover:text-white rounded-lg hover:bg-premium-surface transition-colors"
                  >
                    <MoreVertical className="h-5 w-5" />
                  </button>

                  {menuOpen === member.id && (
                    <div className="absolute right-0 mt-1 w-48 bg-premium-surface border border-premium-border rounded-lg shadow-lg py-1 z-10">
                      <button
                        onClick={() => handleRoleChange(member.id, 'admin')}
                        className="w-full px-4 py-2 text-left text-sm text-gray-300 hover:bg-premium-card flex items-center"
                      >
                        <Shield className="h-4 w-4 mr-2" />
                        Make {t('admin')}
                      </button>
                      <button
                        onClick={() => handleRoleChange(member.id, 'member')}
                        className="w-full px-4 py-2 text-left text-sm text-gray-300 hover:bg-premium-card flex items-center"
                      >
                        <User className="h-4 w-4 mr-2" />
                        Make {t('member')}
                      </button>
                      <button
                        onClick={() => handleRoleChange(member.id, 'viewer')}
                        className="w-full px-4 py-2 text-left text-sm text-gray-300 hover:bg-premium-card flex items-center"
                      >
                        <Eye className="h-4 w-4 mr-2" />
                        Make {t('viewer')}
                      </button>
                      <hr className="my-1 border-premium-border" />
                      <button
                        onClick={() => handleRemove(member.id)}
                        className="w-full px-4 py-2 text-left text-sm text-red-400 hover:bg-premium-card flex items-center"
                      >
                        <Trash2 className="h-4 w-4 mr-2" />
                        {t('remove')}
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
