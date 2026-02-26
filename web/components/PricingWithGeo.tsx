'use client'

import { useEffect, useState } from 'react'
import Pricing from './Pricing'
import GlobalPricing from './GlobalPricing'
import { detectRegion, type Region } from '@/lib/geo'

export default function PricingWithGeo() {
  const [region, setRegion] = useState<Region | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Auto-detect region based on IP
    detectRegion()
      .then((geoData) => {
        setRegion(geoData.region)
      })
      .catch(() => {
        setRegion('western') // Default to western pricing
      })
      .finally(() => {
        setLoading(false)
      })
  }, [])

  if (loading) {
    return (
      <section className="py-24 px-4 bg-premium-surface/50 min-h-[600px] flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-gold-500 mx-auto mb-4"></div>
          <p className="text-gray-400">Loading pricing...</p>
        </div>
      </section>
    )
  }

  // Show appropriate pricing based on detected region - no redirect, seamless experience
  return region === 'global' ? <GlobalPricing /> : <Pricing />
}
