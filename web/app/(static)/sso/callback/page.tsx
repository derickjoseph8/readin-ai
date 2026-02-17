'use client'

import { useEffect, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import { Loader2, CheckCircle, XCircle } from 'lucide-react'
import Link from 'next/link'

export default function SSOCallbackPage() {
  const searchParams = useSearchParams()
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const token = searchParams.get('token')
    const errorParam = searchParams.get('error')

    if (errorParam) {
      setStatus('error')
      setError(errorParam === 'access_denied' ? 'Sign in was cancelled' : errorParam)
      return
    }

    if (token) {
      // Store token and redirect to dashboard
      localStorage.setItem('readin_token', token)
      setStatus('success')

      // Redirect after a brief moment
      setTimeout(() => {
        window.location.href = '/dashboard'
      }, 1500)
    } else {
      setStatus('error')
      setError('No authentication token received')
    }
  }, [searchParams])

  return (
    <main className="min-h-screen bg-premium-bg text-white flex items-center justify-center px-4">
      <div className="absolute inset-0 bg-gradient-to-b from-gold-500/5 via-transparent to-transparent" />

      <div className="relative w-full max-w-md">
        <div className="bg-premium-card rounded-2xl border border-premium-border p-8 text-center">
          {status === 'loading' && (
            <>
              <div className="w-16 h-16 bg-gradient-to-br from-gold-400 to-gold-600 rounded-full flex items-center justify-center mx-auto mb-6">
                <Loader2 className="h-8 w-8 text-premium-bg animate-spin" />
              </div>
              <h1 className="text-2xl font-bold mb-2">Signing you in...</h1>
              <p className="text-gray-400">Please wait while we complete the sign in process.</p>
            </>
          )}

          {status === 'success' && (
            <>
              <div className="w-16 h-16 bg-emerald-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
                <CheckCircle className="h-8 w-8 text-emerald-400" />
              </div>
              <h1 className="text-2xl font-bold mb-2">Sign in successful!</h1>
              <p className="text-gray-400">Redirecting you to the dashboard...</p>
            </>
          )}

          {status === 'error' && (
            <>
              <div className="w-16 h-16 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
                <XCircle className="h-8 w-8 text-red-400" />
              </div>
              <h1 className="text-2xl font-bold mb-2">Sign in failed</h1>
              <p className="text-gray-400 mb-6">{error || 'An error occurred during sign in.'}</p>
              <Link
                href="/login"
                className="inline-flex items-center px-6 py-3 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-semibold rounded-lg hover:shadow-gold transition"
              >
                Try again
              </Link>
            </>
          )}
        </div>
      </div>
    </main>
  )
}
