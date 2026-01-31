# ReadIn AI - Comprehensive Feature Enhancement Plan

**Status: IN PROGRESS**
**Last Updated: January 30, 2026**

---

## Overview

Transform ReadIn AI from a real-time interview assistant into a comprehensive **Meeting Intelligence Platform** with ML-powered learning, email notifications, profession-specific knowledge, and persistent memory across sessions.

---

## Implementation Progress

### Completed
- [x] Database schema (all new models) - `backend/models.py`
- [x] Pydantic schemas for validation - `backend/schemas.py`
- [x] Profession seed data (60+ professions) - `backend/seed_professions.py`
- [x] API Routes:
  - [x] Professions API - `backend/routes/professions.py`
  - [x] Organizations API - `backend/routes/organizations.py`
  - [x] Meetings API - `backend/routes/meetings.py`
  - [x] Conversations API - `backend/routes/conversations.py`
  - [x] Tasks API (Action Items & Commitments) - `backend/routes/tasks.py`
  - [x] Briefings API - `backend/routes/briefings.py`
  - [x] Interviews API - `backend/routes/interviews.py`
- [x] Updated main.py with all new routes
- [x] Updated registration to support profession selection
- [x] Landing page updates:
  - [x] Features.tsx - New features displayed
  - [x] Pricing.tsx - Updated to $29.99, added corporate plans
  - [x] Footer.tsx - All links now working
- [x] Legal pages created:
  - [x] Privacy Policy - `/privacy`
  - [x] Terms of Service - `/terms`
  - [x] Cookie Policy - `/cookies`
  - [x] GDPR Compliance - `/gdpr`
- [x] Support pages created:
  - [x] Documentation - `/docs`
  - [x] Contact Us - `/contact`
  - [x] Changelog - `/changelog`

### In Progress
- [ ] Desktop app ML context integration

### Completed (ML Services & Email)
- [x] ML Services implementation
  - [x] TopicExtractor - Extract topics from conversations
  - [x] PatternAnalyzer - Analyze user communication patterns
  - [x] SummaryGenerator - Generate meeting summaries
  - [x] BriefingGenerator - Generate pre-meeting briefings
  - [x] InterviewCoach - Interview improvement suggestions
- [x] Email service integration (SendGrid)
- [x] Background scheduler for reminders
- [x] Email templates (HTML)
  - [x] meeting_summary.html
  - [x] commitment_reminder.html
  - [x] pre_meeting_briefing.html

### Pending
- [ ] Desktop app UI updates (meeting type dialog, briefing panel)
- [ ] Full testing and QA
- [ ] Server deployment of new features

---

## New Features Summary

| Feature | Description | Priority | Status |
|---------|-------------|----------|--------|
| **Profession Selection** | Users choose career at registration, AI tailors responses | CRITICAL | DONE |
| **Global Career Knowledge** | AI knows terminology for all professions worldwide | CRITICAL | DONE |
| **ML User Learning** | Learn what each user talks about, their style | HIGH | API Ready |
| Meeting Notes & Email | Auto-generate summaries, email to user | HIGH | API Ready |
| Topic Tracking (ML) | Track common topics, identify patterns | HIGH | API Ready |
| User Tendency ML | Learn user patterns, remind of past context | HIGH | API Ready |
| Action Points | Extract WHO does WHAT by WHEN | HIGH | DONE |
| Job Interview Improvement | Track jobs, polish responses over time | MEDIUM | DONE |
| Manager Task Storage | Store assigned tasks for reference | MEDIUM | DONE |
| Commitment Reminders | Email reminders before deadlines | HIGH | API Ready |
| TV Interview Variety | Track points to avoid repetition | MEDIUM | DONE |
| Pre-Meeting Briefings | Context and preparation materials | MEDIUM | DONE |
| **Corporate/Team Plans** | Multi-user accounts with admin controls | HIGH | DONE |

---

## Pricing Structure

### Individual Plans
| Plan | Price | Features |
|------|-------|----------|
| Free Trial | $0 for 14 days | 10 responses/day, profession-tailored AI |
| Premium | $29.99/month | Unlimited, full ML learning, all features |

### Corporate Plans (Admin pays, team joins free)
| Plan | Users | Price | Features |
|------|-------|-------|----------|
| Team | 5-10 | $24.99/user/month | Admin invites team, centralized billing |
| Business | 11-50 | $19.99/user/month | Unlimited invites, admin controls, API |
| Enterprise | 50+ | Custom | SSO, on-premise, custom AI training |

**How Corporate Works:**
1. Admin creates organization account
2. Admin subscribes to a plan (pays per seat)
3. Admin invites team members via email
4. Team members register FREE and join the org
5. All billing goes to admin only

---

## ML Learning Flow

### Before Registration (Profession Knowledge)
When a user registers and selects their profession, the AI immediately has access to:
- Industry-specific terminology
- Common discussion topics for that field
- Appropriate communication style
- Regulatory and compliance awareness

### After Learning the User (Personal Patterns)
As the user continues to use ReadIn AI, ML learns:
- Their personal communication style (formal/casual)
- Topics they frequently discuss
- Their strengths and areas for improvement
- Preferred response length
- Go-to phrases they like to use

The AI prioritizes personal patterns over generic profession knowledge once confidence is high enough.

---

## API Endpoints Summary

### Professions
```
GET  /professions              - List all professions
GET  /professions/categories   - List profession categories
GET  /professions/by-category  - Professions grouped by category
GET  /professions/{id}         - Get specific profession
GET  /professions/user/current - Get current user's profession context
PUT  /professions/user/update  - Update user's profession
```

### Organizations
```
POST   /organizations          - Create organization
GET    /organizations/my       - Get user's organization
PATCH  /organizations/my       - Update organization
GET    /organizations/my/members - List members
POST   /organizations/my/invites - Create invite
GET    /organizations/my/invites - List pending invites
DELETE /organizations/my/invites/{id} - Cancel invite
POST   /organizations/join/{token} - Accept invite
DELETE /organizations/my/members/{id} - Remove member
POST   /organizations/leave    - Leave organization
```

### Meetings
```
POST   /meetings               - Start meeting
POST   /meetings/{id}/end      - End meeting
GET    /meetings               - List meetings
GET    /meetings/active        - Get active meeting
GET    /meetings/{id}          - Get meeting details
PATCH  /meetings/{id}          - Update meeting
DELETE /meetings/{id}          - Delete meeting
GET    /meetings/{id}/summary  - Get summary
POST   /meetings/{id}/summary  - Generate summary
GET    /meetings/analytics/overview - Meeting analytics
```

### Conversations
```
POST   /conversations          - Create conversation
GET    /conversations/meeting/{id} - Get meeting conversations
GET    /conversations/topics   - Get topic analytics
POST   /conversations/topics/extract - Trigger topic extraction
GET    /conversations/search   - Search conversations
GET    /conversations/learning-profile - Get ML profile
POST   /conversations/learning-profile/update - Update ML profile
GET    /conversations/context  - Get context for AI
```

### Tasks
```
POST   /tasks/action-items     - Create action item
GET    /tasks/action-items     - List action items
GET    /tasks/action-items/{id} - Get action item
PATCH  /tasks/action-items/{id} - Update action item
DELETE /tasks/action-items/{id} - Delete action item
POST   /tasks/action-items/{id}/complete - Complete action item
POST   /tasks/commitments      - Create commitment
GET    /tasks/commitments      - List commitments
GET    /tasks/commitments/upcoming - Get upcoming commitments
GET    /tasks/commitments/{id} - Get commitment
PATCH  /tasks/commitments/{id} - Update commitment
DELETE /tasks/commitments/{id} - Delete commitment
POST   /tasks/commitments/{id}/complete - Complete commitment
GET    /tasks/dashboard        - Combined dashboard
```

### Briefings
```
POST   /briefings/generate     - Generate pre-meeting briefing
POST   /briefings/participants - Create participant memory
GET    /briefings/participants - List participants
GET    /briefings/participants/{id} - Get participant
GET    /briefings/participants/by-name/{name} - Find by name
PATCH  /briefings/participants/{id} - Update participant
DELETE /briefings/participants/{id} - Delete participant
POST   /briefings/participants/{id}/add-point - Add key point
POST   /briefings/participants/{id}/add-topic - Add topic
POST   /briefings/participants/auto-extract - Auto-extract from meeting
```

### Interviews
```
POST   /interviews/applications - Create job application
GET    /interviews/applications - List applications
GET    /interviews/applications/{id} - Get application details
PATCH  /interviews/applications/{id} - Update application
DELETE /interviews/applications/{id} - Delete application
POST   /interviews/applications/{id}/interviews - Add interview
GET    /interviews/applications/{id}/interviews - List interviews
GET    /interviews/interviews/{id} - Get interview
PATCH  /interviews/interviews/{id} - Update interview
POST   /interviews/interviews/{id}/link-meeting - Link meeting
GET    /interviews/interviews/{id}/improvement - Get suggestions
POST   /interviews/interviews/{id}/analyze - Trigger analysis
GET    /interviews/analytics   - Interview performance analytics
```

---

## Database Models

All models are implemented in `backend/models.py`:
- **Profession** - Career database with AI customization
- **Organization** - Corporate accounts
- **OrganizationInvite** - Team invitations
- **User** - Updated with profession and org support
- **DailyUsage** - Usage tracking
- **Meeting** - Meeting sessions
- **Conversation** - Q&A exchanges
- **Topic** - ML topic tracking
- **ConversationTopic** - Topic relationships
- **UserLearningProfile** - ML user profile
- **ActionItem** - WHO does WHAT by WHEN
- **Commitment** - User promises
- **MeetingSummary** - Auto-generated summaries
- **JobApplication** - Job tracking
- **Interview** - Interview tracking
- **ParticipantMemory** - Remember participants
- **MediaAppearance** - TV/podcast tracking
- **EmailNotification** - Email log

---

## Environment Variables to Add

```env
# Email Service
SENDGRID_API_KEY=
EMAIL_FROM=noreply@getreadin.ai

# ML Settings
TOPIC_EXTRACTION_MODEL=claude-3-haiku-20240307
SUMMARY_GENERATION_MODEL=claude-sonnet-4-20250514

# Reminder Settings
COMMITMENT_REMINDER_HOURS_BEFORE=24
PRE_MEETING_BRIEFING_HOURS_BEFORE=1
```

---

## Next Steps

1. **Run database migrations** to create new tables
2. **Seed professions** using `python seed_professions.py`
3. **Implement ML services** for topic extraction and pattern analysis
4. **Set up SendGrid** for email delivery
5. **Add background scheduler** for reminders
6. **Update desktop app** to use new APIs
7. **Deploy to server** and test end-to-end

---

## Summary

This plan transforms ReadIn AI into a comprehensive meeting intelligence platform that:
- **Learns** from every conversation
- **Remembers** what was said and by whom
- **Reminds** users of commitments and deadlines
- **Improves** responses over time with ML
- **Prepares** users before every meeting

**New Price Point: $29.99/month** - justified by significantly expanded value proposition.
