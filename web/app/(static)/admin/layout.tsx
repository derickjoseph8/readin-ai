'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import {
  LayoutDashboard,
  Users,
  Ticket,
  MessageSquare,
  Settings,
  LogOut,
  Menu,
  X,
  ChevronDown,
  Shield,
  Bell,
  UserCog
} from 'lucide-react'
import { AuthProvider, useAuth } from '@/lib/hooks/useAuth'
import { useAgentStatus } from '@/lib/hooks/useAdmin'

const navigation = [
  { name: 'Dashboard', href: '/admin', icon: LayoutDashboard },
  { name: 'Teams', href: '/admin/teams', icon: Users },
  { name: 'Tickets', href: '/admin/tickets', icon: Ticket },
  { name: 'Live Chat', href: '/admin/chat', icon: MessageSquare },
  { name: 'Users', href: '/admin/users', icon: UserCog },
]

const statusColors = {
  online: 'bg-emerald-500',
  away: 'bg-yellow-500',
  busy: 'bg-red-500',
  offline: 'bg-gray-500',
}

function AdminSidebar() {
  const pathname = usePathname()
  const router = useRouter()
  const { user, logout } = useAuth()
  const { status: agentStatus, updateStatus } = useAgentStatus()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [statusOpen, setStatusOpen] = useState(false)

  const isActive = (href: string) => {
    if (href === '/admin') return pathname === '/admin'
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
        <Link href="/admin" className="flex items-center space-x-2">
          <div className="w-8 h-8 bg-gradient-to-br from-gold-400 to-gold-600 rounded-lg flex items-center justify-center">
            <Shield className="h-4 w-4 text-premium-bg" />
          </div>
          <span className="text-lg font-bold text-white">Admin</span>
        </Link>
      </div>

      {/* Agent Status */}
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
      </nav>

      {/* Back to Dashboard */}
      <div className="px-4 py-4 border-t border-premium-border">
        <Link
          href="/dashboard"
          className="flex items-center px-3 py-2.5 text-gray-400 hover:bg-premium-surface hover:text-white rounded-lg transition-colors"
        >
          <LayoutDashboard className="h-5 w-5 mr-3" />
          Back to App
        </Link>
      </div>

      {/* User Section */}
      <div className="p-4 border-t border-premium-border">
        <div className="flex items-center justify-between">
          <div className="flex items-center min-w-0">
            <div className="w-9 h-9 bg-gold-500/20 rounded-full flex items-center justify-center flex-shrink-0">
              <span className="text-gold-400 font-medium text-sm">
                {user?.full_name?.[0] || user?.email?.[0] || 'A'}
              </span>
            </div>
            <div className="ml-3 min-w-0">
              <p className="text-sm font-medium text-white truncate">
                {user?.full_name || 'Admin'}
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

function AdminContent({ children }: { children: React.ReactNode }) {
  const { isLoading, isAuthenticated, user } = useAuth()
  const router = useRouter()

  useEffect(() => {
    // Check if user is staff
    if (!isLoading && isAuthenticated) {
      // TODO: Check user.is_staff when available in User type
      // For now, allow access and let backend handle authorization
    }
  }, [isLoading, isAuthenticated, user])

  if (isLoading) {
    return (
      <div className="min-h-screen bg-premium-bg flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-gold-400"></div>
      </div>
    )
  }

  if (!isAuthenticated) {
    if (typeof window !== 'undefined') {
      router.push('/login')
    }
    return null
  }

  return (
    <div className="min-h-screen bg-premium-bg">
      <AdminSidebar />
      <main className="lg:pl-64">
        <div className="p-6 lg:p-8">{children}</div>
      </main>
    </div>
  )
}

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <AuthProvider>
      <AdminContent>{children}</AdminContent>
    </AuthProvider>
  )
}
