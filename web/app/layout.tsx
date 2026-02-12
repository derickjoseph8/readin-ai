import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'ReadIn AI - Your Real-Time AI Assistant for Live Conversations',
  description: 'Never get caught off guard in meetings again. ReadIn AI listens to questions and instantly shows talking points you can glance at and rephrase naturally.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
