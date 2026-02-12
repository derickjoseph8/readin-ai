'use client'

import { useState } from 'react'
import {
  Shield,
  Key,
  Smartphone,
  History,
  Eye,
  EyeOff,
  Check,
  AlertCircle,
  LogOut
} from 'lucide-react'
import { authApi } from '@/lib/api/auth'

export default function SecurityPage() {
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showCurrentPassword, setShowCurrentPassword] = useState(false)
  const [showNewPassword, setShowNewPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const passwordStrength = () => {
    if (!newPassword) return { score: 0, label: '', color: '' }
    let score = 0
    if (newPassword.length >= 8) score++
    if (newPassword.length >= 12) score++
    if (/[A-Z]/.test(newPassword)) score++
    if (/[0-9]/.test(newPassword)) score++
    if (/[^A-Za-z0-9]/.test(newPassword)) score++

    if (score <= 2) return { score, label: 'Weak', color: 'bg-red-500' }
    if (score <= 3) return { score, label: 'Fair', color: 'bg-yellow-500' }
    if (score <= 4) return { score, label: 'Good', color: 'bg-emerald-500' }
    return { score, label: 'Strong', color: 'bg-emerald-400' }
  }

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSuccess(false)

    if (newPassword !== confirmPassword) {
      setError('New passwords do not match')
      return
    }

    if (newPassword.length < 8) {
      setError('Password must be at least 8 characters')
      return
    }

    setIsLoading(true)
    try {
      await authApi.changePassword(currentPassword, newPassword)
      setSuccess(true)
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
      setTimeout(() => setSuccess(false), 5000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to change password')
    } finally {
      setIsLoading(false)
    }
  }

  const strength = passwordStrength()

  return (
    <div className="max-w-2xl space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Security Settings</h1>
        <p className="text-gray-400 mt-1">
          Manage your password and account security
        </p>
      </div>

      {/* Change Password */}
      <div className="bg-premium-card border border-premium-border rounded-xl p-6">
        <h2 className="font-semibold text-white mb-4 flex items-center">
          <Key className="h-5 w-5 text-gold-400 mr-2" />
          Change Password
        </h2>

        <form onSubmit={handlePasswordChange} className="space-y-4">
          {error && (
            <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm flex items-center">
              <AlertCircle className="h-4 w-4 mr-2 flex-shrink-0" />
              {error}
            </div>
          )}

          {success && (
            <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-emerald-400 text-sm flex items-center">
              <Check className="h-4 w-4 mr-2 flex-shrink-0" />
              Password changed successfully
            </div>
          )}

          {/* Current Password */}
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">
              Current Password
            </label>
            <div className="relative">
              <input
                type={showCurrentPassword ? 'text' : 'password'}
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                className="w-full px-4 py-2.5 pr-10 bg-premium-surface border border-premium-border rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-gold-500/50"
                placeholder="Enter current password"
                required
              />
              <button
                type="button"
                onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white"
              >
                {showCurrentPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>

          {/* New Password */}
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">
              New Password
            </label>
            <div className="relative">
              <input
                type={showNewPassword ? 'text' : 'password'}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="w-full px-4 py-2.5 pr-10 bg-premium-surface border border-premium-border rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-gold-500/50"
                placeholder="Enter new password"
                required
              />
              <button
                type="button"
                onClick={() => setShowNewPassword(!showNewPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white"
              >
                {showNewPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>

            {/* Password Strength Indicator */}
            {newPassword && (
              <div className="mt-2">
                <div className="flex items-center gap-2 mb-1">
                  <div className="flex-1 h-1.5 bg-premium-surface rounded-full overflow-hidden flex gap-0.5">
                    {[1, 2, 3, 4, 5].map((i) => (
                      <div
                        key={i}
                        className={`flex-1 rounded-full ${i <= strength.score ? strength.color : 'bg-gray-700'}`}
                      />
                    ))}
                  </div>
                  <span className={`text-xs ${strength.color.replace('bg-', 'text-')}`}>
                    {strength.label}
                  </span>
                </div>
                <p className="text-xs text-gray-500">
                  Use 12+ characters with uppercase, numbers, and symbols
                </p>
              </div>
            )}
          </div>

          {/* Confirm Password */}
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">
              Confirm New Password
            </label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full px-4 py-2.5 bg-premium-surface border border-premium-border rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-gold-500/50"
              placeholder="Confirm new password"
              required
            />
            {confirmPassword && confirmPassword !== newPassword && (
              <p className="text-xs text-red-400 mt-1">Passwords do not match</p>
            )}
          </div>

          <button
            type="submit"
            disabled={isLoading || !currentPassword || !newPassword || newPassword !== confirmPassword}
            className="px-6 py-2.5 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-medium rounded-lg hover:shadow-gold transition-all disabled:opacity-50 flex items-center"
          >
            {isLoading ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-t-2 border-b-2 border-premium-bg mr-2"></div>
                Updating...
              </>
            ) : (
              <>
                <Key className="h-4 w-4 mr-2" />
                Update Password
              </>
            )}
          </button>
        </form>
      </div>

      {/* Two-Factor Authentication */}
      <div className="bg-premium-card border border-premium-border rounded-xl p-6">
        <h2 className="font-semibold text-white mb-4 flex items-center">
          <Smartphone className="h-5 w-5 text-gold-400 mr-2" />
          Two-Factor Authentication
        </h2>

        <div className="flex items-center justify-between p-4 bg-premium-surface rounded-lg">
          <div>
            <p className="text-white font-medium">Authenticator App</p>
            <p className="text-gray-500 text-sm mt-0.5">
              Add an extra layer of security to your account
            </p>
          </div>
          <span className="px-3 py-1 bg-gray-600/50 text-gray-400 text-sm rounded-lg">
            Coming Soon
          </span>
        </div>

        <p className="text-xs text-gray-500 mt-3">
          Two-factor authentication will be available in a future update
        </p>
      </div>

      {/* Active Sessions */}
      <div className="bg-premium-card border border-premium-border rounded-xl p-6">
        <h2 className="font-semibold text-white mb-4 flex items-center">
          <History className="h-5 w-5 text-gold-400 mr-2" />
          Active Sessions
        </h2>

        <div className="space-y-3">
          {/* Current Session */}
          <div className="flex items-center justify-between p-4 bg-premium-surface rounded-lg">
            <div className="flex items-center">
              <div className="w-10 h-10 bg-emerald-500/20 rounded-lg flex items-center justify-center mr-3">
                <Shield className="h-5 w-5 text-emerald-400" />
              </div>
              <div>
                <p className="text-white font-medium flex items-center">
                  Current Session
                  <span className="ml-2 px-2 py-0.5 bg-emerald-500/20 text-emerald-400 text-xs rounded">
                    Active
                  </span>
                </p>
                <p className="text-gray-500 text-sm mt-0.5">
                  Windows - Chrome - Started just now
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-4 pt-4 border-t border-premium-border">
          <button
            onClick={() => {
              if (confirm('This will log you out of all other devices. Continue?')) {
                alert('All other sessions have been terminated.')
              }
            }}
            className="text-red-400 text-sm hover:text-red-300 transition-colors flex items-center"
          >
            <LogOut className="h-4 w-4 mr-2" />
            Log out all other sessions
          </button>
        </div>
      </div>

      {/* Security Tips */}
      <div className="bg-premium-card border border-premium-border rounded-xl p-6">
        <h2 className="font-semibold text-white mb-4 flex items-center">
          <Shield className="h-5 w-5 text-gold-400 mr-2" />
          Security Tips
        </h2>

        <ul className="space-y-3">
          <li className="flex items-start text-sm">
            <Check className="h-4 w-4 text-emerald-400 mr-2 mt-0.5 flex-shrink-0" />
            <span className="text-gray-300">Use a unique password you don&apos;t use elsewhere</span>
          </li>
          <li className="flex items-start text-sm">
            <Check className="h-4 w-4 text-emerald-400 mr-2 mt-0.5 flex-shrink-0" />
            <span className="text-gray-300">Enable two-factor authentication when available</span>
          </li>
          <li className="flex items-start text-sm">
            <Check className="h-4 w-4 text-emerald-400 mr-2 mt-0.5 flex-shrink-0" />
            <span className="text-gray-300">Review your active sessions regularly</span>
          </li>
          <li className="flex items-start text-sm">
            <Check className="h-4 w-4 text-emerald-400 mr-2 mt-0.5 flex-shrink-0" />
            <span className="text-gray-300">Never share your password or access tokens</span>
          </li>
        </ul>
      </div>
    </div>
  )
}
