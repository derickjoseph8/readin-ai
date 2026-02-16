'use client'

import { useState } from 'react'
import Link from 'next/link'
import {
  Users,
  CreditCard,
  Ticket,
  MessageSquare,
  TrendingUp,
  TrendingDown,
  Clock,
  AlertTriangle,
  ArrowRight,
  RefreshCw,
  CheckCircle,
  XCircle,
  UserPlus
} from 'lucide-react'
import { useAdminStats, useAdminTrends, useActivityLog } from '@/lib/hooks/useAdmin'
import { adminApi } from '@/lib/api/admin'

function StatCard({
  title,
  value,
  icon: Icon,
  trend,
  trendUp,
  color = 'gold',
  href
}: {
  title: string
  value: string | number
  icon: React.ElementType
  trend?: string
  trendUp?: boolean
  color?: 'gold' | 'emerald' | 'blue' | 'purple' | 'red'
  href?: string
}) {
  const colorClasses = {
    gold: 'bg-gold-500/20 text-gold-400',
    emerald: 'bg-emerald-500/20 text-emerald-400',
    blue: 'bg-blue-500/20 text-blue-400',
    purple: 'bg-purple-500/20 text-purple-400',
    red: 'bg-red-500/20 text-red-400',
  }

  const content = (
    <div className="bg-premium-card border border-premium-border rounded-xl p-6 hover:border-premium-border/80 transition-colors">
      <div className="flex items-center justify-between mb-4">
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${colorClasses[color]}`}>
          <Icon className="h-5 w-5" />
        </div>
        {trend && (
          <span className={`text-sm flex items-center ${trendUp ? 'text-emerald-400' : 'text-red-400'}`}>
            {trendUp ? <TrendingUp className="h-4 w-4 mr-1" /> : <TrendingDown className="h-4 w-4 mr-1" />}
            {trend}
          </span>
        )}
      </div>
      <p className="text-2xl font-bold text-white">{value}</p>
      <p className="text-gray-500 text-sm mt-1">{title}</p>
    </div>
  )

  if (href) {
    return <Link href={href}>{content}</Link>
  }
  return content
}

function ActivityItem({ log }: { log: { action: string; entity_type: string | null; created_at: string; user_name: string | null } }) {
  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    return `${diffDays}d ago`
  }

  const getActionIcon = (action: string) => {
    if (action.includes('create')) return <UserPlus className="h-4 w-4 text-emerald-400" />
    if (action.includes('update')) return <RefreshCw className="h-4 w-4 text-blue-400" />
    if (action.includes('delete') || action.includes('remove')) return <XCircle className="h-4 w-4 text-red-400" />
    return <CheckCircle className="h-4 w-4 text-gold-400" />
  }

  const formatAction = (action: string) => {
    return action.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
  }

  return (
    <div className="flex items-start space-x-3 py-3 border-b border-premium-border last:border-0">
      <div className="mt-0.5">{getActionIcon(log.action)}</div>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-white">
          <span className="font-medium">{log.user_name || 'System'}</span>
          {' '}
          <span className="text-gray-400">{formatAction(log.action)}</span>
          {log.entity_type && (
            <span className="text-gray-500"> on {log.entity_type}</span>
          )}
        </p>
        <p className="text-xs text-gray-500 mt-0.5">{formatTime(log.created_at)}</p>
      </div>
    </div>
  )
}

export default function AdminDashboardPage() {
  const { stats, isLoading: statsLoading, refresh: refreshStats } = useAdminStats()
  const { trends } = useAdminTrends('daily', 7)
  const { logs } = useActivityLog(10)
  const [seeding, setSeeding] = useState(false)

  const handleSeedData = async () => {
    setSeeding(true)
    try {
      await adminApi.seedTeams()
      await adminApi.seedSLA()
      refreshStats()
    } catch (error) {
      console.error('Failed to seed data:', error)
    } finally {
      setSeeding(false)
    }
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
    }).format(amount)
  }

  if (statsLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-gold-400"></div>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Admin Dashboard</h1>
          <p className="text-gray-400 mt-1">Overview of your platform</p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={handleSeedData}
            disabled={seeding}
            className="px-4 py-2 text-sm text-gray-400 hover:text-white border border-premium-border rounded-lg hover:bg-premium-surface transition-colors disabled:opacity-50"
          >
            {seeding ? 'Setting up...' : 'Setup Default Data'}
          </button>
          <button
            onClick={() => refreshStats()}
            className="p-2 text-gray-400 hover:text-white border border-premium-border rounded-lg hover:bg-premium-surface transition-colors"
          >
            <RefreshCw className="h-5 w-5" />
          </button>
        </div>
      </div>

      {/* Stats Grid - Users */}
      <div>
        <h2 className="text-lg font-semibold text-white mb-4">Users</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            title="Total Users"
            value={stats?.total_users || 0}
            icon={Users}
            color="gold"
            href="/admin/users"
          />
          <StatCard
            title="Active Users (30d)"
            value={stats?.active_users || 0}
            icon={Users}
            color="emerald"
          />
          <StatCard
            title="Trial Users"
            value={stats?.trial_users || 0}
            icon={Clock}
            color="blue"
          />
          <StatCard
            title="Paying Users"
            value={stats?.paying_users || 0}
            icon={CreditCard}
            color="purple"
          />
        </div>
      </div>

      {/* Stats Grid - Revenue */}
      <div>
        <h2 className="text-lg font-semibold text-white mb-4">Revenue</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <StatCard
            title="Revenue This Month"
            value={formatCurrency(stats?.total_revenue_this_month || 0)}
            icon={CreditCard}
            color="emerald"
          />
          <StatCard
            title="MRR"
            value={formatCurrency(stats?.mrr || 0)}
            icon={TrendingUp}
            color="gold"
          />
          <StatCard
            title="New Users Today"
            value={stats?.new_users_today || 0}
            icon={UserPlus}
            trend={`${stats?.new_users_this_week || 0} this week`}
            trendUp={true}
            color="blue"
          />
        </div>
      </div>

      {/* Stats Grid - Support */}
      <div>
        <h2 className="text-lg font-semibold text-white mb-4">Support</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            title="Open Tickets"
            value={stats?.open_tickets || 0}
            icon={Ticket}
            color={stats?.open_tickets && stats.open_tickets > 10 ? 'red' : 'gold'}
            href="/admin/tickets"
          />
          <StatCard
            title="Tickets Today"
            value={stats?.tickets_today || 0}
            icon={Ticket}
            color="blue"
            href="/admin/tickets"
          />
          <StatCard
            title="Avg Response Time"
            value={`${Math.round(stats?.avg_response_time_minutes || 0)}m`}
            icon={Clock}
            color={stats?.avg_response_time_minutes && stats.avg_response_time_minutes > 60 ? 'red' : 'emerald'}
          />
          <StatCard
            title="SLA Breach Rate"
            value={`${(stats?.sla_breach_rate || 0).toFixed(1)}%`}
            icon={AlertTriangle}
            color={stats?.sla_breach_rate && stats.sla_breach_rate > 10 ? 'red' : 'emerald'}
          />
        </div>
      </div>

      {/* Live Chat & Teams */}
      <div className="grid lg:grid-cols-2 gap-4">
        <StatCard
          title="Active Chats"
          value={stats?.active_chats || 0}
          icon={MessageSquare}
          color="emerald"
          href="/admin/chat"
        />
        <StatCard
          title="Waiting in Queue"
          value={stats?.waiting_chats || 0}
          icon={Clock}
          color={stats?.waiting_chats && stats.waiting_chats > 5 ? 'red' : 'blue'}
          href="/admin/chat"
        />
      </div>

      {/* Teams & Agents */}
      <div>
        <h2 className="text-lg font-semibold text-white mb-4">Teams</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <StatCard
            title="Total Teams"
            value={stats?.total_teams || 0}
            icon={Users}
            color="gold"
            href="/admin/teams"
          />
          <StatCard
            title="Online Agents"
            value={stats?.online_agents || 0}
            icon={Users}
            color="emerald"
          />
          <StatCard
            title="Total Agents"
            value={stats?.total_agents || 0}
            icon={Users}
            color="blue"
            href="/admin/teams"
          />
        </div>
      </div>

      {/* Recent Activity & Quick Actions */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Recent Activity */}
        <div className="lg:col-span-2 bg-premium-card border border-premium-border rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-white">Recent Activity</h3>
            <Link href="/admin/activity" className="text-gold-400 text-sm hover:text-gold-300 flex items-center">
              View all
              <ArrowRight className="h-4 w-4 ml-1" />
            </Link>
          </div>
          <div className="divide-y divide-premium-border">
            {logs.length > 0 ? (
              logs.map((log) => (
                <ActivityItem key={log.id} log={log} />
              ))
            ) : (
              <p className="text-gray-500 text-sm py-4 text-center">No recent activity</p>
            )}
          </div>
        </div>

        {/* Quick Actions */}
        <div className="bg-premium-card border border-premium-border rounded-xl p-6">
          <h3 className="font-semibold text-white mb-4">Quick Actions</h3>
          <div className="space-y-3">
            <Link
              href="/admin/teams"
              className="flex items-center p-3 bg-premium-surface rounded-lg hover:bg-premium-surface/80 transition-colors group"
            >
              <Users className="h-5 w-5 text-gold-400 mr-3" />
              <span className="text-white group-hover:text-gold-400 transition-colors">Manage Teams</span>
            </Link>
            <Link
              href="/admin/tickets?status=open"
              className="flex items-center p-3 bg-premium-surface rounded-lg hover:bg-premium-surface/80 transition-colors group"
            >
              <Ticket className="h-5 w-5 text-blue-400 mr-3" />
              <span className="text-white group-hover:text-blue-400 transition-colors">View Open Tickets</span>
            </Link>
            <Link
              href="/admin/chat"
              className="flex items-center p-3 bg-premium-surface rounded-lg hover:bg-premium-surface/80 transition-colors group"
            >
              <MessageSquare className="h-5 w-5 text-emerald-400 mr-3" />
              <span className="text-white group-hover:text-emerald-400 transition-colors">Chat Queue</span>
            </Link>
            <Link
              href="/admin/users?is_staff=true"
              className="flex items-center p-3 bg-premium-surface rounded-lg hover:bg-premium-surface/80 transition-colors group"
            >
              <UserPlus className="h-5 w-5 text-purple-400 mr-3" />
              <span className="text-white group-hover:text-purple-400 transition-colors">View Staff</span>
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
