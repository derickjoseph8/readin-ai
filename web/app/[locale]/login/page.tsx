'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, Mail, Lock, Loader2, User, Building2, UserCircle, Smartphone } from 'lucide-react';
import { useTranslations } from 'next-intl';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://www.getreadin.us';

export default function LoginPage() {
  const router = useRouter();
  const [isLogin, setIsLogin] = useState(true);
  const [loading, setLoading] = useState(false);
  const [checkingAuth, setCheckingAuth] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [accountType, setAccountType] = useState<'individual' | 'business'>('individual');
  const [companyName, setCompanyName] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const t = useTranslations('login');
  const tc = useTranslations('common');

  // 2FA State
  const [requires2FA, setRequires2FA] = useState(false);
  const [twoFactorCode, setTwoFactorCode] = useState('');
  const [isBackupCode, setIsBackupCode] = useState(false);
  const [tempToken, setTempToken] = useState('');

  // Track component mount state
  const isMountedRef = useRef(true);

  // Cleanup on unmount
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  // Check if user is already logged in
  useEffect(() => {
    let isActive = true;

    const checkAuth = async () => {
      const token = localStorage.getItem('readin_token');
      if (token) {
        try {
          const res = await fetch(`${API_URL}/user/me`, {
            headers: { 'Authorization': `Bearer ${token}` }
          });
          if (res.ok && isActive) {
            const userData = await res.json();
            // Redirect based on user role
            if (userData.is_staff && (userData.staff_role === 'super_admin' || userData.staff_role === 'admin')) {
              router.replace('/admin');
            } else {
              router.replace('/dashboard');
            }
            return;
          }
        } catch {
          // Token invalid, continue to login page
        }
      }
      if (isActive) {
        setCheckingAuth(false);
      }
    };
    checkAuth();

    return () => {
      isActive = false;
    };
  }, [router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isMountedRef.current) return;

    setLoading(true);
    setError('');
    setSuccess('');

    try {
      const endpoint = isLogin ? '/api/v1/auth/login' : '/api/v1/auth/register';
      const body = isLogin
        ? { email, password }
        : {
            email,
            password,
            full_name: name,
            account_type: accountType,
            company_name: accountType === 'business' ? companyName : undefined
          };

      const response = await fetch(`${API_URL}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (!isMountedRef.current) return;

      const data = await response.json();

      if (response.ok) {
        if (isLogin) {
          // Check if 2FA is required
          if (data.requires_2fa && data.temp_token) {
            setTempToken(data.temp_token);
            setRequires2FA(true);
            setLoading(false);
          } else if (data.access_token) {
            localStorage.setItem('readin_token', data.access_token);
            setSuccess('Login successful! Redirecting...');

            // Fetch user info to determine redirect destination
            try {
              const userResponse = await fetch(`${API_URL}/user/me`, {
                headers: {
                  'Authorization': `Bearer ${data.access_token}`,
                  'Content-Type': 'application/json'
                }
              });
              const userData = await userResponse.json();

              // Redirect based on user role
              if (userData.is_staff && (userData.staff_role === 'super_admin' || userData.staff_role === 'admin')) {
                router.push('/admin');
              } else {
                router.push('/dashboard');
              }
            } catch {
              router.push('/dashboard');
            }
          } else {
            setError(data.detail || 'Login failed');
            setLoading(false);
          }
        } else {
          setSuccess('Account created! You can now log in.');
          setIsLogin(true);
          setLoading(false);
        }
      } else {
        setError(data.detail || 'Something went wrong. Please try again.');
        setLoading(false);
      }
    } catch {
      if (!isMountedRef.current) return;
      setError('Unable to connect to our servers. Please try again later.');
      setLoading(false);
    }
  };

  const handle2FASubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isMountedRef.current) return;

    setLoading(true);
    setError('');
    setSuccess('');

    try {
      // Complete 2FA login with the proper endpoint
      const res = await fetch(`${API_URL}/api/v1/auth/login/2fa`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          temp_token: tempToken,
          code: twoFactorCode,
          is_backup_code: isBackupCode,
        }),
      });

      if (!isMountedRef.current) return;

      const data = await res.json();

      if (res.ok && data.access_token) {
        localStorage.setItem('readin_token', data.access_token);
        setSuccess('Success! Redirecting...');

        // Fetch user info to determine redirect destination
        try {
          const userRes = await fetch(`${API_URL}/user/me`, {
            headers: {
              'Authorization': `Bearer ${data.access_token}`,
              'Content-Type': 'application/json'
            }
          });
          const userData = await userRes.json();

          // Redirect based on user role
          if (userData.is_staff && (userData.staff_role === 'super_admin' || userData.staff_role === 'admin')) {
            router.push('/admin');
          } else {
            router.push('/dashboard');
          }
        } catch {
          router.push('/dashboard');
        }
      } else {
        setError(data.detail || 'Invalid verification code');
        setLoading(false);
      }
    } catch {
      if (!isMountedRef.current) return;
      setError('Network error - please try again');
      setLoading(false);
    }
  };

  const handleBack = () => {
    setRequires2FA(false);
    setTwoFactorCode('');
    setIsBackupCode(false);
    setTempToken('');
    setError('');
    setSuccess('');
  };

  // Show loading while checking auth
  if (checkingAuth) {
    return (
      <main className="min-h-screen bg-premium-bg text-white flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-gold-500" />
      </main>
    );
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
            {tc('back')}
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
                      setIsBackupCode(e.target.checked);
                      setTwoFactorCode('');
                    }}
                    className="mr-2"
                  />
                  Use a backup code instead
                </label>
              </div>

              {error && (
                <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
                  {error}
                </div>
              )}

              {success && (
                <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-emerald-400 text-sm">
                  {success}
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
    );
  }

  return (
    <main className="min-h-screen bg-premium-bg text-white flex items-center justify-center px-4">
      {/* Lightweight background gradient */}
      <div className="absolute inset-0 bg-gradient-to-b from-gold-500/5 via-transparent to-transparent" />

      <div className="relative w-full max-w-md">
        {/* Back link */}
        <Link
          href="/"
          className="inline-flex items-center text-gray-400 hover:text-gold-400 transition mb-8"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          {tc('back')}
        </Link>

        {/* Card */}
        <div className="bg-premium-card rounded-2xl border border-premium-border p-8">
          {/* Logo */}
          <div className="text-center mb-8">
            <div className="w-12 h-12 bg-gradient-to-br from-gold-400 to-gold-600 rounded-xl flex items-center justify-center mx-auto mb-4">
              <span className="text-premium-bg font-bold text-xl">R</span>
            </div>
            <h1 className="text-2xl font-bold">
              {isLogin ? t('title') : tc('signUp')}
            </h1>
            <p className="text-gray-400 mt-2">
              {isLogin ? t('subtitle') : 'Start your 7-day free trial'}
            </p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {!isLogin && (
              <>
                {/* Account Type Selection */}
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-3">
                    Account Type
                  </label>
                  <div className="grid grid-cols-2 gap-3">
                    <button
                      type="button"
                      onClick={() => setAccountType('individual')}
                      className={`flex flex-col items-center p-4 rounded-lg border transition-all ${
                        accountType === 'individual'
                          ? 'border-gold-500 bg-gold-500/10 text-gold-400'
                          : 'border-premium-border bg-premium-surface text-gray-400 hover:border-gray-600'
                      }`}
                    >
                      <UserCircle className="h-6 w-6 mb-2" />
                      <span className="text-sm font-medium">Individual</span>
                      <span className="text-xs text-gray-500 mt-1">Personal use</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setAccountType('business')}
                      className={`flex flex-col items-center p-4 rounded-lg border transition-all ${
                        accountType === 'business'
                          ? 'border-gold-500 bg-gold-500/10 text-gold-400'
                          : 'border-premium-border bg-premium-surface text-gray-400 hover:border-gray-600'
                      }`}
                    >
                      <Building2 className="h-6 w-6 mb-2" />
                      <span className="text-sm font-medium">Business</span>
                      <span className="text-xs text-gray-500 mt-1">Team features</span>
                    </button>
                  </div>
                </div>

                {/* Company Name (for business accounts) */}
                {accountType === 'business' && (
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Company Name
                    </label>
                    <div className="relative">
                      <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-500" />
                      <input
                        type="text"
                        value={companyName}
                        onChange={(e) => setCompanyName(e.target.value)}
                        className="w-full pl-10 pr-4 py-3 bg-premium-surface border border-premium-border rounded-lg focus:border-gold-500 focus:outline-none transition text-white"
                        placeholder="Acme Inc."
                        required={accountType === 'business'}
                      />
                    </div>
                  </div>
                )}

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Full Name
                  </label>
                  <div className="relative">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-500" />
                    <input
                      type="text"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      className="w-full pl-10 pr-4 py-3 bg-premium-surface border border-premium-border rounded-lg focus:border-gold-500 focus:outline-none transition text-white"
                      placeholder="John Doe"
                      required
                    />
                  </div>
                </div>
              </>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                {t('email')}
              </label>
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
                <label className="block text-sm font-medium text-gray-300">
                  {t('password')}
                </label>
                {isLogin && (
                  <Link href="/forgot-password" className="text-sm text-gold-400 hover:text-gold-300">
                    Forgot password?
                  </Link>
                )}
              </div>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-500" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 bg-premium-surface border border-premium-border rounded-lg focus:border-gold-500 focus:outline-none transition text-white"
                  placeholder={isLogin ? '••••••••' : 'Min 8 characters'}
                  required
                  minLength={8}
                />
              </div>
            </div>

            {error && (
              <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
                {error}
              </div>
            )}

            {success && (
              <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-emerald-400 text-sm">
                {success}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-semibold rounded-lg hover:shadow-gold transition disabled:opacity-50 flex items-center justify-center"
            >
              {loading ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : isLogin ? (
                t('signIn')
              ) : (
                tc('signUp')
              )}
            </button>
          </form>

          {/* Toggle */}
          <div className="mt-6 text-center text-sm">
            <span className="text-gray-400">
              {isLogin ? t('noAccount') + ' ' : 'Already have an account? '}
            </span>
            <button
              onClick={() => {
                setIsLogin(!isLogin);
                setError('');
                setSuccess('');
              }}
              className="text-gold-400 hover:text-gold-300 font-medium"
            >
              {isLogin ? t('signUp') : tc('login')}
            </button>
          </div>

          {/* Divider */}
          <div className="mt-6 pt-6 border-t border-premium-border text-center">
            <p className="text-gray-500 text-sm">
              By continuing, you agree to our{' '}
              <Link href="/terms" className="text-gray-400 hover:text-gold-400">Terms</Link>
              {' '}and{' '}
              <Link href="/privacy" className="text-gray-400 hover:text-gold-400">Privacy Policy</Link>
            </p>
          </div>
        </div>

        {/* Download hint */}
        <p className="text-center text-gray-500 text-sm mt-6">
          Need the app?{' '}
          <Link href="/download" className="text-gold-400 hover:text-gold-300">
            Download ReadIn AI
          </Link>
        </p>
      </div>
    </main>
  );
}
