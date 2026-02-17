'use client'

import { useEffect } from 'react'
import { useRouter, usePathname } from 'next/navigation'

/**
 * Admin layout - Redirects to unified dashboard
 * The admin functionality has been moved to /dashboard with role-based access
 */
export default function AdminLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const router = useRouter()
  const pathname = usePathname()

  useEffect(() => {
    // Map old admin routes to new dashboard routes
    const routeMap: Record<string, string> = {
      '/admin': '/dashboard',
      '/admin/teams': '/dashboard/teams',
      '/admin/tickets': '/dashboard/tickets',
      '/admin/chat': '/dashboard/chat',
      '/admin/users': '/dashboard/users',
    }

    const newPath = routeMap[pathname] || '/dashboard'
    router.replace(newPath)
  }, [pathname, router])

  // Show loading while redirecting
  return (
    <div className="min-h-screen bg-premium-bg flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-gold-400 mx-auto mb-4"></div>
        <p className="text-gray-400">Redirecting to dashboard...</p>
      </div>
    </div>
  )
}
