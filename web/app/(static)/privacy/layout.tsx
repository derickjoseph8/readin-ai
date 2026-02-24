import type { Metadata } from 'next'

const BASE_URL = 'https://www.getreadin.us'

export const metadata: Metadata = {
  title: 'Privacy Policy | ReadIn AI',
  description: 'ReadIn AI Privacy Policy. Learn how we protect your data and privacy. Audio is processed locally on your device - we never store your meeting content.',
  alternates: {
    canonical: `${BASE_URL}/privacy`,
  },
  robots: {
    index: true,
    follow: true,
  },
}

export default function PrivacyLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return <>{children}</>
}
