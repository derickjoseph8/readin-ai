/**
 * Admin API client for e-commerce dashboard
 */

import apiClient from './client'

// Types
export interface AdminDashboardStats {
  total_users: number
  active_users: number
  trial_users: number
  paying_users: number
  new_users_today: number
  new_users_this_week: number
  new_users_this_month: number
  total_revenue_this_month: number
  mrr: number
  churn_rate: number
  open_tickets: number
  tickets_today: number
  avg_response_time_minutes: number
  sla_breach_rate: number
  active_chats: number
  waiting_chats: number
  total_teams: number
  online_agents: number
  total_agents: number
}

export interface TicketTrend {
  date: string
  count: number
  resolved: number
  avg_response_minutes: number | null
}

export interface SubscriptionTrend {
  date: string
  new_subscriptions: number
  cancellations: number
  revenue: number
}

export interface AdminTrends {
  tickets: TicketTrend[]
  subscriptions: SubscriptionTrend[]
  period: string
}

export interface SupportTeam {
  id: number
  name: string
  slug: string
  description: string | null
  color: string
  is_active: boolean
  accepts_tickets: boolean
  accepts_chat: boolean
  working_hours: Record<string, unknown> | null
  timezone: string
  member_count: number
  created_at: string
}

export interface TeamMember {
  id: number
  user_id: number
  team_id: number
  role: string
  is_active: boolean
  joined_at: string
  user_email: string | null
  user_name: string | null
  team_name: string | null
}

export interface TeamInvite {
  id: number
  team_id: number
  email: string
  role: string
  status: string
  expires_at: string
  created_at: string
  team_name: string | null
}

export interface SupportTicket {
  id: number
  ticket_number: string
  user_id: number
  team_id: number | null
  assigned_to_id: number | null
  category: string
  priority: string
  status: string
  subject: string
  description: string
  source: string
  sla_first_response_due: string | null
  sla_resolution_due: string | null
  first_response_at: string | null
  sla_breached: boolean
  created_at: string
  updated_at: string
  resolved_at: string | null
  closed_at: string | null
  user_email: string | null
  user_name: string | null
  team_name: string | null
  assigned_to_name: string | null
  message_count: number
}

export interface TicketMessage {
  id: number
  ticket_id: number
  sender_type: string
  message: string
  attachments: string[]
  is_internal: boolean
  created_at: string
  sender_name: string | null
}

export interface TicketDetail extends SupportTicket {
  messages: TicketMessage[]
}

export interface TicketList {
  tickets: SupportTicket[]
  total: number
  by_status: Record<string, number>
  by_priority: Record<string, number>
}

export interface ChatSession {
  id: number
  session_token: string
  user_id: number
  agent_id: number | null
  team_id: number | null
  status: string
  queue_position: number | null
  started_at: string
  accepted_at: string | null
  ended_at: string | null
  ticket_id: number | null
  user_name: string | null
  agent_name: string | null
  team_name: string | null
}

export interface ChatMessage {
  id: number
  session_id: number
  sender_type: string
  message: string
  message_type: string
  is_read: boolean
  created_at: string
  sender_name: string | null
}

export interface AgentStatus {
  id: number
  team_member_id: number
  status: string
  current_chats: number
  max_chats: number
  last_seen: string
  agent_name: string | null
  team_name: string | null
}

export interface SLAConfig {
  id: number
  priority: string
  first_response_minutes: number
  resolution_minutes: number
  escalation_enabled: boolean
  escalation_after_minutes: number | null
  is_active: boolean
}

export interface AdminUser {
  id: number
  email: string
  full_name: string | null
  subscription_tier: string | null
  subscription_status: string
  subscription_ends_at: string | null
  trial_ends_at: string | null
  is_active: boolean
  is_staff: boolean
  staff_role: string | null
  stripe_customer_id: string | null
  created_at: string
  last_active: string | null
  last_login: string | null
}

export interface ActivityLog {
  id: number
  user_id: number
  action: string
  entity_type: string | null
  entity_id: number | null
  details: Record<string, unknown> | null
  ip_address: string | null
  created_at: string
  user_email: string | null
  user_name: string | null
}

// API Functions
export const adminApi = {
  // Dashboard
  async getStats(): Promise<AdminDashboardStats> {
    return apiClient.get('/api/v1/admin/dashboard/stats')
  },

  async getTrends(period: string = 'daily', days: number = 30): Promise<AdminTrends> {
    return apiClient.get(`/api/v1/admin/dashboard/trends?period=${period}&days=${days}`)
  },

  async getActivityLog(limit: number = 50, offset: number = 0): Promise<ActivityLog[]> {
    return apiClient.get(`/api/v1/admin/dashboard/activity?limit=${limit}&offset=${offset}`)
  },

  async seedSLA(): Promise<{ message: string }> {
    return apiClient.post('/api/v1/admin/dashboard/seed-sla')
  },

  async seedTeams(): Promise<{ message: string }> {
    return apiClient.post('/api/v1/admin/dashboard/seed-teams')
  },

  // Teams
  async getTeams(includeInactive: boolean = false): Promise<{ teams: SupportTeam[]; total: number }> {
    return apiClient.get(`/api/v1/admin/teams/?include_inactive=${includeInactive}`)
  },

  async getTeam(id: number): Promise<SupportTeam> {
    return apiClient.get(`/api/v1/admin/teams/${id}`)
  },

  async createTeam(data: {
    name: string
    slug: string
    description?: string
    color?: string
    accepts_tickets?: boolean
    accepts_chat?: boolean
  }): Promise<SupportTeam> {
    return apiClient.post('/api/v1/admin/teams/', data)
  },

  async updateTeam(id: number, data: Partial<SupportTeam>): Promise<SupportTeam> {
    return apiClient.patch(`/api/v1/admin/teams/${id}`, data)
  },

  async deleteTeam(id: number): Promise<{ message: string }> {
    return apiClient.delete(`/api/v1/admin/teams/${id}`)
  },

  async getTeamMembers(teamId: number): Promise<{ members: TeamMember[]; total: number }> {
    return apiClient.get(`/api/v1/admin/teams/${teamId}/members`)
  },

  async addTeamMember(teamId: number, userId: number, role: string): Promise<TeamMember> {
    return apiClient.post(`/api/v1/admin/teams/${teamId}/members`, { user_id: userId, role })
  },

  async removeTeamMember(teamId: number, memberId: number): Promise<{ message: string }> {
    return apiClient.delete(`/api/v1/admin/teams/${teamId}/members/${memberId}`)
  },

  async updateMemberRole(teamId: number, memberId: number, role: string): Promise<{ message: string }> {
    return apiClient.patch(`/api/v1/admin/teams/${teamId}/members/${memberId}/role?role=${role}`, {})
  },

  async inviteTeamMember(data: { email: string; role: string; team_id: number }): Promise<TeamInvite> {
    return apiClient.post('/api/v1/admin/teams/invite', data)
  },

  async getPendingInvites(teamId?: number): Promise<TeamInvite[]> {
    const query = teamId ? `?team_id=${teamId}` : ''
    return apiClient.get(`/api/v1/admin/teams/invites/pending${query}`)
  },

  async cancelInvite(inviteId: number): Promise<{ message: string }> {
    return apiClient.delete(`/api/v1/admin/teams/invites/${inviteId}`)
  },

  // Tickets
  async getTickets(params: {
    status?: string
    priority?: string
    category?: string
    team_id?: number
    assigned_to_me?: boolean
    unassigned?: boolean
    sla_breached?: boolean
    limit?: number
    offset?: number
  } = {}): Promise<TicketList> {
    const searchParams = new URLSearchParams()
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) searchParams.append(key, String(value))
    })
    return apiClient.get(`/api/v1/admin/tickets/?${searchParams.toString()}`)
  },

  async getTicket(id: number): Promise<TicketDetail> {
    return apiClient.get(`/api/v1/admin/tickets/${id}`)
  },

  async updateTicket(id: number, data: {
    priority?: string
    status?: string
    team_id?: number
    assigned_to_id?: number
  }): Promise<SupportTicket> {
    return apiClient.patch(`/api/v1/admin/tickets/${id}`, data)
  },

  async assignTicket(id: number, teamId?: number, agentId?: number): Promise<{ message: string }> {
    const params = new URLSearchParams()
    if (teamId) params.append('team_id', String(teamId))
    if (agentId) params.append('agent_id', String(agentId))
    return apiClient.post(`/api/v1/admin/tickets/${id}/assign?${params.toString()}`, {})
  },

  async claimTicket(id: number): Promise<{ message: string }> {
    return apiClient.post(`/api/v1/admin/tickets/${id}/claim`, {})
  },

  async addTicketMessage(ticketId: number, data: {
    message: string
    is_internal?: boolean
    attachments?: string[]
  }): Promise<TicketMessage> {
    return apiClient.post(`/api/v1/admin/tickets/${ticketId}/messages`, data)
  },

  async getSLAConfigs(): Promise<SLAConfig[]> {
    return apiClient.get('/api/v1/admin/tickets/sla/config')
  },

  async updateSLAConfig(priority: string, data: Partial<SLAConfig>): Promise<SLAConfig> {
    return apiClient.patch(`/api/v1/admin/tickets/sla/config/${priority}`, data)
  },

  // Chat
  async getChatQueue(teamId?: number): Promise<{ sessions: ChatSession[]; total: number; waiting: number; active: number }> {
    const query = teamId ? `?team_id=${teamId}` : ''
    return apiClient.get(`/api/v1/admin/chat/queue${query}`)
  },

  async getMyChats(): Promise<{ sessions: ChatSession[]; total: number; waiting: number; active: number }> {
    return apiClient.get('/api/v1/admin/chat/my-chats')
  },

  async acceptChat(sessionId: number): Promise<ChatSession> {
    return apiClient.post(`/api/v1/admin/chat/queue/${sessionId}/accept`, {})
  },

  async endChat(sessionId: number, createTicket?: boolean, ticketSubject?: string): Promise<{ message: string }> {
    const params = new URLSearchParams()
    if (createTicket) params.append('create_ticket', 'true')
    if (ticketSubject) params.append('ticket_subject', ticketSubject)
    return apiClient.post(`/api/v1/admin/chat/sessions/${sessionId}/end?${params.toString()}`, {})
  },

  async transferChat(sessionId: number, targetTeamId?: number, targetAgentId?: number): Promise<{ message: string }> {
    const params = new URLSearchParams()
    if (targetTeamId) params.append('target_team_id', String(targetTeamId))
    if (targetAgentId) params.append('target_agent_id', String(targetAgentId))
    return apiClient.post(`/api/v1/admin/chat/sessions/${sessionId}/transfer?${params.toString()}`, {})
  },

  async getChatMessages(sessionId: number, limit: number = 100): Promise<ChatMessage[]> {
    return apiClient.get(`/api/v1/admin/chat/sessions/${sessionId}/messages?limit=${limit}`)
  },

  async sendChatMessage(sessionId: number, message: string, messageType: string = 'text'): Promise<ChatMessage> {
    return apiClient.post(`/api/v1/admin/chat/sessions/${sessionId}/messages`, { message, message_type: messageType })
  },

  async getMyAgentStatus(): Promise<AgentStatus> {
    return apiClient.get('/api/v1/admin/chat/status')
  },

  async updateMyAgentStatus(status: string, maxChats?: number): Promise<AgentStatus> {
    return apiClient.patch('/api/v1/admin/chat/status', { status, max_chats: maxChats })
  },

  async getOnlineAgents(teamId?: number): Promise<AgentStatus[]> {
    const query = teamId ? `?team_id=${teamId}` : ''
    return apiClient.get(`/api/v1/admin/chat/agents/online${query}`)
  },

  // Users
  async getUsers(params: {
    search?: string
    subscription_status?: string
    subscription_tier?: string
    is_active?: boolean
    is_staff?: boolean
    limit?: number
    offset?: number
    skip?: number
  } = {}): Promise<{ users: AdminUser[]; total: number }> {
    const searchParams = new URLSearchParams()
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && key !== 'skip') {
        searchParams.append(key, String(value))
      }
    })
    return apiClient.get(`/api/v1/admin/dashboard/users?${searchParams.toString()}`)
  },

  async getUserDetails(userId: number): Promise<AdminUser & { teams: unknown[]; ticket_count: number }> {
    return apiClient.get(`/api/v1/admin/dashboard/users/${userId}`)
  },

  async updateUserStaffStatus(userId: number, isStaff: boolean, staffRole?: string): Promise<{ message: string }> {
    const params = new URLSearchParams()
    params.append('is_staff', String(isStaff))
    if (staffRole) params.append('staff_role', staffRole)
    return apiClient.patch(`/api/v1/admin/dashboard/users/${userId}/staff?${params.toString()}`, {})
  },

  async updateUser(userId: number, data: {
    is_active?: boolean
    is_staff?: boolean
    staff_role?: string | null
    subscription_tier?: string
  }): Promise<AdminUser> {
    return apiClient.patch(`/api/v1/admin/dashboard/users/${userId}`, data)
  },
}

// Customer Support API
export const supportApi = {
  async createTicket(data: {
    category: string
    priority?: string
    subject: string
    description: string
  }): Promise<SupportTicket> {
    return apiClient.post('/api/v1/tickets/', data)
  },

  async getMyTickets(status?: string, limit: number = 20, offset: number = 0): Promise<TicketList> {
    const params = new URLSearchParams()
    if (status) params.append('status', status)
    params.append('limit', String(limit))
    params.append('offset', String(offset))
    return apiClient.get(`/api/v1/tickets/my-tickets?${params.toString()}`)
  },

  async getTicket(id: number): Promise<TicketDetail> {
    return apiClient.get(`/api/v1/tickets/${id}`)
  },

  async addTicketMessage(ticketId: number, message: string, attachments?: string[]): Promise<TicketMessage> {
    return apiClient.post(`/api/v1/tickets/${ticketId}/reply`, { message, attachments })
  },

  async startChat(teamId?: number): Promise<ChatSession> {
    return apiClient.post('/api/v1/chat/start', { team_id: teamId })
  },

  async getMyChat(): Promise<ChatSession | null> {
    return apiClient.get('/api/v1/chat/session')
  },

  async getChatMessages(sessionId: number, limit: number = 50): Promise<{ messages: ChatMessage[]; status: string; queue_position: number | null }> {
    return apiClient.get(`/api/v1/chat/sessions/${sessionId}/messages?limit=${limit}`)
  },

  async sendChatMessage(sessionId: number, message: string, messageType: string = 'text'): Promise<ChatMessage> {
    return apiClient.post(`/api/v1/chat/sessions/${sessionId}/messages`, { message, message_type: messageType })
  },

  async endChat(sessionId: number): Promise<{ message: string }> {
    return apiClient.post(`/api/v1/chat/sessions/${sessionId}/end`, {})
  },
}

export default adminApi
