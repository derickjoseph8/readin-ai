'use client'

import StaticHeader from '@/components/StaticHeader'
import Footer from '@/components/Footer'
import GlobalPricing from '@/components/GlobalPricing'

export default function GlobalPricingPage() {
  return (
    <>
      <StaticHeader />
      <main className="pt-16 min-h-screen bg-premium-bg">
        <GlobalPricing />
      </main>
      <Footer />
    </>
  )
}
