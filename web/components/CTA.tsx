'use client'

import Link from 'next/link'
import { Download, Apple, Monitor, ArrowRight, Sparkles, Shield, Zap } from 'lucide-react'

export default function CTA() {
  return (
    <section id="download" className="py-24 px-4 relative overflow-hidden">
      {/* Background effects */}
      <div className="absolute inset-0 bg-gradient-to-b from-premium-surface/50 via-premium-bg to-premium-bg" />
      <div className="absolute top-0 left-1/4 w-[600px] h-[600px] bg-gold-500/10 rounded-full blur-[120px]" />
      <div className="absolute bottom-0 right-1/4 w-[400px] h-[400px] bg-emerald-500/10 rounded-full blur-[100px]" />

      <div className="relative max-w-4xl mx-auto text-center">
        {/* Badge */}
        <div className="inline-flex items-center px-4 py-2 bg-gold-500/10 border border-gold-500/30 rounded-full mb-8">
          <Sparkles className="h-4 w-4 text-gold-400 mr-2" />
          <span className="text-sm text-gold-300">14-day free trial • No credit card required</span>
        </div>

        {/* Headline */}
        <h2 className="text-4xl md:text-6xl font-bold mb-6">
          Ready to{' '}
          <span className="text-gradient-gold">Sound Brilliant</span>?
        </h2>
        <p className="text-xl text-gray-400 mb-10 max-w-2xl mx-auto">
          Download ReadIn AI and never get caught off guard in a meeting again.
          Join thousands of professionals who communicate with confidence.
        </p>

        {/* Download Buttons */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-12">
          <Link
            href="/download"
            className="group flex items-center px-8 py-4 bg-gradient-to-r from-gold-600 via-gold-500 to-gold-600 text-premium-bg font-semibold rounded-xl hover:shadow-gold-lg transition-all duration-300 hover:-translate-y-1 w-full sm:w-auto justify-center"
          >
            <Monitor className="mr-3 h-5 w-5" />
            Download for Windows
            <ArrowRight className="ml-2 h-5 w-5 group-hover:translate-x-1 transition" />
          </Link>
          <Link
            href="/download"
            className="group flex items-center px-8 py-4 bg-premium-surface text-white font-semibold rounded-xl hover:bg-premium-card transition-all duration-300 border border-premium-border hover:border-gold-500/30 w-full sm:w-auto justify-center"
          >
            <Apple className="mr-3 h-5 w-5" />
            Download for Mac
          </Link>
        </div>

        {/* System Requirements */}
        <div className="flex flex-wrap items-center justify-center gap-6 text-sm text-gray-500 mb-16">
          <span>Windows 10+ / macOS 11+ / Linux</span>
          <span className="hidden sm:inline text-premium-border">•</span>
          <span>~150MB download</span>
          <span className="hidden sm:inline text-premium-border">•</span>
          <span>No admin required</span>
        </div>

        {/* Stats */}
        <div className="glass-gold rounded-2xl p-8 glow-gold">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            <div className="text-center">
              <div className="text-4xl font-bold text-gradient-gold mb-2">2s</div>
              <p className="text-gray-400 text-sm">Average response time</p>
            </div>
            <div className="text-center">
              <div className="text-4xl font-bold text-gradient-gold mb-2">30+</div>
              <p className="text-gray-400 text-sm">Apps supported</p>
            </div>
            <div className="text-center">
              <div className="text-4xl font-bold text-gradient-gold mb-2">100%</div>
              <p className="text-gray-400 text-sm">Local audio processing</p>
            </div>
            <div className="text-center">
              <div className="text-4xl font-bold text-gradient-gold mb-2">24/7</div>
              <p className="text-gray-400 text-sm">Always ready</p>
            </div>
          </div>
        </div>

        {/* Trust indicators */}
        <div className="mt-12 flex flex-wrap items-center justify-center gap-8">
          <div className="flex items-center text-sm text-gray-500">
            <Shield className="h-5 w-5 mr-2 text-emerald-500" />
            100% Private & Secure
          </div>
          <div className="flex items-center text-sm text-gray-500">
            <Zap className="h-5 w-5 mr-2 text-gold-500" />
            Works with any meeting app
          </div>
        </div>
      </div>
    </section>
  )
}
