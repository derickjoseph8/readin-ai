'use client'

import { useState, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import {
  ArrowLeft,
  Send,
  AlertCircle,
  FileText,
  CreditCard,
  Settings,
  HelpCircle,
  Bug,
  Lightbulb,
  Building2,
  Wrench
} from 'lucide-react'
import { supportApi } from '@/lib/api/admin'

const categories = [
  { id: 'technical', name: 'Technical Support', icon: Wrench, description: 'App issues, bugs, or technical problems' },
  { id: 'billing', name: 'Billing & Subscription', icon: CreditCard, description: 'Payments, plans, invoices, refunds' },
  { id: 'enterprise', name: 'Enterprise Inquiry', icon: Building2, description: 'Custom solutions, volume licensing' },
  { id: 'account', name: 'Account Help', icon: Settings, description: 'Login, settings, profile issues' },
  { id: 'feature', name: 'Feature Request', icon: Lightbulb, description: 'Suggestions and ideas' },
  { id: 'general', name: 'General Question', icon: HelpCircle, description: 'Other inquiries' },
]

const priorities = [
  { id: 'low', name: 'Low', description: 'General questions, no urgency' },
  { id: 'medium', name: 'Medium', description: 'Issues affecting work, can wait' },
  { id: 'high', name: 'High', description: 'Significant impact on productivity' },
  { id: 'urgent', name: 'Urgent', description: 'Critical issue, completely blocked' },
]

export default function NewTicketPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const categoryParam = searchParams.get('category')

  const [category, setCategory] = useState('')
  const [priority, setPriority] = useState('medium')
  const [subject, setSubject] = useState('')
  const [description, setDescription] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')

  // Set initial category from URL param
  useEffect(() => {
    if (categoryParam && categories.some(c => c.id === categoryParam)) {
      setCategory(categoryParam)
    }
  }, [categoryParam])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (!category) {
      setError('Please select a category')
      return
    }
    if (!subject.trim()) {
      setError('Please enter a subject')
      return
    }
    if (!description.trim()) {
      setError('Please describe your issue')
      return
    }

    setIsSubmitting(true)

    try {
      const ticket = await supportApi.createTicket({
        category,
        priority,
        subject: subject.trim(),
        description: description.trim(),
      })
      router.push(`/dashboard/support/${ticket.id}`)
    } catch (err: any) {
      setError(err.message || 'Failed to create ticket. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center space-x-4">
        <Link
          href="/dashboard/support"
          className="p-2 text-gray-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-white">Create Support Ticket</h1>
          <p className="text-gray-400 mt-1">Describe your issue and we'll help you resolve it</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Error Message */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 flex items-center text-red-400">
            <AlertCircle className="h-5 w-5 mr-3 flex-shrink-0" />
            {error}
          </div>
        )}

        {/* Category Selection */}
        <div className="bg-premium-card border border-premium-border rounded-xl p-6">
          <h2 className="text-lg font-semibold text-white mb-4">What do you need help with?</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {categories.map((cat) => (
              <button
                key={cat.id}
                type="button"
                onClick={() => setCategory(cat.id)}
                className={`flex items-start p-4 rounded-lg border transition-colors text-left ${
                  category === cat.id
                    ? 'bg-gold-500/10 border-gold-500/30 text-gold-400'
                    : 'bg-premium-surface border-premium-border text-white hover:border-gold-500/20'
                }`}
              >
                <cat.icon className={`h-5 w-5 mr-3 mt-0.5 flex-shrink-0 ${
                  category === cat.id ? 'text-gold-400' : 'text-gray-400'
                }`} />
                <div>
                  <p className="font-medium">{cat.name}</p>
                  <p className="text-sm text-gray-500 mt-0.5">{cat.description}</p>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Priority Selection */}
        <div className="bg-premium-card border border-premium-border rounded-xl p-6">
          <h2 className="text-lg font-semibold text-white mb-4">How urgent is this?</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {priorities.map((p) => (
              <button
                key={p.id}
                type="button"
                onClick={() => setPriority(p.id)}
                className={`p-3 rounded-lg border transition-colors text-center ${
                  priority === p.id
                    ? 'bg-gold-500/10 border-gold-500/30 text-gold-400'
                    : 'bg-premium-surface border-premium-border text-white hover:border-gold-500/20'
                }`}
              >
                <p className="font-medium capitalize">{p.name}</p>
                <p className="text-xs text-gray-500 mt-1 hidden sm:block">{p.description}</p>
              </button>
            ))}
          </div>
        </div>

        {/* Subject & Description */}
        <div className="bg-premium-card border border-premium-border rounded-xl p-6 space-y-4">
          <div>
            <label htmlFor="subject" className="block text-sm font-medium text-white mb-2">
              Subject
            </label>
            <input
              type="text"
              id="subject"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              placeholder="Brief summary of your issue"
              className="w-full px-4 py-2 bg-premium-surface border border-premium-border rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-gold-500"
              maxLength={200}
            />
          </div>

          <div>
            <label htmlFor="description" className="block text-sm font-medium text-white mb-2">
              Description
            </label>
            <textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Please provide as much detail as possible. Include steps to reproduce the issue, error messages, and what you expected to happen."
              rows={6}
              className="w-full px-4 py-3 bg-premium-surface border border-premium-border rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-gold-500 resize-none"
            />
            <p className="text-xs text-gray-500 mt-2">
              The more details you provide, the faster we can help you.
            </p>
          </div>
        </div>

        {/* Submit */}
        <div className="flex items-center justify-between">
          <Link
            href="/dashboard/support"
            className="px-4 py-2 text-gray-400 hover:text-white transition-colors"
          >
            Cancel
          </Link>
          <button
            type="submit"
            disabled={isSubmitting}
            className="flex items-center px-6 py-2.5 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-medium rounded-lg hover:shadow-gold transition-all disabled:opacity-50"
          >
            {isSubmitting ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-t-2 border-b-2 border-premium-bg mr-2"></div>
                Submitting...
              </>
            ) : (
              <>
                <Send className="h-4 w-4 mr-2" />
                Submit Ticket
              </>
            )}
          </button>
        </div>
      </form>

      {/* Help Tips */}
      <div className="bg-blue-500/10 border border-blue-500/20 rounded-xl p-4">
        <h3 className="text-sm font-medium text-blue-400 mb-2">Tips for faster resolution</h3>
        <ul className="text-sm text-gray-400 space-y-1">
          <li>• Include specific error messages if any</li>
          <li>• Describe the steps that led to the issue</li>
          <li>• Mention your device and browser if relevant</li>
          <li>• Include screenshots if helpful (you can add them in replies)</li>
        </ul>
      </div>
    </div>
  )
}
