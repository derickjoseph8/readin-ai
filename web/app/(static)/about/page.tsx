'use client'

import Link from 'next/link'
import Header from '@/components/Header'
import Footer from '@/components/Footer'
import { Target, Users, Shield, Sparkles, Globe, Heart } from 'lucide-react'

const values = [
  {
    icon: Shield,
    title: 'Privacy First',
    description: 'Your audio never leaves your device. Whisper AI runs locally for complete privacy and security.',
  },
  {
    icon: Sparkles,
    title: 'AI That Learns You',
    description: 'Our ML adapts to your communication style, profession, and preferences over time.',
  },
  {
    icon: Users,
    title: 'Built for Professionals',
    description: '60+ profession profiles ensure AI responses are tailored to your industry and expertise.',
  },
  {
    icon: Globe,
    title: 'Works Everywhere',
    description: 'Seamlessly integrates with Zoom, Teams, Meet, and any video conferencing platform.',
  },
]

const team = [
  {
    name: 'Derick Joseph',
    role: 'Founder & CEO',
    bio: 'Building the future of meeting intelligence.',
  },
]

export default function AboutPage() {
  return (
    <>
      <Header />
      <main className="pt-24 pb-16 px-4 min-h-screen bg-premium-bg">
        <div className="max-w-5xl mx-auto">
          {/* Hero Section */}
          <div className="text-center mb-16">
            <h1 className="text-4xl md:text-5xl font-bold mb-6 text-white">
              About{' '}
              <span className="text-gradient-gold">ReadIn AI</span>
            </h1>
            <p className="text-xl text-gray-400 max-w-3xl mx-auto">
              We're on a mission to help professionals sound brilliant in every meeting.
              Our AI-powered assistant provides real-time talking points so you can focus on
              what matters most - building relationships and closing deals.
            </p>
          </div>

          {/* Mission Section */}
          <div className="bg-premium-card border border-premium-border rounded-2xl p-8 md:p-12 mb-16">
            <div className="flex items-center justify-center mb-6">
              <div className="w-16 h-16 bg-gold-500/20 rounded-2xl flex items-center justify-center">
                <Target className="h-8 w-8 text-gold-400" />
              </div>
            </div>
            <h2 className="text-2xl md:text-3xl font-bold text-center mb-4 text-white">Our Mission</h2>
            <p className="text-gray-400 text-center text-lg max-w-2xl mx-auto">
              To democratize meeting intelligence by giving every professional access to
              AI-powered insights that help them communicate more effectively, make better
              decisions, and never miss an important detail.
            </p>
          </div>

          {/* Values Section */}
          <div className="mb-16">
            <h2 className="text-2xl md:text-3xl font-bold text-center mb-8 text-white">Our Values</h2>
            <div className="grid md:grid-cols-2 gap-6">
              {values.map((value, index) => (
                <div key={index} className="bg-premium-card border border-premium-border rounded-xl p-6 hover:border-gold-500/30 transition-all">
                  <div className="w-12 h-12 bg-gold-500/20 rounded-xl flex items-center justify-center mb-4">
                    <value.icon className="h-6 w-6 text-gold-400" />
                  </div>
                  <h3 className="text-lg font-semibold text-white mb-2">{value.title}</h3>
                  <p className="text-gray-400">{value.description}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Story Section */}
          <div className="bg-gradient-to-b from-gold-500/10 to-transparent border border-gold-500/30 rounded-2xl p-8 md:p-12 mb-16">
            <h2 className="text-2xl md:text-3xl font-bold text-center mb-6 text-white">Our Story</h2>
            <div className="text-gray-400 space-y-4 max-w-3xl mx-auto">
              <p>
                ReadIn AI was born from a simple observation: professionals spend countless hours
                in meetings, yet often struggle to articulate their thoughts perfectly in real-time.
              </p>
              <p>
                We believed there had to be a better way. What if AI could listen alongside you
                and provide intelligent talking points exactly when you need them? What if it
                could learn your profession, your style, and your preferences to become your
                personal meeting copilot?
              </p>
              <p>
                That vision became ReadIn AI - a privacy-first, AI-powered meeting assistant
                that runs locally on your device, learns from every conversation, and helps
                you sound brilliant in every meeting.
              </p>
            </div>
          </div>

          {/* CTA Section */}
          <div className="text-center">
            <div className="inline-flex items-center px-4 py-2 bg-emerald-500/10 border border-emerald-500/20 rounded-full mb-6">
              <Heart className="h-4 w-4 text-emerald-400 mr-2" />
              <span className="text-sm text-emerald-300">Join thousands of professionals</span>
            </div>
            <h2 className="text-2xl md:text-3xl font-bold mb-4 text-white">Ready to sound brilliant?</h2>
            <p className="text-gray-400 mb-8 max-w-xl mx-auto">
              Start your free 7-day trial today. No credit card required.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link
                href="/download"
                className="px-8 py-4 bg-gradient-to-r from-gold-600 to-gold-500 rounded-xl font-semibold text-premium-bg hover:shadow-gold transition-all"
              >
                Download Free Trial
              </Link>
              <Link
                href="/contact"
                className="px-8 py-4 bg-premium-surface border border-premium-border rounded-xl font-semibold text-white hover:border-gold-500/30 transition-all"
              >
                Contact Us
              </Link>
            </div>
          </div>

          <div className="mt-12 text-center">
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
