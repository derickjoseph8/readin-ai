import type { Metadata, Viewport } from 'next';
import '../globals.css';
import { JsonLd, organizationSchema, softwareApplicationSchema } from '@/components/seo/JsonLd';

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
  description: 'Never get caught off guard in meetings again. ReadIn AI listens to conversations and instantly provides AI-powered talking points you can glance at and deliver naturally.',
};

/**
 * Static pages layout - completely independent from i18n
 * Provides its own html/body to avoid inheriting NextIntlClientProvider
 */
export default function StaticLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body className="bg-premium-bg text-white antialiased">
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-[100] focus:px-4 focus:py-2 focus:bg-gold-500 focus:text-premium-bg focus:rounded-lg focus:font-medium focus:outline-none focus:ring-2 focus:ring-gold-400 focus:ring-offset-2 focus:ring-offset-premium-bg"
        >
          Skip to main content
        </a>
        {children}
        <JsonLd data={[organizationSchema, softwareApplicationSchema]} />
      </body>
    </html>
  );
}
