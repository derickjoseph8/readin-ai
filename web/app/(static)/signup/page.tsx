'use client'

import { useState } from 'react'
import Link from 'next/link'
import { User, Building2 } from 'lucide-react'

type AccountType = 'individual' | 'company'

const COUNTRIES = [
  'United States', 'United Kingdom', 'Canada', 'Australia', 'Germany', 'France',
  'Netherlands', 'Sweden', 'Norway', 'Denmark', 'Finland', 'Switzerland', 'Austria',
  'Belgium', 'Ireland', 'New Zealand', 'Singapore', 'Japan', 'South Korea', 'India',
  'Brazil', 'Mexico', 'South Africa', 'Kenya', 'Nigeria', 'Ghana', 'Egypt', 'UAE',
  'Saudi Arabia', 'Israel', 'Spain', 'Italy', 'Portugal', 'Poland', 'Czech Republic',
  'Argentina', 'Chile', 'Colombia', 'Philippines', 'Malaysia', 'Indonesia', 'Thailand',
  'Vietnam', 'Taiwan', 'Hong Kong', 'China', 'Russia', 'Turkey', 'Other'
]

const INDUSTRIES = [
  'Technology', 'Finance & Banking', 'Healthcare', 'Education', 'Legal',
  'Consulting', 'Real Estate', 'Manufacturing', 'Retail & E-commerce',
  'Media & Entertainment', 'Marketing & Advertising', 'Telecommunications',
  'Energy & Utilities', 'Transportation & Logistics', 'Hospitality & Tourism',
  'Non-profit', 'Government', 'Agriculture', 'Construction', 'Insurance',
  'Pharmaceutical', 'Automotive', 'Aerospace', 'Food & Beverage', 'Other'
]

export default function SignupPage() {
  const [loading, setLoading] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [accountType, setAccountType] = useState<AccountType>('individual')
  const [companyName, setCompanyName] = useState('')
  const [country, setCountry] = useState('')
  const [industry, setIndustry] = useState('')
  const [message, setMessage] = useState('')
  const [isError, setIsError] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setMessage('')
    setIsError(false)

    try {
      const payload: Record<string, string> = {
        email,
        password,
        full_name: name,
        account_type: accountType,
      }

      if (country) {
        payload.country = country
      }

      if (accountType === 'company') {
        if (companyName) payload.company = companyName
        if (industry) payload.industry = industry
      }

      const res = await fetch('https://www.getreadin.us/api/v1/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      const data = await res.json()

      if (res.ok) {
        // Check if requires email verification (new flow)
        if (data.requires_verification) {
          setIsError(false)
          setMessage(`Account created! Please check your email (${data.email}) to verify your account before logging in.`)
          setLoading(false)
          // Clear the form
          setEmail('')
          setPassword('')
          setName('')
          setCompanyName('')
          setCountry('')
          setIndustry('')
        } else if (data.access_token) {
          // Legacy flow - direct login (for backwards compatibility)
          localStorage.setItem('readin_token', data.access_token)
          setMessage('Success! Redirecting...')
          window.location.href = '/dashboard'
        }
      } else {
        setIsError(true)
        let errorMsg = 'Registration failed'
        if (typeof data.detail === 'string') {
          errorMsg = data.detail
        } else if (Array.isArray(data.detail) && data.detail.length > 0) {
          errorMsg = data.detail.map((e: { msg?: string }) => e.msg || 'Validation error').join('. ')
        }
        setMessage(errorMsg)
        setLoading(false)
      }
    } catch {
      setIsError(true)
      setMessage('Network error - please try again')
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-premium-bg text-white flex items-center justify-center px-4 py-8">
      <div className="w-full max-w-md">
        <Link href="/" className="text-gray-400 hover:text-gold-400 mb-8 inline-block">
          ← Back to Home
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
            {/* Account Type Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Account Type</label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setAccountType('individual')}
                  className={`flex flex-col items-center p-4 rounded-lg border transition-all ${
                    accountType === 'individual'
                      ? 'border-gold-500 bg-gold-500/10'
                      : 'border-premium-border bg-premium-surface hover:border-gray-600'
                  }`}
                >
                  <User className={`h-6 w-6 mb-2 ${accountType === 'individual' ? 'text-gold-400' : 'text-gray-400'}`} />
                  <span className={`text-sm font-medium ${accountType === 'individual' ? 'text-gold-400' : 'text-gray-300'}`}>
                    Individual
                  </span>
                  <span className="text-xs text-gray-500 mt-1">Personal use</span>
                </button>
                <button
                  type="button"
                  onClick={() => setAccountType('company')}
                  className={`flex flex-col items-center p-4 rounded-lg border transition-all ${
                    accountType === 'company'
                      ? 'border-gold-500 bg-gold-500/10'
                      : 'border-premium-border bg-premium-surface hover:border-gray-600'
                  }`}
                >
                  <Building2 className={`h-6 w-6 mb-2 ${accountType === 'company' ? 'text-gold-400' : 'text-gray-400'}`} />
                  <span className={`text-sm font-medium ${accountType === 'company' ? 'text-gold-400' : 'text-gray-300'}`}>
                    Company
                  </span>
                  <span className="text-xs text-gray-500 mt-1">Team access</span>
                </button>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Full Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-4 py-3 bg-premium-surface border border-premium-border rounded-lg focus:border-gold-500 focus:outline-none text-white"
                placeholder="John Doe"
                required
              />
            </div>

            {/* Company Name - Only shown for company accounts */}
            {accountType === 'company' && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Company Name</label>
                  <input
                    type="text"
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    className="w-full px-4 py-3 bg-premium-surface border border-premium-border rounded-lg focus:border-gold-500 focus:outline-none text-white"
                    placeholder="Acme Inc."
                    required={accountType === 'company'}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Industry</label>
                  <select
                    value={industry}
                    onChange={(e) => setIndustry(e.target.value)}
                    className="w-full px-4 py-3 bg-premium-surface border border-premium-border rounded-lg focus:border-gold-500 focus:outline-none text-white"
                    required={accountType === 'company'}
                  >
                    <option value="">Select Industry</option>
                    {INDUSTRIES.map((ind) => (
                      <option key={ind} value={ind}>{ind}</option>
                    ))}
                  </select>
                </div>
              </>
            )}

            {/* Country - Required for company accounts */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Country {accountType === 'company' && <span className="text-red-400">*</span>}
              </label>
              <select
                value={country}
                onChange={(e) => setCountry(e.target.value)}
                className="w-full px-4 py-3 bg-premium-surface border border-premium-border rounded-lg focus:border-gold-500 focus:outline-none text-white"
                required={accountType === 'company'}
              >
                <option value="">Select Country</option>
                {COUNTRIES.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-3 bg-premium-surface border border-premium-border rounded-lg focus:border-gold-500 focus:outline-none text-white"
                placeholder="you@example.com"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-3 bg-premium-surface border border-premium-border rounded-lg focus:border-gold-500 focus:outline-none text-white"
                placeholder="••••••••"
                required
                minLength={6}
              />
            </div>

            {message && (
              <div className={`p-3 rounded-lg text-sm ${isError ? 'bg-red-500/10 border border-red-500/20 text-red-400' : 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400'}`}>
                {message}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-semibold rounded-lg hover:shadow-gold disabled:opacity-50"
            >
              {loading ? 'Creating Account...' : 'Create Account'}
            </button>
          </form>

          <div className="mt-6 text-center text-sm">
            <span className="text-gray-400">Already have an account? </span>
            <Link href="/login" className="text-gold-400 hover:text-gold-300 font-medium">
              Log In
            </Link>
          </div>
        </div>
      </div>
    </main>
  )
}
