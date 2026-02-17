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
