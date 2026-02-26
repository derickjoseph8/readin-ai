import type { Metadata } from 'next';
import Script from 'next/script';
import { organizationSchema, softwareApplicationSchema, createWebPageSchema, generateJsonLd } from '@/components/seo/schemas';

const BASE_URL = 'https://www.getreadin.us';

export const metadata: Metadata = {
  title: 'Pricing for Africa, UAE & Asia | ReadIn AI',
  description: 'Get ReadIn AI at $19.99/month - special pricing for Africa, UAE, and Asia. Never get caught off guard in meetings. Real-time AI suggestions tailored for professionals.',
  alternates: {
    canonical: `${BASE_URL}/global`,
  },
  openGraph: {
    title: 'ReadIn AI - Accessible AI Meeting Assistant | $19.99/month',
    description: 'Professional meeting intelligence at prices that work for your region. Real-time AI suggestions, M-Pesa & Paystack supported.',
    url: `${BASE_URL}/global`,
    siteName: 'ReadIn AI',
    locale: 'en_US',
    type: 'website',
    images: [
      {
        url: `${BASE_URL}/og-global.png`,
        width: 1200,
        height: 630,
        alt: 'ReadIn AI - $19.99/month for Africa, UAE & Asia',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'ReadIn AI - $19.99/month for Africa, UAE & Asia',
    description: 'Professional AI meeting assistant at accessible pricing. M-Pesa, Paystack & Flutterwave supported.',
    images: [`${BASE_URL}/og-global.png`],
  },
  keywords: [
    'AI meeting assistant Africa',
    'meeting assistant Kenya',
    'meeting assistant Nigeria',
    'meeting assistant South Africa',
    'meeting assistant UAE',
    'meeting assistant India',
    'M-Pesa payment',
    'Paystack',
    'Flutterwave',
    'affordable AI tool',
    'real-time meeting suggestions',
  ],
};

export default function GlobalLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const webPageSchema = createWebPageSchema(
    'ReadIn AI - Pricing for Africa, UAE & Asia',
    'Get ReadIn AI at $19.99/month. Professional meeting intelligence with M-Pesa, Paystack & Flutterwave payment options.',
    `${BASE_URL}/global`
  );

  const jsonLdData = [organizationSchema, softwareApplicationSchema, webPageSchema];

  return (
    <>
      {children}
      <Script
        id="global-json-ld"
        type="application/ld+json"
        strategy="afterInteractive"
        dangerouslySetInnerHTML={{
          __html: generateJsonLd(jsonLdData),
        }}
      />
    </>
  );
}
