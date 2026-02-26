'use client'

import StaticHeader from '@/components/StaticHeader'
import Footer from '@/components/Footer'
import Pricing from '@/components/Pricing'

export default function PricingPage() {
  return (
    <>
      <StaticHeader />
      <main className="pt-16 min-h-screen bg-premium-bg">
        <Pricing />
      </main>
      <Footer />
    </>
  )
}
