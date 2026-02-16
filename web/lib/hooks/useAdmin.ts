/**
 * Admin hooks for dashboard data
 */

import { useState, useEffect, useCallback } from 'react'
import { adminApi, supportApi, AdminDashboardStats, AdminTrends, SupportTeam, TeamMember, SupportTicket, TicketDetail, ChatSession, AgentStatus, SLAConfig, AdminUser, ActivityLog, TicketList, ChatMessage } from '../api/admin'

// Dashboard Stats Hook
export function useAdminStats() {
  const [stats, setStats] = useState<AdminDashboardStats | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      setIsLoading(true)
      const data = await adminApi.getStats()
      setStats(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load stats')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  return { stats, isLoading, error, refresh }
}

// Trends Hook
export function useAdminTrends(period: string = 'daily', days: number = 30) {
  const [trends, setTrends] = useState<AdminTrends | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchTrends = async () => {
      try {
        setIsLoading(true)
        const data = await adminApi.getTrends(period, days)
        setTrends(data)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load trends')
      } finally {
        setIsLoading(false)
      }
    }
    fetchTrends()
  }, [period, days])

  return { trends, isLoading, error }
}

// Teams Hook
export function useTeams() {
  const [teams, setTeams] = useState<SupportTeam[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      setIsLoading(true)
      const data = await adminApi.getTeams()
      setTeams(data.teams)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load teams')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  return { teams, isLoading, error, refresh }
}

// Team Members Hook
export function useTeamMembers(teamId: number) {
  const [members, setMembers] = useState<TeamMember[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    if (!teamId) return
    try {
      setIsLoading(true)
      const data = await adminApi.getTeamMembers(teamId)
      setMembers(data.members)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load members')
    } finally {
      setIsLoading(false)
    }
  }, [teamId])

  useEffect(() => {
    refresh()
  }, [refresh])

  return { members, isLoading, error, refresh }
}

// Tickets Hook
export function useTickets(params: {
  status?: string
  priority?: string
  team_id?: number
  assigned_to_me?: boolean
  unassigned?: boolean
  limit?: number
} = {}) {
  const [tickets, setTickets] = useState<SupportTicket[]>([])
  const [total, setTotal] = useState(0)
  const [byStatus, setByStatus] = useState<Record<string, number>>({})
  const [byPriority, setByPriority] = useState<Record<string, number>>({})
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      setIsLoading(true)
      const data = await adminApi.getTickets(params)
      setTickets(data.tickets)
      setTotal(data.total)
      setByStatus(data.by_status)
      setByPriority(data.by_priority)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load tickets')
    } finally {
      setIsLoading(false)
    }
  }, [JSON.stringify(params)])

  useEffect(() => {
    refresh()
  }, [refresh])

  return { tickets, total, byStatus, byPriority, isLoading, error, refresh }
}

// Single Ticket Hook
export function useTicket(ticketId: number) {
  const [ticket, setTicket] = useState<TicketDetail | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    if (!ticketId) return
    try {
      setIsLoading(true)
      const data = await adminApi.getTicket(ticketId)
      setTicket(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load ticket')
    } finally {
      setIsLoading(false)
    }
  }, [ticketId])

  useEffect(() => {
    refresh()
  }, [refresh])

  return { ticket, isLoading, error, refresh }
}

// Chat Queue Hook
export function useChatQueue(teamId?: number) {
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [waiting, setWaiting] = useState(0)
  const [active, setActive] = useState(0)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      setIsLoading(true)
      const data = await adminApi.getChatQueue(teamId)
      setSessions(data.sessions)
      setWaiting(data.waiting)
      setActive(data.active)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load chat queue')
    } finally {
      setIsLoading(false)
    }
  }, [teamId])

  useEffect(() => {
    refresh()
    // Poll for updates every 5 seconds
    const interval = setInterval(refresh, 5000)
    return () => clearInterval(interval)
  }, [refresh])

  return { sessions, waiting, active, isLoading, error, refresh }
}

// Agent Status Hook
export function useAgentStatus() {
  const [status, setStatus] = useState<AgentStatus | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      setIsLoading(true)
      const data = await adminApi.getMyAgentStatus()
      setStatus(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load agent status')
    } finally {
      setIsLoading(false)
    }
  }, [])

  const updateStatus = async (newStatus: string, maxChats?: number) => {
    try {
      const data = await adminApi.updateMyAgentStatus(newStatus, maxChats)
      setStatus(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update status')
    }
  }

  useEffect(() => {
    refresh()
  }, [refresh])

  return { status, isLoading, error, refresh, updateStatus }
}

// Users Hook
export function useAdminUsers(params: {
  search?: string
  subscription_status?: string
  subscription_tier?: string
  is_active?: boolean
  is_staff?: boolean
  limit?: number
  skip?: number
  offset?: number
} = {}) {
  const [users, setUsers] = useState<AdminUser[]>([])
  const [total, setTotal] = useState(0)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      setIsLoading(true)
      // Map skip to offset for API compatibility
      const apiParams = {
        ...params,
        offset: params.skip ?? params.offset
      }
      const data = await adminApi.getUsers(apiParams)
      setUsers(data.users)
      setTotal(data.total)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load users')
    } finally {
      setIsLoading(false)
    }
  }, [JSON.stringify(params)])

  useEffect(() => {
    refresh()
  }, [refresh])

  return { users, total, isLoading, error, refresh }
}

// Activity Log Hook
export function useActivityLog(limit: number = 50) {
  const [logs, setLogs] = useState<ActivityLog[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        setIsLoading(true)
        const data = await adminApi.getActivityLog(limit)
        setLogs(data)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load activity log')
      } finally {
        setIsLoading(false)
      }
    }
    fetchLogs()
  }, [limit])

  return { logs, isLoading, error }
}

// SLA Config Hook
export function useSLAConfigs() {
  const [configs, setConfigs] = useState<SLAConfig[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      setIsLoading(true)
      const data = await adminApi.getSLAConfigs()
      setConfigs(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load SLA configs')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  return { configs, isLoading, error, refresh }
}

// Customer Support Hooks
export function useMyTickets(params: { status?: string } = {}) {
  const [tickets, setTickets] = useState<SupportTicket[]>([])
  const [total, setTotal] = useState(0)
  const [byStatus, setByStatus] = useState<Record<string, number>>({})
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      setIsLoading(true)
      const data = await supportApi.getMyTickets(params.status)
      setTickets(data.tickets)
      setTotal(data.total)
      setByStatus(data.by_status)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load tickets')
    } finally {
      setIsLoading(false)
    }
  }, [params.status])

  useEffect(() => {
    refresh()
  }, [refresh])

  return { tickets, total, byStatus, isLoading, error, refresh }
}

export function useMyTicket(ticketId: number) {
  const [ticket, setTicket] = useState<TicketDetail | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    if (!ticketId) return
    try {
      setIsLoading(true)
      const data = await supportApi.getTicket(ticketId)
      setTicket(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load ticket')
    } finally {
      setIsLoading(false)
    }
  }, [ticketId])

  useEffect(() => {
    refresh()
  }, [refresh])

  return { ticket, isLoading, error, refresh }
}

export function useMyChat() {
  const [session, setSession] = useState<ChatSession | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      setIsLoading(true)
      const sessionData = await supportApi.getMyChat()
      setSession(sessionData)
      if (sessionData) {
        const data = await supportApi.getChatMessages(sessionData.id)
        setMessages(data.messages)
      }
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load chat')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  return { session, messages, isLoading, error, refresh }
}
