import type { Metadata } from 'next'
import Script from 'next/script'
import { organizationSchema, createWebPageSchema, generateJsonLd } from '@/components/seo/schemas'

const BASE_URL = 'https://www.getreadin.us'

export const metadata: Metadata = {
  title: 'About ReadIn AI | Our Mission & Story',
  description: 'Learn about ReadIn AI - the real-time AI meeting assistant built to help professionals communicate with confidence. Our mission, values, and the team behind the product.',
  keywords: [
    'about ReadIn AI',
    'ReadIn AI company',
    'AI meeting assistant company',
    'ReadIn AI mission',
    'meeting AI technology',
  ],
  alternates: {
    canonical: `${BASE_URL}/about`,
  },
  openGraph: {
    title: 'About ReadIn AI - Our Mission & Story',
    description: 'Empowering professionals to communicate with confidence using AI-powered meeting assistance.',
    url: `${BASE_URL}/about`,
    type: 'website',
  },
  twitter: {
    title: 'About ReadIn AI',
    description: 'Learn about the AI meeting assistant helping professionals communicate better.',
  },
}

export default function AboutLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const jsonLdData = [
    organizationSchema,
    createWebPageSchema(
      'About ReadIn AI',
      'Learn about ReadIn AI and our mission to help professionals communicate with confidence',
      `${BASE_URL}/about`
    ),
  ]

  return (
    <>
      {children}
      <Script
        id="about-json-ld"
        type="application/ld+json"
        strategy="afterInteractive"
        dangerouslySetInnerHTML={{ __html: generateJsonLd(jsonLdData) }}
      />
    </>
  )
}
