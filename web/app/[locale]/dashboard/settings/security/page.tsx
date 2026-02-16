'use client';

import { useState, useEffect } from 'react';
import { Lock, Shield, Eye, EyeOff, Loader2, Check, AlertTriangle, Smartphone, Copy, RefreshCw, X } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { useAuth } from '@/lib/hooks/useAuth';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://www.getreadin.us';

function PasswordStrength({ password }: { password: string }) {
  const getStrength = (pwd: string): { score: number; label: string; color: string } => {
    let score = 0;
    if (pwd.length >= 8) score++;
    if (pwd.length >= 12) score++;
    if (/[A-Z]/.test(pwd)) score++;
    if (/[a-z]/.test(pwd)) score++;
    if (/[0-9]/.test(pwd)) score++;
    if (/[^A-Za-z0-9]/.test(pwd)) score++;

    if (score <= 2) return { score, label: 'Weak', color: 'bg-red-500' };
    if (score <= 4) return { score, label: 'Medium', color: 'bg-yellow-500' };
    return { score, label: 'Strong', color: 'bg-emerald-500' };
  };

  const strength = getStrength(password);

  if (!password) return null;

  return (
    <div className="mt-2">
      <div className="flex gap-1 h-1.5">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <div
            key={i}
            className={`flex-1 rounded-full transition-colors ${
              i <= strength.score ? strength.color : 'bg-premium-surface'
            }`}
          />
        ))}
      </div>
      <p className={`text-xs mt-1 ${
        strength.label === 'Weak' ? 'text-red-400' :
        strength.label === 'Medium' ? 'text-yellow-400' : 'text-emerald-400'
      }`}>
        {strength.label}
      </p>
    </div>
  );
}

interface TwoFactorStatus {
  enabled: boolean;
  backup_codes_remaining: number;
}

interface TwoFactorSetup {
  secret: string;
  qr_code: string;
  provisioning_uri: string;
}

function TwoFactorSection() {
  const { token } = useAuth();
  const [status, setStatus] = useState<TwoFactorStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [setupData, setSetupData] = useState<TwoFactorSetup | null>(null);
  const [verificationCode, setVerificationCode] = useState('');
  const [backupCodes, setBackupCodes] = useState<string[]>([]);
  const [showBackupCodes, setShowBackupCodes] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [showDisableModal, setShowDisableModal] = useState(false);
  const [disablePassword, setDisablePassword] = useState('');
  const [disableCode, setDisableCode] = useState('');
  const [copiedSecret, setCopiedSecret] = useState(false);

  // Fetch 2FA status
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const response = await fetch(`${API_URL}/api/v1/2fa/status`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (response.ok) {
          const data = await response.json();
          setStatus(data);
        }
      } catch (err) {
        console.error('Failed to fetch 2FA status:', err);
      } finally {
        setIsLoading(false);
      }
    };

    if (token) {
      fetchStatus();
    }
  }, [token]);

  const handleSetup = async () => {
    setError('');
    setIsProcessing(true);

    try {
      const response = await fetch(`${API_URL}/api/v1/2fa/setup`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      });

      if (response.ok) {
        const data = await response.json();
        setSetupData(data);
      } else {
        const data = await response.json();
        setError(data.detail || 'Failed to initialize 2FA setup');
      }
    } catch {
      setError('Unable to connect to server');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleVerify = async () => {
    setError('');
    setIsProcessing(true);

    try {
      const response = await fetch(`${API_URL}/api/v1/2fa/verify`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ code: verificationCode })
      });

      if (response.ok) {
        const data = await response.json();
        setBackupCodes(data.backup_codes);
        setShowBackupCodes(true);
        setSetupData(null);
        setVerificationCode('');
        setStatus({ enabled: true, backup_codes_remaining: data.backup_codes.length });
        setSuccess('Two-factor authentication enabled successfully!');
      } else {
        const data = await response.json();
        setError(data.detail || 'Invalid verification code');
      }
    } catch {
      setError('Unable to connect to server');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDisable = async () => {
    setError('');
    setIsProcessing(true);

    try {
      const response = await fetch(`${API_URL}/api/v1/2fa/disable`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          password: disablePassword,
          code: disableCode || undefined
        })
      });

      if (response.ok) {
        setStatus({ enabled: false, backup_codes_remaining: 0 });
        setShowDisableModal(false);
        setDisablePassword('');
        setDisableCode('');
        setSuccess('Two-factor authentication disabled');
      } else {
        const data = await response.json();
        setError(data.detail || 'Failed to disable 2FA');
      }
    } catch {
      setError('Unable to connect to server');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleRegenerateBackupCodes = async () => {
    const code = prompt('Enter your current authenticator code to regenerate backup codes:');
    if (!code) return;

    setIsProcessing(true);
    setError('');

    try {
      const response = await fetch(`${API_URL}/api/v1/2fa/backup-codes/regenerate`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ code })
      });

      if (response.ok) {
        const data = await response.json();
        setBackupCodes(data.codes);
        setShowBackupCodes(true);
        setStatus(prev => prev ? { ...prev, backup_codes_remaining: data.codes.length } : null);
        setSuccess('Backup codes regenerated');
      } else {
        const data = await response.json();
        setError(data.detail || 'Failed to regenerate backup codes');
      }
    } catch {
      setError('Unable to connect to server');
    } finally {
      setIsProcessing(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedSecret(true);
    setTimeout(() => setCopiedSecret(false), 2000);
  };

  const copyBackupCodes = () => {
    const codesText = backupCodes.join('\n');
    navigator.clipboard.writeText(codesText);
    setSuccess('Backup codes copied to clipboard');
    setTimeout(() => setSuccess(''), 3000);
  };

  if (isLoading) {
    return (
      <div className="bg-premium-card border border-premium-border rounded-xl p-6">
        <div className="flex items-center justify-center py-4">
          <Loader2 className="h-6 w-6 animate-spin text-gold-400" />
        </div>
      </div>
    );
  }

  return (
    <div className="bg-premium-card border border-premium-border rounded-xl p-6 space-y-4">
      <div className="flex items-center gap-3 mb-2">
        <Shield className="h-5 w-5 text-gold-400" />
        <h2 className="text-lg font-semibold text-white">Two-Factor Authentication</h2>
      </div>

      {error && (
        <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm flex items-center">
          <AlertTriangle className="h-4 w-4 mr-2 flex-shrink-0" />
          {error}
        </div>
      )}

      {success && (
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-emerald-400 text-sm flex items-center">
          <Check className="h-4 w-4 mr-2 flex-shrink-0" />
          {success}
        </div>
      )}

      {/* Setup Flow */}
      {setupData && (
        <div className="space-y-4 p-4 bg-premium-surface rounded-lg border border-premium-border">
          <h3 className="font-medium text-white">Setup Two-Factor Authentication</h3>

          <div className="flex flex-col items-center space-y-4">
            <p className="text-sm text-gray-400 text-center">
              Scan this QR code with your authenticator app (Google Authenticator, Duo, Authy, etc.)
            </p>

            {/* QR Code */}
            <div className="bg-white p-4 rounded-lg">
              <img
                src={`data:image/png;base64,${setupData.qr_code}`}
                alt="2FA QR Code"
                className="w-48 h-48"
              />
            </div>

            {/* Manual Entry */}
            <div className="w-full">
              <p className="text-xs text-gray-500 mb-2 text-center">Or enter this code manually:</p>
              <div className="flex items-center gap-2 bg-premium-bg p-3 rounded-lg">
                <code className="flex-1 text-sm text-gold-400 font-mono break-all">
                  {setupData.secret}
                </code>
                <button
                  onClick={() => copyToClipboard(setupData.secret)}
                  className="p-2 hover:bg-premium-surface rounded-lg transition-colors"
                  title="Copy secret"
                >
                  {copiedSecret ? (
                    <Check className="h-4 w-4 text-emerald-400" />
                  ) : (
                    <Copy className="h-4 w-4 text-gray-400" />
                  )}
                </button>
              </div>
            </div>

            {/* Verification Code Input */}
            <div className="w-full">
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Enter the 6-digit code from your app
              </label>
              <input
                type="text"
                value={verificationCode}
                onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                placeholder="000000"
                className="w-full px-4 py-3 bg-premium-bg border border-premium-border rounded-lg focus:border-gold-500 focus:outline-none text-white text-center text-2xl tracking-widest font-mono"
                maxLength={6}
              />
            </div>

            <div className="flex gap-3 w-full">
              <button
                onClick={() => {
                  setSetupData(null);
                  setVerificationCode('');
                  setError('');
                }}
                className="flex-1 px-4 py-3 bg-premium-surface border border-premium-border rounded-lg text-gray-400 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleVerify}
                disabled={verificationCode.length !== 6 || isProcessing}
                className="flex-1 px-4 py-3 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-semibold rounded-lg hover:shadow-gold transition-all disabled:opacity-50 flex items-center justify-center"
              >
                {isProcessing ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <>
                    <Check className="h-5 w-5 mr-2" />
                    Verify & Enable
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Backup Codes Modal */}
      {showBackupCodes && backupCodes.length > 0 && (
        <div className="space-y-4 p-4 bg-premium-surface rounded-lg border border-gold-500/30">
          <div className="flex items-center justify-between">
            <h3 className="font-medium text-white">Backup Codes</h3>
            <button
              onClick={() => setShowBackupCodes(false)}
              className="text-gray-400 hover:text-white"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          <p className="text-sm text-gray-400">
            Save these backup codes in a secure place. Each code can only be used once.
          </p>

          <div className="grid grid-cols-2 gap-2">
            {backupCodes.map((code, index) => (
              <div key={index} className="bg-premium-bg p-2 rounded font-mono text-sm text-center text-gold-400">
                {code}
              </div>
            ))}
          </div>

          <button
            onClick={copyBackupCodes}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-premium-bg border border-premium-border rounded-lg text-gray-300 hover:text-white hover:border-gold-500/30 transition-colors"
          >
            <Copy className="h-4 w-4" />
            Copy All Codes
          </button>
        </div>
      )}

      {/* Current Status */}
      {!setupData && status && (
        <div className="flex items-center justify-between p-4 bg-premium-surface rounded-lg">
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
              status.enabled ? 'bg-emerald-500/20' : 'bg-premium-bg'
            }`}>
              <Smartphone className={`h-5 w-5 ${status.enabled ? 'text-emerald-400' : 'text-gray-400'}`} />
            </div>
            <div>
              <p className="font-medium text-white">
                {status.enabled ? 'Enabled' : 'Not Enabled'}
              </p>
              {status.enabled && (
                <p className="text-sm text-gray-500">
                  {status.backup_codes_remaining} backup codes remaining
                </p>
              )}
            </div>
          </div>

          {status.enabled ? (
            <div className="flex gap-2">
              <button
                onClick={handleRegenerateBackupCodes}
                disabled={isProcessing}
                className="flex items-center gap-2 px-3 py-2 bg-premium-bg border border-premium-border rounded-lg text-gray-400 hover:text-white hover:border-gold-500/30 transition-colors text-sm"
              >
                <RefreshCw className="h-4 w-4" />
                New Codes
              </button>
              <button
                onClick={() => setShowDisableModal(true)}
                className="px-4 py-2 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 hover:bg-red-500/20 transition-colors text-sm"
              >
                Disable
              </button>
            </div>
          ) : (
            <button
              onClick={handleSetup}
              disabled={isProcessing}
              className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-semibold rounded-lg hover:shadow-gold transition-all disabled:opacity-50"
            >
              {isProcessing ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <>
                  <Shield className="h-4 w-4" />
                  Enable 2FA
                </>
              )}
            </button>
          )}
        </div>
      )}

      {/* Disable Modal */}
      {showDisableModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-premium-card border border-premium-border rounded-xl p-6 max-w-md w-full mx-4 space-y-4">
            <h3 className="text-lg font-semibold text-white">Disable Two-Factor Authentication</h3>
            <p className="text-sm text-gray-400">
              Enter your password and optionally a verification code to disable 2FA.
            </p>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Password</label>
              <input
                type="password"
                value={disablePassword}
                onChange={(e) => setDisablePassword(e.target.value)}
                className="w-full px-4 py-3 bg-premium-surface border border-premium-border rounded-lg focus:border-gold-500 focus:outline-none text-white"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Verification Code (optional)
              </label>
              <input
                type="text"
                value={disableCode}
                onChange={(e) => setDisableCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                placeholder="000000"
                className="w-full px-4 py-3 bg-premium-surface border border-premium-border rounded-lg focus:border-gold-500 focus:outline-none text-white font-mono"
                maxLength={6}
              />
            </div>

            {error && (
              <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
                {error}
              </div>
            )}

            <div className="flex gap-3">
              <button
                onClick={() => {
                  setShowDisableModal(false);
                  setDisablePassword('');
                  setDisableCode('');
                  setError('');
                }}
                className="flex-1 px-4 py-3 bg-premium-surface border border-premium-border rounded-lg text-gray-400 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleDisable}
                disabled={!disablePassword || isProcessing}
                className="flex-1 px-4 py-3 bg-red-500 text-white font-semibold rounded-lg hover:bg-red-600 transition-colors disabled:opacity-50 flex items-center justify-center"
              >
                {isProcessing ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  'Disable 2FA'
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      <p className="text-xs text-gray-500">
        Two-factor authentication adds an extra layer of security by requiring a code from your authenticator app when you sign in.
      </p>
    </div>
  );
}

export default function SecurityPage() {
  const { token } = useAuth();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const t = useTranslations('settings.security');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess(false);

    if (newPassword !== confirmPassword) {
      setError('New passwords do not match');
      return;
    }

    if (newPassword.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }

    setIsLoading(true);

    try {
      const response = await fetch(`${API_URL}/api/v1/auth/change-password`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword
        })
      });

      if (response.ok) {
        setSuccess(true);
        setCurrentPassword('');
        setNewPassword('');
        setConfirmPassword('');
        setTimeout(() => setSuccess(false), 5000);
      } else {
        const data = await response.json();
        setError(data.detail || 'Failed to change password');
      }
    } catch {
      setError('Unable to connect to server');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-2xl">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">{t('title')}</h1>
        <p className="text-gray-400 mt-1">
          Manage your password and security settings
        </p>
      </div>

      {/* Change Password */}
      <form onSubmit={handleSubmit} className="bg-premium-card border border-premium-border rounded-xl p-6 space-y-6">
        <div className="flex items-center gap-3 mb-2">
          <Lock className="h-5 w-5 text-gold-400" />
          <h2 className="text-lg font-semibold text-white">{t('password')}</h2>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            {t('currentPassword')}
          </label>
          <div className="relative">
            <input
              type={showCurrent ? 'text' : 'password'}
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              className="w-full px-4 py-3 pr-10 bg-premium-surface border border-premium-border rounded-lg focus:border-gold-500 focus:outline-none text-white"
              required
            />
            <button
              type="button"
              onClick={() => setShowCurrent(!showCurrent)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300"
            >
              {showCurrent ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
            </button>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            {t('newPassword')}
          </label>
          <div className="relative">
            <input
              type={showNew ? 'text' : 'password'}
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="w-full px-4 py-3 pr-10 bg-premium-surface border border-premium-border rounded-lg focus:border-gold-500 focus:outline-none text-white"
              required
              minLength={8}
            />
            <button
              type="button"
              onClick={() => setShowNew(!showNew)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300"
            >
              {showNew ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
            </button>
          </div>
          <PasswordStrength password={newPassword} />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            {t('confirmPassword')}
          </label>
          <div className="relative">
            <input
              type={showConfirm ? 'text' : 'password'}
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className={`w-full px-4 py-3 pr-10 bg-premium-surface border rounded-lg focus:outline-none text-white ${
                confirmPassword && confirmPassword !== newPassword
                  ? 'border-red-500 focus:border-red-500'
                  : confirmPassword && confirmPassword === newPassword
                  ? 'border-emerald-500 focus:border-emerald-500'
                  : 'border-premium-border focus:border-gold-500'
              }`}
              required
            />
            <button
              type="button"
              onClick={() => setShowConfirm(!showConfirm)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300"
            >
              {showConfirm ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
            </button>
          </div>
          {confirmPassword && confirmPassword !== newPassword && (
            <p className="text-xs text-red-400 mt-1">Passwords do not match</p>
          )}
          {confirmPassword && confirmPassword === newPassword && (
            <p className="text-xs text-emerald-400 mt-1 flex items-center">
              <Check className="h-3 w-3 mr-1" /> Passwords match
            </p>
          )}
        </div>

        {error && (
          <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm flex items-center">
            <AlertTriangle className="h-4 w-4 mr-2 flex-shrink-0" />
            {error}
          </div>
        )}

        {success && (
          <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-emerald-400 text-sm flex items-center">
            <Check className="h-4 w-4 mr-2 flex-shrink-0" />
            Password changed successfully!
          </div>
        )}

        <button
          type="submit"
          disabled={isLoading || !currentPassword || !newPassword || newPassword !== confirmPassword}
          className="flex items-center px-6 py-3 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-semibold rounded-lg hover:shadow-gold transition-all disabled:opacity-50"
        >
          {isLoading ? (
            <Loader2 className="h-5 w-5 mr-2 animate-spin" />
          ) : (
            <Lock className="h-5 w-5 mr-2" />
          )}
          Update Password
        </button>
      </form>

      {/* Two-Factor Authentication */}
      <TwoFactorSection />
    </div>
  );
}
