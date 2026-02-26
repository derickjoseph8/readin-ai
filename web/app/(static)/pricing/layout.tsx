import type { Metadata } from 'next'
import Script from 'next/script'
import { createWebPageSchema, createFAQSchema, generateJsonLd } from '@/components/seo/schemas'

const BASE_URL = 'https://www.getreadin.us'

export const metadata: Metadata = {
  title: 'Pricing - ReadIn AI | Free Trial & Affordable Plans',
  description: 'Start free with ReadIn AI. 7-day trial, no credit card required. Simple pricing with unlimited AI-powered meeting assistance. See our plans.',
  keywords: [
    'ReadIn AI pricing',
    'AI meeting assistant cost',
    'meeting AI free trial',
    'Zoom AI assistant price',
    'Teams meeting helper pricing',
  ],
  alternates: {
    canonical: `${BASE_URL}/pricing`,
  },
  openGraph: {
    title: 'ReadIn AI Pricing - Start Your Free Trial Today',
    description: 'Try ReadIn AI free for 7 days. No credit card required. Get AI-powered talking points in every meeting.',
    url: `${BASE_URL}/pricing`,
    type: 'website',
  },
  twitter: {
    title: 'ReadIn AI Pricing - Free Trial Available',
    description: 'Try ReadIn AI free for 7 days. AI-powered meeting assistant.',
  },
}

const pricingFAQs = [
  {
    question: 'Is there a free trial?',
    answer: 'Yes! We offer a 7-day free trial with no credit card required. You get full access to all features during the trial.',
  },
  {
    question: 'Can I cancel anytime?',
    answer: 'Absolutely. You can cancel your subscription at any time with no questions asked. Your access continues until the end of your billing period.',
  },
  {
    question: 'What payment methods do you accept?',
    answer: 'We accept all major credit cards (Visa, MasterCard, American Express) and process payments securely through Stripe.',
  },
]

export default function PricingLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const jsonLdData = [
    createWebPageSchema(
      'ReadIn AI Pricing',
      'Affordable pricing plans for AI-powered meeting assistance',
      `${BASE_URL}/pricing`
    ),
    createFAQSchema(pricingFAQs),
  ]

  return (
    <>
      {children}
      <Script
        id="pricing-json-ld"
        type="application/ld+json"
        strategy="afterInteractive"
        dangerouslySetInnerHTML={{ __html: generateJsonLd(jsonLdData) }}
      />
    </>
  )
}
