import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'ReadIn AI - Your Real-Time AI Assistant for Live Conversations',
  description: 'Never get caught off guard in meetings again. ReadIn AI listens to questions and instantly shows talking points you can glance at and rephrase naturally.',
  keywords: 'AI assistant, meeting helper, interview prep, real-time transcription, talking points',
  openGraph: {
    title: 'ReadIn AI - Your Real-Time AI Assistant for Live Conversations',
    description: 'Never get caught off guard in meetings again. Instant AI-powered talking points for any conversation.',
    type: 'website',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="bg-dark-950 text-white antialiased">
        {children}
      </body>
    </html>
  )
}
