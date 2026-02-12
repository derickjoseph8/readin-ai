import { NextIntlClientProvider } from 'next-intl';
import type { AbstractIntlMessages } from 'next-intl';
import '../globals.css';

// Import default English messages for static pages
import messages from '../../messages/en.json';

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
