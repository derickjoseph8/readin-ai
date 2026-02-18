'use client'

import { useState, useEffect, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { Loader2, CheckCircle, XCircle, Mail } from 'lucide-react'

function VerifyEmailContent() {
  const searchParams = useSearchParams()
  const token = searchParams.get('token')

  const [loading, setLoading] = useState(true)
  const [verified, setVerified] = useState(false)
  const [alreadyVerified, setAlreadyVerified] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    const verifyEmail = async () => {
      if (!token) {
        setError('Invalid verification link')
        setLoading(false)
        return
      }

      try {
        const res = await fetch(`https://www.getreadin.us/api/v1/auth/verify-email?token=${token}`)
        const data = await res.json()

        if (res.ok) {
          if (data.already_verified) {
            setAlreadyVerified(true)
          } else {
            setVerified(true)
          }
        } else {
          setError(data.detail || 'Verification failed')
        }
      } catch (err) {
        setError('Network error - please try again')
      } finally {
        setLoading(false)
      }
    }

    verifyEmail()
  }, [token])

  if (loading) {
    return (
      <main className="min-h-screen bg-premium-bg text-white flex items-center justify-center px-4">
        <div className="absolute inset-0 bg-gradient-to-b from-gold-500/5 via-transparent to-transparent" />

        <div className="relative w-full max-w-md">
          <div className="bg-premium-card rounded-2xl border border-premium-border p-8 text-center">
            <Loader2 className="h-12 w-12 animate-spin text-gold-500 mx-auto mb-6" />
            <h1 className="text-2xl font-bold mb-4">Verifying Email...</h1>
            <p className="text-gray-400">Please wait while we verify your email address.</p>
          </div>
        </div>
      </main>
    )
  }

  if (verified || alreadyVerified) {
    return (
      <main className="min-h-screen bg-premium-bg text-white flex items-center justify-center px-4">
        <div className="absolute inset-0 bg-gradient-to-b from-gold-500/5 via-transparent to-transparent" />

        <div className="relative w-full max-w-md">
          <div className="bg-premium-card rounded-2xl border border-premium-border p-8 text-center">
            <div className="w-16 h-16 bg-emerald-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
              <CheckCircle className="h-8 w-8 text-emerald-400" />
            </div>
            <h1 className="text-2xl font-bold mb-4">
              {alreadyVerified ? 'Already Verified' : 'Email Verified!'}
            </h1>
            <p className="text-gray-400 mb-6">
              {alreadyVerified
                ? 'Your email address has already been verified.'
                : 'Your email address has been successfully verified. You now have full access to ReadIn AI.'}
            </p>
            <Link
              href="/dashboard"
              className="inline-block px-6 py-3 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-semibold rounded-lg hover:shadow-gold transition"
            >
              Go to Dashboard
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
        <div className="bg-premium-card rounded-2xl border border-premium-border p-8 text-center">
          <div className="w-16 h-16 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
            <XCircle className="h-8 w-8 text-red-400" />
          </div>
          <h1 className="text-2xl font-bold mb-4">Verification Failed</h1>
          <p className="text-gray-400 mb-6">
            {error || 'This verification link is invalid or has expired.'}
          </p>
          <div className="space-y-3">
            <Link
              href="/login"
              className="inline-block w-full px-6 py-3 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-semibold rounded-lg hover:shadow-gold transition"
            >
              Go to Login
            </Link>
            <p className="text-gray-500 text-sm">
              You can request a new verification email from your dashboard settings.
            </p>
          </div>
        </div>
      </div>
    </main>
  )
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={
      <main className="min-h-screen bg-premium-bg text-white flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-gold-500" />
      </main>
    }>
      <VerifyEmailContent />
    </Suspense>
  )
}
