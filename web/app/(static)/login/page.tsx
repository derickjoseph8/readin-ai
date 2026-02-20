'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Mail, Lock, Loader2, Smartphone } from 'lucide-react'

export default function LoginPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [checkingAuth, setCheckingAuth] = useState(true)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [message, setMessage] = useState('')
  const [isError, setIsError] = useState(false)
  const [needsVerification, setNeedsVerification] = useState(false)
  const [resendingEmail, setResendingEmail] = useState(false)

  // 2FA State
  const [requires2FA, setRequires2FA] = useState(false)
  const [twoFactorCode, setTwoFactorCode] = useState('')
  const [isBackupCode, setIsBackupCode] = useState(false)
  const [pendingUserId, setPendingUserId] = useState<number | null>(null)

  // Track component mount state to prevent state updates after unmount
  const isMountedRef = useRef(true)

  // Safe state update helper
  const safeSetState = useCallback(<T,>(setter: React.Dispatch<React.SetStateAction<T>>, value: T) => {
    if (isMountedRef.current) {
      setter(value)
    }
  }, [])

  // Cleanup on unmount
  useEffect(() => {
    isMountedRef.current = true
    return () => {
      isMountedRef.current = false
    }
  }, [])

  // Check if user is already logged in
  useEffect(() => {
    let isActive = true

    const checkAuth = async () => {
      const token = localStorage.getItem('readin_token')
      if (token) {
        try {
          const res = await fetch('https://www.getreadin.us/user/me', {
            headers: { 'Authorization': `Bearer ${token}` }
          })
          if (res.ok && isActive) {
            // User is authenticated, redirect to dashboard using Next.js router
            router.replace('/dashboard')
            return
          }
        } catch (err) {
          // Token invalid, continue to login page
        }
      }
      if (isActive) {
        setCheckingAuth(false)
      }
    }
    checkAuth()

    return () => {
      isActive = false
    }
  }, [router])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!isMountedRef.current) return

    setLoading(true)
    setMessage('')
    setIsError(false)

    const apiUrl = 'https://www.getreadin.us'

    try {
      const res = await fetch(apiUrl + '/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })

      // Check if component is still mounted before updating state
      if (!isMountedRef.current) return

      const data = await res.json()

      if (res.ok && data.access_token) {
        localStorage.setItem('readin_token', data.access_token)
        setMessage('Success! Redirecting...')
        // Use Next.js router for client-side navigation (no setTimeout needed)
        router.push('/dashboard')
      } else if (res.ok && data.requires_2fa) {
        // User has 2FA enabled, show 2FA input
        setRequires2FA(true)
        setPendingUserId(data.user_id)
        setLoading(false)
      } else {
        setIsError(true)
        const errorDetail = data.detail || 'Login failed'
        setMessage(errorDetail)
        // Check if this is an email verification error
        if (res.status === 403 && errorDetail.toLowerCase().includes('verify')) {
          setNeedsVerification(true)
        }
        setLoading(false)
      }
    } catch (err) {
      // Check if component is still mounted before updating state
      if (!isMountedRef.current) return
      setIsError(true)
      setMessage('Network error - please try again')
      setLoading(false)
    }
  }

  const handleResendVerification = async () => {
    if (!isMountedRef.current) return

    setResendingEmail(true)
    try {
      const res = await fetch('https://www.getreadin.us/api/v1/auth/resend-verification', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      })

      // Check if component is still mounted before updating state
      if (!isMountedRef.current) return

      const data = await res.json()
      if (res.ok) {
        setIsError(false)
        setMessage('Verification email sent! Please check your inbox.')
        setNeedsVerification(false)
      } else {
        setMessage(data.detail || 'Failed to send verification email')
      }
    } catch {
      if (!isMountedRef.current) return
      setMessage('Network error - please try again')
    }
    if (isMountedRef.current) {
      setResendingEmail(false)
    }
  }

  const handle2FASubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!isMountedRef.current) return

    setLoading(true)
    setMessage('')
    setIsError(false)

    try {
      // First do a temporary login to get a short-lived token for 2FA validation
      const apiUrl = 'https://www.getreadin.us'
      const loginRes = await fetch(apiUrl + '/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })

      // Check if component is still mounted before continuing
      if (!isMountedRef.current) return

      const loginData = await loginRes.json()

      if (loginData.requires_2fa) {
        // Temporarily store token for 2FA validation
        const tempToken = loginData.temp_token || ''

        // Validate 2FA code
        const res = await fetch(apiUrl + '/api/v1/2fa/validate', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${tempToken}`,
          },
          body: JSON.stringify({
            code: twoFactorCode,
            is_backup_code: isBackupCode,
          }),
        })

        // Check if component is still mounted before updating state
        if (!isMountedRef.current) return

        const data = await res.json()

        if (res.ok && data.access_token) {
          localStorage.setItem('readin_token', data.access_token)
          setMessage('Success! Redirecting...')
          // Use Next.js router for client-side navigation
          router.push('/dashboard')
        } else {
          setIsError(true)
          setMessage(data.detail || 'Invalid verification code')
          setLoading(false)
        }
      } else if (loginData.access_token) {
        // No 2FA required after all
        localStorage.setItem('readin_token', loginData.access_token)
        setMessage('Success! Redirecting...')
        // Use Next.js router for client-side navigation
        router.push('/dashboard')
      } else {
        setIsError(true)
        setMessage(loginData.detail || 'Login failed')
        setLoading(false)
      }
    } catch (err) {
      // Check if component is still mounted before updating state
      if (!isMountedRef.current) return
      setIsError(true)
      setMessage('Network error - please try again')
      setLoading(false)
    }
  }

  const handleBack = () => {
    setRequires2FA(false)
    setTwoFactorCode('')
    setIsBackupCode(false)
    setMessage('')
  }

  // Show loading while checking auth
  if (checkingAuth) {
    return (
      <main className="min-h-screen bg-premium-bg text-white flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-gold-500" />
      </main>
    )
  }

  // 2FA Verification Screen
  if (requires2FA) {
    return (
      <main className="min-h-screen bg-premium-bg text-white flex items-center justify-center px-4">
        <div className="absolute inset-0 bg-gradient-to-b from-gold-500/5 via-transparent to-transparent" />

        <div className="relative w-full max-w-md">
          <button
            onClick={handleBack}
            className="inline-flex items-center text-gray-400 hover:text-gold-400 transition mb-8"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Login
          </button>

          <div className="bg-premium-card rounded-2xl border border-premium-border p-8">
            <div className="text-center mb-8">
              <div className="w-12 h-12 bg-gradient-to-br from-gold-400 to-gold-600 rounded-xl flex items-center justify-center mx-auto mb-4">
                <Smartphone className="h-6 w-6 text-premium-bg" />
              </div>
              <h1 className="text-2xl font-bold">Two-Factor Authentication</h1>
              <p className="text-gray-400 mt-2">Enter the code from your authenticator app</p>
            </div>

            <form onSubmit={handle2FASubmit} className="space-y-4">
              <div>
                <input
                  type="text"
                  value={twoFactorCode}
                  onChange={(e) => setTwoFactorCode(e.target.value.replace(/\D/g, '').slice(0, isBackupCode ? 8 : 6))}
                  className="w-full px-4 py-4 bg-premium-surface border border-premium-border rounded-lg focus:border-gold-500 focus:outline-none transition text-white text-center text-2xl font-mono tracking-widest"
                  placeholder={isBackupCode ? '00000000' : '000000'}
                  maxLength={isBackupCode ? 8 : 6}
                  autoFocus
                />
              </div>

              <div className="flex items-center justify-center">
                <label className="flex items-center text-sm text-gray-400 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={isBackupCode}
                    onChange={(e) => {
                      setIsBackupCode(e.target.checked)
                      setTwoFactorCode('')
                    }}
                    className="mr-2"
                  />
                  Use a backup code instead
                </label>
              </div>

              {message && (
                <div className={`p-3 rounded-lg text-sm ${isError ? 'bg-red-500/10 border border-red-500/20 text-red-400' : 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400'}`}>
                  {message}
                </div>
              )}

              <button
                type="submit"
                disabled={loading || twoFactorCode.length < (isBackupCode ? 8 : 6)}
                className="w-full py-3 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-semibold rounded-lg hover:shadow-gold transition disabled:opacity-50 flex items-center justify-center"
              >
                {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : 'Verify'}
              </button>
            </form>
          </div>
        </div>
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
            <h1 className="text-2xl font-bold">Welcome Back</h1>
            <p className="text-gray-400 mt-2">Log in to your ReadIn AI account</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
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
              <div className="flex items-center justify-between mb-2">
                <label className="block text-sm font-medium text-gray-300">Password</label>
                <Link href="/forgot-password" className="text-sm text-gold-400 hover:text-gold-300">
                  Forgot password?
                </Link>
              </div>
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
                {needsVerification && (
                  <button
                    type="button"
                    onClick={handleResendVerification}
                    disabled={resendingEmail}
                    className="mt-2 w-full py-2 bg-gold-500/20 text-gold-400 rounded-lg hover:bg-gold-500/30 transition disabled:opacity-50"
                  >
                    {resendingEmail ? 'Sending...' : 'Resend Verification Email'}
                  </button>
                )}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-semibold rounded-lg hover:shadow-gold transition disabled:opacity-50 flex items-center justify-center"
            >
              {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : 'Log In'}
            </button>
          </form>

          {/* SSO Options */}
          <div className="mt-6">
            <div className="mt-6">
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-premium-border"></div>
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-2 bg-premium-card text-gray-400">Or continue with</span>
                </div>
              </div>

              <div className="mt-4 grid grid-cols-3 gap-3">
                <a
                  href="https://www.getreadin.us/api/v1/sso/google/initiate"
                  className="flex items-center justify-center px-4 py-2.5 bg-premium-surface border border-premium-border rounded-lg hover:border-gold-500/30 transition"
                >
                  <svg className="h-5 w-5" viewBox="0 0 24 24">
                    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                  </svg>
                </a>
                <a
                  href="https://www.getreadin.us/api/v1/sso/microsoft/initiate"
                  className="flex items-center justify-center px-4 py-2.5 bg-premium-surface border border-premium-border rounded-lg hover:border-gold-500/30 transition"
                >
                  <svg className="h-5 w-5" viewBox="0 0 23 23">
                    <path fill="#f35325" d="M1 1h10v10H1z"/>
                    <path fill="#81bc06" d="M12 1h10v10H12z"/>
                    <path fill="#05a6f0" d="M1 12h10v10H1z"/>
                    <path fill="#ffba08" d="M12 12h10v10H12z"/>
                  </svg>
                </a>
                <a
                  href="https://www.getreadin.us/api/v1/sso/apple/initiate"
                  className="flex items-center justify-center px-4 py-2.5 bg-premium-surface border border-premium-border rounded-lg hover:border-gold-500/30 transition"
                >
                  <svg className="h-5 w-5 text-white" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.81-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11z"/>
                  </svg>
                </a>
              </div>
            </div>
          </div>

          <div className="mt-6 text-center text-sm">
            <span className="text-gray-400">Don&apos;t have an account? </span>
            <Link href="/signup" className="text-gold-400 hover:text-gold-300 font-medium">
              Sign Up
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
