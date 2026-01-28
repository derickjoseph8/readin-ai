'use client'

import Link from 'next/link'
import { Check, Sparkles } from 'lucide-react'

const plans = [
  {
    name: 'Free Trial',
    price: '$0',
    period: 'for 7 days',
    description: 'Try ReadIn AI risk-free',
    features: [
      '10 AI responses per day',
      'All video conferencing apps',
      'Real-time transcription',
      'Floating overlay UI',
      'Context-aware responses',
    ],
    cta: 'Start Free Trial',
    href: '/download',
    popular: false,
  },
  {
    name: 'Premium',
    price: '$29.99',
    period: '/month',
    description: 'Unlimited power for professionals',
    features: [
      'Unlimited AI responses',
      'All video conferencing apps',
      'Real-time transcription',
      'Floating overlay UI',
      'Context-aware responses',
      'Priority support',
      'Early access to new features',
    ],
    cta: 'Get Premium',
    href: '/download',
    popular: true,
  },
]

export default function Pricing() {
  return (
    <section id="pricing" className="py-24 px-4 bg-dark-900/50">
      <div className="max-w-7xl mx-auto">
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <h2 className="text-4xl md:text-5xl font-bold mb-6">
            Simple,{' '}
            <span className="text-gradient">Transparent Pricing</span>
          </h2>
          <p className="text-xl text-gray-400">
            Start free, upgrade when you're ready. No hidden fees, cancel anytime.
          </p>
        </div>

        {/* Pricing Cards */}
        <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
          {plans.map((plan, index) => (
            <div
              key={index}
              className={`relative p-8 rounded-2xl border ${
                plan.popular
                  ? 'bg-gradient-to-b from-blue-600/20 to-transparent border-blue-500/50'
                  : 'bg-dark-800/50 border-white/10'
              }`}
            >
              {/* Popular Badge */}
              {plan.popular && (
                <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                  <div className="flex items-center px-4 py-1 bg-gradient-to-r from-blue-600 to-cyan-500 rounded-full text-sm font-medium">
                    <Sparkles className="h-4 w-4 mr-1" />
                    Most Popular
                  </div>
                </div>
              )}

              {/* Plan Header */}
              <div className="text-center mb-8">
                <h3 className="text-xl font-semibold mb-2">{plan.name}</h3>
                <div className="flex items-baseline justify-center mb-2">
                  <span className="text-5xl font-bold">{plan.price}</span>
                  <span className="text-gray-400 ml-2">{plan.period}</span>
                </div>
                <p className="text-gray-400">{plan.description}</p>
              </div>

              {/* Features */}
              <ul className="space-y-4 mb-8">
                {plan.features.map((feature, featureIndex) => (
                  <li key={featureIndex} className="flex items-center">
                    <div className={`w-5 h-5 rounded-full flex items-center justify-center mr-3 ${
                      plan.popular ? 'bg-blue-500/20 text-blue-400' : 'bg-green-500/20 text-green-400'
                    }`}>
                      <Check className="h-3 w-3" />
                    </div>
                    <span className="text-gray-300">{feature}</span>
                  </li>
                ))}
              </ul>

              {/* CTA Button */}
              <Link
                href="/download"
                className={`block w-full py-4 rounded-xl font-semibold text-center transition ${
                  plan.popular
                    ? 'bg-gradient-to-r from-blue-600 to-cyan-500 text-white hover:opacity-90'
                    : 'bg-white/10 text-white hover:bg-white/20 border border-white/10'
                }`}
              >
                {plan.cta}
              </Link>
            </div>
          ))}
        </div>

        {/* Money-back guarantee */}
        <p className="text-center text-gray-500 mt-8">
          No credit card required for trial. Cancel premium anytime.
        </p>
      </div>
    </section>
  )
}
