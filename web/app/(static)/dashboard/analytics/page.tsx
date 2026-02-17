'use client'

import { useState, useEffect } from 'react'
import {
  BarChart3,
  TrendingUp,
  Clock,
  MessageSquare,
  Calendar,
  Zap,
  Star
} from 'lucide-react'
import { analyticsApi, AnalyticsDashboard, MeetingTrend } from '@/lib/api/analytics'
import { AnalyticsPageSkeleton } from '@/components/ui/Skeleton'

function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  color = 'gold'
}: {
  title: string
  value: string | number
  subtitle?: string
  icon: React.ElementType
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
      </div>
      <p className="text-2xl font-bold text-white">{value}</p>
      <p className="text-gray-500 text-sm mt-1">{title}</p>
      {subtitle && <p className="text-xs text-gray-600 mt-1">{subtitle}</p>}
    </div>
  )
}

function MeetingTrendsChart({ trends }: { trends: MeetingTrend[] }) {
  const maxCount = Math.max(...trends.map(t => t.count), 1)

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }

  return (
    <div className="bg-premium-card border border-premium-border rounded-xl p-6">
      <h3 className="font-semibold text-white mb-6 flex items-center">
        <TrendingUp className="h-5 w-5 text-gold-400 mr-2" />
        Meeting Activity (Last 30 Days)
      </h3>

      {trends.length > 0 ? (
        <div className="space-y-4">
          {/* Chart */}
          <div className="flex items-end justify-between h-40 gap-1">
            {trends.slice(-14).map((trend, i) => (
              <div key={i} className="flex-1 flex flex-col items-center">
                <div
                  className="w-full bg-gold-500/20 hover:bg-gold-500/40 rounded-t transition-colors relative group"
                  style={{ height: `${(trend.count / maxCount) * 100}%`, minHeight: trend.count > 0 ? '4px' : '0' }}
                >
                  {/* Tooltip */}
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-premium-surface border border-premium-border rounded text-xs text-white opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-10">
                    {trend.count} meetings
                    <br />
                    {trend.duration_minutes}m total
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* X-axis labels */}
          <div className="flex justify-between text-xs text-gray-500 px-1">
            <span>{formatDate(trends[trends.length - 14]?.date || trends[0]?.date)}</span>
            <span>{formatDate(trends[trends.length - 1]?.date)}</span>
          </div>
        </div>
      ) : (
        <div className="text-center py-12">
          <Calendar className="h-12 w-12 text-gray-600 mx-auto mb-3" />
          <p className="text-gray-500">No meeting data available</p>
        </div>
      )}
    </div>
  )
}

function TopicsChart({ topics }: { topics: { topic: string; count: number; percentage: number }[] }) {
  return (
    <div className="bg-premium-card border border-premium-border rounded-xl p-6">
      <h3 className="font-semibold text-white mb-6 flex items-center">
        <BarChart3 className="h-5 w-5 text-gold-400 mr-2" />
        Top Discussion Topics
      </h3>

      {topics.length > 0 ? (
        <div className="space-y-4">
          {topics.slice(0, 8).map((topic, i) => (
            <div key={i}>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-gray-300 truncate mr-4">{topic.topic}</span>
                <span className="text-gray-500">{topic.count} mentions</span>
              </div>
              <div className="h-2 bg-premium-surface rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-gold-600 to-gold-400 rounded-full transition-all"
                  style={{ width: `${topic.percentage}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-12">
          <MessageSquare className="h-12 w-12 text-gray-600 mx-auto mb-3" />
          <p className="text-gray-500">No topics analyzed yet</p>
        </div>
      )}
    </div>
  )
}

function UsageProgress({ usage, limit }: { usage: number; limit: number | null }) {
  const percentage = limit ? Math.min((usage / limit) * 100, 100) : 0
  const remaining = limit ? limit - usage : null

  return (
    <div className="bg-premium-card border border-premium-border rounded-xl p-6">
      <h3 className="font-semibold text-white mb-4 flex items-center">
        <Zap className="h-5 w-5 text-gold-400 mr-2" />
        Daily AI Usage
      </h3>

      <div className="mb-4">
        <div className="flex justify-between text-sm mb-2">
          <span className="text-gray-400">Responses Used</span>
          <span className="text-white font-medium">
            {usage}
            {limit && <span className="text-gray-500"> / {limit}</span>}
          </span>
        </div>
        <div className="h-3 bg-premium-surface rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${
              percentage > 90 ? 'bg-red-500' : percentage > 70 ? 'bg-yellow-500' : 'bg-gradient-to-r from-gold-600 to-gold-400'
            }`}
            style={{ width: limit ? `${percentage}%` : '0%' }}
          />
        </div>
      </div>

      {remaining !== null && (
        <p className="text-sm text-gray-500">
          {remaining > 0 ? `${remaining} responses remaining today` : 'Daily limit reached'}
        </p>
      )}

      {!limit && (
        <p className="text-sm text-emerald-400">Unlimited responses (Premium)</p>
      )}
    </div>
  )
}

function ResponseQuality({ average, total }: { average: number; total: number }) {
  const stars = Math.round(average)

  return (
    <div className="bg-premium-card border border-premium-border rounded-xl p-6">
      <h3 className="font-semibold text-white mb-4 flex items-center">
        <Star className="h-5 w-5 text-gold-400 mr-2" />
        Response Quality
      </h3>

      <div className="text-center">
        <div className="text-4xl font-bold text-white mb-2">
          {average.toFixed(1)}
          <span className="text-lg text-gray-500">/5</span>
        </div>

        <div className="flex justify-center gap-1 mb-3">
          {[1, 2, 3, 4, 5].map((star) => (
            <Star
              key={star}
              className={`h-5 w-5 ${star <= stars ? 'text-gold-400 fill-gold-400' : 'text-gray-600'}`}
            />
          ))}
        </div>

        <p className="text-sm text-gray-500">Based on {total} ratings</p>
      </div>
    </div>
  )
}

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsDashboard | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const dashboard = await analyticsApi.getDashboard()
        setData(dashboard)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load analytics')
      } finally {
        setIsLoading(false)
      }
    }
    fetchAnalytics()
  }, [])

  if (isLoading) {
    return <AnalyticsPageSkeleton />
  }

  if (error) {
    return (
      <div className="text-center py-20">
        <BarChart3 className="h-12 w-12 text-gray-600 mx-auto mb-3" />
        <p className="text-red-400">{error}</p>
        <p className="text-gray-500 text-sm mt-2">Unable to load analytics data</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Analytics</h1>
        <p className="text-gray-400 mt-1">
          Track your meeting activity and AI usage
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total AI Responses"
          value={data?.usage.total_usage || 0}
          icon={MessageSquare}
          color="gold"
        />
        <StatCard
          title="This Week"
          value={data?.usage.weekly_usage || 0}
          subtitle="AI responses generated"
          icon={TrendingUp}
          color="emerald"
        />
        <StatCard
          title="This Month"
          value={data?.usage.monthly_usage || 0}
          subtitle="AI responses generated"
          icon={Calendar}
          color="blue"
        />
        <StatCard
          title="Time Saved"
          value={`${data?.time_saved_minutes || 0}m`}
          subtitle="Estimated from AI assistance"
          icon={Clock}
          color="purple"
        />
      </div>

      {/* Charts Row */}
      <div className="grid lg:grid-cols-2 gap-6">
        <MeetingTrendsChart trends={data?.meeting_trends || []} />
        <TopicsChart topics={data?.top_topics || []} />
      </div>

      {/* Bottom Row */}
      <div className="grid md:grid-cols-2 gap-6">
        <UsageProgress
          usage={data?.usage.daily_usage || 0}
          limit={data?.usage.daily_limit || null}
        />
        <ResponseQuality
          average={data?.response_quality.average_rating || 0}
          total={data?.response_quality.total_ratings || 0}
        />
      </div>
    </div>
  )
}
