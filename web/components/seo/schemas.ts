// Server-side schema utilities for SEO
// This file should NOT have 'use client' directive

const BASE_URL = 'https://www.getreadin.us'

interface OrganizationSchema {
  '@context': 'https://schema.org'
  '@type': 'Organization'
  name: string
  url: string
  logo: string
  description: string
  sameAs?: string[]
  contactPoint?: {
    '@type': 'ContactPoint'
    contactType: string
    email?: string
    url?: string
  }
}

interface SoftwareApplicationSchema {
  '@context': 'https://schema.org'
  '@type': 'SoftwareApplication'
  name: string
  description: string
  applicationCategory: string
  operatingSystem: string
  offers: {
    '@type': 'Offer'
    price: string
    priceCurrency: string
    priceValidUntil?: string
  }
  aggregateRating?: {
    '@type': 'AggregateRating'
    ratingValue: string
    ratingCount: string
  }
}

interface WebPageSchema {
  '@context': 'https://schema.org'
  '@type': 'WebPage'
  name: string
  description: string
  url: string
  inLanguage?: string
  isPartOf?: {
    '@type': 'WebSite'
    name: string
    url: string
  }
}

// Pre-built schemas
export const organizationSchema: OrganizationSchema = {
  '@context': 'https://schema.org',
  '@type': 'Organization',
  name: 'ReadIn AI',
  url: BASE_URL,
  logo: `${BASE_URL}/icon.png`,
  description: 'AI-powered real-time meeting assistant that provides instant talking points during live conversations.',
  sameAs: [
    'https://twitter.com/getreadinai',
    'https://www.linkedin.com/company/readin-ai',
    'https://github.com/derickjoseph8/readin-ai',
  ],
  contactPoint: {
    '@type': 'ContactPoint',
    contactType: 'customer support',
    email: 'support@getreadin.us',
    url: `${BASE_URL}/contact`,
  },
}

export const softwareApplicationSchema: SoftwareApplicationSchema = {
  '@context': 'https://schema.org',
  '@type': 'SoftwareApplication',
  name: 'ReadIn AI',
  description: 'Real-time AI meeting assistant that listens to conversations and provides instant talking points. Works with Zoom, Teams, Google Meet, and more.',
  applicationCategory: 'BusinessApplication',
  operatingSystem: 'Windows, macOS, Linux',
  offers: {
    '@type': 'Offer',
    price: '0',
    priceCurrency: 'USD',
  },
  aggregateRating: {
    '@type': 'AggregateRating',
    ratingValue: '4.8',
    ratingCount: '127',
  },
}

export function createWebPageSchema(
  name: string,
  description: string,
  url: string,
  locale: string = 'en'
): WebPageSchema {
  return {
    '@context': 'https://schema.org',
    '@type': 'WebPage',
    name,
    description,
    url,
    inLanguage: locale,
    isPartOf: {
      '@type': 'WebSite',
      name: 'ReadIn AI',
      url: BASE_URL,
    },
  }
}

interface FAQSchema {
  '@context': 'https://schema.org'
  '@type': 'FAQPage'
  mainEntity: Array<{
    '@type': 'Question'
    name: string
    acceptedAnswer: {
      '@type': 'Answer'
      text: string
    }
  }>
}

export function createFAQSchema(
  faqs: Array<{ question: string; answer: string }>
): FAQSchema {
  return {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: faqs.map((faq) => ({
      '@type': 'Question',
      name: faq.question,
      acceptedAnswer: {
        '@type': 'Answer',
        text: faq.answer,
      },
    })),
  }
}

// Generate JSON-LD script content
export function generateJsonLd(data: object | object[]): string {
  return JSON.stringify(data)
}
