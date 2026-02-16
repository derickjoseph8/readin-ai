# E-Commerce Admin Dashboard & Support System Plan

## Overview

A comprehensive internal management system for ReadIn AI that includes:
- Admin dashboard with full system oversight
- Team management (Sales, Tech Support, Accounts, etc.)
- Customer ticketing system with smart routing
- Live chat support
- Team member benefits (lifetime app access)

---

## 1. Database Schema Changes

### New Tables

```sql
-- Team definitions
CREATE TABLE teams (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,          -- "Tech Support", "Sales", "Accounts", etc.
    slug VARCHAR(50) UNIQUE NOT NULL,    -- "tech-support", "sales", "accounts"
    description TEXT,
    color VARCHAR(7),                     -- Hex color for UI
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Team members (internal staff)
CREATE TABLE team_members (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    team_id INTEGER REFERENCES teams(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,           -- "admin", "manager", "agent"
    is_active BOOLEAN DEFAULT TRUE,
    joined_at TIMESTAMP DEFAULT NOW(),
    removed_at TIMESTAMP,
    UNIQUE(user_id, team_id)
);

-- Support tickets
CREATE TABLE tickets (
    id SERIAL PRIMARY KEY,
    ticket_number VARCHAR(20) UNIQUE NOT NULL,  -- "TKT-2026-00001"
    user_id INTEGER REFERENCES users(id),        -- Customer who created ticket
    team_id INTEGER REFERENCES teams(id),        -- Assigned team
    assigned_to INTEGER REFERENCES team_members(id),  -- Specific agent
    category VARCHAR(50) NOT NULL,               -- "billing", "technical", "sales", "general"
    priority VARCHAR(20) DEFAULT 'medium',       -- "low", "medium", "high", "urgent"
    status VARCHAR(30) DEFAULT 'open',           -- "open", "in_progress", "waiting", "resolved", "closed"
    subject VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP,
    closed_at TIMESTAMP
);

-- Ticket messages/replies
CREATE TABLE ticket_messages (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER REFERENCES tickets(id) ON DELETE CASCADE,
    sender_id INTEGER REFERENCES users(id),
    sender_type VARCHAR(20) NOT NULL,    -- "customer", "agent", "system"
    message TEXT NOT NULL,
    attachments JSONB,                   -- Array of attachment URLs
    is_internal BOOLEAN DEFAULT FALSE,   -- Internal notes not visible to customer
    created_at TIMESTAMP DEFAULT NOW()
);

-- Live chat sessions
CREATE TABLE chat_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    agent_id INTEGER REFERENCES team_members(id),
    team_id INTEGER REFERENCES teams(id),
    status VARCHAR(20) DEFAULT 'waiting',  -- "waiting", "active", "ended"
    started_at TIMESTAMP DEFAULT NOW(),
    ended_at TIMESTAMP,
    ticket_id INTEGER REFERENCES tickets(id)  -- Optional: convert to ticket
);

-- Chat messages
CREATE TABLE chat_messages (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES chat_sessions(id) ON DELETE CASCADE,
    sender_id INTEGER REFERENCES users(id),
    sender_type VARCHAR(20) NOT NULL,    -- "customer", "agent", "bot"
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Agent availability/status
CREATE TABLE agent_status (
    id SERIAL PRIMARY KEY,
    team_member_id INTEGER REFERENCES team_members(id) UNIQUE,
    status VARCHAR(20) DEFAULT 'offline',  -- "online", "away", "busy", "offline"
    current_chats INTEGER DEFAULT 0,
    max_chats INTEGER DEFAULT 3,
    last_seen TIMESTAMP DEFAULT NOW()
);

-- Admin activity log
CREATE TABLE admin_activity_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50),             -- "ticket", "team", "user", "subscription"
    entity_id INTEGER,
    details JSONB,
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Modify Existing Tables

```sql
-- Add to users table
ALTER TABLE users ADD COLUMN is_staff BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN staff_access_expires TIMESTAMP;  -- NULL = lifetime
ALTER TABLE users ADD COLUMN added_by INTEGER REFERENCES users(id);
```

---

## 2. User Roles & Permissions

### Role Hierarchy

```
Super Admin (Owner - You)
├── Full system access
├── Manage all teams
├── View all analytics
├── Manage subscriptions
└── Add/remove admins

Admin
├── Manage assigned teams
├── View team analytics
├── Handle escalations
└── Cannot remove other admins

Team Manager
├── Manage team members
├── Assign tickets
├── View team metrics
└── Handle complex tickets

Agent
├── Handle assigned tickets
├── Live chat support
├── View own metrics
└── Basic ticket operations
```

### Permission Matrix

| Permission              | Super Admin | Admin | Manager | Agent |
|------------------------|-------------|-------|---------|-------|
| View all teams         | ✓           | ✓     | ✗       | ✗     |
| Manage teams           | ✓           | ✓     | ✗       | ✗     |
| Add team members       | ✓           | ✓     | ✓       | ✗     |
| Remove team members    | ✓           | ✓     | ✓       | ✗     |
| View all tickets       | ✓           | ✓     | Team    | Own   |
| Assign tickets         | ✓           | ✓     | ✓       | ✗     |
| Handle tickets         | ✓           | ✓     | ✓       | ✓     |
| View subscriptions     | ✓           | ✓     | ✗       | ✗     |
| Manage subscriptions   | ✓           | ✗     | ✗       | ✗     |
| View analytics         | ✓           | ✓     | Team    | Own   |
| System settings        | ✓           | ✗     | ✗       | ✗     |
| Live chat              | ✓           | ✓     | ✓       | ✓     |

---

## 3. Backend API Endpoints

### Team Management
```
POST   /api/admin/teams                    - Create team
GET    /api/admin/teams                    - List all teams
GET    /api/admin/teams/:id                - Get team details
PUT    /api/admin/teams/:id                - Update team
DELETE /api/admin/teams/:id                - Delete team

POST   /api/admin/teams/:id/members        - Add member to team
GET    /api/admin/teams/:id/members        - List team members
PUT    /api/admin/teams/:id/members/:uid   - Update member role
DELETE /api/admin/teams/:id/members/:uid   - Remove member (revokes access)
```

### Ticketing System
```
POST   /api/tickets                        - Create ticket (customer)
GET    /api/tickets                        - List tickets (filtered by role)
GET    /api/tickets/:id                    - Get ticket details
PUT    /api/tickets/:id                    - Update ticket
POST   /api/tickets/:id/messages           - Add message/reply
PUT    /api/tickets/:id/assign             - Assign to agent
PUT    /api/tickets/:id/transfer           - Transfer to team
PUT    /api/tickets/:id/status             - Change status
GET    /api/tickets/stats                  - Ticket statistics
```

### Live Chat
```
POST   /api/chat/start                     - Start chat session
GET    /api/chat/sessions                  - List chat sessions (agent)
POST   /api/chat/sessions/:id/accept       - Agent accepts chat
POST   /api/chat/sessions/:id/messages     - Send message
PUT    /api/chat/sessions/:id/end          - End session
POST   /api/chat/sessions/:id/to-ticket    - Convert to ticket
GET    /api/chat/agents/available          - Check agent availability
PUT    /api/chat/status                    - Update agent status
```

### Admin Dashboard
```
GET    /api/admin/dashboard                - Dashboard overview
GET    /api/admin/analytics/subscriptions  - Subscription metrics
GET    /api/admin/analytics/tickets        - Ticket metrics
GET    /api/admin/analytics/teams          - Team performance
GET    /api/admin/analytics/revenue        - Revenue trends
GET    /api/admin/users                    - User management
GET    /api/admin/activity-log             - Activity audit log
```

---

## 4. Frontend Pages & Components

### Admin Dashboard (`/admin`)

```
/admin
├── /dashboard          - Overview with KPIs, charts, recent activity
├── /teams
│   ├── /              - Team list
│   ├── /new           - Create team
│   └── /:id           - Team details & members
├── /tickets
│   ├── /              - All tickets (filterable)
│   ├── /:id           - Ticket detail view
│   └── /stats         - Ticket analytics
├── /chat
│   ├── /              - Chat queue & active sessions
│   └── /:id           - Chat window
├── /subscriptions
│   ├── /              - All subscriptions
│   ├── /:id           - Subscription details
│   └── /stats         - Subscription analytics
├── /users
│   ├── /              - User list
│   └── /:id           - User details
├── /analytics
│   ├── /              - Overview
│   ├── /revenue       - Revenue charts
│   └── /trends        - Usage trends
└── /settings
    ├── /              - General settings
    ├── /categories    - Ticket categories
    └── /notifications - Alert settings
```

### Customer Dashboard Updates (`/dashboard`)

```
/dashboard
├── /support
│   ├── /              - My tickets list
│   ├── /new           - Create ticket
│   └── /:id           - Ticket conversation
└── /chat              - Live chat widget (floating)
```

### UI Components

```
Components/
├── Admin/
│   ├── AdminSidebar.tsx
│   ├── AdminHeader.tsx
│   ├── StatsCard.tsx
│   ├── RevenueChart.tsx
│   ├── TicketChart.tsx
│   ├── TeamCard.tsx
│   ├── MemberList.tsx
│   ├── ActivityFeed.tsx
│   └── QuickActions.tsx
├── Tickets/
│   ├── TicketList.tsx
│   ├── TicketCard.tsx
│   ├── TicketDetail.tsx
│   ├── TicketForm.tsx
│   ├── TicketMessages.tsx
│   ├── TicketFilters.tsx
│   ├── AssignModal.tsx
│   └── PriorityBadge.tsx
├── Chat/
│   ├── ChatWidget.tsx       - Floating chat for customers
│   ├── ChatWindow.tsx       - Agent chat interface
│   ├── ChatQueue.tsx
│   ├── ChatMessage.tsx
│   ├── AgentStatus.tsx
│   └── TypingIndicator.tsx
└── Shared/
    ├── DataTable.tsx
    ├── Pagination.tsx
    ├── SearchInput.tsx
    └── DateRangePicker.tsx
```

---

## 5. Real-time Features (WebSocket)

### Events

```typescript
// Chat events
'chat:new_session'      - New customer waiting
'chat:message'          - New message in chat
'chat:typing'           - User is typing
'chat:session_ended'    - Chat ended
'chat:agent_joined'     - Agent accepted chat

// Ticket events
'ticket:created'        - New ticket
'ticket:updated'        - Ticket status changed
'ticket:assigned'       - Ticket assigned to agent
'ticket:new_message'    - New reply on ticket

// Agent events
'agent:status_changed'  - Agent online/offline
'agent:notification'    - Alert for agent
```

---

## 6. Ticket Routing Logic

```python
def route_ticket(ticket):
    """Auto-assign ticket to appropriate team"""

    category_team_map = {
        'billing': 'accounts',
        'payment': 'accounts',
        'refund': 'accounts',
        'subscription': 'accounts',
        'technical': 'tech-support',
        'bug': 'tech-support',
        'installation': 'tech-support',
        'feature': 'tech-support',
        'sales': 'sales',
        'pricing': 'sales',
        'enterprise': 'sales',
        'general': 'tech-support',  # Default
    }

    team_slug = category_team_map.get(ticket.category, 'tech-support')
    team = get_team_by_slug(team_slug)

    # Find available agent with least load
    agent = find_available_agent(team.id)

    return team, agent
```

---

## 7. Team Member Benefits

### Access Control Logic

```python
def check_staff_access(user):
    """Check if user has staff/team member access"""

    team_member = get_active_team_membership(user.id)

    if not team_member:
        return False, "Not a team member"

    if not team_member.is_active:
        return False, "Membership deactivated"

    # Staff access is lifetime while active
    # No subscription required
    return True, "Active team member"

def remove_team_member(member_id, removed_by):
    """Remove team member and revoke access"""

    member = get_team_member(member_id)
    member.is_active = False
    member.removed_at = datetime.now()

    # Revoke app access
    user = member.user
    user.is_staff = False

    # Log activity
    log_admin_activity(
        user_id=removed_by,
        action="removed_team_member",
        entity_type="team_member",
        entity_id=member_id
    )
```

---

## 8. Default Teams to Create

| Team Name    | Slug         | Description                          | Color   |
|-------------|--------------|--------------------------------------|---------|
| Tech Support | tech-support | Technical issues and troubleshooting | #3B82F6 |
| Accounts    | accounts     | Billing, payments, subscriptions     | #10B981 |
| Sales       | sales        | Sales inquiries and enterprise       | #F59E0B |
| Customer Success | success  | Onboarding and customer satisfaction | #8B5CF6 |

---

## 9. Admin Dashboard Metrics

### Overview Cards
- Total Users (with growth %)
- Active Subscriptions
- Monthly Revenue
- Open Tickets
- Active Chats
- Team Members Online

### Charts
- Revenue over time (line chart)
- Subscriptions by plan (pie chart)
- Ticket volume by category (bar chart)
- Resolution time trends (line chart)
- Team performance (bar chart)

### Recent Activity Feed
- New signups
- Subscription changes
- Ticket updates
- Team member actions

---

## 10. Implementation Phases

### Phase 1: Foundation (Database & Auth) ✅ COMPLETE
- [x] Create database migrations (models added to models.py)
- [x] Update user model with staff fields (is_staff, staff_role)
- [x] Implement role-based permissions (StaffRole constants)
- [x] Create team management APIs (routes/admin/teams.py)

### Phase 2: Ticketing System ✅ COMPLETE
- [x] Ticket CRUD APIs (routes/admin/tickets.py)
- [x] Ticket routing logic (services/ticket_service.py)
- [x] Customer ticket creation API (customer_router in tickets.py)
- [x] Agent ticket management APIs
- [x] SLA configuration and tracking

### Phase 3: Admin Dashboard ✅ COMPLETE
- [x] Dashboard stats API (routes/admin/dashboard.py)
- [x] Trend analytics API
- [x] User management API
- [x] Activity logging API
- [x] Admin layout and navigation (web/app/(static)/admin/layout.tsx)
- [x] Dashboard overview page (web/app/(static)/admin/page.tsx)
- [x] Team management pages (web/app/(static)/admin/teams/page.tsx)
- [x] Ticket management pages (web/app/(static)/admin/tickets/page.tsx)
- [x] User management pages (web/app/(static)/admin/users/page.tsx)

### Phase 4: Live Chat ✅ COMPLETE
- [x] Chat session management (services/ticket_service.py - ChatService)
- [x] Chat API routes (routes/admin/chat.py)
- [x] Agent status management
- [x] Chat-to-ticket conversion
- [x] Agent chat interface (web/app/(static)/admin/chat/page.tsx)
- [x] Customer chat widget (web/components/ChatWidget.tsx)
- [ ] WebSocket real-time events (currently using polling)

### Phase 5: Polish & Testing
- [ ] Email notifications for tickets
- [x] Activity logging
- [ ] Performance optimization
- [ ] Testing & bug fixes

---

## 11. File Structure

```
backend/
├── routes/
│   ├── admin/
│   │   ├── __init__.py
│   │   ├── dashboard.py
│   │   ├── teams.py
│   │   ├── tickets.py
│   │   ├── users.py
│   │   └── analytics.py
│   ├── tickets.py
│   └── chat.py
├── services/
│   ├── ticket_service.py
│   ├── chat_service.py
│   ├── team_service.py
│   └── notification_service.py
├── models/
│   ├── team.py
│   ├── ticket.py
│   └── chat.py
└── websocket/
    ├── __init__.py
    ├── chat_handler.py
    └── notification_handler.py

web/
├── app/
│   ├── admin/
│   │   ├── layout.tsx
│   │   ├── page.tsx              # Dashboard
│   │   ├── teams/
│   │   ├── tickets/
│   │   ├── chat/
│   │   ├── subscriptions/
│   │   ├── users/
│   │   └── analytics/
│   └── dashboard/
│       └── support/
│           ├── page.tsx          # My tickets
│           └── new/
│               └── page.tsx      # Create ticket
├── components/
│   ├── admin/
│   ├── tickets/
│   └── chat/
└── lib/
    ├── websocket.ts
    └── admin-api.ts
```

---

## 12. Security Considerations

- All admin routes require authentication + admin role check
- Rate limiting on ticket creation (prevent spam)
- Input sanitization for ticket/chat messages
- File upload validation for attachments
- WebSocket connection authentication
- Audit logging for all admin actions
- Session timeout for agent status

---

## Confirmed Requirements

1. **Super Admin**: Only the owner (you) - cannot be added/removed by anyone
2. **Admin**: Same permissions as Super Admin EXCEPT cannot add/remove other Admins
3. **Team Invitations**: Members invited via email invitation system
4. **Chat Hours**: 24/7 availability with customizable working hours display
5. **Notifications**: Both email AND in-app/push notifications
6. **Ticket SLAs**: Yes - implement response time SLAs

---

## SLA Configuration

| Priority | First Response | Resolution Target |
|----------|---------------|-------------------|
| Urgent   | 1 hour        | 4 hours           |
| High     | 4 hours       | 24 hours          |
| Medium   | 8 hours       | 48 hours          |
| Low      | 24 hours      | 72 hours          |

---

## Updated Permission Matrix

| Permission              | Super Admin | Admin | Manager | Agent |
|------------------------|-------------|-------|---------|-------|
| Add/Remove Admins      | ✓           | ✗     | ✗       | ✗     |
| All other admin perms  | ✓           | ✓     | -       | -     |
| Manage teams           | ✓           | ✓     | ✗       | ✗     |
| Invite team members    | ✓           | ✓     | ✓       | ✗     |
| Remove team members    | ✓           | ✓     | ✓       | ✗     |
| View all tickets       | ✓           | ✓     | Team    | Own   |
| Assign tickets         | ✓           | ✓     | ✓       | ✗     |
| Handle tickets         | ✓           | ✓     | ✓       | ✓     |
| View subscriptions     | ✓           | ✓     | ✗       | ✗     |
| Manage subscriptions   | ✓           | ✓     | ✗       | ✗     |
| View analytics         | ✓           | ✓     | Team    | Own   |
| System settings        | ✓           | ✓     | ✗       | ✗     |
| Live chat              | ✓           | ✓     | ✓       | ✓     |

---

## Status: ✅ COMPLETE (Backend + Frontend)

### Completed Backend Files:
- `backend/models.py` - Added all support system models
- `backend/schemas.py` - Added all request/response schemas
- `backend/services/ticket_service.py` - Ticket routing, SLA tracking, chat management
- `backend/routes/admin/__init__.py` - Admin routes module
- `backend/routes/admin/dashboard.py` - Dashboard stats and trends API
- `backend/routes/admin/teams.py` - Team CRUD and member management
- `backend/routes/admin/tickets.py` - Ticket management (admin + customer)
- `backend/routes/admin/chat.py` - Live chat management (admin + customer)
- `backend/main.py` - Updated to register all new routes

### Completed Frontend Files:
- `web/lib/api/admin.ts` - Admin API client with all endpoints
- `web/lib/hooks/useAdmin.ts` - React hooks for admin data fetching
- `web/app/(static)/admin/layout.tsx` - Admin layout with sidebar navigation
- `web/app/(static)/admin/page.tsx` - Admin dashboard overview
- `web/app/(static)/admin/teams/page.tsx` - Team management
- `web/app/(static)/admin/tickets/page.tsx` - Ticket management
- `web/app/(static)/admin/chat/page.tsx` - Live chat agent interface
- `web/app/(static)/admin/users/page.tsx` - User management
- `web/app/(static)/dashboard/support/page.tsx` - Customer support tickets list
- `web/app/(static)/dashboard/support/new/page.tsx` - Create new ticket
- `web/app/(static)/dashboard/support/[id]/page.tsx` - Ticket detail/conversation
- `web/components/ChatWidget.tsx` - Floating chat widget for customers
- `web/app/(static)/dashboard/layout.tsx` - Updated with Support nav link and ChatWidget

### API Endpoints Added:
- `/api/v1/admin/dashboard/*` - Dashboard stats, trends, user management
- `/api/v1/admin/teams/*` - Team CRUD, member management, invitations
- `/api/v1/admin/tickets/*` - Ticket management, SLA config
- `/api/v1/admin/chat/*` - Chat queue, agent status, messaging
- `/api/v1/tickets/*` - Customer ticket creation and viewing
- `/api/v1/chat/*` - Customer chat initiation and messaging

### Remaining Tasks (Optional Enhancements):
1. Add WebSocket real-time events for chat/tickets (currently using polling)
2. Email notifications for new tickets and replies
3. Analytics dashboard with charts
4. Performance optimization

