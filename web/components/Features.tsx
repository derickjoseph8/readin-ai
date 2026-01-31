'use client'

import { Zap, Shield, Monitor, Mic, Brain, Eye, Mail, CheckSquare, TrendingUp, Bell, Users, Briefcase } from 'lucide-react'

const features = [
  {
    icon: Zap,
    title: 'Instant Responses',
    description: 'Get AI-powered talking points in under 2 seconds. No awkward pauses or fumbling for words.',
    color: 'from-gold-500 to-gold-600',
    iconColor: 'text-gold-400',
  },
  {
    icon: Mail,
    title: 'Smart Meeting Notes',
    description: 'Auto-generated meeting summaries sent straight to your email. Never miss a key discussion point.',
    color: 'from-emerald-500 to-emerald-600',
    iconColor: 'text-emerald-400',
  },
  {
    icon: CheckSquare,
    title: 'Action Item Tracking',
    description: 'Automatically extract WHO does WHAT by WHEN. Track tasks and commitments across all your meetings.',
    color: 'from-gold-500 to-gold-600',
    iconColor: 'text-gold-400',
  },
  {
    icon: TrendingUp,
    title: 'Interview Improvement',
    description: 'ML-powered coaching that learns from every interview. Get better with each conversation.',
    color: 'from-emerald-500 to-emerald-600',
    iconColor: 'text-emerald-400',
  },
  {
    icon: Bell,
    title: 'Commitment Reminders',
    description: 'Email alerts before deadlines. Never forget what you promised to do or when it\'s due.',
    color: 'from-gold-500 to-gold-600',
    iconColor: 'text-gold-400',
  },
  {
    icon: Users,
    title: 'Participant Memory',
    description: 'Remember what everyone said across meetings. Get context on participants before every call.',
    color: 'from-emerald-500 to-emerald-600',
    iconColor: 'text-emerald-400',
  },
  {
    icon: Briefcase,
    title: 'Job Application Tracker',
    description: 'Track your interviews across companies. Polish responses and improve with each round.',
    color: 'from-gold-500 to-gold-600',
    iconColor: 'text-gold-400',
  },
  {
    icon: Brain,
    title: 'Pre-Meeting Briefings',
    description: 'Get context and preparation materials before every meeting. Know what to discuss and what to avoid.',
    color: 'from-emerald-500 to-emerald-600',
    iconColor: 'text-emerald-400',
  },
  {
    icon: Shield,
    title: 'Privacy First',
    description: 'Audio is processed locally on your device. Your data is encrypted and you control what\'s stored.',
    color: 'from-gold-500 to-gold-600',
    iconColor: 'text-gold-400',
  },
  {
    icon: Monitor,
    title: 'Works Everywhere',
    description: 'Teams, Zoom, Google Meet, Webex, and 30+ video conferencing tools. Desktop and browser calls.',
    color: 'from-emerald-500 to-emerald-600',
    iconColor: 'text-emerald-400',
  },
  {
    icon: Mic,
    title: 'Real-Time Transcription',
    description: 'Powered by OpenAI Whisper running locally. Accurate speech-to-text without cloud uploads.',
    color: 'from-gold-500 to-gold-600',
    iconColor: 'text-gold-400',
  },
  {
    icon: Eye,
    title: 'Glanceable Design',
    description: 'Bullet points, not paragraphs. Scan in 2 seconds, rephrase in your own words, sound natural.',
    color: 'from-emerald-500 to-emerald-600',
    iconColor: 'text-emerald-400',
  },
]

export default function Features() {
  return (
    <section id="features" className="py-24 px-4 bg-premium-surface/50">
      <div className="max-w-7xl mx-auto">
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <h2 className="text-4xl md:text-5xl font-bold mb-6">
            Your Complete{' '}
            <span className="text-gradient-gold">Meeting Intelligence Platform</span>
          </h2>
          <p className="text-xl text-gray-400">
            From real-time assistance to post-meeting summaries. Never miss a detail, always be prepared.
          </p>
        </div>

        {/* Features Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature, index) => (
            <div
              key={index}
              className="group p-6 bg-premium-card rounded-2xl border border-premium-border hover:border-gold-500/30 transition-all duration-300 hover:-translate-y-1"
            >
              <div className={`w-12 h-12 bg-gradient-to-br ${feature.color} rounded-xl flex items-center justify-center mb-4 group-hover:scale-110 group-hover:shadow-gold transition-all duration-300`}>
                <feature.icon className="h-6 w-6 text-premium-bg" />
              </div>
              <h3 className="text-xl font-semibold mb-2 text-white">{feature.title}</h3>
              <p className="text-gray-400">{feature.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
