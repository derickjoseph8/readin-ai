import { NextIntlClientProvider } from 'next-intl';
import type { AbstractIntlMessages } from 'next-intl';

// Import default English messages for static pages
import messages from '../../messages/en.json';

// Force dynamic rendering to avoid next-intl static generation issues
export const dynamic = 'force-dynamic';

export default function StaticLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-premium-bg text-white antialiased">
        <NextIntlClientProvider locale="en" messages={messages as unknown as AbstractIntlMessages}>
          {children}
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
