'use client'

import Header from '@/components/Header'
import Footer from '@/components/Footer'
import Pricing from '@/components/Pricing'

export default function PricingPage() {
  return (
    <>
      <Header />
      <main className="pt-16 min-h-screen bg-premium-bg">
        <Pricing />
      </main>
      <Footer />
    </>
  )
}
