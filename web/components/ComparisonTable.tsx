'use client'

import { Check, X, Sparkles } from 'lucide-react'
import Link from 'next/link'

const features = [
  { name: 'AI-powered responses', free: true, premium: true },
  { name: 'Real-time transcription', free: true, premium: true },
  { name: 'All video conferencing apps', free: true, premium: true },
  { name: 'Floating overlay UI', free: true, premium: true },
  { name: 'Context-aware responses', free: true, premium: true },
  { name: 'Responses per day', free: '10', premium: 'Unlimited' },
  { name: 'Custom AI prompts', free: false, premium: true },
  { name: 'Multi-language support', free: false, premium: true },
  { name: 'Conversation export', free: false, premium: true },
  { name: 'Priority support', free: false, premium: true },
  { name: 'Early access to features', free: false, premium: true },
]

export default function ComparisonTable() {
  return (
    <section className="py-24 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Section Header */}
        <div className="text-center mb-16">
          <h2 className="text-4xl md:text-5xl font-bold mb-6">
            Compare{' '}
            <span className="text-gradient-gold">Plans</span>
          </h2>
          <p className="text-xl text-gray-400">
            See exactly what you get with each plan.
          </p>
        </div>

        {/* Comparison Table */}
        <div className="bg-premium-card rounded-2xl border border-premium-border overflow-hidden">
          {/* Header */}
          <div className="grid grid-cols-3 border-b border-premium-border">
            <div className="p-6 bg-premium-surface">
              <span className="text-gray-400 font-medium">Features</span>
            </div>
            <div className="p-6 text-center bg-premium-surface border-x border-premium-border">
              <span className="text-white font-semibold">Free Trial</span>
              <p className="text-sm text-gray-500 mt-1">14 days</p>
            </div>
            <div className="p-6 text-center bg-gradient-to-b from-gold-500/10 to-transparent">
              <div className="flex items-center justify-center">
                <Sparkles className="h-4 w-4 text-gold-400 mr-2" />
                <span className="text-gold-400 font-semibold">Premium</span>
              </div>
              <p className="text-sm text-gray-500 mt-1">$19.99/month</p>
            </div>
          </div>

          {/* Features */}
          {features.map((feature, index) => (
            <div
              key={index}
              className={`grid grid-cols-3 ${
                index !== features.length - 1 ? 'border-b border-premium-border' : ''
              }`}
            >
              <div className="p-4 flex items-center">
                <span className="text-gray-300 text-sm">{feature.name}</span>
              </div>
              <div className="p-4 flex items-center justify-center border-x border-premium-border">
                {typeof feature.free === 'boolean' ? (
                  feature.free ? (
                    <Check className="h-5 w-5 text-emerald-400" />
                  ) : (
                    <X className="h-5 w-5 text-gray-600" />
                  )
                ) : (
                  <span className="text-gray-400 text-sm">{feature.free}</span>
                )}
              </div>
              <div className="p-4 flex items-center justify-center bg-gold-500/5">
                {typeof feature.premium === 'boolean' ? (
                  feature.premium ? (
                    <Check className="h-5 w-5 text-gold-400" />
                  ) : (
                    <X className="h-5 w-5 text-gray-600" />
                  )
                ) : (
                  <span className="text-gold-400 text-sm font-medium">{feature.premium}</span>
                )}
              </div>
            </div>
          ))}

          {/* CTA Row */}
          <div className="grid grid-cols-3 border-t border-premium-border bg-premium-surface">
            <div className="p-6"></div>
            <div className="p-6 flex items-center justify-center border-x border-premium-border">
              <Link
                href="/download"
                className="px-6 py-2.5 bg-premium-border text-white text-sm font-medium rounded-lg hover:bg-premium-border-light transition-colors"
              >
                Start Free
              </Link>
            </div>
            <div className="p-6 flex items-center justify-center">
              <Link
                href="/download"
                className="px-6 py-2.5 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg text-sm font-semibold rounded-lg hover:shadow-gold transition-all"
              >
                Get Premium
              </Link>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
