import type { Metadata } from 'next';
import { NextIntlClientProvider } from 'next-intl';
import { getMessages, unstable_setRequestLocale } from 'next-intl/server';
import { notFound } from 'next/navigation';
import { locales, type Locale } from '@/i18n';
import '../globals.css';

export const metadata: Metadata = {
  title: 'ReadIn AI - Your Real-Time AI Assistant for Live Conversations',
  description: 'Never get caught off guard in meetings again. ReadIn AI listens to questions and instantly shows talking points you can glance at and rephrase naturally.',
  keywords: 'AI assistant, meeting helper, interview prep, real-time transcription, talking points',
  openGraph: {
    title: 'ReadIn AI - Your Real-Time AI Assistant for Live Conversations',
    description: 'Never get caught off guard in meetings again. Instant AI-powered talking points for any conversation.',
    type: 'website',
  },
};

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

export default async function LocaleLayout({
  children,
  params
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;

  // Validate that the incoming `locale` parameter is valid
  if (!locales.includes(locale as Locale)) {
    notFound();
  }

  // Enable static rendering
  unstable_setRequestLocale(locale);

  // Fetch messages for the current locale
  const messages = await getMessages();

  return (
    <html lang={locale}>
      <body className="bg-premium-bg text-white antialiased">
        <NextIntlClientProvider messages={messages}>
          {children}
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
