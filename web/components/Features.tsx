'use client'

import { Zap, Shield, Monitor, Mic, Brain, Eye } from 'lucide-react'

const features = [
  {
    icon: Zap,
    title: 'Instant Responses',
    description: 'Get AI-powered talking points in under 2 seconds. No awkward pauses or fumbling for words.',
    color: 'from-yellow-500 to-orange-500',
  },
  {
    icon: Shield,
    title: 'Privacy First',
    description: 'Audio is processed locally on your device. Only transcribed text reaches our AI — nothing is stored.',
    color: 'from-green-500 to-emerald-500',
  },
  {
    icon: Monitor,
    title: 'Works Everywhere',
    description: 'Teams, Zoom, Google Meet, Webex, and 30+ video conferencing tools. Desktop and browser calls.',
    color: 'from-blue-500 to-cyan-500',
  },
  {
    icon: Mic,
    title: 'Real-Time Transcription',
    description: 'Powered by OpenAI Whisper running locally. Accurate speech-to-text without cloud uploads.',
    color: 'from-purple-500 to-pink-500',
  },
  {
    icon: Brain,
    title: 'Context-Aware AI',
    description: 'Remembers the last 3 exchanges for coherent, relevant responses that build on the conversation.',
    color: 'from-red-500 to-rose-500',
  },
  {
    icon: Eye,
    title: 'Glanceable Design',
    description: 'Bullet points, not paragraphs. Scan in 2 seconds, rephrase in your own words, sound natural.',
    color: 'from-indigo-500 to-violet-500',
  },
]

export default function Features() {
  return (
    <section id="features" className="py-24 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <h2 className="text-4xl md:text-5xl font-bold mb-6">
            Everything You Need to{' '}
            <span className="text-gradient">Sound Brilliant</span>
          </h2>
          <p className="text-xl text-gray-400">
            Powerful features designed to help you communicate confidently in any live conversation.
          </p>
        </div>

        {/* Features Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
          {features.map((feature, index) => (
            <div
              key={index}
              className="group p-6 bg-dark-900/50 rounded-2xl border border-white/5 hover:border-white/10 transition-all hover:-translate-y-1"
            >
              <div className={`w-12 h-12 bg-gradient-to-br ${feature.color} rounded-xl flex items-center justify-center mb-4 group-hover:scale-110 transition`}>
                <feature.icon className="h-6 w-6 text-white" />
              </div>
              <h3 className="text-xl font-semibold mb-2">{feature.title}</h3>
              <p className="text-gray-400">{feature.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
