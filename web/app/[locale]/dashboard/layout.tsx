'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useTranslations } from 'next-intl';
import {
  LayoutDashboard,
  Calendar,
  BarChart3,
  Settings,
  Users,
  LogOut,
  Menu,
  X,
  CreditCard,
  Shield,
  ChevronDown
} from 'lucide-react';
import { AuthProvider, useAuth } from '@/lib/hooks/useAuth';

function DashboardSidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const t = useTranslations('dashboard');
  const ts = useTranslations('settings');

  const isBusinessAccount = user?.account_type === 'business';

  const navigation = [
    { name: t('title'), href: '/dashboard', icon: LayoutDashboard },
    { name: 'Meetings', href: '/dashboard/meetings', icon: Calendar },
    { name: 'Analytics', href: '/dashboard/analytics', icon: BarChart3 },
    // Only show Team menu for business accounts
    ...(isBusinessAccount ? [{ name: 'Team', href: '/dashboard/team', icon: Users }] : []),
  ];

  const settingsNav = [
    { name: ts('profile.title'), href: '/dashboard/settings', icon: Settings },
    { name: ts('billing.title'), href: '/dashboard/settings/billing', icon: CreditCard },
    { name: ts('security.title'), href: '/dashboard/settings/security', icon: Shield },
  ];

  const isActive = (href: string) => {
    if (href === '/dashboard') return pathname === '/dashboard' || pathname?.endsWith('/dashboard');
    return pathname?.includes(href.replace('/dashboard', ''));
  };

  const SidebarContent = () => (
    <>
      {/* Logo */}
      <div className="flex items-center h-16 px-6 border-b border-premium-border">
        <Link href="/" className="flex items-center space-x-2">
          <div className="w-8 h-8 bg-gradient-to-br from-gold-400 to-gold-600 rounded-lg flex items-center justify-center">
            <span className="text-premium-bg font-bold text-sm">R</span>
          </div>
          <span className="text-lg font-bold text-white">ReadIn AI</span>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-4 py-6 space-y-1">
        {navigation.map((item) => (
          <Link
            key={item.name}
            href={item.href}
            className={`flex items-center px-3 py-2.5 rounded-lg transition-colors ${
              isActive(item.href)
                ? 'bg-gold-500/20 text-gold-400'
                : 'text-gray-400 hover:bg-premium-surface hover:text-white'
            }`}
          >
            <item.icon className="h-5 w-5 mr-3" />
            {item.name}
          </Link>
        ))}

        {/* Settings Dropdown */}
        <div className="pt-4">
          <button
            onClick={() => setSettingsOpen(!settingsOpen)}
            className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg transition-colors ${
              pathname?.includes('/settings')
                ? 'bg-gold-500/20 text-gold-400'
                : 'text-gray-400 hover:bg-premium-surface hover:text-white'
            }`}
          >
            <div className="flex items-center">
              <Settings className="h-5 w-5 mr-3" />
              {ts('title')}
            </div>
            <ChevronDown className={`h-4 w-4 transition-transform ${settingsOpen ? 'rotate-180' : ''}`} />
          </button>

          {settingsOpen && (
            <div className="mt-1 ml-4 space-y-1">
              {settingsNav.map((item) => (
                <Link
                  key={item.name}
                  href={item.href}
                  className={`flex items-center px-3 py-2 rounded-lg text-sm transition-colors ${
                    pathname === item.href || pathname?.endsWith(item.href.split('/dashboard')[1])
                      ? 'bg-gold-500/10 text-gold-400'
                      : 'text-gray-500 hover:bg-premium-surface hover:text-white'
                  }`}
                >
                  <item.icon className="h-4 w-4 mr-3" />
                  {item.name}
                </Link>
              ))}
            </div>
          )}
        </div>
      </nav>

      {/* User Section */}
      <div className="p-4 border-t border-premium-border">
        <div className="flex items-center justify-between">
          <div className="flex items-center min-w-0">
            <div className="w-9 h-9 bg-gold-500/20 rounded-full flex items-center justify-center flex-shrink-0">
              <span className="text-gold-400 font-medium text-sm">
                {user?.full_name?.[0] || user?.email?.[0] || 'U'}
              </span>
            </div>
            <div className="ml-3 min-w-0">
              <p className="text-sm font-medium text-white truncate">
                {user?.full_name || 'User'}
              </p>
              <p className="text-xs text-gray-500 truncate">{user?.email}</p>
            </div>
          </div>
          <button
            onClick={logout}
            className="p-2 text-gray-500 hover:text-red-400 transition-colors"
            title="Logout"
          >
            <LogOut className="h-5 w-5" />
          </button>
        </div>
      </div>
    </>
  );

  return (
    <>
      {/* Mobile menu button */}
      <button
        onClick={() => setMobileOpen(!mobileOpen)}
        className="lg:hidden fixed top-4 left-4 z-50 p-2 bg-premium-card border border-premium-border rounded-lg"
      >
        {mobileOpen ? <X className="h-5 w-5 text-white" /> : <Menu className="h-5 w-5 text-white" />}
      </button>

      {/* Mobile sidebar */}
      {mobileOpen && (
        <div className="lg:hidden fixed inset-0 z-40">
          <div className="fixed inset-0 bg-black/50" onClick={() => setMobileOpen(false)} />
          <div className="fixed left-0 top-0 bottom-0 w-64 bg-premium-card border-r border-premium-border flex flex-col">
            <SidebarContent />
          </div>
        </div>
      )}

      {/* Desktop sidebar */}
      <div className="hidden lg:flex lg:flex-col lg:w-64 lg:fixed lg:inset-y-0 bg-premium-card border-r border-premium-border">
        <SidebarContent />
      </div>
    </>
  );
}

function DashboardContent({ children }: { children: React.ReactNode }) {
  const { isLoading, isAuthenticated } = useAuth();
  const tc = useTranslations('common');

  if (isLoading) {
    return (
      <div className="min-h-screen bg-premium-bg flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-gold-400 mx-auto"></div>
          <p className="mt-4 text-gray-400">{tc('loading')}</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    if (typeof window !== 'undefined') {
      window.location.href = '/login';
    }
    return null;
  }

  return (
    <div className="min-h-screen bg-premium-bg">
      <DashboardSidebar />
      <main className="lg:pl-64">
        <div className="p-6 lg:p-8">{children}</div>
      </main>
    </div>
  );
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthProvider>
      <DashboardContent>{children}</DashboardContent>
    </AuthProvider>
  );
}
