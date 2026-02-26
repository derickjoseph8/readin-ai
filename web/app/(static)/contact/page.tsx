'use client'

import { useState } from 'react'
import Link from 'next/link'
import StaticHeader from '@/components/StaticHeader'
import Footer from '@/components/Footer'
import { Mail, MessageSquare, Building2, Clock, Send, CheckCircle, Loader2 } from 'lucide-react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://www.getreadin.us'

export default function Contact() {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    subject: 'general',
    message: ''
  })
  const [submitted, setSubmitted] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      const response = await fetch(`${API_URL}/api/v1/contact`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      })

      if (response.ok) {
        setSubmitted(true)
        setFormData({ name: '', email: '', subject: 'general', message: '' })
      } else {
        setError('Failed to send message. Please try again.')
      }
    } catch {
      setError('Unable to connect. Please email us directly at support@getreadin.ai')
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <StaticHeader />
      <main className="pt-24 pb-16 px-4 min-h-screen bg-premium-bg">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-12">
            <h1 className="text-4xl font-bold mb-4 text-white">Contact Us</h1>
            <p className="text-xl text-gray-400">
              Have a question or need help? We&apos;re here for you.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8 mb-12">
            <div className="bg-premium-card border border-premium-border rounded-2xl p-6 text-center">
              <div className="w-12 h-12 bg-gold-500/20 rounded-xl flex items-center justify-center mx-auto mb-4">
                <Mail className="h-6 w-6 text-gold-400" />
              </div>
              <h3 className="text-lg font-semibold text-white mb-2">Email Support</h3>
              <p className="text-gray-400 text-sm mb-3">For general inquiries</p>
              <a href="mailto:support@getreadin.ai" className="text-gold-400 hover:text-gold-300 transition-colors">
                support@getreadin.ai
              </a>
            </div>

            <div className="bg-premium-card border border-premium-border rounded-2xl p-6 text-center">
              <div className="w-12 h-12 bg-emerald-500/20 rounded-xl flex items-center justify-center mx-auto mb-4">
                <Building2 className="h-6 w-6 text-emerald-400" />
              </div>
              <h3 className="text-lg font-semibold text-white mb-2">Enterprise Sales</h3>
              <p className="text-gray-400 text-sm mb-3">For team and enterprise plans</p>
              <a href="mailto:sales@getreadin.ai" className="text-gold-400 hover:text-gold-300 transition-colors">
                sales@getreadin.ai
              </a>
            </div>

            <div className="bg-premium-card border border-premium-border rounded-2xl p-6 text-center">
              <div className="w-12 h-12 bg-gold-500/20 rounded-xl flex items-center justify-center mx-auto mb-4">
                <Clock className="h-6 w-6 text-gold-400" />
              </div>
              <h3 className="text-lg font-semibold text-white mb-2">Response Time</h3>
              <p className="text-gray-400 text-sm mb-3">We typically respond within</p>
              <span className="text-gold-400">24 hours</span>
            </div>
          </div>

          <div className="max-w-2xl mx-auto">
            <div className="bg-premium-card border border-premium-border rounded-2xl p-8">
              {submitted ? (
                <div className="text-center py-8">
                  <div className="w-16 h-16 bg-emerald-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
                    <CheckCircle className="h-8 w-8 text-emerald-400" />
                  </div>
                  <h3 className="text-2xl font-bold text-white mb-2">Message Sent!</h3>
                  <p className="text-gray-400 mb-6">
                    Thank you for reaching out. We&apos;ll get back to you within 24 hours.
                  </p>
                  <button
                    onClick={() => setSubmitted(false)}
                    className="text-gold-400 hover:text-gold-300 transition-colors"
                  >
                    Send another message
                  </button>
                </div>
              ) : (
                <>
                  <div className="flex items-center mb-6">
                    <MessageSquare className="h-6 w-6 text-gold-400 mr-3" />
                    <h2 className="text-2xl font-bold text-white">Send us a message</h2>
                  </div>

                  <form onSubmit={handleSubmit} className="space-y-6">
                    <div className="grid md:grid-cols-2 gap-6">
                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-2">
                          Your Name
                        </label>
                        <input
                          type="text"
                          required
                          value={formData.name}
                          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                          className="w-full px-4 py-3 bg-premium-surface border border-premium-border rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-gold-500/50 transition-colors"
                          placeholder="John Doe"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-2">
                          Email Address
                        </label>
                        <input
                          type="email"
                          required
                          value={formData.email}
                          onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                          className="w-full px-4 py-3 bg-premium-surface border border-premium-border rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-gold-500/50 transition-colors"
                          placeholder="john@example.com"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Subject
                      </label>
                      <select
                        value={formData.subject}
                        onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
                        className="w-full px-4 py-3 bg-premium-surface border border-premium-border rounded-xl text-white focus:outline-none focus:border-gold-500/50 transition-colors"
                      >
                        <option value="general">General Inquiry</option>
                        <option value="support">Technical Support</option>
                        <option value="billing">Billing Question</option>
                        <option value="enterprise">Enterprise Sales</option>
                        <option value="partnership">Partnership Opportunity</option>
                        <option value="feedback">Feedback/Suggestion</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Message
                      </label>
                      <textarea
                        required
                        rows={5}
                        value={formData.message}
                        onChange={(e) => setFormData({ ...formData, message: e.target.value })}
                        className="w-full px-4 py-3 bg-premium-surface border border-premium-border rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-gold-500/50 transition-colors resize-none"
                        placeholder="Tell us how we can help..."
                      />
                    </div>

                    {error && (
                      <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-sm">
                        {error}
                      </div>
                    )}

                    <button
                      type="submit"
                      disabled={loading}
                      className="w-full py-4 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-semibold rounded-xl hover:shadow-gold transition-all flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {loading ? (
                        <Loader2 className="h-5 w-5 animate-spin" />
                      ) : (
                        <>
                          <Send className="h-5 w-5 mr-2" />
                          Send Message
                        </>
                      )}
                    </button>
                  </form>
                </>
              )}
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
