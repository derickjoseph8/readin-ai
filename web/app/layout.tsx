import type { Metadata, Viewport } from 'next';
import { NextIntlClientProvider } from 'next-intl';
import './globals.css';
import ChatWidget from '@/components/ChatWidget';
import { JsonLd, organizationSchema, softwareApplicationSchema } from '@/components/seo/JsonLd';

// Import default messages for non-locale routes
import messages from '../messages/en.json';

// Cast messages to the expected type
const typedMessages = messages as any;

const BASE_URL = 'https://www.getreadin.us';

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5,
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#d4af37' },
    { media: '(prefers-color-scheme: dark)', color: '#0a0a0a' },
  ],
};

export const metadata: Metadata = {
  metadataBase: new URL(BASE_URL),
  title: {
    default: 'ReadIn AI - Real-Time AI Meeting Assistant | Never Miss a Beat',
    template: '%s | ReadIn AI',
  },
  description: 'Never get caught off guard in meetings again. ReadIn AI listens to conversations and instantly provides AI-powered talking points you can glance at and deliver naturally. Works with Zoom, Teams, Meet & more.',
  keywords: [
    'AI meeting assistant',
    'real-time transcription',
    'meeting helper',
    'interview prep',
    'talking points',
    'AI assistant',
    'Zoom assistant',
    'Teams helper',
    'Google Meet AI',
    'meeting notes',
    'conversation AI',
    'presentation helper',
    'sales calls AI',
    'meeting intelligence',
  ],
  authors: [{ name: 'ReadIn AI', url: BASE_URL }],
  creator: 'ReadIn AI',
  publisher: 'ReadIn AI',
  formatDetection: {
    email: false,
    address: false,
    telephone: false,
  },
  alternates: {
    canonical: BASE_URL,
    languages: {
      'en': BASE_URL,
      'es': `${BASE_URL}/es`,
      'fr': `${BASE_URL}/fr`,
      'de': `${BASE_URL}/de`,
      'pt': `${BASE_URL}/pt`,
      'ja': `${BASE_URL}/ja`,
      'sw': `${BASE_URL}/sw`,
      'x-default': BASE_URL,
    },
  },
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: BASE_URL,
    siteName: 'ReadIn AI',
    title: 'ReadIn AI - Real-Time AI Meeting Assistant',
    description: 'Never get caught off guard in meetings. Get AI-powered talking points instantly during any conversation.',
    images: [
      {
        url: `${BASE_URL}/og-image.png`,
        width: 1200,
        height: 630,
        alt: 'ReadIn AI - Your Real-Time AI Meeting Assistant',
        type: 'image/png',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    site: '@getreadinai',
    creator: '@getreadinai',
    title: 'ReadIn AI - Real-Time AI Meeting Assistant',
    description: 'Never get caught off guard in meetings. Get AI-powered talking points instantly.',
    images: [`${BASE_URL}/og-image.png`],
  },
  robots: {
    index: true,
    follow: true,
    nocache: false,
    googleBot: {
      index: true,
      follow: true,
      noimageindex: false,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
  icons: {
    icon: [
      { url: '/favicon.ico', sizes: 'any' },
      { url: '/icon.png', type: 'image/png', sizes: '192x192' },
    ],
    apple: [
      { url: '/apple-icon.png', sizes: '180x180', type: 'image/png' },
    ],
  },
  manifest: '/manifest.webmanifest',
  category: 'technology',
  classification: 'Business Software',
  referrer: 'origin-when-cross-origin',
  appLinks: {
    web: {
      url: BASE_URL,
      should_fallback: true,
    },
  },
  verification: {
    // Add your verification codes here
    // google: 'your-google-verification-code',
    // yandex: 'your-yandex-verification-code',
    // bing: 'your-bing-verification-code',
  },
  other: {
    'msapplication-TileColor': '#0a0a0a',
    'apple-mobile-web-app-capable': 'yes',
    'apple-mobile-web-app-status-bar-style': 'black-translucent',
    'apple-mobile-web-app-title': 'ReadIn AI',
  },
};

// Force dynamic rendering for root routes
export const dynamic = 'force-dynamic';

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        {/* Preconnect to external resources for performance */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link rel="dns-prefetch" href="https://www.google-analytics.com" />
        <link rel="dns-prefetch" href="https://api.getreadin.us" />
      </head>
      <body className="bg-premium-bg text-white antialiased">
        {/* Skip link for accessibility - visible only on focus */}
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-[100] focus:px-4 focus:py-2 focus:bg-gold-500 focus:text-premium-bg focus:rounded-lg focus:font-medium focus:outline-none focus:ring-2 focus:ring-gold-400 focus:ring-offset-2 focus:ring-offset-premium-bg"
        >
          Skip to main content
        </a>
        <NextIntlClientProvider messages={typedMessages} locale="en">
          {children}
          <ChatWidget />
        </NextIntlClientProvider>
        {/* Structured Data */}
        <JsonLd data={[organizationSchema, softwareApplicationSchema]} />
      </body>
    </html>
  );
}
