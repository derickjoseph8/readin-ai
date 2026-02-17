'use client'

import { useState, useMemo } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
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
  ChevronDown,
  HelpCircle,
  Ticket,
  MessageSquare,
  UserCog
} from 'lucide-react'
import { AuthProvider, useAuth } from '@/lib/hooks/useAuth'
import { usePermissions } from '@/lib/hooks/usePermissions'
import { useAgentStatus } from '@/lib/hooks/useAdmin'
import ChatWidget from '@/components/ChatWidget'

// Status colors for agent status indicator
const statusColors = {
  online: 'bg-emerald-500',
  away: 'bg-yellow-500',
  busy: 'bg-red-500',
  offline: 'bg-gray-500',
}

function DashboardSidebar() {
  const pathname = usePathname()
  const router = useRouter()
  const { user, logout } = useAuth()
  const { permissions } = usePermissions()
  const { status: agentStatus, updateStatus } = useAgentStatus()
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [statusOpen, setStatusOpen] = useState(false)

  // Build navigation based on permissions
  const navigation = useMemo(() => {
    const nav = [
      { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    ]

    // Customer items (also visible to staff)
    nav.push({ name: 'Meetings', href: '/dashboard/meetings', icon: Calendar })
    nav.push({ name: 'Analytics', href: '/dashboard/analytics', icon: BarChart3 })

    // Staff items
    if (permissions.canViewAllTickets) {
      nav.push({ name: 'Tickets', href: '/dashboard/tickets', icon: Ticket })
    }

    if (permissions.canViewChatQueue) {
      nav.push({ name: 'Live Chat', href: '/dashboard/chat', icon: MessageSquare })
    }

    if (permissions.canManageTeams) {
      nav.push({ name: 'Teams', href: '/dashboard/teams', icon: Users })
    }

    if (permissions.canViewAllUsers) {
      nav.push({ name: 'Users', href: '/dashboard/users', icon: UserCog })
    }

    // Customer support (for non-staff to create tickets)
    if (!permissions.isStaff) {
      nav.push({ name: 'Team', href: '/dashboard/team', icon: Users })
      nav.push({ name: 'Support', href: '/dashboard/support', icon: HelpCircle })
    }

    return nav
  }, [permissions])

  const settingsNav = [
    { name: 'Profile', href: '/dashboard/settings', icon: Settings },
    { name: 'Billing', href: '/dashboard/settings/billing', icon: CreditCard },
    { name: 'Security', href: '/dashboard/settings/security', icon: Shield },
  ]

  const isActive = (href: string) => {
    if (href === '/dashboard') return pathname === '/dashboard'
    return pathname.startsWith(href)
  }

  const handleLogout = () => {
    logout()
    router.push('/login')
  }

  const SidebarContent = () => (
    <>
      {/* Logo */}
      <div className="flex items-center h-16 px-6 border-b border-premium-border">
        <Link href="/dashboard" className="flex items-center space-x-2">
          <div className="w-8 h-8 bg-gradient-to-br from-gold-400 to-gold-600 rounded-lg flex items-center justify-center">
            <span className="text-premium-bg font-bold text-sm">R</span>
          </div>
          <span className="text-lg font-bold text-white">ReadIn AI</span>
          {permissions.isStaff && (
            <span className="ml-2 px-2 py-0.5 text-xs bg-gold-500/20 text-gold-400 rounded">
              {permissions.isSuperAdmin ? 'Admin' : 'Staff'}
            </span>
          )}
        </Link>
      </div>

      {/* Agent Status (only for staff) */}
      {permissions.isStaff && (
        <div className="px-4 py-4 border-b border-premium-border">
          <div className="relative">
            <button
              onClick={() => setStatusOpen(!statusOpen)}
              className="w-full flex items-center justify-between px-3 py-2 bg-premium-surface rounded-lg hover:bg-premium-surface/80 transition-colors"
            >
              <div className="flex items-center">
                <div className={`w-2.5 h-2.5 rounded-full ${statusColors[agentStatus?.status as keyof typeof statusColors || 'offline']} mr-2`} />
                <span className="text-sm text-white capitalize">{agentStatus?.status || 'Offline'}</span>
              </div>
              <ChevronDown className={`h-4 w-4 text-gray-400 transition-transform ${statusOpen ? 'rotate-180' : ''}`} />
            </button>

            {statusOpen && (
              <div className="absolute top-full left-0 right-0 mt-1 bg-premium-card border border-premium-border rounded-lg shadow-lg z-10">
                {['online', 'away', 'busy', 'offline'].map((s) => (
                  <button
                    key={s}
                    onClick={() => {
                      updateStatus(s)
                      setStatusOpen(false)
                    }}
                    className="w-full flex items-center px-3 py-2 hover:bg-premium-surface transition-colors first:rounded-t-lg last:rounded-b-lg"
                  >
                    <div className={`w-2.5 h-2.5 rounded-full ${statusColors[s as keyof typeof statusColors]} mr-2`} />
                    <span className="text-sm text-white capitalize">{s}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
          {agentStatus && (
            <p className="text-xs text-gray-500 mt-2 px-3">
              {agentStatus.current_chats}/{agentStatus.max_chats} active chats
            </p>
          )}
        </div>
      )}

      {/* Navigation */}
      <nav className="flex-1 px-4 py-6 space-y-1 overflow-y-auto">
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
              pathname.startsWith('/dashboard/settings')
                ? 'bg-gold-500/20 text-gold-400'
                : 'text-gray-400 hover:bg-premium-surface hover:text-white'
            }`}
          >
            <div className="flex items-center">
              <Settings className="h-5 w-5 mr-3" />
              Settings
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
                    pathname === item.href
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
            onClick={handleLogout}
            className="p-2 text-gray-500 hover:text-red-400 transition-colors"
            title="Logout"
          >
            <LogOut className="h-5 w-5" />
          </button>
        </div>
      </div>
    </>
  )

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
  )
}

function DashboardContent({ children }: { children: React.ReactNode }) {
  const { isLoading, isAuthenticated } = useAuth()
  const { permissions } = usePermissions()

  if (isLoading) {
    return (
      <div className="min-h-screen bg-premium-bg flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-gold-400"></div>
      </div>
    )
  }

  if (!isAuthenticated) {
    if (typeof window !== 'undefined') {
      window.location.href = '/login'
    }
    return null
  }

  return (
    <div className="min-h-screen bg-premium-bg">
      <DashboardSidebar />
      <main className="lg:pl-64">
        <div className="p-6 lg:p-8">{children}</div>
      </main>
      {/* Only show chat widget for non-staff users */}
      {!permissions.isStaff && <ChatWidget />}
    </div>
  )
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <AuthProvider>
      <DashboardContent>{children}</DashboardContent>
    </AuthProvider>
  )
}
