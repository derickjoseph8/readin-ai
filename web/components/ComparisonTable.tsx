'use client'

import { useState } from 'react'
import { Check, X, Sparkles, Users, Building2 } from 'lucide-react'
import Link from 'next/link'

const individualFeatures = [
  { name: 'AI-powered responses', free: true, premium: true },
  { name: 'Real-time transcription', free: true, premium: true },
  { name: 'All video conferencing apps', free: true, premium: true },
  { name: 'Floating overlay UI', free: true, premium: true },
  { name: 'Profession-tailored responses', free: true, premium: true },
  { name: 'Responses per day', free: '10', premium: 'Unlimited' },
  { name: 'Smart meeting notes & summaries', free: false, premium: true },
  { name: 'Action item tracking', free: false, premium: true },
  { name: 'Pre-meeting briefings', free: false, premium: true },
  { name: 'Participant memory', free: false, premium: true },
  { name: 'Priority support', free: false, premium: true },
]

const businessFeatures = [
  { name: 'Everything in Premium', team: true, growth: true, enterprise: true },
  { name: 'Team members included', team: '5-10', growth: '11-50', enterprise: 'Unlimited' },
  { name: 'Minimum seats required', team: '5 seats', growth: 'No minimum', enterprise: 'Custom' },
  { name: 'Price per user/month', team: '$19.99', growth: '$14.99', enterprise: 'Custom' },
  { name: 'Annual pricing (2 mo free)', team: '$199.90/user', growth: '$149.90/user', enterprise: 'Custom' },
  { name: 'Admin dashboard', team: true, growth: true, enterprise: true },
  { name: 'Centralized billing', team: true, growth: true, enterprise: true },
  { name: 'Shared meeting insights', team: true, growth: true, enterprise: true },
  { name: 'Usage analytics', team: false, growth: true, enterprise: true },
  { name: 'Custom profession profiles', team: false, growth: true, enterprise: true },
  { name: 'SAML SSO', team: false, growth: true, enterprise: true },
  { name: 'On-premise deployment', team: false, growth: false, enterprise: true },
  { name: 'SLA & compliance support', team: false, growth: false, enterprise: true },
  { name: 'Dedicated success team', team: false, growth: false, enterprise: true },
]

export default function ComparisonTable() {
  const [activeTab, setActiveTab] = useState<'individual' | 'business'>('individual')

  return (
    <section className="py-24 px-4">
      <div className="max-w-5xl mx-auto">
        {/* Section Header */}
        <div className="text-center mb-12">
          <h2 className="text-4xl md:text-5xl font-bold mb-6">
            Compare{' '}
            <span className="text-gradient-gold">Plans</span>
          </h2>
          <p className="text-xl text-gray-400 mb-8">
            See exactly what you get with each plan.
          </p>

          {/* Tab Switcher */}
          <div className="inline-flex items-center p-1 bg-premium-surface rounded-xl border border-premium-border">
            <button
              onClick={() => setActiveTab('individual')}
              className={`flex items-center px-6 py-3 rounded-lg font-medium transition-all duration-300 ${
                activeTab === 'individual'
                  ? 'bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              <Users className="h-4 w-4 mr-2" />
              Individual
            </button>
            <button
              onClick={() => setActiveTab('business')}
              className={`flex items-center px-6 py-3 rounded-lg font-medium transition-all duration-300 ${
                activeTab === 'business'
                  ? 'bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              <Building2 className="h-4 w-4 mr-2" />
              Teams & Business
            </button>
          </div>
        </div>

        {/* Individual Plans Table */}
        {activeTab === 'individual' && (
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
                <p className="text-sm text-gray-500 mt-1">$29.99/month</p>
              </div>
            </div>

            {/* Features */}
            {individualFeatures.map((feature, index) => (
              <div
                key={index}
                className={`grid grid-cols-3 ${
                  index !== individualFeatures.length - 1 ? 'border-b border-premium-border' : ''
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
        )}

        {/* Business Plans Table */}
        {activeTab === 'business' && (
          <div className="bg-premium-card rounded-2xl border border-premium-border overflow-hidden">
            {/* Header */}
            <div className="grid grid-cols-4 border-b border-premium-border">
              <div className="p-6 bg-premium-surface">
                <span className="text-gray-400 font-medium">Features</span>
              </div>
              <div className="p-6 text-center bg-premium-surface border-x border-premium-border">
                <span className="text-white font-semibold">Team</span>
                <p className="text-sm text-gray-500 mt-1">5-10 users</p>
                <p className="text-xs text-gold-400">5 seats min</p>
              </div>
              <div className="p-6 text-center bg-gradient-to-b from-gold-500/10 to-transparent border-r border-premium-border">
                <div className="flex items-center justify-center">
                  <Sparkles className="h-4 w-4 text-gold-400 mr-2" />
                  <span className="text-gold-400 font-semibold">Growth</span>
                </div>
                <p className="text-sm text-gray-500 mt-1">11-50 users</p>
              </div>
              <div className="p-6 text-center bg-premium-surface">
                <span className="text-white font-semibold">Enterprise</span>
                <p className="text-sm text-gray-500 mt-1">50+ users</p>
              </div>
            </div>

            {/* Features */}
            {businessFeatures.map((feature, index) => (
              <div
                key={index}
                className={`grid grid-cols-4 ${
                  index !== businessFeatures.length - 1 ? 'border-b border-premium-border' : ''
                }`}
              >
                <div className="p-4 flex items-center">
                  <span className="text-gray-300 text-sm">{feature.name}</span>
                </div>
                <div className="p-4 flex items-center justify-center border-x border-premium-border">
                  {typeof feature.team === 'boolean' ? (
                    feature.team ? (
                      <Check className="h-5 w-5 text-emerald-400" />
                    ) : (
                      <X className="h-5 w-5 text-gray-600" />
                    )
                  ) : (
                    <span className="text-gray-400 text-sm">{feature.team}</span>
                  )}
                </div>
                <div className="p-4 flex items-center justify-center bg-gold-500/5 border-r border-premium-border">
                  {typeof feature.growth === 'boolean' ? (
                    feature.growth ? (
                      <Check className="h-5 w-5 text-gold-400" />
                    ) : (
                      <X className="h-5 w-5 text-gray-600" />
                    )
                  ) : (
                    <span className="text-gold-400 text-sm font-medium">{feature.growth}</span>
                  )}
                </div>
                <div className="p-4 flex items-center justify-center">
                  {typeof feature.enterprise === 'boolean' ? (
                    feature.enterprise ? (
                      <Check className="h-5 w-5 text-emerald-400" />
                    ) : (
                      <X className="h-5 w-5 text-gray-600" />
                    )
                  ) : (
                    <span className="text-gray-400 text-sm">{feature.enterprise}</span>
                  )}
                </div>
              </div>
            ))}

            {/* CTA Row */}
            <div className="grid grid-cols-4 border-t border-premium-border bg-premium-surface">
              <div className="p-6"></div>
              <div className="p-6 flex items-center justify-center border-x border-premium-border">
                <Link
                  href="/login"
                  className="px-5 py-2.5 bg-premium-border text-white text-sm font-medium rounded-lg hover:bg-premium-border-light transition-colors"
                >
                  Sign Up
                </Link>
              </div>
              <div className="p-6 flex items-center justify-center border-r border-premium-border">
                <Link
                  href="/login"
                  className="px-5 py-2.5 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg text-sm font-semibold rounded-lg hover:shadow-gold transition-all"
                >
                  Sign Up
                </Link>
              </div>
              <div className="p-6 flex items-center justify-center">
                <a
                  href="mailto:enterprise@getreadin.ai?subject=Enterprise Inquiry"
                  className="px-5 py-2.5 bg-premium-border text-white text-sm font-medium rounded-lg hover:bg-premium-border-light transition-colors"
                >
                  Contact Sales
                </a>
              </div>
            </div>
          </div>
        )}

        {/* Bottom Note */}
        <p className="text-center text-gray-500 text-sm mt-8">
          {activeTab === 'individual'
            ? 'All plans include a 30-day money-back guarantee. No credit card required for trial.'
            : 'One admin pays, entire team gets access. Volume discounts available for larger teams.'}
        </p>
      </div>
    </section>
  )
}
