import { MetadataRoute } from 'next'

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: 'ReadIn AI - Real-Time AI Meeting Assistant',
    short_name: 'ReadIn AI',
    description: 'Never get caught off guard in meetings again. AI-powered talking points in real-time.',
    start_url: '/',
    display: 'standalone',
    background_color: '#0a0a0a',
    theme_color: '#d4af37',
    orientation: 'portrait-primary',
    categories: ['business', 'productivity', 'utilities'],
    icons: [
      {
        src: '/icon.png',
        sizes: '192x192',
        type: 'image/png',
        purpose: 'maskable',
      },
      {
        src: '/icon.png',
        sizes: '192x192',
        type: 'image/png',
        purpose: 'any',
      },
      {
        src: '/apple-icon.png',
        sizes: '180x180',
        type: 'image/png',
        purpose: 'any',
      },
    ],
    screenshots: [],
    shortcuts: [
      {
        name: 'Download App',
        url: '/download',
        description: 'Download ReadIn AI for your platform',
      },
      {
        name: 'View Pricing',
        url: '/pricing',
        description: 'See pricing plans',
      },
    ],
  }
}
