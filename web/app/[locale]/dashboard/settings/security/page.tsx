'use client';

import { useState } from 'react';
import { Lock, Shield, Eye, EyeOff, Loader2, Check, AlertTriangle } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { useAuth } from '@/lib/hooks/useAuth';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://18.198.173.81:7500';

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
      const response = await fetch(`${API_URL}/auth/change-password`, {
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
      <div className="bg-premium-card border border-premium-border rounded-xl p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-premium-surface rounded-lg flex items-center justify-center">
              <Shield className="h-5 w-5 text-gray-400" />
            </div>
            <div>
              <h3 className="font-medium text-white">{t('twoFactor')}</h3>
              <p className="text-sm text-gray-500">Add an extra layer of security</p>
            </div>
          </div>

          <button className="px-4 py-2 bg-premium-surface border border-premium-border rounded-lg text-gray-400 hover:text-white hover:border-gold-500/30 transition-colors">
            {t('enable2FA')}
          </button>
        </div>
      </div>
    </div>
  );
}
