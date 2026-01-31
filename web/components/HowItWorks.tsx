'use client'

import { Headphones, MessageSquare, Sparkles, UserCheck } from 'lucide-react'

const steps = [
  {
    icon: Headphones,
    number: '01',
    title: 'Start Your Meeting',
    description: 'Open Teams, Zoom, or any video call. ReadIn AI automatically detects when your meeting starts.',
  },
  {
    icon: MessageSquare,
    number: '02',
    title: 'Someone Asks a Question',
    description: 'The app listens and transcribes in real-time using local AI. Your audio never leaves your device.',
  },
  {
    icon: Sparkles,
    number: '03',
    title: 'Get Instant Talking Points',
    description: 'Within 2 seconds, you see 2-4 bullet points with key ideas to address the question.',
  },
  {
    icon: UserCheck,
    number: '04',
    title: 'Glance, Rephrase, Deliver',
    description: 'Quick glance at the points, rephrase in your own words, and respond naturally and confidently.',
  },
]

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="py-24 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <h2 className="text-4xl md:text-5xl font-bold mb-6">
            How It{' '}
            <span className="text-gradient-gold">Works</span>
          </h2>
          <p className="text-xl text-gray-400">
            From question to confident answer in seconds — without looking like you're reading a script.
          </p>
        </div>

        {/* Steps */}
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
          {steps.map((step, index) => (
            <div key={index} className="relative">
              {/* Connector line */}
              {index < steps.length - 1 && (
                <div className="hidden lg:block absolute top-12 left-full w-full h-0.5 bg-gradient-to-r from-gold-500/50 to-transparent" />
              )}

              <div className="text-center">
                {/* Icon */}
                <div className="relative inline-block mb-6">
                  <div className="w-24 h-24 bg-premium-card rounded-2xl flex items-center justify-center border border-premium-border group-hover:border-gold-500/30 transition-colors">
                    <step.icon className="h-10 w-10 text-gold-400" />
                  </div>
                  <span className="absolute -top-2 -right-2 w-8 h-8 bg-gradient-to-br from-gold-500 to-gold-600 rounded-lg flex items-center justify-center text-sm font-bold text-premium-bg">
                    {step.number}
                  </span>
                </div>

                {/* Content */}
                <h3 className="text-xl font-semibold mb-3 text-white">{step.title}</h3>
                <p className="text-gray-400">{step.description}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Demo Video Placeholder */}
        <div className="mt-16 max-w-4xl mx-auto">
          <div className="relative aspect-video bg-premium-card rounded-2xl border border-premium-border flex items-center justify-center overflow-hidden group cursor-pointer hover:border-gold-500/30 transition-colors">
            <div className="absolute inset-0 bg-gradient-to-br from-gold-500/5 to-emerald-500/5" />
            <div className="relative z-10 text-center">
              <div className="w-20 h-20 bg-gradient-to-br from-gold-500 to-gold-600 rounded-full flex items-center justify-center mb-4 mx-auto group-hover:scale-110 group-hover:shadow-gold transition-all duration-300">
                <div className="w-0 h-0 border-l-[20px] border-l-premium-bg border-y-[12px] border-y-transparent ml-1" />
              </div>
              <p className="text-gray-400">Watch ReadIn AI in action</p>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
