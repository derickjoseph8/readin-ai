import type { Metadata } from 'next'

const BASE_URL = 'https://www.getreadin.us'

export const metadata: Metadata = {
  title: 'Contact Us | ReadIn AI Support',
  description: 'Get in touch with the ReadIn AI team. We\'re here to help with questions about our AI meeting assistant, technical support, or partnership inquiries.',
  keywords: [
    'contact ReadIn AI',
    'ReadIn AI support',
    'AI meeting assistant help',
    'ReadIn AI customer service',
  ],
  alternates: {
    canonical: `${BASE_URL}/contact`,
  },
  openGraph: {
    title: 'Contact ReadIn AI - We\'re Here to Help',
    description: 'Get in touch with our support team for questions about ReadIn AI.',
    url: `${BASE_URL}/contact`,
    type: 'website',
  },
}

export default function ContactLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return <>{children}</>
}
