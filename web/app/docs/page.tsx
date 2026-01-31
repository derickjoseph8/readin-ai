'use client'

import Link from 'next/link'
import Header from '@/components/Header'
import Footer from '@/components/Footer'
import { Book, Download, Settings, Mic, Brain, Mail, Shield, Users, Briefcase, HelpCircle } from 'lucide-react'

const docSections = [
  {
    title: 'Getting Started',
    icon: Download,
    color: 'text-gold-400',
    bgColor: 'bg-gold-500/20',
    links: [
      { title: 'Installation Guide', description: 'Download and install ReadIn AI on Windows' },
      { title: 'System Requirements', description: 'Minimum specs for optimal performance' },
      { title: 'Quick Start Tutorial', description: 'Get up and running in 5 minutes' },
      { title: 'Account Setup', description: 'Create your account and select your profession' },
    ]
  },
  {
    title: 'Core Features',
    icon: Mic,
    color: 'text-emerald-400',
    bgColor: 'bg-emerald-500/20',
    links: [
      { title: 'Real-Time Transcription', description: 'How audio capture and Whisper work' },
      { title: 'AI-Powered Responses', description: 'Getting intelligent talking points' },
      { title: 'Profession Customization', description: 'How AI tailors responses to your career' },
      { title: 'Overlay Interface', description: 'Using the floating overlay during calls' },
    ]
  },
  {
    title: 'Meeting Intelligence',
    icon: Brain,
    color: 'text-gold-400',
    bgColor: 'bg-gold-500/20',
    links: [
      { title: 'Meeting Summaries', description: 'Auto-generated notes sent to your email' },
      { title: 'Action Item Tracking', description: 'WHO does WHAT by WHEN extraction' },
      { title: 'Commitment Reminders', description: 'Never forget what you promised' },
      { title: 'Pre-Meeting Briefings', description: 'Context and preparation before calls' },
    ]
  },
  {
    title: 'ML Learning',
    icon: Brain,
    color: 'text-emerald-400',
    bgColor: 'bg-emerald-500/20',
    links: [
      { title: 'How ML Learns You', description: 'Understanding the personalization engine' },
      { title: 'Profession Knowledge Base', description: 'Industry-specific AI customization' },
      { title: 'Topic Tracking', description: 'How we track what you discuss' },
      { title: 'Communication Style', description: 'Learning your unique patterns' },
    ]
  },
  {
    title: 'Teams & Organizations',
    icon: Users,
    color: 'text-gold-400',
    bgColor: 'bg-gold-500/20',
    links: [
      { title: 'Creating an Organization', description: 'Set up your team account' },
      { title: 'Inviting Team Members', description: 'How team members join for free' },
      { title: 'Admin Controls', description: 'Managing your organization' },
      { title: 'Shared Insights', description: 'Team analytics and reporting' },
    ]
  },
  {
    title: 'Job Interview Mode',
    icon: Briefcase,
    color: 'text-emerald-400',
    bgColor: 'bg-emerald-500/20',
    links: [
      { title: 'Job Application Tracker', description: 'Track your applications and interviews' },
      { title: 'Interview Improvement', description: 'ML-powered coaching over time' },
      { title: 'Response Polishing', description: 'Getting better with each interview' },
      { title: 'Performance Analytics', description: 'Track your interview performance' },
    ]
  },
  {
    title: 'Privacy & Security',
    icon: Shield,
    color: 'text-gold-400',
    bgColor: 'bg-gold-500/20',
    links: [
      { title: 'Local Audio Processing', description: 'How Whisper runs on your device' },
      { title: 'Data Encryption', description: 'How we protect your data' },
      { title: 'Data Retention', description: 'What we store and for how long' },
      { title: 'Recording Consent', description: 'Legal considerations' },
    ]
  },
  {
    title: 'Settings & Configuration',
    icon: Settings,
    color: 'text-emerald-400',
    bgColor: 'bg-emerald-500/20',
    links: [
      { title: 'Audio Settings', description: 'Microphone and speaker configuration' },
      { title: 'Hotkeys', description: 'Keyboard shortcuts for quick access' },
      { title: 'Email Preferences', description: 'Control what emails you receive' },
      { title: 'Display Options', description: 'Customize the overlay appearance' },
    ]
  },
]

export default function Documentation() {
  return (
    <>
      <Header />
      <main className="pt-24 pb-16 px-4 min-h-screen bg-premium-bg">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-12">
            <div className="w-16 h-16 bg-gold-500/20 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <Book className="h-8 w-8 text-gold-400" />
            </div>
            <h1 className="text-4xl font-bold mb-4 text-white">Documentation</h1>
            <p className="text-xl text-gray-400 max-w-2xl mx-auto">
              Everything you need to get the most out of ReadIn AI. From quick start guides to advanced features.
            </p>
          </div>

          {/* Quick Links */}
          <div className="grid md:grid-cols-3 gap-4 mb-12">
            <Link href="/download" className="flex items-center p-4 bg-premium-card border border-premium-border rounded-xl hover:border-gold-500/30 transition-all group">
              <Download className="h-5 w-5 text-gold-400 mr-3" />
              <span className="text-white group-hover:text-gold-400 transition-colors">Download App</span>
            </Link>
            <Link href="/contact" className="flex items-center p-4 bg-premium-card border border-premium-border rounded-xl hover:border-gold-500/30 transition-all group">
              <Mail className="h-5 w-5 text-gold-400 mr-3" />
              <span className="text-white group-hover:text-gold-400 transition-colors">Contact Support</span>
            </Link>
            <Link href="/#faq" className="flex items-center p-4 bg-premium-card border border-premium-border rounded-xl hover:border-gold-500/30 transition-all group">
              <HelpCircle className="h-5 w-5 text-gold-400 mr-3" />
              <span className="text-white group-hover:text-gold-400 transition-colors">View FAQ</span>
            </Link>
          </div>

          {/* Documentation Sections */}
          <div className="grid md:grid-cols-2 gap-8">
            {docSections.map((section, index) => (
              <div key={index} className="bg-premium-card border border-premium-border rounded-2xl p-6">
                <div className="flex items-center mb-4">
                  <div className={`w-10 h-10 ${section.bgColor} rounded-xl flex items-center justify-center mr-3`}>
                    <section.icon className={`h-5 w-5 ${section.color}`} />
                  </div>
                  <h2 className="text-xl font-semibold text-white">{section.title}</h2>
                </div>
                <ul className="space-y-3">
                  {section.links.map((link, linkIndex) => (
                    <li key={linkIndex}>
                      <a href="#" className="block p-3 rounded-lg hover:bg-premium-surface transition-colors group">
                        <span className="text-white group-hover:text-gold-400 transition-colors font-medium">
                          {link.title}
                        </span>
                        <p className="text-gray-500 text-sm mt-1">{link.description}</p>
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>

          <div className="mt-12 text-center">
            <p className="text-gray-400 mb-4">
              Can&apos;t find what you&apos;re looking for?
            </p>
            <Link href="/contact" className="inline-flex items-center px-6 py-3 bg-gold-500/10 border border-gold-500/30 rounded-xl text-gold-400 hover:bg-gold-500/20 transition-all">
              <Mail className="h-4 w-4 mr-2" />
              Contact Support
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
