import { MetadataRoute } from 'next'
import { locales } from '@/i18n'

const BASE_URL = 'https://www.getreadin.us'

// Define all static pages
const staticPages = [
  { path: '', priority: 1.0, changeFrequency: 'weekly' as const },
  { path: '/pricing', priority: 0.9, changeFrequency: 'weekly' as const },
  { path: '/download', priority: 0.9, changeFrequency: 'weekly' as const },
  { path: '/about', priority: 0.7, changeFrequency: 'monthly' as const },
  { path: '/contact', priority: 0.6, changeFrequency: 'monthly' as const },
  { path: '/terms', priority: 0.3, changeFrequency: 'yearly' as const },
  { path: '/privacy', priority: 0.3, changeFrequency: 'yearly' as const },
  { path: '/cookies', priority: 0.3, changeFrequency: 'yearly' as const },
  { path: '/gdpr', priority: 0.3, changeFrequency: 'yearly' as const },
]

export default function sitemap(): MetadataRoute.Sitemap {
  const currentDate = new Date().toISOString()
  const entries: MetadataRoute.Sitemap = []

  // Add pages for default locale (en) without prefix
  for (const page of staticPages) {
    entries.push({
      url: `${BASE_URL}${page.path || '/'}`,
      lastModified: currentDate,
      changeFrequency: page.changeFrequency,
      priority: page.priority,
    })
  }

  // Add pages for other locales with prefix
  for (const locale of locales) {
    if (locale === 'en') continue // Skip default locale (already added without prefix)

    for (const page of staticPages) {
      entries.push({
        url: `${BASE_URL}/${locale}${page.path}`,
        lastModified: currentDate,
        changeFrequency: page.changeFrequency,
        priority: page.priority * 0.9, // Slightly lower priority for non-default locales
      })
    }
  }

  return entries
}
