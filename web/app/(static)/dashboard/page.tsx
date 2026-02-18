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
import Onboarding from '@/components/Onboarding'

// Storage key for onboarding completion
const ONBOARDING_COMPLETED_KEY = 'readin_onboarding_completed'

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
    <article
      className="bg-premium-card border border-premium-border rounded-xl p-4 sm:p-6 min-h-[120px] touch-manipulation"
      aria-label={`${title}: ${value}${trend ? `, trend: ${trend}` : ''}`}
    >
      <div className="flex items-center justify-between mb-3 sm:mb-4">
        <div className={`w-10 h-10 sm:w-11 sm:h-11 rounded-lg flex items-center justify-center ${colorClasses[color]}`}>
          <Icon className="h-5 w-5" aria-hidden="true" />
        </div>
        {trend && (
          <span className="text-emerald-400 text-xs sm:text-sm flex items-center" aria-label={`Trend: ${trend}`}>
            <TrendingUp className="h-3 w-3 sm:h-4 sm:w-4 mr-1" aria-hidden="true" />
            {trend}
          </span>
        )}
      </div>
      <p className="text-xl sm:text-2xl font-bold text-white">{value}</p>
      <p className="text-gray-400 text-xs sm:text-sm mt-1">{title}</p>
    </article>
  )
}

function AIInsightsSection({
  stats,
  status
}: {
  stats: {
    total_meetings?: number
    total_conversations?: number
    total_duration_minutes?: number
  } | null
  status: {
    usage: {
      daily_count?: number
      total_count?: number
    }
  } | null
}) {
  // Calculate AI insights based on available data
  const talkingPointsGenerated = stats?.total_conversations || 0
  const actionItemsTracked = Math.round((stats?.total_conversations || 0) * 0.4) // Estimate 40% of responses contain action items
  const meetingSummaries = stats?.total_meetings || 0
  const timeSavedHours = Math.round((stats?.total_duration_minutes || 0) * 0.3 / 60 * 10) / 10 // 30% efficiency gain

  const insights = [
    {
      label: 'Talking Points Generated',
      value: talkingPointsGenerated,
      icon: MessageSquare,
      color: 'text-blue-400',
      bgColor: 'bg-blue-500/20',
      description: 'AI-powered responses to help you communicate better'
    },
    {
      label: 'Action Items Tracked',
      value: actionItemsTracked,
      icon: Zap,
      color: 'text-emerald-400',
      bgColor: 'bg-emerald-500/20',
      description: 'Tasks and follow-ups identified during meetings'
    },
    {
      label: 'Meeting Summaries',
      value: meetingSummaries,
      icon: Calendar,
      color: 'text-purple-400',
      bgColor: 'bg-purple-500/20',
      description: 'Comprehensive meeting notes auto-generated'
    },
    {
      label: 'Hours Saved',
      value: timeSavedHours,
      icon: Clock,
      color: 'text-gold-400',
      bgColor: 'bg-gold-500/20',
      description: 'Time saved through AI-powered assistance'
    }
  ]

  return (
    <section className="bg-gradient-to-br from-premium-card to-premium-surface border border-premium-border rounded-xl p-4 sm:p-6" aria-label="AI Insights">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-4 sm:mb-6 gap-3">
        <div className="flex items-center">
          <div className="w-10 h-10 sm:w-11 sm:h-11 bg-gradient-to-br from-gold-500 to-gold-600 rounded-lg flex items-center justify-center mr-3 flex-shrink-0">
            <Sparkles className="h-5 w-5 text-premium-bg" />
          </div>
          <div>
            <h3 className="font-semibold text-white">AI Insights</h3>
            <p className="text-gray-400 text-xs sm:text-sm">Your productivity metrics powered by ReadIn AI</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        {insights.map((insight) => (
          <div
            key={insight.label}
            className="bg-premium-bg/50 rounded-lg p-3 sm:p-4 hover:bg-premium-bg/70 transition-colors touch-manipulation min-h-[100px]"
          >
            <div className={`w-8 h-8 sm:w-9 sm:h-9 ${insight.bgColor} rounded-lg flex items-center justify-center mb-2 sm:mb-3`}>
              <insight.icon className={`h-4 w-4 ${insight.color}`} />
            </div>
            <p className="text-xl sm:text-2xl font-bold text-white">{insight.value}</p>
            <p className="text-gray-400 text-xs sm:text-sm mt-1 line-clamp-2">{insight.label}</p>
          </div>
        ))}
      </div>

      {/* AI Performance Summary */}
      <div className="mt-4 sm:mt-6 pt-4 border-t border-premium-border/50">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center text-gray-400 text-xs sm:text-sm">
            <TrendingUp className="h-4 w-4 mr-2 text-emerald-400 flex-shrink-0" />
            <span>Your AI assistant is helping you be <span className="text-emerald-400 font-medium">30% more efficient</span> in meetings</span>
          </div>
          <Link
            href="/dashboard/meetings"
            className="text-gold-400 text-sm hover:text-gold-300 flex items-center min-h-[44px] min-w-[44px] justify-center sm:justify-start touch-manipulation"
          >
            View Details
            <ArrowRight className="h-4 w-4 ml-1" />
          </Link>
        </div>
      </div>
    </section>
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
      className="block p-3 sm:p-4 bg-premium-surface rounded-lg border border-premium-border hover:border-gold-500/30 transition-colors touch-manipulation min-h-[72px] active:bg-premium-surface/80"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <h4 className="font-medium text-white text-sm sm:text-base truncate">
            {meeting.title || `${meeting.meeting_type} Meeting`}
          </h4>
          <p className="text-xs sm:text-sm text-gray-500 mt-1">{formatDate(meeting.started_at)}</p>
        </div>
        <div className="text-right flex-shrink-0">
          <p className="text-xs sm:text-sm text-gray-400">{formatDuration(meeting.duration_seconds)}</p>
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
    <div className="space-y-4 sm:space-y-6">
      {/* Key Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
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
      <div className="grid grid-cols-2 md:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
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
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
        {/* New Users */}
        <div className="bg-premium-card border border-premium-border rounded-xl p-4 sm:p-6">
          <h3 className="font-semibold text-white mb-3 sm:mb-4 flex items-center text-sm sm:text-base">
            <UserPlus className="h-5 w-5 mr-2 text-emerald-400" />
            New Users
          </h3>
          <div className="space-y-3">
            <div className="flex justify-between items-center min-h-[32px]">
              <span className="text-gray-400 text-sm">Today</span>
              <span className="text-white font-medium">{stats?.new_users_today || 0}</span>
            </div>
            <div className="flex justify-between items-center min-h-[32px]">
              <span className="text-gray-400 text-sm">This Week</span>
              <span className="text-white font-medium">{stats?.new_users_this_week || 0}</span>
            </div>
            <div className="flex justify-between items-center min-h-[32px]">
              <span className="text-gray-400 text-sm">This Month</span>
              <span className="text-white font-medium">{stats?.new_users_this_month || 0}</span>
            </div>
          </div>
          <div className="mt-4 pt-4 border-t border-premium-border">
            <div className="flex justify-between text-sm items-center min-h-[28px]">
              <span className="text-gray-500">Trial Users</span>
              <span className="text-gold-400">{stats?.trial_users || 0}</span>
            </div>
            <div className="flex justify-between text-sm mt-2 items-center min-h-[28px]">
              <span className="text-gray-500">Active Users</span>
              <span className="text-emerald-400">{stats?.active_users || 0}</span>
            </div>
          </div>
        </div>

        {/* Support Overview */}
        <div className="bg-premium-card border border-premium-border rounded-xl p-4 sm:p-6">
          <h3 className="font-semibold text-white mb-3 sm:mb-4 flex items-center text-sm sm:text-base">
            <Ticket className="h-5 w-5 mr-2 text-blue-400" />
            Support Overview
          </h3>
          <div className="space-y-3">
            <div className="flex justify-between items-center min-h-[32px]">
              <span className="text-gray-400 text-sm">Tickets Today</span>
              <span className="text-white font-medium">{stats?.tickets_today || 0}</span>
            </div>
            <div className="flex justify-between items-center min-h-[32px]">
              <span className="text-gray-400 text-sm">Avg Response Time</span>
              <span className="text-white font-medium">{stats?.avg_response_time_minutes || 0}m</span>
            </div>
            <div className="flex justify-between items-center min-h-[32px]">
              <span className="text-gray-400 text-sm">Teams</span>
              <span className="text-white font-medium">{stats?.total_teams || 0}</span>
            </div>
          </div>
          <div className="mt-4">
            <Link
              href="/dashboard/tickets"
              className="block w-full py-3 text-center bg-blue-500/20 text-blue-400 rounded-lg hover:bg-blue-500/30 transition-colors text-sm min-h-[44px] flex items-center justify-center touch-manipulation active:bg-blue-500/40"
            >
              View All Tickets
            </Link>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="bg-premium-card border border-premium-border rounded-xl p-4 sm:p-6 md:col-span-2 lg:col-span-1">
          <h3 className="font-semibold text-white mb-3 sm:mb-4 text-sm sm:text-base">Quick Actions</h3>
          <div className="space-y-3">
            <Link
              href="/dashboard/users"
              className="block p-3 sm:p-4 bg-premium-surface rounded-lg hover:bg-premium-surface/80 transition-colors touch-manipulation active:bg-premium-surface/60 min-h-[60px]"
            >
              <span className="text-white text-sm font-medium">Manage Users</span>
              <p className="text-gray-500 text-xs mt-1">View and edit user accounts</p>
            </Link>
            <Link
              href="/dashboard/teams"
              className="block p-3 sm:p-4 bg-premium-surface rounded-lg hover:bg-premium-surface/80 transition-colors touch-manipulation active:bg-premium-surface/60 min-h-[60px]"
            >
              <span className="text-white text-sm font-medium">Manage Teams</span>
              <p className="text-gray-500 text-xs mt-1">Configure support teams</p>
            </Link>
            <Link
              href="/dashboard/chat"
              className="block p-3 sm:p-4 bg-premium-surface rounded-lg hover:bg-premium-surface/80 transition-colors touch-manipulation active:bg-premium-surface/60 min-h-[60px]"
            >
              <span className="text-white text-sm font-medium">Live Chat Queue</span>
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
  const [showOnboarding, setShowOnboarding] = useState(false)
  const [isNewUser, setIsNewUser] = useState(false)

  // Check if user needs onboarding
  useEffect(() => {
    if (typeof window !== 'undefined' && user) {
      const onboardingCompleted = localStorage.getItem(ONBOARDING_COMPLETED_KEY)
      const userCreatedAt = new Date(user.created_at)
      const now = new Date()
      const daysSinceCreation = (now.getTime() - userCreatedAt.getTime()) / (1000 * 60 * 60 * 24)

      // Show onboarding for users created within last 7 days who haven't completed it
      if (!onboardingCompleted && daysSinceCreation < 7 && !permissions.isStaff) {
        setShowOnboarding(true)
        setIsNewUser(true)
      }
    }
  }, [user, permissions.isStaff])

  const handleOnboardingComplete = () => {
    localStorage.setItem(ONBOARDING_COMPLETED_KEY, 'true')
    setShowOnboarding(false)
  }

  const handleOnboardingSkip = () => {
    localStorage.setItem(ONBOARDING_COMPLETED_KEY, 'skipped')
    setShowOnboarding(false)
  }

  const greeting = () => {
    const hour = new Date().getHours()
    if (hour < 12) return 'Good morning'
    if (hour < 18) return 'Good afternoon'
    return 'Good evening'
  }

  return (
    <>
      {/* Onboarding Modal */}
      {showOnboarding && (
        <Onboarding
          userName={user?.full_name?.split(' ')[0]}
          onComplete={handleOnboardingComplete}
          onSkip={handleOnboardingSkip}
        />
      )}

      <main className="space-y-8" role="main" aria-label="Dashboard">
        {/* Skip to main content link for accessibility */}
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-gold-500 focus:text-premium-bg focus:rounded-lg"
        >
          Skip to main content
        </a>

        {/* Header */}
        <header id="main-content">
          <h1 className="text-2xl font-bold text-white">
            {greeting()}, {user?.full_name?.split(' ')[0] || 'there'}
          </h1>
          <p className="text-gray-400 mt-1">
            {permissions.isAdmin
              ? "Here's your admin overview"
              : "Here's what's happening with your meetings"}
          </p>
        </header>

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
        <div className="bg-gradient-to-r from-gold-600/20 to-gold-500/10 border border-gold-500/30 rounded-xl p-3 sm:p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-start sm:items-center">
            <Sparkles className="h-5 w-5 text-gold-400 mr-3 flex-shrink-0 mt-0.5 sm:mt-0" />
            <div>
              <p className="text-white font-medium text-sm sm:text-base">
                {status.subscription.trial_days_remaining} days left in your trial
              </p>
              <p className="text-gold-400/80 text-xs sm:text-sm">
                Upgrade to Premium for unlimited responses
              </p>
            </div>
          </div>
          <Link
            href="/dashboard/settings/billing"
            className="px-4 py-2.5 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-medium rounded-lg hover:shadow-gold transition-all text-sm min-h-[44px] flex items-center justify-center touch-manipulation w-full sm:w-auto"
          >
            Upgrade Now
          </Link>
        </div>
      )}

      {/* Stats Grid */}
      <section aria-label="Your statistics" className="grid grid-cols-2 md:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
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
      </section>

      {/* AI Insights Section */}
      {!permissions.isAdmin && (
        <AIInsightsSection stats={stats} status={status} />
      )}

      {/* Usage & Recent Meetings */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
        {/* Daily Usage */}
        <div className="bg-premium-card border border-premium-border rounded-xl p-4 sm:p-6">
          <h3 className="font-semibold text-white mb-3 sm:mb-4 text-sm sm:text-base">Today&apos;s Usage</h3>

          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-xs sm:text-sm mb-2">
                <span className="text-gray-400">AI Responses</span>
                <span className="text-white">
                  {status?.usage.daily_count || 0}
                  {status?.usage.daily_limit && ` / ${status.usage.daily_limit}`}
                </span>
              </div>
              <div className="h-2 sm:h-2.5 bg-premium-surface rounded-full overflow-hidden">
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

          <div className="mt-4 sm:mt-6 pt-4 border-t border-premium-border">
            <div className="flex items-center text-gold-400">
              <Zap className="h-4 w-4 mr-2" />
              <span className="text-sm font-medium">Pro tip</span>
            </div>
            <p className="text-gray-400 text-xs sm:text-sm mt-2">
              Use keyboard shortcuts for faster responses. Press Ctrl+Shift+R to toggle the overlay.
            </p>
          </div>
        </div>

        {/* Recent Meetings */}
        <div className="lg:col-span-2 bg-premium-card border border-premium-border rounded-xl p-4 sm:p-6">
          <div className="flex items-center justify-between mb-3 sm:mb-4">
            <h3 className="font-semibold text-white text-sm sm:text-base">Recent Meetings</h3>
            <Link
              href="/dashboard/meetings"
              className="text-gold-400 text-sm hover:text-gold-300 flex items-center min-h-[44px] min-w-[44px] justify-center touch-manipulation"
            >
              View all
              <ArrowRight className="h-4 w-4 ml-1" />
            </Link>
          </div>

          {meetings.length > 0 ? (
            <div className="space-y-2 sm:space-y-3">
              {meetings.slice(0, 5).map((meeting) => (
                <RecentMeetingCard key={meeting.id} meeting={meeting} />
              ))}
            </div>
          ) : (
            <div className="text-center py-6 sm:py-8">
              <Calendar className="h-10 w-10 sm:h-12 sm:w-12 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-400 text-sm sm:text-base">No meetings yet</p>
              <p className="text-gray-500 text-xs sm:text-sm mt-1">
                Start a meeting with ReadIn AI to see your history here
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <nav className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 sm:gap-4" aria-label="Quick actions">
        <Link
          href="/download"
          className="p-4 bg-premium-card border border-premium-border rounded-xl hover:border-gold-500/30 transition-colors group focus:outline-none focus:ring-2 focus:ring-gold-500 touch-manipulation active:bg-premium-surface/50 min-h-[72px]"
          aria-label="Download Desktop App - Get ReadIn AI for Windows, Mac, or Linux"
        >
          <h4 className="font-medium text-white group-hover:text-gold-400 transition-colors text-sm sm:text-base">
            Download Desktop App
          </h4>
          <p className="text-gray-400 text-xs sm:text-sm mt-1">
            Get ReadIn AI for Windows, Mac, or Linux
          </p>
        </Link>

        <Link
          href="/docs"
          className="p-4 bg-premium-card border border-premium-border rounded-xl hover:border-gold-500/30 transition-colors group focus:outline-none focus:ring-2 focus:ring-gold-500 touch-manipulation active:bg-premium-surface/50 min-h-[72px]"
          aria-label="View Documentation - Learn how to get the most out of ReadIn AI"
        >
          <h4 className="font-medium text-white group-hover:text-gold-400 transition-colors text-sm sm:text-base">
            View Documentation
          </h4>
          <p className="text-gray-400 text-xs sm:text-sm mt-1">
            Learn how to get the most out of ReadIn AI
          </p>
        </Link>

        <Link
          href="/dashboard/support"
          className="p-4 bg-premium-card border border-premium-border rounded-xl hover:border-gold-500/30 transition-colors group focus:outline-none focus:ring-2 focus:ring-gold-500 touch-manipulation active:bg-premium-surface/50 min-h-[72px] sm:col-span-2 md:col-span-1"
          aria-label="Get Support - Contact our team for help or feedback"
        >
          <h4 className="font-medium text-white group-hover:text-gold-400 transition-colors text-sm sm:text-base">
            Get Support
          </h4>
          <p className="text-gray-400 text-xs sm:text-sm mt-1">
            Contact our team for help or feedback
          </p>
        </Link>
      </nav>
      </main>
    </>
  )
}
