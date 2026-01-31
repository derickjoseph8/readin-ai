'use client'

import Link from 'next/link'
import { Play, Download, ArrowRight, Shield, Zap, Check } from 'lucide-react'

export default function Hero() {
  return (
    <section className="relative pt-40 pb-24 px-4 overflow-hidden">
      {/* Background effects */}
      <div className="absolute inset-0 bg-gradient-to-b from-gold-500/5 via-transparent to-transparent" />
      <div className="absolute top-1/4 left-1/4 w-[500px] h-[500px] bg-gold-500/10 rounded-full blur-[100px] animate-pulse-gold" />
      <div className="absolute top-1/3 right-1/4 w-[400px] h-[400px] bg-emerald-500/10 rounded-full blur-[100px]" />

      <div className="relative max-w-7xl mx-auto">
        <div className="text-center max-w-4xl mx-auto">
          {/* Badge */}
          <div className="inline-flex items-center px-4 py-2 bg-gold-500/10 border border-gold-500/30 rounded-full mb-8 animate-fade-in">
            <span className="w-2 h-2 bg-emerald-400 rounded-full mr-2 animate-pulse" />
            <span className="text-sm text-gold-300">Works with Teams, Zoom, Meet & 30+ apps</span>
          </div>

          {/* Headline */}
          <h1 className="text-5xl md:text-7xl font-bold mb-6 leading-tight animate-fade-in-up">
            Never Get{' '}
            <span className="text-gradient-gold">Caught Off Guard</span>
            {' '}in Meetings Again
          </h1>

          {/* Subheadline */}
          <p className="text-xl md:text-2xl text-gray-400 mb-10 max-w-3xl mx-auto animate-fade-in-up" style={{ animationDelay: '0.1s' }}>
            AI-powered talking points in real-time. Glance, rephrase, and sound natural
            — like you always knew the answer.
          </p>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-12 animate-fade-in-up" style={{ animationDelay: '0.2s' }}>
            <Link
              href="/download"
              className="group flex items-center px-8 py-4 bg-gradient-to-r from-gold-600 via-gold-500 to-gold-600 text-premium-bg font-semibold rounded-xl hover:shadow-gold-lg transition-all duration-300 hover:-translate-y-1"
            >
              <Download className="mr-2 h-5 w-5" />
              Download for Free
              <ArrowRight className="ml-2 h-5 w-5 group-hover:translate-x-1 transition" />
            </Link>
            <a
              href="#how-it-works"
              className="flex items-center px-8 py-4 bg-premium-surface text-white font-semibold rounded-xl hover:bg-premium-card transition-all border border-premium-border hover:border-gold-500/30"
            >
              <Play className="mr-2 h-5 w-5 text-gold-400" />
              See How It Works
            </a>
          </div>

          {/* Trust indicators */}
          <div className="flex flex-wrap items-center justify-center gap-6 mb-16 animate-fade-in-up" style={{ animationDelay: '0.3s' }}>
            <div className="flex items-center text-sm text-gray-500">
              <Shield className="h-4 w-4 mr-1 text-emerald-500" />
              100% Private
            </div>
            <div className="flex items-center text-sm text-gray-500">
              <Zap className="h-4 w-4 mr-1 text-gold-500" />
              2-second responses
            </div>
            <div className="flex items-center text-sm text-gray-500">
              <Check className="h-4 w-4 mr-1 text-emerald-500" />
              No credit card required
            </div>
          </div>

          {/* App Preview */}
          <div className="relative max-w-2xl mx-auto animate-fade-in-up" style={{ animationDelay: '0.4s' }}>
            <div className="glass-gold rounded-2xl p-6 glow-gold">
              {/* Mock Overlay Window */}
              <div className="bg-premium-bg rounded-xl overflow-hidden border border-premium-border">
                {/* Header */}
                <div className="flex items-center justify-between px-4 py-3 border-b border-premium-border bg-premium-surface">
                  <div className="flex items-center space-x-2">
                    <div className="w-6 h-6 bg-gradient-to-br from-gold-400 to-gold-600 rounded flex items-center justify-center">
                      <span className="text-premium-bg font-bold text-xs">R</span>
                    </div>
                    <span className="text-sm font-medium text-gold-400">ReadIn AI</span>
                  </div>
                  <div className="flex space-x-2">
                    <div className="w-6 h-6 bg-premium-card rounded text-gray-400 text-xs flex items-center justify-center hover:bg-premium-border-light cursor-pointer">A+</div>
                    <div className="w-6 h-6 bg-premium-card rounded text-gray-400 text-xs flex items-center justify-center hover:bg-premium-border-light cursor-pointer">−</div>
                    <div className="w-6 h-6 bg-red-500/80 rounded text-white text-xs flex items-center justify-center hover:bg-red-500 cursor-pointer">×</div>
                  </div>
                </div>

                {/* Content */}
                <div className="p-4 space-y-4">
                  <div>
                    <p className="text-xs text-gray-500 uppercase tracking-wider mb-2 font-medium">They Asked:</p>
                    <div className="bg-premium-surface rounded-lg p-3 border border-premium-border">
                      <p className="text-gray-300 text-sm">"What's your view on AI regulation in the tech industry?"</p>
                    </div>
                  </div>

                  <div>
                    <p className="text-xs text-emerald-400 uppercase tracking-wider mb-2 font-medium">Your Answer:</p>
                    <div className="bg-premium-surface rounded-lg p-3 border-l-2 border-emerald-500 border-r border-t border-b border-premium-border">
                      <ul className="text-emerald-400 text-sm space-y-2">
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
            <div className="absolute -top-4 -right-4 w-20 h-20 bg-gradient-to-br from-gold-500 to-gold-600 rounded-xl opacity-20 blur-xl animate-float" />
            <div className="absolute -bottom-4 -left-4 w-20 h-20 bg-gradient-to-br from-emerald-500 to-emerald-600 rounded-xl opacity-20 blur-xl animate-float" style={{ animationDelay: '1s' }} />
          </div>

          {/* Social Proof */}
          <div className="mt-16 flex flex-col items-center animate-fade-in" style={{ animationDelay: '0.5s' }}>
            <p className="text-gray-600 text-sm mb-4">Trusted by professionals at</p>
            <div className="flex items-center space-x-8 opacity-40 hover:opacity-60 transition-opacity">
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
