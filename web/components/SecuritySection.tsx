'use client'

import { Shield, Mic, Cloud, Lock, Server, Eye } from 'lucide-react'

const securityFeatures = [
  {
    icon: Mic,
    title: 'Local Audio Processing',
    description: 'Your audio is transcribed directly on your device using OpenAI Whisper. No audio ever leaves your computer.',
  },
  {
    icon: Cloud,
    title: 'Minimal Data Transfer',
    description: 'Only transcribed text is sent to generate responses. No audio recordings, no persistent storage.',
  },
  {
    icon: Lock,
    title: 'Encrypted Transmission',
    description: 'All data between your device and our servers uses TLS 1.3 encryption — the same security banks use.',
  },
  {
    icon: Server,
    title: 'No Data Retention',
    description: 'Conversations are processed in real-time and immediately discarded. We don\'t build profiles or store history.',
  },
]

export default function SecuritySection() {
  return (
    <section className="py-24 px-4">
      <div className="max-w-7xl mx-auto">
        <div className="grid lg:grid-cols-2 gap-16 items-center">
          {/* Left: Content */}
          <div>
            <div className="inline-flex items-center px-4 py-2 bg-emerald-500/10 border border-emerald-500/30 rounded-full mb-6">
              <Shield className="h-4 w-4 text-emerald-400 mr-2" />
              <span className="text-sm text-emerald-300">Privacy First</span>
            </div>

            <h2 className="text-4xl md:text-5xl font-bold mb-6">
              Your Privacy is{' '}
              <span className="text-gradient-gold">Non-Negotiable</span>
            </h2>

            <p className="text-xl text-gray-400 mb-8">
              We built ReadIn AI with privacy at its core. Your conversations are your own — we never listen, store, or sell your data.
            </p>

            <div className="space-y-6">
              {securityFeatures.map((feature, index) => (
                <div key={index} className="flex items-start">
                  <div className="w-12 h-12 bg-emerald-500/10 rounded-xl flex items-center justify-center mr-4 flex-shrink-0">
                    <feature.icon className="h-6 w-6 text-emerald-400" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-white mb-1">{feature.title}</h4>
                    <p className="text-gray-400 text-sm">{feature.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Right: Visual */}
          <div className="relative">
            <div className="glass-gold rounded-2xl p-8 glow-gold">
              {/* Privacy Flow Diagram */}
              <div className="space-y-6">
                {/* Step 1 */}
                <div className="flex items-center">
                  <div className="w-14 h-14 bg-premium-surface rounded-xl flex items-center justify-center border border-premium-border">
                    <Mic className="h-7 w-7 text-gold-400" />
                  </div>
                  <div className="flex-1 mx-4 h-0.5 bg-gradient-to-r from-gold-500 to-emerald-500" />
                  <div className="px-4 py-2 bg-emerald-500/10 border border-emerald-500/30 rounded-lg">
                    <span className="text-sm text-emerald-400">On Your Device</span>
                  </div>
                </div>

                <div className="pl-7 border-l-2 border-gold-500/30 ml-0">
                  <p className="text-gray-500 text-sm py-2">Audio transcribed locally</p>
                </div>

                {/* Step 2 */}
                <div className="flex items-center">
                  <div className="w-14 h-14 bg-premium-surface rounded-xl flex items-center justify-center border border-premium-border">
                    <Lock className="h-7 w-7 text-gold-400" />
                  </div>
                  <div className="flex-1 mx-4 h-0.5 bg-gradient-to-r from-gold-500 to-emerald-500" />
                  <div className="px-4 py-2 bg-emerald-500/10 border border-emerald-500/30 rounded-lg">
                    <span className="text-sm text-emerald-400">TLS 1.3 Encrypted</span>
                  </div>
                </div>

                <div className="pl-7 border-l-2 border-gold-500/30 ml-0">
                  <p className="text-gray-500 text-sm py-2">Text only, no audio</p>
                </div>

                {/* Step 3 */}
                <div className="flex items-center">
                  <div className="w-14 h-14 bg-premium-surface rounded-xl flex items-center justify-center border border-premium-border">
                    <Eye className="h-7 w-7 text-gold-400" />
                  </div>
                  <div className="flex-1 mx-4 h-0.5 bg-gradient-to-r from-gold-500 to-emerald-500" />
                  <div className="px-4 py-2 bg-emerald-500/10 border border-emerald-500/30 rounded-lg">
                    <span className="text-sm text-emerald-400">Instantly Deleted</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Decorative elements */}
            <div className="absolute -top-4 -right-4 w-24 h-24 bg-gradient-to-br from-emerald-500 to-emerald-600 rounded-xl opacity-20 blur-xl" />
            <div className="absolute -bottom-4 -left-4 w-24 h-24 bg-gradient-to-br from-gold-500 to-gold-600 rounded-xl opacity-20 blur-xl" />
          </div>
        </div>
      </div>
    </section>
  )
}
