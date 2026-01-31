'use client'

import { Shield, Lock, Eye, Server, CheckCircle, Award } from 'lucide-react'

const badges = [
  {
    icon: Shield,
    title: '100% Private',
    description: 'Audio never leaves your device',
  },
  {
    icon: Lock,
    title: 'End-to-End Encrypted',
    description: 'All data transfers secured',
  },
  {
    icon: Eye,
    title: 'No Data Storage',
    description: 'Nothing saved after sessions',
  },
  {
    icon: Server,
    title: 'Local Processing',
    description: 'Whisper AI runs on your device',
  },
  {
    icon: CheckCircle,
    title: 'SOC 2 Compliant',
    description: 'Enterprise-grade security',
  },
  {
    icon: Award,
    title: 'GDPR Ready',
    description: 'Full EU compliance',
  },
]

export default function TrustBadges() {
  return (
    <section className="py-12 px-4 border-y border-premium-border bg-premium-surface/30">
      <div className="max-w-7xl mx-auto">
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-6">
          {badges.map((badge, index) => (
            <div
              key={index}
              className="flex flex-col items-center text-center p-4"
            >
              <div className="w-12 h-12 bg-emerald-500/10 rounded-xl flex items-center justify-center mb-3">
                <badge.icon className="h-6 w-6 text-emerald-400" />
              </div>
              <h4 className="font-semibold text-white text-sm mb-1">{badge.title}</h4>
              <p className="text-xs text-gray-500">{badge.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
