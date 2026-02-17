'use client'

import { useState, useEffect } from 'react'
import {
  BarChart3,
  TrendingUp,
  Clock,
  MessageSquare,
  Calendar,
  Zap,
  Star,
  Download,
  CheckCircle2,
  AlertTriangle,
  Target,
  Activity
} from 'lucide-react'
import { analyticsApi, AnalyticsDashboard, MeetingTrend, TimeRange, DashboardOverview, ProductivityScore, HeatmapData } from '@/lib/api/analytics'
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

function ProductivityScoreCard({ score, components }: { score: number; components: { action_completion: number; meeting_efficiency: number; commitment_rate: number } }) {
  const getScoreColor = (value: number) => {
    if (value >= 80) return 'text-emerald-400'
    if (value >= 60) return 'text-gold-400'
    if (value >= 40) return 'text-yellow-400'
    return 'text-red-400'
  }

  const getProgressColor = (value: number) => {
    if (value >= 80) return 'from-emerald-600 to-emerald-400'
    if (value >= 60) return 'from-gold-600 to-gold-400'
    if (value >= 40) return 'from-yellow-600 to-yellow-400'
    return 'from-red-600 to-red-400'
  }

  return (
    <div className="bg-premium-card border border-premium-border rounded-xl p-6">
      <h3 className="font-semibold text-white mb-4 flex items-center">
        <Target className="h-5 w-5 text-gold-400 mr-2" />
        Productivity Score
      </h3>

      <div className="text-center mb-6">
        <div className={`text-5xl font-bold ${getScoreColor(score)}`}>
          {Math.round(score)}
        </div>
        <p className="text-gray-500 text-sm mt-1">out of 100</p>
      </div>

      <div className="space-y-4">
        <div>
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-400 flex items-center">
              <CheckCircle2 className="h-4 w-4 mr-1" />
              Action Completion
            </span>
            <span className="text-white">{Math.round(components.action_completion)}%</span>
          </div>
          <div className="h-2 bg-premium-surface rounded-full overflow-hidden">
            <div
              className={`h-full bg-gradient-to-r ${getProgressColor(components.action_completion)} rounded-full`}
              style={{ width: `${components.action_completion}%` }}
            />
          </div>
        </div>

        <div>
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-400 flex items-center">
              <Activity className="h-4 w-4 mr-1" />
              Meeting Efficiency
            </span>
            <span className="text-white">{Math.round(components.meeting_efficiency)}%</span>
          </div>
          <div className="h-2 bg-premium-surface rounded-full overflow-hidden">
            <div
              className={`h-full bg-gradient-to-r ${getProgressColor(components.meeting_efficiency)} rounded-full`}
              style={{ width: `${components.meeting_efficiency}%` }}
            />
          </div>
        </div>

        <div>
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-400 flex items-center">
              <AlertTriangle className="h-4 w-4 mr-1" />
              Commitment Rate
            </span>
            <span className="text-white">{Math.round(components.commitment_rate)}%</span>
          </div>
          <div className="h-2 bg-premium-surface rounded-full overflow-hidden">
            <div
              className={`h-full bg-gradient-to-r ${getProgressColor(components.commitment_rate)} rounded-full`}
              style={{ width: `${components.commitment_rate}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  )
}

function ActionItemsOverview({ stats }: { stats: { total_created: number; total_completed: number; completion_rate: number; overdue_count: number; by_status: Record<string, number> } }) {
  return (
    <div className="bg-premium-card border border-premium-border rounded-xl p-6">
      <h3 className="font-semibold text-white mb-4 flex items-center">
        <CheckCircle2 className="h-5 w-5 text-gold-400 mr-2" />
        Action Items
      </h3>

      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="text-center p-3 bg-premium-surface rounded-lg">
          <p className="text-2xl font-bold text-white">{stats.total_created}</p>
          <p className="text-xs text-gray-500">Created</p>
        </div>
        <div className="text-center p-3 bg-premium-surface rounded-lg">
          <p className="text-2xl font-bold text-emerald-400">{stats.total_completed}</p>
          <p className="text-xs text-gray-500">Completed</p>
        </div>
      </div>

      <div className="mb-4">
        <div className="flex justify-between text-sm mb-1">
          <span className="text-gray-400">Completion Rate</span>
          <span className="text-white">{stats.completion_rate.toFixed(1)}%</span>
        </div>
        <div className="h-3 bg-premium-surface rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-emerald-600 to-emerald-400 rounded-full"
            style={{ width: `${stats.completion_rate}%` }}
          />
        </div>
      </div>

      {stats.overdue_count > 0 && (
        <div className="flex items-center justify-between p-2 bg-red-500/10 border border-red-500/30 rounded-lg">
          <span className="text-red-400 text-sm flex items-center">
            <AlertTriangle className="h-4 w-4 mr-1" />
            Overdue
          </span>
          <span className="text-red-400 font-medium">{stats.overdue_count}</span>
        </div>
      )}
    </div>
  )
}

function TimeRangeSelector({ value, onChange }: { value: TimeRange; onChange: (v: TimeRange) => void }) {
  const options: { value: TimeRange; label: string }[] = [
    { value: 'week', label: 'Week' },
    { value: 'month', label: 'Month' },
    { value: 'quarter', label: 'Quarter' },
    { value: 'year', label: 'Year' },
  ]

  return (
    <div className="flex bg-premium-surface rounded-lg p-1">
      {options.map((option) => (
        <button
          key={option.value}
          onClick={() => onChange(option.value)}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            value === option.value
              ? 'bg-gold-500 text-premium-bg'
              : 'text-gray-400 hover:text-white'
          }`}
        >
          {option.label}
        </button>
      ))}
    </div>
  )
}

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsDashboard | null>(null)
  const [overview, setOverview] = useState<DashboardOverview | null>(null)
  const [productivity, setProductivity] = useState<ProductivityScore | null>(null)
  const [timeRange, setTimeRange] = useState<TimeRange>('month')
  const [isLoading, setIsLoading] = useState(true)
  const [isExporting, setIsExporting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchAnalytics()
  }, [timeRange])

  const fetchAnalytics = async () => {
    setIsLoading(true)
    try {
      const [dashboard, overviewData, productivityData] = await Promise.all([
        analyticsApi.getDashboard(),
        analyticsApi.getOverview(timeRange).catch(() => null),
        analyticsApi.getProductivityScore(timeRange).catch(() => null),
      ])
      setData(dashboard)
      setOverview(overviewData)
      setProductivity(productivityData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load analytics')
    } finally {
      setIsLoading(false)
    }
  }

  const handleExport = async (format: 'json' | 'csv') => {
    setIsExporting(true)
    try {
      const result = await analyticsApi.exportAnalytics(timeRange, format)
      if (format === 'csv' && result instanceof Blob) {
        const url = window.URL.createObjectURL(result)
        const a = document.createElement('a')
        a.href = url
        a.download = `analytics-${timeRange}.csv`
        a.click()
        window.URL.revokeObjectURL(url)
      } else {
        const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' })
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `analytics-${timeRange}.json`
        a.click()
        window.URL.revokeObjectURL(url)
      }
    } catch (err) {
      console.error('Export failed:', err)
    } finally {
      setIsExporting(false)
    }
  }

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
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Analytics</h1>
          <p className="text-gray-400 mt-1">
            Track your meeting activity and productivity
          </p>
        </div>

        <div className="flex items-center gap-3">
          <TimeRangeSelector value={timeRange} onChange={setTimeRange} />

          <div className="relative">
            <button
              onClick={() => handleExport('csv')}
              disabled={isExporting}
              className="px-4 py-2 bg-premium-surface border border-premium-border text-gray-300 rounded-lg hover:bg-premium-card transition-colors flex items-center text-sm"
            >
              <Download className="h-4 w-4 mr-2" />
              {isExporting ? 'Exporting...' : 'Export'}
            </button>
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Meetings"
          value={overview?.meetings.total_meetings || 0}
          icon={Calendar}
          color="gold"
        />
        <StatCard
          title="AI Responses"
          value={overview?.ai_usage.total_responses || data?.usage.total_usage || 0}
          subtitle={`${overview?.ai_usage.daily_average?.toFixed(1) || 0}/day avg`}
          icon={MessageSquare}
          color="emerald"
        />
        <StatCard
          title="Action Items"
          value={overview?.action_items.total_created || 0}
          subtitle={`${overview?.action_items.completion_rate?.toFixed(0) || 0}% completed`}
          icon={CheckCircle2}
          color="blue"
        />
        <StatCard
          title="Meeting Hours"
          value={`${Math.round((overview?.meetings.total_duration_minutes || 0) / 60)}h`}
          subtitle={`${overview?.meetings.avg_duration_minutes?.toFixed(0) || 0}m avg per meeting`}
          icon={Clock}
          color="purple"
        />
      </div>

      {/* Charts Row */}
      <div className="grid lg:grid-cols-2 gap-6">
        <MeetingTrendsChart trends={data?.meeting_trends || []} />
        <TopicsChart topics={data?.top_topics || []} />
      </div>

      {/* Productivity & Action Items Row */}
      <div className="grid lg:grid-cols-2 gap-6">
        {productivity && (
          <ProductivityScoreCard
            score={productivity.score}
            components={productivity.components}
          />
        )}
        {overview?.action_items && (
          <ActionItemsOverview stats={overview.action_items} />
        )}
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

      {/* Engagement Score */}
      {overview && (
        <div className="bg-premium-card border border-premium-border rounded-xl p-6">
          <h3 className="font-semibold text-white mb-4 flex items-center">
            <Activity className="h-5 w-5 text-gold-400 mr-2" />
            Engagement Score
          </h3>
          <div className="flex items-center gap-6">
            <div className="text-4xl font-bold text-gold-400">
              {Math.round(overview.engagement_score)}%
            </div>
            <div className="flex-1">
              <div className="h-4 bg-premium-surface rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-gold-600 to-gold-400 rounded-full transition-all"
                  style={{ width: `${overview.engagement_score}%` }}
                />
              </div>
              <p className="text-gray-500 text-sm mt-2">
                Based on your activity over the selected time period
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
