'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import {
  Calendar,
  Clock,
  MessageSquare,
  TrendingUp,
  Zap,
  ArrowRight,
  Sparkles,
  Users,
  DollarSign,
  Ticket,
  UserPlus,
  Activity,
  AlertTriangle
} from 'lucide-react'
import { useAuth } from '@/lib/hooks/useAuth'
import { usePermissions } from '@/lib/hooks/usePermissions'
import { useMeetings, useMeetingStats } from '@/lib/hooks/useMeetings'
import { useAdminStats, useAdminTrends } from '@/lib/hooks/useAdmin'

function StatCard({
  title,
  value,
  icon: Icon,
  trend,
  color = 'gold'
}: {
  title: string
  value: string | number
  icon: React.ElementType
  trend?: string
  color?: 'gold' | 'emerald' | 'blue' | 'purple'
}) {
  const colorClasses = {
    gold: 'bg-gold-500/20 text-gold-400',
    emerald: 'bg-emerald-500/20 text-emerald-400',
    blue: 'bg-blue-500/20 text-blue-400',
    purple: 'bg-purple-500/20 text-purple-400',
  }

  return (
    <div className="bg-premium-card border border-premium-border rounded-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${colorClasses[color]}`}>
          <Icon className="h-5 w-5" />
        </div>
        {trend && (
          <span className="text-emerald-400 text-sm flex items-center">
            <TrendingUp className="h-4 w-4 mr-1" />
            {trend}
          </span>
        )}
      </div>
      <p className="text-2xl font-bold text-white">{value}</p>
      <p className="text-gray-500 text-sm mt-1">{title}</p>
    </div>
  )
}

function RecentMeetingCard({
  meeting
}: {
  meeting: {
    id: number
    title: string | null
    meeting_type: string
    started_at: string
    duration_seconds: number | null
    conversation_count: number
  }
}) {
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }

  const formatDuration = (seconds: number | null) => {
    if (!seconds) return '—'
    const mins = Math.floor(seconds / 60)
    return `${mins} min`
  }

  return (
    <Link
      href={`/dashboard/meetings/${meeting.id}`}
      className="block p-4 bg-premium-surface rounded-lg border border-premium-border hover:border-gold-500/30 transition-colors"
    >
      <div className="flex items-start justify-between">
        <div>
          <h4 className="font-medium text-white">
            {meeting.title || `${meeting.meeting_type} Meeting`}
          </h4>
          <p className="text-sm text-gray-500 mt-1">{formatDate(meeting.started_at)}</p>
        </div>
        <div className="text-right">
          <p className="text-sm text-gray-400">{formatDuration(meeting.duration_seconds)}</p>
          <p className="text-xs text-gray-500 mt-1">
            {meeting.conversation_count} responses
          </p>
        </div>
      </div>
    </Link>
  )
}

// Admin Stats Section Component
function AdminDashboard() {
  const { stats, isLoading } = useAdminStats()
  const { trends } = useAdminTrends('daily', 7)

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-32">
        <div className="animate-spin rounded-full h-6 w-6 border-t-2 border-b-2 border-gold-400"></div>
      </div>
    )
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0 }).format(amount)
  }

  return (
    <div className="space-y-6">
      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Users"
          value={stats?.total_users || 0}
          icon={Users}
          color="blue"
        />
        <StatCard
          title="Paying Customers"
          value={stats?.paying_users || 0}
          icon={DollarSign}
          trend={`${stats?.new_users_this_week || 0} this week`}
          color="emerald"
        />
        <StatCard
          title="Monthly Revenue"
          value={formatCurrency(stats?.total_revenue_this_month || 0)}
          icon={TrendingUp}
          color="gold"
        />
        <StatCard
          title="MRR"
          value={formatCurrency(stats?.mrr || 0)}
          icon={Activity}
          color="purple"
        />
      </div>

      {/* Support & Operations */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Open Tickets"
          value={stats?.open_tickets || 0}
          icon={Ticket}
          color="blue"
        />
        <StatCard
          title="Active Chats"
          value={stats?.active_chats || 0}
          icon={MessageSquare}
          trend={`${stats?.waiting_chats || 0} waiting`}
          color="emerald"
        />
        <StatCard
          title="Online Agents"
          value={`${stats?.online_agents || 0}/${stats?.total_agents || 0}`}
          icon={Users}
          color="gold"
        />
        <StatCard
          title="SLA Breach Rate"
          value={`${((stats?.sla_breach_rate || 0) * 100).toFixed(1)}%`}
          icon={AlertTriangle}
          color={stats?.sla_breach_rate && stats.sla_breach_rate > 0.1 ? 'purple' : 'emerald'}
        />
      </div>

      {/* Recent Activity Grid */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* New Users */}
        <div className="bg-premium-card border border-premium-border rounded-xl p-6">
          <h3 className="font-semibold text-white mb-4 flex items-center">
            <UserPlus className="h-5 w-5 mr-2 text-emerald-400" />
            New Users
          </h3>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-gray-400">Today</span>
              <span className="text-white font-medium">{stats?.new_users_today || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">This Week</span>
              <span className="text-white font-medium">{stats?.new_users_this_week || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">This Month</span>
              <span className="text-white font-medium">{stats?.new_users_this_month || 0}</span>
            </div>
          </div>
          <div className="mt-4 pt-4 border-t border-premium-border">
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Trial Users</span>
              <span className="text-gold-400">{stats?.trial_users || 0}</span>
            </div>
            <div className="flex justify-between text-sm mt-2">
              <span className="text-gray-500">Active Users</span>
              <span className="text-emerald-400">{stats?.active_users || 0}</span>
            </div>
          </div>
        </div>

        {/* Support Overview */}
        <div className="bg-premium-card border border-premium-border rounded-xl p-6">
          <h3 className="font-semibold text-white mb-4 flex items-center">
            <Ticket className="h-5 w-5 mr-2 text-blue-400" />
            Support Overview
          </h3>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-gray-400">Tickets Today</span>
              <span className="text-white font-medium">{stats?.tickets_today || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Avg Response Time</span>
              <span className="text-white font-medium">{stats?.avg_response_time_minutes || 0}m</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Teams</span>
              <span className="text-white font-medium">{stats?.total_teams || 0}</span>
            </div>
          </div>
          <div className="mt-4">
            <Link
              href="/dashboard/tickets"
              className="block w-full py-2 text-center bg-blue-500/20 text-blue-400 rounded-lg hover:bg-blue-500/30 transition-colors text-sm"
            >
              View All Tickets
            </Link>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="bg-premium-card border border-premium-border rounded-xl p-6">
          <h3 className="font-semibold text-white mb-4">Quick Actions</h3>
          <div className="space-y-3">
            <Link
              href="/dashboard/users"
              className="block p-3 bg-premium-surface rounded-lg hover:bg-premium-surface/80 transition-colors"
            >
              <span className="text-white text-sm">Manage Users</span>
              <p className="text-gray-500 text-xs mt-1">View and edit user accounts</p>
            </Link>
            <Link
              href="/dashboard/teams"
              className="block p-3 bg-premium-surface rounded-lg hover:bg-premium-surface/80 transition-colors"
            >
              <span className="text-white text-sm">Manage Teams</span>
              <p className="text-gray-500 text-xs mt-1">Configure support teams</p>
            </Link>
            <Link
              href="/dashboard/chat"
              className="block p-3 bg-premium-surface rounded-lg hover:bg-premium-surface/80 transition-colors"
            >
              <span className="text-white text-sm">Live Chat Queue</span>
              <p className="text-gray-500 text-xs mt-1">{stats?.waiting_chats || 0} customers waiting</p>
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function DashboardPage() {
  const { user, status } = useAuth()
  const { permissions } = usePermissions()
  const { meetings } = useMeetings(1, 5)
  const { stats } = useMeetingStats()

  const greeting = () => {
    const hour = new Date().getHours()
    if (hour < 12) return 'Good morning'
    if (hour < 18) return 'Good afternoon'
    return 'Good evening'
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">
          {greeting()}, {user?.full_name?.split(' ')[0] || 'there'}
        </h1>
        <p className="text-gray-400 mt-1">
          {permissions.isAdmin
            ? "Here's your admin overview"
            : "Here's what's happening with your meetings"}
        </p>
      </div>

      {/* Admin Dashboard for staff */}
      {permissions.isAdmin && <AdminDashboard />}

      {/* Divider for admins */}
      {permissions.isAdmin && (
        <div className="border-t border-premium-border pt-8">
          <h2 className="text-lg font-semibold text-white mb-4">Your Personal Stats</h2>
        </div>
      )}

      {/* Subscription Banner */}
      {status?.subscription.status === 'trial' && (
        <div className="bg-gradient-to-r from-gold-600/20 to-gold-500/10 border border-gold-500/30 rounded-xl p-4 flex items-center justify-between">
          <div className="flex items-center">
            <Sparkles className="h-5 w-5 text-gold-400 mr-3" />
            <div>
              <p className="text-white font-medium">
                {status.subscription.trial_days_remaining} days left in your trial
              </p>
              <p className="text-gold-400/80 text-sm">
                Upgrade to Premium for unlimited responses
              </p>
            </div>
          </div>
          <Link
            href="/dashboard/settings/billing"
            className="px-4 py-2 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-medium rounded-lg hover:shadow-gold transition-all text-sm"
          >
            Upgrade Now
          </Link>
        </div>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Meetings"
          value={stats?.total_meetings || 0}
          icon={Calendar}
          color="gold"
        />
        <StatCard
          title="This Week"
          value={stats?.meetings_this_week || 0}
          icon={TrendingUp}
          trend="+12%"
          color="emerald"
        />
        <StatCard
          title="AI Responses"
          value={stats?.total_conversations || 0}
          icon={MessageSquare}
          color="blue"
        />
        <StatCard
          title="Time Saved"
          value={`${Math.round((stats?.total_duration_minutes || 0) * 0.3)}m`}
          icon={Clock}
          color="purple"
        />
      </div>

      {/* Usage & Recent Meetings */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Daily Usage */}
        <div className="bg-premium-card border border-premium-border rounded-xl p-6">
          <h3 className="font-semibold text-white mb-4">Today&apos;s Usage</h3>

          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span className="text-gray-400">AI Responses</span>
                <span className="text-white">
                  {status?.usage.daily_count || 0}
                  {status?.usage.daily_limit && ` / ${status.usage.daily_limit}`}
                </span>
              </div>
              <div className="h-2 bg-premium-surface rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-gold-600 to-gold-400 rounded-full transition-all"
                  style={{
                    width: `${Math.min(
                      ((status?.usage.daily_count || 0) /
                        (status?.usage.daily_limit || 100)) *
                        100,
                      100
                    )}%`,
                  }}
                />
              </div>
            </div>

            {status?.usage.daily_limit && (
              <p className="text-xs text-gray-500">
                {status.usage.daily_limit - (status.usage.daily_count || 0)} responses remaining today
              </p>
            )}
          </div>

          <div className="mt-6 pt-4 border-t border-premium-border">
            <div className="flex items-center text-gold-400">
              <Zap className="h-4 w-4 mr-2" />
              <span className="text-sm font-medium">Pro tip</span>
            </div>
            <p className="text-gray-400 text-sm mt-2">
              Use keyboard shortcuts for faster responses. Press Ctrl+Shift+R to toggle the overlay.
            </p>
          </div>
        </div>

        {/* Recent Meetings */}
        <div className="lg:col-span-2 bg-premium-card border border-premium-border rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-white">Recent Meetings</h3>
            <Link
              href="/dashboard/meetings"
              className="text-gold-400 text-sm hover:text-gold-300 flex items-center"
            >
              View all
              <ArrowRight className="h-4 w-4 ml-1" />
            </Link>
          </div>

          {meetings.length > 0 ? (
            <div className="space-y-3">
              {meetings.slice(0, 5).map((meeting) => (
                <RecentMeetingCard key={meeting.id} meeting={meeting} />
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <Calendar className="h-12 w-12 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-400">No meetings yet</p>
              <p className="text-gray-500 text-sm mt-1">
                Start a meeting with ReadIn AI to see your history here
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid md:grid-cols-3 gap-4">
        <Link
          href="/download"
          className="p-4 bg-premium-card border border-premium-border rounded-xl hover:border-gold-500/30 transition-colors group"
        >
          <h4 className="font-medium text-white group-hover:text-gold-400 transition-colors">
            Download Desktop App
          </h4>
          <p className="text-gray-500 text-sm mt-1">
            Get ReadIn AI for Windows, Mac, or Linux
          </p>
        </Link>

        <Link
          href="/docs"
          className="p-4 bg-premium-card border border-premium-border rounded-xl hover:border-gold-500/30 transition-colors group"
        >
          <h4 className="font-medium text-white group-hover:text-gold-400 transition-colors">
            View Documentation
          </h4>
          <p className="text-gray-500 text-sm mt-1">
            Learn how to get the most out of ReadIn AI
          </p>
        </Link>

        <Link
          href="/contact"
          className="p-4 bg-premium-card border border-premium-border rounded-xl hover:border-gold-500/30 transition-colors group"
        >
          <h4 className="font-medium text-white group-hover:text-gold-400 transition-colors">
            Get Support
          </h4>
          <p className="text-gray-500 text-sm mt-1">
            Contact our team for help or feedback
          </p>
        </Link>
      </div>
    </div>
  )
}
