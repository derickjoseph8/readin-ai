'use client'

import Link from 'next/link'
import Header from '@/components/Header'
import Footer from '@/components/Footer'
import { Sparkles, Zap, Bug, Shield, ArrowUpCircle } from 'lucide-react'

const releases = [
  {
    version: '2.0.0',
    date: 'January 30, 2026',
    type: 'major',
    title: 'Meeting Intelligence Platform',
    description: 'Complete platform overhaul with ML-powered learning, meeting summaries, and team features.',
    changes: [
      { type: 'feature', text: 'Profession selection at registration for tailored AI responses' },
      { type: 'feature', text: 'ML learning engine that adapts to your communication style' },
      { type: 'feature', text: 'Automatic meeting summaries sent to your email' },
      { type: 'feature', text: 'Action item extraction - WHO does WHAT by WHEN' },
      { type: 'feature', text: 'Commitment tracking with email reminders' },
      { type: 'feature', text: 'Pre-meeting briefings with participant context' },
      { type: 'feature', text: 'Job application and interview tracker' },
      { type: 'feature', text: 'Corporate/team plans - admin pays, team joins free' },
      { type: 'feature', text: 'Participant memory across meetings' },
      { type: 'improvement', text: 'Updated pricing to $29.99/month with expanded features' },
      { type: 'improvement', text: '60+ profession profiles with industry-specific knowledge' },
    ]
  },
  {
    version: '1.1.0',
    date: 'January 15, 2026',
    type: 'minor',
    title: 'Performance & Stability',
    description: 'Major improvements to transcription accuracy and system stability.',
    changes: [
      { type: 'improvement', text: 'Upgraded to latest Whisper model for better accuracy' },
      { type: 'improvement', text: 'Reduced memory usage by 40%' },
      { type: 'improvement', text: 'Faster AI response generation' },
      { type: 'fix', text: 'Fixed audio capture on some Windows configurations' },
      { type: 'fix', text: 'Fixed overlay positioning on multi-monitor setups' },
      { type: 'fix', text: 'Fixed occasional crashes during long meetings' },
    ]
  },
  {
    version: '1.0.0',
    date: 'January 1, 2026',
    type: 'major',
    title: 'Initial Release',
    description: 'The first public release of ReadIn AI.',
    changes: [
      { type: 'feature', text: 'Real-time audio transcription with Whisper' },
      { type: 'feature', text: 'AI-powered response suggestions' },
      { type: 'feature', text: 'Floating overlay interface' },
      { type: 'feature', text: 'Support for 30+ video conferencing apps' },
      { type: 'feature', text: 'Desktop audio capture' },
      { type: 'feature', text: '14-day free trial with 10 responses/day' },
      { type: 'feature', text: 'Stripe payment integration' },
    ]
  },
]

const getChangeIcon = (type: string) => {
  switch (type) {
    case 'feature':
      return <Sparkles className="h-4 w-4 text-gold-400" />
    case 'improvement':
      return <ArrowUpCircle className="h-4 w-4 text-emerald-400" />
    case 'fix':
      return <Bug className="h-4 w-4 text-blue-400" />
    case 'security':
      return <Shield className="h-4 w-4 text-red-400" />
    default:
      return <Zap className="h-4 w-4 text-gray-400" />
  }
}

const getChangeLabel = (type: string) => {
  switch (type) {
    case 'feature':
      return { text: 'New', bg: 'bg-gold-500/20', color: 'text-gold-400' }
    case 'improvement':
      return { text: 'Improved', bg: 'bg-emerald-500/20', color: 'text-emerald-400' }
    case 'fix':
      return { text: 'Fixed', bg: 'bg-blue-500/20', color: 'text-blue-400' }
    case 'security':
      return { text: 'Security', bg: 'bg-red-500/20', color: 'text-red-400' }
    default:
      return { text: 'Changed', bg: 'bg-gray-500/20', color: 'text-gray-400' }
  }
}

export default function Changelog() {
  return (
    <>
      <Header />
      <main className="pt-24 pb-16 px-4 min-h-screen bg-premium-bg">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-12">
            <h1 className="text-4xl font-bold mb-4 text-white">Changelog</h1>
            <p className="text-xl text-gray-400">
              Track all updates, improvements, and new features in ReadIn AI.
            </p>
          </div>

          <div className="space-y-12">
            {releases.map((release, index) => (
              <div key={index} className="relative">
                {/* Timeline line */}
                {index < releases.length - 1 && (
                  <div className="absolute left-[15px] top-12 bottom-0 w-0.5 bg-premium-border" />
                )}

                <div className="flex items-start gap-6">
                  {/* Version badge */}
                  <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                    release.type === 'major' ? 'bg-gold-500' : 'bg-premium-surface border border-premium-border'
                  }`}>
                    <span className={`text-xs font-bold ${
                      release.type === 'major' ? 'text-premium-bg' : 'text-gray-400'
                    }`}>
                      {release.version.split('.')[0]}
                    </span>
                  </div>

                  <div className="flex-1">
                    <div className="bg-premium-card border border-premium-border rounded-2xl p-6">
                      <div className="flex flex-wrap items-center gap-3 mb-3">
                        <span className={`px-3 py-1 rounded-full text-sm font-semibold ${
                          release.type === 'major'
                            ? 'bg-gold-500/20 text-gold-400'
                            : 'bg-premium-surface text-gray-400'
                        }`}>
                          v{release.version}
                        </span>
                        <span className="text-gray-500 text-sm">{release.date}</span>
                      </div>

                      <h2 className="text-xl font-bold text-white mb-2">{release.title}</h2>
                      <p className="text-gray-400 mb-6">{release.description}</p>

                      <ul className="space-y-3">
                        {release.changes.map((change, changeIndex) => {
                          const label = getChangeLabel(change.type)
                          return (
                            <li key={changeIndex} className="flex items-start gap-3">
                              <span className={`flex-shrink-0 px-2 py-0.5 rounded text-xs font-medium ${label.bg} ${label.color}`}>
                                {label.text}
                              </span>
                              <span className="text-gray-300">{change.text}</span>
                            </li>
                          )
                        })}
                      </ul>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-12 text-center">
            <p className="text-gray-400 mb-4">
              Want to be notified of new releases?
            </p>
            <Link href="/" className="inline-flex items-center px-6 py-3 bg-gold-500/10 border border-gold-500/30 rounded-xl text-gold-400 hover:bg-gold-500/20 transition-all">
              Subscribe to Updates
            </Link>
          </div>

          <div className="mt-8 text-center">
            <Link href="/" className="text-gold-400 hover:text-gold-300 transition-colors">
              &larr; Back to Home
            </Link>
          </div>
        </div>
      </main>
      <Footer />
    </>
  )
}
