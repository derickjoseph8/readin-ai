import type { Metadata } from 'next'

const BASE_URL = 'https://www.getreadin.us'

export const metadata: Metadata = {
  title: 'Terms of Service | ReadIn AI',
  description: 'ReadIn AI Terms of Service. Read our terms and conditions for using the ReadIn AI meeting assistant software and services.',
  alternates: {
    canonical: `${BASE_URL}/terms`,
  },
  robots: {
    index: true,
    follow: true,
  },
}

export default function TermsLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return <>{children}</>
}
