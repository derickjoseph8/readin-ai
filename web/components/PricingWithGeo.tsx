'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Pricing from './Pricing'
import GlobalPricing from './GlobalPricing'
import { detectRegion, type Region } from '@/lib/geo'

export default function PricingWithGeo() {
  const router = useRouter()
  const [region, setRegion] = useState<Region | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Check if user explicitly chose a region (stored in localStorage)
    const storedRegion = localStorage.getItem('pricing_region')
    if (storedRegion === 'global' || storedRegion === 'western') {
      setRegion(storedRegion)
      setLoading(false)
      return
    }

    // Auto-detect region
    detectRegion()
      .then((geoData) => {
        setRegion(geoData.region)
        // Optionally redirect to /global for Africa/UAE/Asia users
        if (geoData.region === 'global') {
          router.replace('/global')
        }
      })
      .catch(() => {
        setRegion('western') // Default to western pricing
      })
      .finally(() => {
        setLoading(false)
      })
  }, [router])

  if (loading) {
    return (
      <section className="py-24 px-4 bg-premium-surface/50 min-h-[600px] flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-gold-500 mx-auto mb-4"></div>
          <p className="text-gray-400">Loading pricing for your region...</p>
        </div>
      </section>
    )
  }

  // Show appropriate pricing based on region
  return region === 'global' ? <GlobalPricing /> : <Pricing />
}
