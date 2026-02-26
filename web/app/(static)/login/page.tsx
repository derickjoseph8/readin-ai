'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Mail, Lock, Loader2, Smartphone } from 'lucide-react'

const API_URL = 'https://www.getreadin.us'

export default function LoginPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [message, setMessage] = useState('')
  const [isError, setIsError] = useState(false)

  // 2FA State
  const [requires2FA, setRequires2FA] = useState(false)
  const [twoFactorCode, setTwoFactorCode] = useState('')
  const [isBackupCode, setIsBackupCode] = useState(false)
  const [tempToken, setTempToken] = useState('')

  // Check if user is already logged in on mount
  useEffect(() => {
    const token = localStorage.getItem('readin_token')
    if (token) {
      // Verify token and redirect
      fetch(`${API_URL}/user/me`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
        .then(res => res.ok ? res.json() : Promise.reject())
        .then(userData => {
          if (userData.is_staff && (userData.staff_role === 'super_admin' || userData.staff_role === 'admin')) {
            window.location.href = '/admin'
          } else {
            window.location.href = '/dashboard'
          }
        })
        .catch(() => {
          // Token invalid, stay on login page
          localStorage.removeItem('readin_token')
        })
    }
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setMessage('')
    setIsError(false)

    try {
      const res = await fetch(`${API_URL}/api/v1/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })

      const data = await res.json()

      if (res.ok && data.access_token) {
        // Login successful - save token
        localStorage.setItem('readin_token', data.access_token)
        setMessage('Success! Redirecting...')

        // Fetch user info and redirect
        try {
          const userRes = await fetch(`${API_URL}/user/me`, {
            headers: { 'Authorization': `Bearer ${data.access_token}` }
          })
          const userData = await userRes.json()

          // Use window.location for reliable redirect
          if (userData.is_staff && (userData.staff_role === 'super_admin' || userData.staff_role === 'admin')) {
            window.location.href = '/admin'
          } else {
            window.location.href = '/dashboard'
          }
        } catch {
          window.location.href = '/dashboard'
        }
      } else if (res.ok && data.requires_2fa) {
        // 2FA required
        setTempToken(data.temp_token)
        setRequires2FA(true)
        setLoading(false)
      } else {
        setIsError(true)
        setMessage(data.detail || 'Login failed')
        setLoading(false)
      }
    } catch (err) {
      setIsError(true)
      setMessage('Network error - please try again')
      setLoading(false)
    }
  }

  const handle2FASubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setMessage('')
    setIsError(false)

    try {
      const res = await fetch(`${API_URL}/api/v1/auth/login/2fa`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          temp_token: tempToken,
          code: twoFactorCode,
          is_backup_code: isBackupCode,
        }),
      })

      const data = await res.json()

      if (res.ok && data.access_token) {
        localStorage.setItem('readin_token', data.access_token)
        setMessage('Success! Redirecting...')

        // Fetch user info and redirect
        try {
          const userRes = await fetch(`${API_URL}/user/me`, {
            headers: { 'Authorization': `Bearer ${data.access_token}` }
          })
          const userData = await userRes.json()

          if (userData.is_staff && (userData.staff_role === 'super_admin' || userData.staff_role === 'admin')) {
            window.location.href = '/admin'
          } else {
            window.location.href = '/dashboard'
          }
        } catch {
          window.location.href = '/dashboard'
        }
      } else {
        setIsError(true)
        setMessage(data.detail || 'Invalid verification code')
        setLoading(false)
      }
    } catch {
      setIsError(true)
      setMessage('Network error - please try again')
      setLoading(false)
    }
  }

  // 2FA Verification Screen
  if (requires2FA) {
    return (
      <main className="min-h-screen bg-[#0a0a0a] text-white flex items-center justify-center px-4">
        <div className="absolute inset-0 bg-gradient-to-b from-yellow-500/5 via-transparent to-transparent" />

        <div className="relative w-full max-w-md">
          <button
            onClick={() => {
              setRequires2FA(false)
              setTwoFactorCode('')
              setTempToken('')
              setMessage('')
            }}
            className="inline-flex items-center text-gray-400 hover:text-yellow-400 transition mb-8"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Login
          </button>

          <div className="bg-[#111] rounded-2xl border border-gray-800 p-8">
            <div className="text-center mb-8">
              <div className="w-12 h-12 bg-gradient-to-br from-yellow-400 to-yellow-600 rounded-xl flex items-center justify-center mx-auto mb-4">
                <Smartphone className="h-6 w-6 text-black" />
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
                  className="w-full px-4 py-4 bg-[#1a1a1a] border border-gray-700 rounded-lg focus:border-yellow-500 focus:outline-none transition text-white text-center text-2xl font-mono tracking-widest"
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
                <div className={`p-3 rounded-lg text-sm ${isError ? 'bg-red-500/10 border border-red-500/20 text-red-400' : 'bg-green-500/10 border border-green-500/20 text-green-400'}`}>
                  {message}
                </div>
              )}

              <button
                type="submit"
                disabled={loading || twoFactorCode.length < (isBackupCode ? 8 : 6)}
                className="w-full py-3 bg-gradient-to-r from-yellow-600 to-yellow-500 text-black font-semibold rounded-lg hover:opacity-90 transition disabled:opacity-50 flex items-center justify-center"
              >
                {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : 'Verify'}
              </button>
            </form>
          </div>
        </div>
      </main>
    )
  }

  // Main Login Form
  return (
    <main className="min-h-screen bg-[#0a0a0a] text-white flex items-center justify-center px-4">
      <div className="absolute inset-0 bg-gradient-to-b from-yellow-500/5 via-transparent to-transparent" />

      <div className="relative w-full max-w-md">
        <Link href="/" className="inline-flex items-center text-gray-400 hover:text-yellow-400 transition mb-8">
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Home
        </Link>

        <div className="bg-[#111] rounded-2xl border border-gray-800 p-8">
          <div className="text-center mb-8">
            <div className="w-12 h-12 bg-gradient-to-br from-yellow-400 to-yellow-600 rounded-xl flex items-center justify-center mx-auto mb-4">
              <span className="text-black font-bold text-xl">R</span>
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
                  className="w-full pl-10 pr-4 py-3 bg-[#1a1a1a] border border-gray-700 rounded-lg focus:border-yellow-500 focus:outline-none transition text-white"
                  placeholder="you@example.com"
                  required
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-sm font-medium text-gray-300">Password</label>
                <Link href="/forgot-password" className="text-sm text-yellow-400 hover:text-yellow-300">
                  Forgot password?
                </Link>
              </div>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-500" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 bg-[#1a1a1a] border border-gray-700 rounded-lg focus:border-yellow-500 focus:outline-none transition text-white"
                  placeholder="••••••••"
                  required
                  minLength={6}
                />
              </div>
            </div>

            {message && (
              <div className={`p-3 rounded-lg text-sm ${isError ? 'bg-red-500/10 border border-red-500/20 text-red-400' : 'bg-green-500/10 border border-green-500/20 text-green-400'}`}>
                {message}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-gradient-to-r from-yellow-600 to-yellow-500 text-black font-semibold rounded-lg hover:opacity-90 transition disabled:opacity-50 flex items-center justify-center"
            >
              {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : 'Log In'}
            </button>
          </form>

          <div className="mt-6 text-center text-sm">
            <span className="text-gray-400">Don&apos;t have an account? </span>
            <Link href="/signup" className="text-yellow-400 hover:text-yellow-300 font-medium">
              Sign Up
            </Link>
          </div>

          <div className="mt-6 pt-6 border-t border-gray-800 text-center">
            <p className="text-gray-500 text-sm">
              By continuing, you agree to our{' '}
              <Link href="/terms" className="text-gray-400 hover:text-yellow-400">Terms</Link>
              {' '}and{' '}
              <Link href="/privacy" className="text-gray-400 hover:text-yellow-400">Privacy Policy</Link>
            </p>
          </div>
        </div>

        <p className="text-center text-gray-500 text-sm mt-6">
          Need the app?{' '}
          <Link href="/download" className="text-yellow-400 hover:text-yellow-300">Download ReadIn AI</Link>
        </p>
      </div>
    </main>
  )
}
