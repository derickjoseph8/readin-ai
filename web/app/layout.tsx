import type { Metadata } from 'next';
import { NextIntlClientProvider } from 'next-intl';
import './globals.css';
import ChatWidget from '@/components/ChatWidget';

// Import default messages for non-locale routes
import messages from '../messages/en.json';

// Cast messages to the expected type
const typedMessages = messages as any;

export const metadata: Metadata = {
  title: 'ReadIn AI - Your Real-Time AI Assistant for Live Conversations',
  description: 'Never get caught off guard in meetings again. ReadIn AI listens to questions and instantly shows talking points you can glance at and rephrase naturally.',
};

// Force dynamic rendering for root routes
export const dynamic = 'force-dynamic';

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-premium-bg text-white antialiased">
        <NextIntlClientProvider messages={typedMessages} locale="en">
          {children}
          <ChatWidget />
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
