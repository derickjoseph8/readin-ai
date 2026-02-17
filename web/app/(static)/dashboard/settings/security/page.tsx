'use client'

import { useState, useEffect } from 'react'
import {
  Shield,
  Key,
  Smartphone,
  History,
  Eye,
  EyeOff,
  Check,
  AlertCircle,
  LogOut,
  Copy,
  RefreshCw,
  X,
  Loader2
} from 'lucide-react'
import { authApi, twoFactorApi, sessionsApi, TwoFactorStatus, TwoFactorSetupResponse, UserSession } from '@/lib/api/auth'

export default function SecurityPage() {
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showCurrentPassword, setShowCurrentPassword] = useState(false)
  const [showNewPassword, setShowNewPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // 2FA State
  const [twoFactorStatus, setTwoFactorStatus] = useState<TwoFactorStatus | null>(null)
  const [twoFactorLoading, setTwoFactorLoading] = useState(true)
  const [showSetupModal, setShowSetupModal] = useState(false)
  const [showDisableModal, setShowDisableModal] = useState(false)
  const [showBackupCodesModal, setShowBackupCodesModal] = useState(false)
  const [backupCodes, setBackupCodes] = useState<string[]>([])

  // Sessions State
  const [sessions, setSessions] = useState<UserSession[]>([])
  const [currentSessionId, setCurrentSessionId] = useState<number | null>(null)
  const [sessionsLoading, setSessionsLoading] = useState(true)
  const [revokingSessionId, setRevokingSessionId] = useState<number | null>(null)

  // Fetch 2FA status and sessions on mount
  useEffect(() => {
    const fetch2FAStatus = async () => {
      try {
        const status = await twoFactorApi.getStatus()
        setTwoFactorStatus(status)
      } catch (err) {
        console.error('Failed to fetch 2FA status:', err)
      } finally {
        setTwoFactorLoading(false)
      }
    }

    const fetchSessions = async () => {
      try {
        const data = await sessionsApi.getSessions()
        setSessions(data.sessions)
        setCurrentSessionId(data.current_session_id)
      } catch (err) {
        console.error('Failed to fetch sessions:', err)
      } finally {
        setSessionsLoading(false)
      }
    }

    fetch2FAStatus()
    fetchSessions()
  }, [])

  const handleRevokeSession = async (sessionId: number) => {
    setRevokingSessionId(sessionId)
    try {
      await sessionsApi.revokeSession(sessionId)
      setSessions(prev => prev.filter(s => s.id !== sessionId))
    } catch (err) {
      console.error('Failed to revoke session:', err)
    } finally {
      setRevokingSessionId(null)
    }
  }

  const handleRevokeAllSessions = async () => {
    if (!confirm('This will log you out of all other devices. Continue?')) return

    try {
      const result = await sessionsApi.revokeAllSessions(true)
      setSessions(prev => prev.filter(s => s.id === currentSessionId))
      alert(result.message)
    } catch (err) {
      console.error('Failed to revoke all sessions:', err)
    }
  }

  const formatSessionTime = (dateStr: string) => {
    const date = new Date(dateStr)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const minutes = Math.floor(diff / 60000)
    const hours = Math.floor(minutes / 60)
    const days = Math.floor(hours / 24)

    if (minutes < 1) return 'Just now'
    if (minutes < 60) return `${minutes}m ago`
    if (hours < 24) return `${hours}h ago`
    if (days < 7) return `${days}d ago`
    return date.toLocaleDateString()
  }

  const getDeviceIcon = (deviceType: string | null) => {
    switch (deviceType) {
      case 'mobile':
        return <Smartphone className="h-5 w-5 text-blue-400" />
      case 'tablet':
        return <Smartphone className="h-5 w-5 text-purple-400" />
      default:
        return <Shield className="h-5 w-5 text-emerald-400" />
    }
  }

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

  const handle2FAEnabled = (codes: string[]) => {
    setBackupCodes(codes)
    setTwoFactorStatus({ enabled: true, backup_codes_remaining: codes.length })
    setShowSetupModal(false)
    setShowBackupCodesModal(true)
  }

  const handle2FADisabled = () => {
    setTwoFactorStatus({ enabled: false, backup_codes_remaining: 0 })
    setShowDisableModal(false)
  }

  const handleRegenerateBackupCodes = async (code: string) => {
    try {
      const result = await twoFactorApi.regenerateBackupCodes(code)
      setBackupCodes(result.codes)
      setTwoFactorStatus(prev => prev ? { ...prev, backup_codes_remaining: result.codes.length } : null)
      setShowBackupCodesModal(true)
    } catch (err) {
      throw err
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

        {twoFactorLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-gold-400" />
          </div>
        ) : twoFactorStatus?.enabled ? (
          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-lg">
              <div className="flex items-center">
                <Check className="h-5 w-5 text-emerald-400 mr-3" />
                <div>
                  <p className="text-white font-medium">2FA is enabled</p>
                  <p className="text-gray-400 text-sm mt-0.5">
                    {twoFactorStatus.backup_codes_remaining} backup codes remaining
                  </p>
                </div>
              </div>
              <span className="px-3 py-1 bg-emerald-500/20 text-emerald-400 text-sm rounded-lg">
                Active
              </span>
            </div>

            <div className="flex flex-wrap gap-3">
              <button
                onClick={() => setShowBackupCodesModal(true)}
                className="px-4 py-2 bg-premium-surface border border-premium-border rounded-lg text-white hover:bg-premium-surface/80 transition-colors flex items-center"
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                View/Regenerate Backup Codes
              </button>
              <button
                onClick={() => setShowDisableModal(true)}
                className="px-4 py-2 bg-red-500/10 border border-red-500/30 text-red-400 rounded-lg hover:bg-red-500/20 transition-colors flex items-center"
              >
                <X className="h-4 w-4 mr-2" />
                Disable 2FA
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 bg-premium-surface rounded-lg">
              <div>
                <p className="text-white font-medium">Authenticator App</p>
                <p className="text-gray-500 text-sm mt-0.5">
                  Add an extra layer of security to your account
                </p>
              </div>
              <button
                onClick={() => setShowSetupModal(true)}
                className="px-4 py-2 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-medium rounded-lg hover:shadow-gold transition-all"
              >
                Enable
              </button>
            </div>

            <p className="text-xs text-gray-500">
              Use an authenticator app like Google Authenticator, Authy, or 1Password to generate verification codes
            </p>
          </div>
        )}
      </div>

      {/* Active Sessions */}
      <div className="bg-premium-card border border-premium-border rounded-xl p-6">
        <h2 className="font-semibold text-white mb-4 flex items-center">
          <History className="h-5 w-5 text-gold-400 mr-2" />
          Active Sessions
          {!sessionsLoading && (
            <span className="ml-2 px-2 py-0.5 bg-premium-surface text-gray-400 text-xs rounded">
              {sessions.length} active
            </span>
          )}
        </h2>

        {sessionsLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-gold-400" />
          </div>
        ) : sessions.length > 0 ? (
          <div className="space-y-3">
            {sessions.map((session) => (
              <div
                key={session.id}
                className="flex items-center justify-between p-4 bg-premium-surface rounded-lg"
              >
                <div className="flex items-center">
                  <div className={`w-10 h-10 ${session.id === currentSessionId ? 'bg-emerald-500/20' : 'bg-premium-bg'} rounded-lg flex items-center justify-center mr-3`}>
                    {getDeviceIcon(session.device_type)}
                  </div>
                  <div>
                    <p className="text-white font-medium flex items-center">
                      {session.os || 'Unknown'} - {session.browser || 'Unknown Browser'}
                      {session.id === currentSessionId && (
                        <span className="ml-2 px-2 py-0.5 bg-emerald-500/20 text-emerald-400 text-xs rounded">
                          Current
                        </span>
                      )}
                    </p>
                    <p className="text-gray-500 text-sm mt-0.5">
                      {session.ip_address || 'Unknown IP'} • Last active {formatSessionTime(session.last_activity)}
                    </p>
                  </div>
                </div>
                {session.id !== currentSessionId && (
                  <button
                    onClick={() => handleRevokeSession(session.id)}
                    disabled={revokingSessionId === session.id}
                    className="text-red-400 hover:text-red-300 transition-colors p-2 rounded-lg hover:bg-red-500/10"
                    title="Revoke session"
                  >
                    {revokingSessionId === session.id ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <X className="h-4 w-4" />
                    )}
                  </button>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            <Shield className="h-12 w-12 mx-auto mb-3 text-gray-600" />
            <p>No active sessions found</p>
          </div>
        )}

        {sessions.length > 1 && (
          <div className="mt-4 pt-4 border-t border-premium-border">
            <button
              onClick={handleRevokeAllSessions}
              className="text-red-400 text-sm hover:text-red-300 transition-colors flex items-center"
            >
              <LogOut className="h-4 w-4 mr-2" />
              Log out all other sessions
            </button>
          </div>
        )}
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
            <span className="text-gray-300">Enable two-factor authentication for extra security</span>
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

      {/* 2FA Setup Modal */}
      {showSetupModal && (
        <TwoFactorSetupModal
          onClose={() => setShowSetupModal(false)}
          onSuccess={handle2FAEnabled}
        />
      )}

      {/* 2FA Disable Modal */}
      {showDisableModal && (
        <TwoFactorDisableModal
          onClose={() => setShowDisableModal(false)}
          onSuccess={handle2FADisabled}
        />
      )}

      {/* Backup Codes Modal */}
      {showBackupCodesModal && (
        <BackupCodesModal
          codes={backupCodes}
          onClose={() => setShowBackupCodesModal(false)}
          onRegenerate={handleRegenerateBackupCodes}
          isEnabled={twoFactorStatus?.enabled || false}
        />
      )}
    </div>
  )
}

// 2FA Setup Modal Component
function TwoFactorSetupModal({
  onClose,
  onSuccess
}: {
  onClose: () => void
  onSuccess: (codes: string[]) => void
}) {
  const [step, setStep] = useState<'setup' | 'verify'>('setup')
  const [setupData, setSetupData] = useState<TwoFactorSetupResponse | null>(null)
  const [verificationCode, setVerificationCode] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const initSetup = async () => {
      try {
        const data = await twoFactorApi.setup()
        setSetupData(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to initialize 2FA setup')
      }
    }
    initSetup()
  }, [])

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError(null)

    try {
      const result = await twoFactorApi.verify(verificationCode)
      onSuccess(result.backup_codes)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Invalid verification code')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="fixed inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-premium-card border border-premium-border rounded-xl shadow-2xl w-full max-w-md">
        <div className="p-6 border-b border-premium-border flex items-center justify-between">
          <h3 className="text-lg font-semibold text-white">
            {step === 'setup' ? 'Set Up 2FA' : 'Verify Setup'}
          </h3>
          <button onClick={onClose} className="text-gray-400 hover:text-white">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-6">
          {error && (
            <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm flex items-center">
              <AlertCircle className="h-4 w-4 mr-2 flex-shrink-0" />
              {error}
            </div>
          )}

          {step === 'setup' && setupData ? (
            <div className="space-y-4">
              <p className="text-gray-300 text-sm">
                Scan this QR code with your authenticator app:
              </p>

              <div className="flex justify-center p-4 bg-white rounded-lg">
                <img
                  src={`data:image/png;base64,${setupData.qr_code}`}
                  alt="2FA QR Code"
                  className="w-48 h-48"
                />
              </div>

              <div className="text-center">
                <p className="text-xs text-gray-500 mb-2">Or enter this key manually:</p>
                <code className="px-3 py-1.5 bg-premium-surface rounded text-sm text-gold-400 font-mono">
                  {setupData.secret}
                </code>
              </div>

              <button
                onClick={() => setStep('verify')}
                className="w-full py-2.5 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-medium rounded-lg hover:shadow-gold transition-all"
              >
                Continue
              </button>
            </div>
          ) : step === 'verify' ? (
            <form onSubmit={handleVerify} className="space-y-4">
              <p className="text-gray-300 text-sm">
                Enter the 6-digit code from your authenticator app:
              </p>

              <input
                type="text"
                value={verificationCode}
                onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                className="w-full px-4 py-3 bg-premium-surface border border-premium-border rounded-lg text-white text-center text-2xl font-mono tracking-widest focus:outline-none focus:border-gold-500"
                placeholder="000000"
                maxLength={6}
                autoFocus
              />

              <button
                type="submit"
                disabled={verificationCode.length !== 6 || isLoading}
                className="w-full py-2.5 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-medium rounded-lg hover:shadow-gold transition-all disabled:opacity-50 flex items-center justify-center"
              >
                {isLoading ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  'Verify & Enable'
                )}
              </button>
            </form>
          ) : (
            <div className="flex justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-gold-400" />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// 2FA Disable Modal Component
function TwoFactorDisableModal({
  onClose,
  onSuccess
}: {
  onClose: () => void
  onSuccess: () => void
}) {
  const [password, setPassword] = useState('')
  const [code, setCode] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleDisable = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError(null)

    try {
      await twoFactorApi.disable(password, code || undefined)
      onSuccess()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to disable 2FA')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="fixed inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-premium-card border border-premium-border rounded-xl shadow-2xl w-full max-w-md">
        <div className="p-6 border-b border-premium-border flex items-center justify-between">
          <h3 className="text-lg font-semibold text-white">Disable 2FA</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-white">
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleDisable} className="p-6 space-y-4">
          {error && (
            <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm flex items-center">
              <AlertCircle className="h-4 w-4 mr-2 flex-shrink-0" />
              {error}
            </div>
          )}

          <p className="text-gray-300 text-sm">
            To disable two-factor authentication, enter your password and a verification code:
          </p>

          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2.5 bg-premium-surface border border-premium-border rounded-lg text-white focus:outline-none focus:border-gold-500"
              placeholder="Enter your password"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">
              Verification Code (optional)
            </label>
            <input
              type="text"
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
              className="w-full px-4 py-2.5 bg-premium-surface border border-premium-border rounded-lg text-white focus:outline-none focus:border-gold-500"
              placeholder="6-digit code"
              maxLength={6}
            />
          </div>

          <button
            type="submit"
            disabled={!password || isLoading}
            className="w-full py-2.5 bg-red-500 text-white font-medium rounded-lg hover:bg-red-600 transition-all disabled:opacity-50 flex items-center justify-center"
          >
            {isLoading ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              'Disable 2FA'
            )}
          </button>
        </form>
      </div>
    </div>
  )
}

// Backup Codes Modal Component
function BackupCodesModal({
  codes,
  onClose,
  onRegenerate,
  isEnabled
}: {
  codes: string[]
  onClose: () => void
  onRegenerate: (code: string) => Promise<void>
  isEnabled: boolean
}) {
  const [showRegenerate, setShowRegenerate] = useState(false)
  const [regenerateCode, setRegenerateCode] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(codes.join('\n'))
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleRegenerate = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError(null)

    try {
      await onRegenerate(regenerateCode)
      setShowRegenerate(false)
      setRegenerateCode('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to regenerate codes')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="fixed inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-premium-card border border-premium-border rounded-xl shadow-2xl w-full max-w-md">
        <div className="p-6 border-b border-premium-border flex items-center justify-between">
          <h3 className="text-lg font-semibold text-white">Backup Codes</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-white">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-6 space-y-4">
          {codes.length > 0 ? (
            <>
              <p className="text-gray-300 text-sm">
                Save these backup codes in a safe place. Each code can only be used once.
              </p>

              <div className="bg-premium-surface rounded-lg p-4 font-mono text-sm">
                <div className="grid grid-cols-2 gap-2">
                  {codes.map((code, i) => (
                    <div key={i} className="text-white">
                      {code}
                    </div>
                  ))}
                </div>
              </div>

              <button
                onClick={handleCopy}
                className="w-full py-2 bg-premium-surface border border-premium-border rounded-lg text-white hover:bg-premium-surface/80 transition-colors flex items-center justify-center"
              >
                {copied ? (
                  <>
                    <Check className="h-4 w-4 mr-2 text-emerald-400" />
                    Copied!
                  </>
                ) : (
                  <>
                    <Copy className="h-4 w-4 mr-2" />
                    Copy Codes
                  </>
                )}
              </button>
            </>
          ) : (
            <p className="text-gray-400 text-center py-4">
              No backup codes available. Generate new codes below.
            </p>
          )}

          {isEnabled && !showRegenerate && (
            <button
              onClick={() => setShowRegenerate(true)}
              className="w-full py-2 text-gold-400 hover:text-gold-300 transition-colors flex items-center justify-center"
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Regenerate Backup Codes
            </button>
          )}

          {showRegenerate && (
            <form onSubmit={handleRegenerate} className="space-y-3 pt-4 border-t border-premium-border">
              {error && (
                <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
                  {error}
                </div>
              )}
              <p className="text-gray-400 text-sm">
                Enter a verification code to generate new backup codes. This will invalidate existing codes.
              </p>
              <input
                type="text"
                value={regenerateCode}
                onChange={(e) => setRegenerateCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                className="w-full px-4 py-2.5 bg-premium-surface border border-premium-border rounded-lg text-white focus:outline-none focus:border-gold-500"
                placeholder="6-digit code"
                maxLength={6}
              />
              <button
                type="submit"
                disabled={regenerateCode.length !== 6 || isLoading}
                className="w-full py-2 bg-gold-500 text-premium-bg font-medium rounded-lg hover:bg-gold-400 transition-all disabled:opacity-50 flex items-center justify-center"
              >
                {isLoading ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  'Generate New Codes'
                )}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}
