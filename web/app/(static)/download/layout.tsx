import type { Metadata } from 'next'
import Script from 'next/script'
import { softwareApplicationSchema, createWebPageSchema, generateJsonLd } from '@/components/seo/schemas'

const BASE_URL = 'https://www.getreadin.us'

export const metadata: Metadata = {
  title: 'Download ReadIn AI | Windows, macOS, Linux',
  description: 'Download ReadIn AI for Windows, macOS, or Linux. Free 7-day trial. Real-time AI meeting assistant that works with Zoom, Teams, Meet, and more.',
  keywords: [
    'download ReadIn AI',
    'ReadIn AI Windows',
    'ReadIn AI Mac',
    'ReadIn AI Linux',
    'AI meeting assistant download',
    'meeting helper app',
  ],
  alternates: {
    canonical: `${BASE_URL}/download`,
  },
  openGraph: {
    title: 'Download ReadIn AI - Available for All Platforms',
    description: 'Get ReadIn AI for Windows, macOS, or Linux. Free trial, no credit card required.',
    url: `${BASE_URL}/download`,
    type: 'website',
  },
  twitter: {
    title: 'Download ReadIn AI for Windows, Mac, Linux',
    description: 'Free AI meeting assistant. Download now for your platform.',
  },
}

export default function DownloadLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const jsonLdData = [
    softwareApplicationSchema,
    createWebPageSchema(
      'Download ReadIn AI',
      'Download ReadIn AI for Windows, macOS, or Linux',
      `${BASE_URL}/download`
    ),
  ]

  return (
    <>
      {children}
      <Script
        id="download-json-ld"
        type="application/ld+json"
        strategy="afterInteractive"
        dangerouslySetInnerHTML={{ __html: generateJsonLd(jsonLdData) }}
      />
    </>
  )
}
