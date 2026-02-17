'use client'

import { useMemo } from 'react'
import { useAuth } from './useAuth'
import { User, StaffRole, TeamMembership } from '@/lib/api/auth'

// Team category mappings
export const TEAM_CATEGORIES = {
  'tech-support': ['technical', 'bug', 'installation', 'feature', 'account', 'general'],
  'accounts': ['billing', 'payment', 'refund', 'subscription'],
  'sales': ['sales', 'pricing', 'enterprise'],
} as const

export type UserRole = 'super_admin' | 'admin' | 'manager' | 'agent' | 'customer'

export interface Permissions {
  // Role checks
  isStaff: boolean
  isAdmin: boolean
  isSuperAdmin: boolean

  // Dashboard sections
  canViewAdminDashboard: boolean
  canViewAnalytics: boolean
  canViewAllUsers: boolean
  canManageUsers: boolean
  canManageTeams: boolean
  canViewBilling: boolean
  canManageBilling: boolean

  // Tickets
  canViewAllTickets: boolean
  canViewTechTickets: boolean
  canViewBillingTickets: boolean
  canViewSalesTickets: boolean
  canAssignTickets: boolean
  canViewInternalNotes: boolean

  // Chat
  canAcceptChats: boolean
  canViewChatQueue: boolean

  // Ticket category filtering
  allowedTicketCategories: string[] | 'all'

  // Teams the user belongs to
  userTeams: TeamMembership[]
  userTeamSlugs: string[]
}

export function usePermissions() {
  const { user, isAuthenticated } = useAuth()

  const role: UserRole = useMemo(() => {
    if (!user) return 'customer'
    if (!user.is_staff) return 'customer'
    return (user.staff_role as UserRole) || 'agent'
  }, [user])

  const permissions = useMemo((): Permissions => {
    const isStaff = user?.is_staff || false
    const staffRole = user?.staff_role
    const isSuperAdmin = staffRole === 'super_admin'
    const isAdmin = staffRole === 'admin' || isSuperAdmin
    const isManager = staffRole === 'manager'
    const isAgent = staffRole === 'agent'

    const userTeams = user?.team_memberships || []
    const userTeamSlugs = userTeams.map(t => t.team_slug)

    // Determine allowed ticket categories based on team memberships
    let allowedTicketCategories: string[] | 'all' = 'all'
    if (isStaff && !isAdmin) {
      // Non-admin staff can only see tickets for their team's categories
      const categories: string[] = []
      for (const team of userTeams) {
        const teamCategories = TEAM_CATEGORIES[team.team_slug as keyof typeof TEAM_CATEGORIES]
        if (teamCategories) {
          categories.push(...teamCategories)
        }
      }
      if (categories.length > 0) {
        allowedTicketCategories = Array.from(new Set(categories)) // Remove duplicates
      }
    }

    return {
      // Role checks
      isStaff,
      isAdmin,
      isSuperAdmin,

      // Dashboard sections
      canViewAdminDashboard: isAdmin,
      canViewAnalytics: isAdmin,
      canViewAllUsers: isAdmin,
      canManageUsers: isSuperAdmin,
      canManageTeams: isAdmin,
      canViewBilling: isAdmin || userTeamSlugs.includes('accounts'),
      canManageBilling: isAdmin,

      // Tickets
      canViewAllTickets: isStaff,
      canViewTechTickets: isAdmin || userTeamSlugs.includes('tech-support'),
      canViewBillingTickets: isAdmin || userTeamSlugs.includes('accounts'),
      canViewSalesTickets: isAdmin || userTeamSlugs.includes('sales'),
      canAssignTickets: isAdmin || isManager,
      canViewInternalNotes: isStaff,

      // Chat
      canAcceptChats: isStaff,
      canViewChatQueue: isStaff,

      // Filtering
      allowedTicketCategories,

      // Team info
      userTeams,
      userTeamSlugs,
    }
  }, [user])

  return {
    user,
    role,
    permissions,
    isAuthenticated,
  }
}

export default usePermissions
