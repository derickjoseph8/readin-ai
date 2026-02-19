'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Mail, Lock, Loader2 } from 'lucide-react'

export default function SignupPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [checkingAuth, setCheckingAuth] = useState(true)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [message, setMessage] = useState('')
  const [isError, setIsError] = useState(false)

  // Check if user is already logged in
  useEffect(() => {
    const checkAuth = async () => {
      try {
        // Only access localStorage on client
        if (typeof window === 'undefined') {
          setCheckingAuth(false)
          return
        }

        const token = localStorage.getItem('readin_token')
        if (token) {
          try {
            const res = await fetch('https://www.getreadin.us/user/me', {
              headers: { 'Authorization': `Bearer ${token}` }
            })
            if (res.ok) {
              router.replace('/dashboard')
              return
            }
          } catch {
            // Token invalid or network error, continue to signup page
          }
        }
        setCheckingAuth(false)
      } catch {
        // Any error, just show the signup form
        setCheckingAuth(false)
      }
    }
    checkAuth()
  }, [router])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setMessage('')
    setIsError(false)

    const apiUrl = 'https://www.getreadin.us'

    try {
      const res = await fetch(apiUrl + '/api/v1/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, full_name: name }),
      })

      const data = await res.json()

      if (res.ok && data.access_token) {
        localStorage.setItem('readin_token', data.access_token)
        setMessage('Success! Redirecting...')
        router.push('/dashboard')
      } else {
        setIsError(true)
        setMessage(data.detail || 'Registration failed')
        setLoading(false)
      }
    } catch (err) {
      setIsError(true)
      setMessage('Network error - please try again')
      setLoading(false)
    }
  }

  // Show loading while checking auth
  if (checkingAuth) {
    return (
      <main className="min-h-screen bg-premium-bg text-white flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-gold-500" />
      </main>
    )
  }

  return (
    <main className="min-h-screen bg-premium-bg text-white flex items-center justify-center px-4">
      <div className="absolute inset-0 bg-gradient-to-b from-gold-500/5 via-transparent to-transparent" />

      <div className="relative w-full max-w-md">
        <Link href="/" className="inline-flex items-center text-gray-400 hover:text-gold-400 transition mb-8">
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Home
        </Link>

        <div className="bg-premium-card rounded-2xl border border-premium-border p-8">
          <div className="text-center mb-8">
            <div className="w-12 h-12 bg-gradient-to-br from-gold-400 to-gold-600 rounded-xl flex items-center justify-center mx-auto mb-4">
              <span className="text-premium-bg font-bold text-xl">R</span>
            </div>
            <h1 className="text-2xl font-bold">Create Account</h1>
            <p className="text-gray-400 mt-2">Start your 14-day free trial</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Full Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-4 py-3 bg-premium-surface border border-premium-border rounded-lg focus:border-gold-500 focus:outline-none transition text-white"
                placeholder="John Doe"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Email</label>
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

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-500" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 bg-premium-surface border border-premium-border rounded-lg focus:border-gold-500 focus:outline-none transition text-white"
                  placeholder="••••••••"
                  required
                  minLength={6}
                />
              </div>
            </div>

            {message && (
              <div className={`p-3 rounded-lg text-sm ${isError ? 'bg-red-500/10 border border-red-500/20 text-red-400' : 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400'}`}>
                {message}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-semibold rounded-lg hover:shadow-gold transition disabled:opacity-50 flex items-center justify-center"
            >
              {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : 'Create Account'}
            </button>
          </form>

          <div className="mt-6 text-center text-sm">
            <span className="text-gray-400">Already have an account? </span>
            <Link href="/login" className="text-gold-400 hover:text-gold-300 font-medium">
              Log In
            </Link>
          </div>

          <div className="mt-6 pt-6 border-t border-premium-border text-center">
            <p className="text-gray-500 text-sm">
              By continuing, you agree to our{' '}
              <Link href="/terms" className="text-gray-400 hover:text-gold-400">Terms</Link>
              {' '}and{' '}
              <Link href="/privacy" className="text-gray-400 hover:text-gold-400">Privacy Policy</Link>
            </p>
          </div>
        </div>

        <p className="text-center text-gray-500 text-sm mt-6">
          Need the app?{' '}
          <Link href="/download" className="text-gold-400 hover:text-gold-300">Download ReadIn AI</Link>
        </p>
      </div>
    </main>
  )
}
