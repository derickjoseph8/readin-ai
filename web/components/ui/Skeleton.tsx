'use client'

import React from 'react'

export function Skeleton({ className = '', style }: { className?: string; style?: React.CSSProperties }) {
  return (
    <div className={`animate-pulse bg-premium-surface rounded ${className}`} style={style} />
  )
}

export function SkeletonCard({ className = '' }: { className?: string }) {
  return (
    <div className={`bg-premium-card border border-premium-border rounded-xl p-6 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <Skeleton className="w-10 h-10 rounded-lg" />
      </div>
      <Skeleton className="h-8 w-24 mb-2" />
      <Skeleton className="h-4 w-32" />
    </div>
  )
}

export function SkeletonTable({ rows = 5 }: { rows?: number }) {
  return (
    <div className="bg-premium-card border border-premium-border rounded-xl overflow-hidden">
      {/* Header */}
      <div className="border-b border-premium-border bg-premium-surface/50 px-4 py-3 flex gap-4">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-4 w-20" />
        <Skeleton className="h-4 w-16" />
        <Skeleton className="h-4 w-20" />
      </div>

      {/* Rows */}
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="border-b border-premium-border px-4 py-4 flex items-center gap-4">
          <div className="flex-1">
            <Skeleton className="h-5 w-48 mb-2" />
            <Skeleton className="h-3 w-24" />
          </div>
          <div className="w-24">
            <Skeleton className="h-4 w-20 mb-1" />
            <Skeleton className="h-3 w-16" />
          </div>
          <div className="w-16">
            <Skeleton className="h-4 w-12" />
          </div>
          <div className="w-16">
            <Skeleton className="h-4 w-8" />
          </div>
          <Skeleton className="w-8 h-8 rounded" />
        </div>
      ))}
    </div>
  )
}

export function SkeletonChart({ className = '' }: { className?: string }) {
  return (
    <div className={`bg-premium-card border border-premium-border rounded-xl p-6 ${className}`}>
      <div className="flex items-center mb-6">
        <Skeleton className="w-5 h-5 rounded mr-2" />
        <Skeleton className="h-5 w-48" />
      </div>

      {/* Chart bars */}
      <div className="flex items-end justify-between h-40 gap-1">
        {Array.from({ length: 14 }).map((_, i) => (
          <Skeleton
            key={i}
            className="flex-1 rounded-t"
            style={{ height: `${Math.random() * 80 + 20}%` }}
          />
        ))}
      </div>

      {/* X-axis */}
      <div className="flex justify-between mt-4">
        <Skeleton className="h-3 w-16" />
        <Skeleton className="h-3 w-16" />
      </div>
    </div>
  )
}

export function MeetingsPageSkeleton() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Skeleton className="h-8 w-32 mb-2" />
        <Skeleton className="h-4 w-64" />
      </div>

      {/* Search */}
      <div className="flex items-center gap-4">
        <Skeleton className="h-10 w-full max-w-md rounded-lg" />
      </div>

      {/* Table */}
      <SkeletonTable rows={5} />
    </div>
  )
}

export function AnalyticsPageSkeleton() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Skeleton className="h-8 w-32 mb-2" />
        <Skeleton className="h-4 w-64" />
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>

      {/* Charts Row */}
      <div className="grid lg:grid-cols-2 gap-6">
        <SkeletonChart />
        <div className="bg-premium-card border border-premium-border rounded-xl p-6">
          <div className="flex items-center mb-6">
            <Skeleton className="w-5 h-5 rounded mr-2" />
            <Skeleton className="h-5 w-40" />
          </div>
          <div className="space-y-4">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i}>
                <div className="flex justify-between mb-1">
                  <Skeleton className="h-4 w-32" />
                  <Skeleton className="h-4 w-16" />
                </div>
                <Skeleton className="h-2 w-full rounded-full" />
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Bottom Row */}
      <div className="grid md:grid-cols-2 gap-6">
        {Array.from({ length: 2 }).map((_, i) => (
          <div key={i} className="bg-premium-card border border-premium-border rounded-xl p-6">
            <div className="flex items-center mb-4">
              <Skeleton className="w-5 h-5 rounded mr-2" />
              <Skeleton className="h-5 w-32" />
            </div>
            <div className="space-y-4">
              <Skeleton className="h-3 w-full rounded-full" />
              <Skeleton className="h-4 w-48" />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export function DashboardSkeleton() {
  return (
    <div className="space-y-6 sm:space-y-8">
      {/* Header */}
      <div>
        <Skeleton className="h-8 w-48 mb-2" />
        <Skeleton className="h-4 w-72" />
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>

      {/* AI Insights Section */}
      <div className="bg-premium-card border border-premium-border rounded-xl p-4 sm:p-6">
        <div className="flex items-center mb-4 sm:mb-6">
          <Skeleton className="w-10 h-10 sm:w-11 sm:h-11 rounded-lg mr-3" />
          <div>
            <Skeleton className="h-5 w-24 mb-2" />
            <Skeleton className="h-3 w-48" />
          </div>
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="bg-premium-bg/50 rounded-lg p-3 sm:p-4">
              <Skeleton className="w-8 h-8 sm:w-9 sm:h-9 rounded-lg mb-2 sm:mb-3" />
              <Skeleton className="h-6 w-12 mb-2" />
              <Skeleton className="h-3 w-20" />
            </div>
          ))}
        </div>
      </div>

      {/* Usage & Recent Meetings */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
        {/* Daily Usage */}
        <div className="bg-premium-card border border-premium-border rounded-xl p-4 sm:p-6">
          <Skeleton className="h-5 w-28 mb-4" />
          <div className="space-y-4">
            <div>
              <div className="flex justify-between mb-2">
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-4 w-16" />
              </div>
              <Skeleton className="h-2.5 w-full rounded-full" />
            </div>
            <Skeleton className="h-3 w-40" />
          </div>
          <div className="mt-6 pt-4 border-t border-premium-border">
            <div className="flex items-center">
              <Skeleton className="w-4 h-4 mr-2 rounded" />
              <Skeleton className="h-4 w-16" />
            </div>
            <Skeleton className="h-3 w-full mt-2" />
          </div>
        </div>

        {/* Recent Meetings */}
        <div className="lg:col-span-2 bg-premium-card border border-premium-border rounded-xl p-4 sm:p-6">
          <div className="flex items-center justify-between mb-4">
            <Skeleton className="h-5 w-32" />
            <Skeleton className="h-4 w-16" />
          </div>
          <div className="space-y-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="p-3 sm:p-4 bg-premium-surface rounded-lg">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <Skeleton className="h-5 w-48 mb-2" />
                    <Skeleton className="h-3 w-24" />
                  </div>
                  <div className="text-right">
                    <Skeleton className="h-4 w-16 mb-1" />
                    <Skeleton className="h-3 w-20" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 sm:gap-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="p-4 bg-premium-card border border-premium-border rounded-xl">
            <Skeleton className="h-5 w-40 mb-2" />
            <Skeleton className="h-4 w-56" />
          </div>
        ))}
      </div>
    </div>
  )
}

export function StatCardSkeleton() {
  return (
    <div className="bg-premium-card border border-premium-border rounded-xl p-4 sm:p-6 min-h-[120px]">
      <div className="flex items-center justify-between mb-3 sm:mb-4">
        <Skeleton className="w-10 h-10 sm:w-11 sm:h-11 rounded-lg" />
        <Skeleton className="h-4 w-12" />
      </div>
      <Skeleton className="h-7 w-16 mb-2" />
      <Skeleton className="h-4 w-24" />
    </div>
  )
}

export function RecentMeetingsSkeleton() {
  return (
    <div className="space-y-2 sm:space-y-3">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="p-3 sm:p-4 bg-premium-surface rounded-lg border border-premium-border">
          <div className="flex items-start justify-between gap-3">
            <div className="flex-1 min-w-0">
              <Skeleton className="h-5 w-48 mb-2" />
              <Skeleton className="h-3 w-24" />
            </div>
            <div className="text-right flex-shrink-0">
              <Skeleton className="h-4 w-16 mb-1" />
              <Skeleton className="h-3 w-20" />
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
