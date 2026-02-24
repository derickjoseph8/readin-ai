'use client'

import Script from 'next/script'

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

interface BreadcrumbSchema {
  '@context': 'https://schema.org'
  '@type': 'BreadcrumbList'
  itemListElement: Array<{
    '@type': 'ListItem'
    position: number
    name: string
    item: string
  }>
}

type SchemaType =
  | OrganizationSchema
  | SoftwareApplicationSchema
  | WebPageSchema
  | FAQSchema
  | BreadcrumbSchema

interface JsonLdProps {
  data: SchemaType | SchemaType[]
}

export function JsonLd({ data }: JsonLdProps) {
  return (
    <Script
      id="json-ld"
      type="application/ld+json"
      strategy="afterInteractive"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }}
    />
  )
}

// Pre-built schemas for common use cases
export const organizationSchema: OrganizationSchema = {
  '@context': 'https://schema.org',
  '@type': 'Organization',
  name: 'ReadIn AI',
  url: 'https://www.getreadin.us',
  logo: 'https://www.getreadin.us/icon.png',
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
    url: 'https://www.getreadin.us/contact',
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
      url: 'https://www.getreadin.us',
    },
  }
}

export function createBreadcrumbSchema(
  items: Array<{ name: string; url: string }>
): BreadcrumbSchema {
  return {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: items.map((item, index) => ({
      '@type': 'ListItem',
      position: index + 1,
      name: item.name,
      item: item.url,
    })),
  }
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
