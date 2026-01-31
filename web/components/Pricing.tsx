'use client'

import Link from 'next/link'
import { Check, Sparkles, Shield, Building2, Users, Globe } from 'lucide-react'

const plans = [
  {
    name: 'Free Trial',
    price: '$0',
    period: 'for 14 days',
    description: 'Try ReadIn AI risk-free',
    features: [
      '10 AI responses per day',
      'All video conferencing apps',
      'Real-time transcription',
      'Profession-tailored responses',
      'Context-aware AI',
    ],
    cta: 'Start Free Trial',
    href: '/download',
    popular: false,
  },
  {
    name: 'Premium',
    price: '$29.99',
    period: '/month',
    description: 'Complete meeting intelligence for individuals',
    features: [
      'Unlimited AI responses',
      'Profession-specific knowledge base',
      'Smart meeting notes emailed to you',
      'Action item & commitment tracking',
      'ML learns your communication style',
      'Pre-meeting briefings & context',
      'Participant memory across meetings',
      'Job application tracker',
      'Priority support',
    ],
    cta: 'Get Premium',
    href: '/download',
    popular: true,
  },
]

const corporatePlans = [
  {
    name: 'Team',
    price: '$24.99',
    period: '/user/month',
    users: '5-10 users',
    description: 'Admin pays, team joins free',
    features: [
      'Everything in Premium',
      'Invite team members (no extra payment)',
      'Team admin dashboard',
      'Shared meeting insights',
      'Centralized billing',
    ],
    cta: 'Contact Sales',
    href: 'mailto:sales@getreadin.ai?subject=Team Plan Inquiry',
  },
  {
    name: 'Business',
    price: '$19.99',
    period: '/user/month',
    users: '11-50 users',
    description: 'One bill, unlimited team invites',
    features: [
      'Everything in Team',
      'Add unlimited team members',
      'Advanced admin controls',
      'Usage analytics & reports',
      'Custom profession profiles',
      'Dedicated account manager',
    ],
    cta: 'Contact Sales',
    href: 'mailto:sales@getreadin.ai?subject=Business Plan Inquiry',
    popular: true,
  },
  {
    name: 'Enterprise',
    price: 'Custom',
    period: '',
    users: '50+ users',
    description: 'Unlimited seats, custom pricing',
    features: [
      'Everything in Business',
      'Unlimited team members',
      'Single Sign-On (SSO)',
      'On-premise deployment option',
      'SLA & compliance support',
      'Dedicated success team',
      'Custom AI training',
    ],
    cta: 'Contact Sales',
    href: 'mailto:sales@getreadin.ai?subject=Enterprise Plan Inquiry',
  },
]

export default function Pricing() {
  return (
    <section id="pricing" className="py-24 px-4 bg-premium-surface/50">
      <div className="max-w-7xl mx-auto">
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <h2 className="text-4xl md:text-5xl font-bold mb-6">
            Simple,{' '}
            <span className="text-gradient-gold">Transparent Pricing</span>
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
              className={`relative p-8 rounded-2xl border transition-all duration-300 ${
                plan.popular
                  ? 'bg-gradient-to-b from-gold-500/10 to-transparent border-gold-500/50 shadow-gold'
                  : 'bg-premium-card border-premium-border hover:border-gold-500/30'
              }`}
            >
              {/* Popular Badge */}
              {plan.popular && (
                <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                  <div className="flex items-center px-4 py-1.5 bg-gradient-to-r from-gold-600 to-gold-500 rounded-full text-sm font-semibold text-premium-bg">
                    <Sparkles className="h-4 w-4 mr-1" />
                    Most Popular
                  </div>
                </div>
              )}

              {/* Plan Header */}
              <div className="text-center mb-8">
                <h3 className="text-xl font-semibold mb-2 text-white">{plan.name}</h3>
                <div className="flex items-baseline justify-center mb-2">
                  <span className={`text-5xl font-bold ${plan.popular ? 'text-gradient-gold' : 'text-white'}`}>{plan.price}</span>
                  <span className="text-gray-400 ml-2">{plan.period}</span>
                </div>
                <p className="text-gray-400">{plan.description}</p>
              </div>

              {/* Features */}
              <ul className="space-y-4 mb-8">
                {plan.features.map((feature, featureIndex) => (
                  <li key={featureIndex} className="flex items-center">
                    <div className={`w-5 h-5 rounded-full flex items-center justify-center mr-3 ${
                      plan.popular ? 'bg-gold-500/20 text-gold-400' : 'bg-emerald-500/20 text-emerald-400'
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
                className={`block w-full py-4 rounded-xl font-semibold text-center transition-all duration-300 ${
                  plan.popular
                    ? 'bg-gradient-to-r from-gold-600 via-gold-500 to-gold-600 text-premium-bg hover:shadow-gold hover:-translate-y-0.5'
                    : 'bg-premium-surface text-white hover:bg-premium-border-light border border-premium-border'
                }`}
              >
                {plan.cta}
              </Link>
            </div>
          ))}
        </div>

        {/* Money-back guarantee */}
        <div className="text-center mt-12">
          <div className="inline-flex items-center px-4 py-2 bg-emerald-500/10 border border-emerald-500/20 rounded-full">
            <Shield className="h-4 w-4 text-emerald-400 mr-2" />
            <span className="text-sm text-emerald-300">30-day money-back guarantee on Premium</span>
          </div>
          <p className="text-gray-500 mt-4 text-sm">
            No credit card required for trial. Cancel premium anytime.
          </p>
        </div>

        {/* Corporate Plans Section */}
        <div className="mt-24">
          <div className="text-center max-w-3xl mx-auto mb-12">
            <div className="inline-flex items-center px-4 py-2 bg-gold-500/10 border border-gold-500/20 rounded-full mb-6">
              <Building2 className="h-4 w-4 text-gold-400 mr-2" />
              <span className="text-sm text-gold-300">Corporate & Enterprise</span>
            </div>
            <h3 className="text-3xl md:text-4xl font-bold mb-4">
              Plans for{' '}
              <span className="text-gradient-gold">Teams & Organizations</span>
            </h3>
            <p className="text-lg text-gray-400">
              One admin pays, entire team gets access. Invite team members with no additional cost per invite.
            </p>
          </div>

          {/* Corporate Cards */}
          <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
            {corporatePlans.map((plan, index) => (
              <div
                key={index}
                className={`relative p-6 rounded-2xl border transition-all duration-300 ${
                  plan.popular
                    ? 'bg-gradient-to-b from-gold-500/10 to-transparent border-gold-500/50 shadow-gold'
                    : 'bg-premium-card border-premium-border hover:border-gold-500/30'
                }`}
              >
                {/* Popular Badge */}
                {plan.popular && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <div className="flex items-center px-3 py-1 bg-gradient-to-r from-gold-600 to-gold-500 rounded-full text-xs font-semibold text-premium-bg">
                      <Sparkles className="h-3 w-3 mr-1" />
                      Best Value
                    </div>
                  </div>
                )}

                {/* Plan Header */}
                <div className="text-center mb-6">
                  <div className="inline-flex items-center px-3 py-1 bg-premium-surface rounded-full text-xs text-gray-400 mb-3">
                    <Users className="h-3 w-3 mr-1" />
                    {plan.users}
                  </div>
                  <h4 className="text-lg font-semibold mb-1 text-white">{plan.name}</h4>
                  <div className="flex items-baseline justify-center mb-1">
                    <span className={`text-3xl font-bold ${plan.popular ? 'text-gradient-gold' : 'text-white'}`}>{plan.price}</span>
                    {plan.period && <span className="text-gray-400 ml-1 text-sm">{plan.period}</span>}
                  </div>
                  <p className="text-gray-400 text-sm">{plan.description}</p>
                </div>

                {/* Features */}
                <ul className="space-y-3 mb-6">
                  {plan.features.map((feature, featureIndex) => (
                    <li key={featureIndex} className="flex items-start">
                      <div className={`w-4 h-4 rounded-full flex items-center justify-center mr-2 mt-0.5 ${
                        plan.popular ? 'bg-gold-500/20 text-gold-400' : 'bg-emerald-500/20 text-emerald-400'
                      }`}>
                        <Check className="h-2.5 w-2.5" />
                      </div>
                      <span className="text-gray-300 text-sm">{feature}</span>
                    </li>
                  ))}
                </ul>

                {/* CTA Button */}
                <a
                  href={plan.href}
                  className={`block w-full py-3 rounded-xl font-semibold text-center text-sm transition-all duration-300 ${
                    plan.popular
                      ? 'bg-gradient-to-r from-gold-600 via-gold-500 to-gold-600 text-premium-bg hover:shadow-gold hover:-translate-y-0.5'
                      : 'bg-premium-surface text-white hover:bg-premium-border-light border border-premium-border'
                  }`}
                >
                  {plan.cta}
                </a>
              </div>
            ))}
          </div>

          {/* Enterprise CTA */}
          <div className="text-center mt-12">
            <p className="text-gray-400 mb-4">
              Need a custom solution? We work with organizations of all sizes across every industry.
            </p>
            <a
              href="mailto:enterprise@getreadin.ai?subject=Enterprise Inquiry"
              className="inline-flex items-center px-6 py-3 bg-premium-surface border border-premium-border rounded-xl text-white hover:border-gold-500/30 transition-all duration-300"
            >
              <Globe className="h-4 w-4 mr-2 text-gold-400" />
              Talk to our Enterprise Team
            </a>
          </div>
        </div>
      </div>
    </section>
  )
}
