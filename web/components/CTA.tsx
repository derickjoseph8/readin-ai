'use client'

import Link from 'next/link'
import { Download, Apple, Monitor } from 'lucide-react'

export default function CTA() {
  return (
    <section id="download" className="py-24 px-4 bg-gradient-to-b from-dark-900/50 to-dark-950">
      <div className="max-w-4xl mx-auto text-center">
        {/* Headline */}
        <h2 className="text-4xl md:text-5xl font-bold mb-6">
          Ready to{' '}
          <span className="text-gradient">Sound Brilliant</span>?
        </h2>
        <p className="text-xl text-gray-400 mb-10">
          Download ReadIn AI and never get caught off guard in a meeting again.
          Free for 7 days, no credit card required.
        </p>

        {/* Download Buttons */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-12">
          <Link
            href="/download"
            className="group flex items-center px-8 py-4 bg-gradient-to-r from-blue-600 to-cyan-500 text-white font-semibold rounded-xl hover:opacity-90 transition shadow-lg shadow-blue-500/25 w-full sm:w-auto justify-center"
          >
            <Monitor className="mr-3 h-5 w-5" />
            Download for Windows
          </Link>
          <Link
            href="/download"
            className="group flex items-center px-8 py-4 bg-white/10 text-white font-semibold rounded-xl hover:bg-white/20 transition border border-white/10 w-full sm:w-auto justify-center"
          >
            <Apple className="mr-3 h-5 w-5" />
            Download for Mac
          </Link>
        </div>

        {/* System Requirements */}
        <div className="flex flex-wrap items-center justify-center gap-6 text-sm text-gray-500">
          <span>Windows 10+ / macOS 11+ / Linux</span>
          <span className="hidden sm:inline">•</span>
          <span>~150MB download</span>
          <span className="hidden sm:inline">•</span>
          <span>No admin required</span>
        </div>

        {/* Trust Badges */}
        <div className="mt-16 pt-16 border-t border-white/10">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            <div className="text-center">
              <div className="text-3xl font-bold text-gradient mb-2">2s</div>
              <p className="text-gray-500 text-sm">Average response time</p>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-gradient mb-2">30+</div>
              <p className="text-gray-500 text-sm">Apps supported</p>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-gradient mb-2">100%</div>
              <p className="text-gray-500 text-sm">Local audio processing</p>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-gradient mb-2">24/7</div>
              <p className="text-gray-500 text-sm">Always ready</p>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
