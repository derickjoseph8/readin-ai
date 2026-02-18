'use client'

import { useState } from 'react'
import Link from 'next/link'
import { ArrowLeft, Mail, Loader2, CheckCircle } from 'lucide-react'

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [sent, setSent] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      const res = await fetch('https://www.getreadin.us/api/v1/auth/forgot-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      })

      if (res.ok) {
        setSent(true)
      } else {
        const data = await res.json()
        setError(data.detail || 'Failed to send reset email')
      }
    } catch (err) {
      setError('Network error - please try again')
    } finally {
      setLoading(false)
    }
  }

  if (sent) {
    return (
      <main className="min-h-screen bg-premium-bg text-white flex items-center justify-center px-4">
        <div className="absolute inset-0 bg-gradient-to-b from-gold-500/5 via-transparent to-transparent" />

        <div className="relative w-full max-w-md">
          <div className="bg-premium-card rounded-2xl border border-premium-border p-8 text-center">
            <div className="w-16 h-16 bg-emerald-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
              <CheckCircle className="h-8 w-8 text-emerald-400" />
            </div>
            <h1 className="text-2xl font-bold mb-4">Check Your Email</h1>
            <p className="text-gray-400 mb-6">
              If an account exists for <span className="text-white">{email}</span>,
              we've sent a password reset link. The link will expire in 1 hour.
            </p>
            <p className="text-gray-500 text-sm mb-6">
              Don't see the email? Check your spam folder.
            </p>
            <Link
              href="/login"
              className="inline-flex items-center text-gold-400 hover:text-gold-300"
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Login
            </Link>
          </div>
        </div>
      </main>
    )
  }

  return (
    <main className="min-h-screen bg-premium-bg text-white flex items-center justify-center px-4">
      <div className="absolute inset-0 bg-gradient-to-b from-gold-500/5 via-transparent to-transparent" />

      <div className="relative w-full max-w-md">
        <Link href="/login" className="inline-flex items-center text-gray-400 hover:text-gold-400 transition mb-8">
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Login
        </Link>

        <div className="bg-premium-card rounded-2xl border border-premium-border p-8">
          <div className="text-center mb-8">
            <div className="w-12 h-12 bg-gradient-to-br from-gold-400 to-gold-600 rounded-xl flex items-center justify-center mx-auto mb-4">
              <Mail className="h-6 w-6 text-premium-bg" />
            </div>
            <h1 className="text-2xl font-bold">Forgot Password?</h1>
            <p className="text-gray-400 mt-2">
              Enter your email and we'll send you a reset link
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Email Address</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-500" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 bg-premium-surface border border-premium-border rounded-lg focus:border-gold-500 focus:outline-none transition text-white"
                  placeholder="you@example.com"
                  required
                />
              </div>
            </div>

            {error && (
              <div className="p-3 rounded-lg text-sm bg-red-500/10 border border-red-500/20 text-red-400">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading || !email}
              className="w-full py-3 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-semibold rounded-lg hover:shadow-gold transition disabled:opacity-50 flex items-center justify-center"
            >
              {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : 'Send Reset Link'}
            </button>
          </form>

          <div className="mt-6 text-center text-sm">
            <span className="text-gray-400">Remember your password? </span>
            <Link href="/login" className="text-gold-400 hover:text-gold-300 font-medium">
              Log In
            </Link>
          </div>
        </div>
      </div>
    </main>
  )
}
