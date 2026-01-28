'use client'

import Link from 'next/link'
import { Play, Download, ArrowRight } from 'lucide-react'

export default function Hero() {
  return (
    <section className="relative pt-32 pb-20 px-4 overflow-hidden">
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-b from-blue-600/20 via-transparent to-transparent" />
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-500/30 rounded-full blur-3xl" />
      <div className="absolute top-1/3 right-1/4 w-96 h-96 bg-cyan-500/20 rounded-full blur-3xl" />

      <div className="relative max-w-7xl mx-auto">
        <div className="text-center max-w-4xl mx-auto">
          {/* Badge */}
          <div className="inline-flex items-center px-4 py-2 bg-blue-500/10 border border-blue-500/20 rounded-full mb-8">
            <span className="w-2 h-2 bg-green-400 rounded-full mr-2 animate-pulse" />
            <span className="text-sm text-blue-300">Works with Teams, Zoom, Meet & 30+ apps</span>
          </div>

          {/* Headline */}
          <h1 className="text-5xl md:text-7xl font-bold mb-6 leading-tight">
            Never Get{' '}
            <span className="text-gradient">Caught Off Guard</span>
            {' '}in Meetings Again
          </h1>

          {/* Subheadline */}
          <p className="text-xl md:text-2xl text-gray-400 mb-10 max-w-3xl mx-auto">
            AI-powered talking points in real-time. Glance, rephrase, and sound natural
            — like you always knew the answer.
          </p>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16">
            <Link
              href="/download"
              className="group flex items-center px-8 py-4 bg-gradient-to-r from-blue-600 to-cyan-500 text-white font-semibold rounded-xl hover:opacity-90 transition shadow-lg shadow-blue-500/25"
            >
              <Download className="mr-2 h-5 w-5" />
              Download for Free
              <ArrowRight className="ml-2 h-5 w-5 group-hover:translate-x-1 transition" />
            </Link>
            <a
              href="#how-it-works"
              className="flex items-center px-8 py-4 bg-white/10 text-white font-semibold rounded-xl hover:bg-white/20 transition border border-white/10"
            >
              <Play className="mr-2 h-5 w-5" />
              See How It Works
            </a>
          </div>

          {/* App Preview */}
          <div className="relative max-w-2xl mx-auto">
            <div className="glass rounded-2xl p-6 shadow-2xl">
              {/* Mock Overlay Window */}
              <div className="bg-dark-900 rounded-xl overflow-hidden border border-white/10">
                {/* Header */}
                <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
                  <div className="flex items-center space-x-2">
                    <div className="w-6 h-6 bg-gradient-to-br from-blue-500 to-cyan-400 rounded flex items-center justify-center">
                      <span className="text-white font-bold text-xs">R</span>
                    </div>
                    <span className="text-sm font-medium text-blue-400">ReadIn AI</span>
                  </div>
                  <div className="flex space-x-2">
                    <div className="w-6 h-6 bg-dark-700 rounded text-gray-400 text-xs flex items-center justify-center">A+</div>
                    <div className="w-6 h-6 bg-dark-700 rounded text-gray-400 text-xs flex items-center justify-center">-</div>
                    <div className="w-6 h-6 bg-red-500/80 rounded text-white text-xs flex items-center justify-center">x</div>
                  </div>
                </div>

                {/* Content */}
                <div className="p-4 space-y-4">
                  <div>
                    <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">They Asked:</p>
                    <div className="bg-dark-800 rounded-lg p-3">
                      <p className="text-gray-300 text-sm">"What's your view on AI regulation in the tech industry?"</p>
                    </div>
                  </div>

                  <div>
                    <p className="text-xs text-green-400 uppercase tracking-wider mb-2">Your Answer:</p>
                    <div className="bg-dark-800 rounded-lg p-3 border-l-2 border-green-400">
                      <ul className="text-green-300 text-sm space-y-2">
                        <li>• Balance innovation with consumer safety</li>
                        <li>• Industry self-regulation as first step</li>
                        <li>• Government oversight for high-risk applications</li>
                        <li>• Transparency requirements are essential</li>
                      </ul>
                    </div>
                  </div>

                  <p className="text-xs text-gray-600 italic text-center">Glance & rephrase naturally — works with any meeting app</p>
                </div>
              </div>
            </div>

            {/* Decorative elements */}
            <div className="absolute -top-4 -right-4 w-20 h-20 bg-gradient-to-br from-blue-500 to-cyan-400 rounded-xl opacity-20 blur-xl" />
            <div className="absolute -bottom-4 -left-4 w-20 h-20 bg-gradient-to-br from-purple-500 to-pink-400 rounded-xl opacity-20 blur-xl" />
          </div>

          {/* Social Proof */}
          <div className="mt-16 flex flex-col items-center">
            <p className="text-gray-500 text-sm mb-4">Trusted by professionals at</p>
            <div className="flex items-center space-x-8 opacity-50">
              <span className="text-xl font-bold text-gray-400">Google</span>
              <span className="text-xl font-bold text-gray-400">Microsoft</span>
              <span className="text-xl font-bold text-gray-400">Amazon</span>
              <span className="text-xl font-bold text-gray-400">Meta</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
