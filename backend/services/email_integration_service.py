"""Email Integration Service - Deep email integration with meetings and tasks.

This service provides:
- Link emails to meetings for context
- AI-powered task extraction from emails
- Send meeting summaries as email replies
- Get email context for meeting preparation
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

import anthropic
from sqlalchemy.orm import Session
from sqlalchemy import desc

from models import (
    EmailMeetingLink,
    Meeting,
    MeetingSummary,
    ActionItem,
    Commitment,
    User,
    EmailNotification,
)
from services.email_service import EmailService
from config import APP_URL

logger = logging.getLogger(__name__)


class EmailIntegrationService:
    """
    Deep email integration service for ReadIn AI.

    Provides functionality to:
    - Link emails to meetings bidirectionally
    - Extract tasks and action items from emails using AI
    - Send meeting summaries as email replies
    - Retrieve email context for meeting preparation
    """

    def __init__(self, db: Session):
        self.db = db
        self.email_service = EmailService(db)
        self.ai_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = os.getenv("TASK_EXTRACTION_MODEL", "claude-sonnet-4-20250514")

    async def link_email_to_meeting(
        self,
        user_id: int,
        meeting_id: int,
        email_id: str,
        email_subject: str,
        email_from: str,
        email_body: str,
        email_date: Optional[datetime] = None,
        email_thread_id: Optional[str] = None,
        email_provider: str = "generic",
        link_type: str = "context",
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Link an email to a meeting for context and reference.

        Args:
            user_id: The ID of the user making the link
            meeting_id: The ID of the meeting to link to
            email_id: External email ID (from email provider)
            email_subject: Subject line of the email
            email_from: Sender email address
            email_body: Body content of the email
            email_date: Date the email was sent
            email_thread_id: Thread ID for conversation tracking
            email_provider: Email provider (gmail, outlook, etc.)
            link_type: Type of link (context, follow_up, action_required, reference)
            notes: Optional notes about the link

        Returns:
            Dict containing the created link details
        """
        # Verify meeting belongs to user
        meeting = self.db.query(Meeting).filter(
            Meeting.id == meeting_id,
            Meeting.user_id == user_id
        ).first()

        if not meeting:
            return {
                "success": False,
                "error": "Meeting not found or access denied"
            }

        # Check if link already exists
        existing = self.db.query(EmailMeetingLink).filter(
            EmailMeetingLink.email_id == email_id,
            EmailMeetingLink.meeting_id == meeting_id,
            EmailMeetingLink.user_id == user_id
        ).first()

        if existing:
            # Update existing link
            existing.email_subject = email_subject
            existing.email_from = email_from
            existing.email_body = email_body[:50000] if email_body else None  # Limit size
            existing.email_date = email_date
            existing.link_type = link_type
            existing.notes = notes
            existing.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(existing)

            return {
                "success": True,
                "link_id": existing.id,
                "message": "Email link updated",
                "link": _email_link_to_dict(existing)
            }

        # Create new link
        link = EmailMeetingLink(
            user_id=user_id,
            meeting_id=meeting_id,
            email_id=email_id,
            email_subject=email_subject[:500] if email_subject else None,
            email_from=email_from[:255] if email_from else None,
            email_body=email_body[:50000] if email_body else None,
            email_date=email_date,
            email_thread_id=email_thread_id,
            email_provider=email_provider,
            link_type=link_type,
            notes=notes
        )

        self.db.add(link)
        self.db.commit()
        self.db.refresh(link)

        logger.info(f"Email linked to meeting: email_id={email_id}, meeting_id={meeting_id}")

        return {
            "success": True,
            "link_id": link.id,
            "message": "Email linked to meeting successfully",
            "link": _email_link_to_dict(link)
        }

    async def create_task_from_email(
        self,
        user_id: int,
        email_subject: str,
        email_body: str,
        email_from: str,
        meeting_id: Optional[int] = None,
        auto_create: bool = False,
    ) -> Dict[str, Any]:
        """
        Extract and optionally create tasks/action items from an email using AI.

        Args:
            user_id: The ID of the user
            email_subject: Subject line of the email
            email_body: Body content of the email
            email_from: Sender of the email
            meeting_id: Optional meeting to associate tasks with
            auto_create: If True, automatically create extracted tasks

        Returns:
            Dict containing extracted tasks and creation status
        """
        # Get user for context
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"success": False, "error": "User not found"}

        # If meeting_id provided, verify ownership
        meeting = None
        if meeting_id:
            meeting = self.db.query(Meeting).filter(
                Meeting.id == meeting_id,
                Meeting.user_id == user_id
            ).first()
            if not meeting:
                return {"success": False, "error": "Meeting not found"}

        # Use AI to extract tasks
        extracted_tasks = await self._extract_tasks_with_ai(
            email_subject=email_subject,
            email_body=email_body,
            email_from=email_from,
            user_name=user.full_name or "User"
        )

        if not extracted_tasks.get("tasks"):
            return {
                "success": True,
                "message": "No actionable tasks found in email",
                "extracted_tasks": [],
                "created_tasks": []
            }

        created_tasks = []

        # Auto-create tasks if requested
        if auto_create and meeting:
            for task in extracted_tasks.get("tasks", []):
                action_item = ActionItem(
                    meeting_id=meeting.id,
                    user_id=user_id,
                    assignee=task.get("assignee", user.full_name or "User"),
                    assignee_role=task.get("assignee_role", "user"),
                    description=task.get("description", ""),
                    due_date=self._parse_relative_date(task.get("due_date")),
                    priority=task.get("priority", "medium"),
                    status="pending"
                )
                self.db.add(action_item)
                created_tasks.append({
                    "description": action_item.description,
                    "assignee": action_item.assignee,
                    "due_date": action_item.due_date.isoformat() if action_item.due_date else None,
                    "priority": action_item.priority
                })

            self.db.commit()
            logger.info(f"Created {len(created_tasks)} tasks from email for user {user_id}")

        return {
            "success": True,
            "message": f"Extracted {len(extracted_tasks.get('tasks', []))} tasks from email",
            "extracted_tasks": extracted_tasks.get("tasks", []),
            "commitments": extracted_tasks.get("commitments", []),
            "created_tasks": created_tasks,
            "email_summary": extracted_tasks.get("summary", "")
        }

    async def send_summary_as_reply(
        self,
        user_id: int,
        meeting_id: int,
        recipient_email: str,
        include_action_items: bool = True,
        include_commitments: bool = True,
        custom_message: Optional[str] = None,
        reply_to_email_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send meeting summary as an email reply.

        Args:
            user_id: The ID of the user sending the summary
            meeting_id: The ID of the meeting
            recipient_email: Email address to send to
            include_action_items: Whether to include action items
            include_commitments: Whether to include commitments
            custom_message: Optional custom message to prepend
            reply_to_email_id: Original email ID for threading (if available)

        Returns:
            Dict containing send status
        """
        # Get user
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"success": False, "error": "User not found"}

        # Get meeting
        meeting = self.db.query(Meeting).filter(
            Meeting.id == meeting_id,
            Meeting.user_id == user_id
        ).first()

        if not meeting:
            return {"success": False, "error": "Meeting not found"}

        # Get meeting summary
        summary = self.db.query(MeetingSummary).filter(
            MeetingSummary.meeting_id == meeting_id
        ).first()

        if not summary:
            return {"success": False, "error": "Meeting summary not available yet"}

        # Get action items if requested
        action_items = []
        if include_action_items:
            action_items = self.db.query(ActionItem).filter(
                ActionItem.meeting_id == meeting_id
            ).all()

        # Get commitments if requested
        commitments = []
        if include_commitments:
            commitments = self.db.query(Commitment).filter(
                Commitment.meeting_id == meeting_id
            ).all()

        # Build email content
        html_content = self._build_summary_email_html(
            meeting=meeting,
            summary=summary,
            action_items=action_items,
            commitments=commitments,
            custom_message=custom_message,
            user_name=user.full_name or "User"
        )

        # Build subject
        meeting_title = meeting.title or "Meeting"
        subject = f"Meeting Summary: {meeting_title}"
        if reply_to_email_id:
            subject = f"Re: {subject}"

        # Send email
        result = await self.email_service.send_email(
            to_email=recipient_email,
            subject=subject,
            html_content=html_content,
            user_id=user_id,
            email_type="meeting_summary_reply",
            related_meeting_id=meeting_id
        )

        if result.get("success"):
            logger.info(f"Meeting summary sent to {recipient_email} for meeting {meeting_id}")

        return result

    async def get_email_context_for_meeting(
        self,
        user_id: int,
        meeting_id: int,
        include_body: bool = True,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """
        Get all email context linked to a meeting.

        Args:
            user_id: The ID of the user
            meeting_id: The ID of the meeting
            include_body: Whether to include full email bodies
            limit: Maximum number of emails to return

        Returns:
            Dict containing linked emails and context
        """
        # Verify meeting ownership
        meeting = self.db.query(Meeting).filter(
            Meeting.id == meeting_id,
            Meeting.user_id == user_id
        ).first()

        if not meeting:
            return {"success": False, "error": "Meeting not found"}

        # Get linked emails
        links = self.db.query(EmailMeetingLink).filter(
            EmailMeetingLink.meeting_id == meeting_id,
            EmailMeetingLink.user_id == user_id
        ).order_by(desc(EmailMeetingLink.email_date)).limit(limit).all()

        emails = []
        for link in links:
            email_data = {
                "link_id": link.id,
                "email_id": link.email_id,
                "subject": link.email_subject,
                "from": link.email_from,
                "date": link.email_date.isoformat() if link.email_date else None,
                "link_type": link.link_type,
                "notes": link.notes,
                "thread_id": link.email_thread_id,
                "provider": link.email_provider,
            }
            if include_body:
                email_data["body"] = link.email_body

            emails.append(email_data)

        # Group by link type
        by_type = {}
        for email in emails:
            link_type = email.get("link_type", "other")
            if link_type not in by_type:
                by_type[link_type] = []
            by_type[link_type].append(email)

        # Generate AI summary of email context if there are emails
        context_summary = None
        if emails and len(emails) > 0:
            context_summary = await self._generate_email_context_summary(
                emails=emails,
                meeting_title=meeting.title or "Meeting"
            )

        return {
            "success": True,
            "meeting_id": meeting_id,
            "meeting_title": meeting.title,
            "email_count": len(emails),
            "emails": emails,
            "emails_by_type": by_type,
            "context_summary": context_summary
        }

    async def unlink_email_from_meeting(
        self,
        user_id: int,
        link_id: int,
    ) -> Dict[str, Any]:
        """
        Remove an email-meeting link.

        Args:
            user_id: The ID of the user
            link_id: The ID of the link to remove

        Returns:
            Dict containing deletion status
        """
        link = self.db.query(EmailMeetingLink).filter(
            EmailMeetingLink.id == link_id,
            EmailMeetingLink.user_id == user_id
        ).first()

        if not link:
            return {"success": False, "error": "Link not found"}

        self.db.delete(link)
        self.db.commit()

        return {"success": True, "message": "Email unlinked from meeting"}

    # =========================================================================
    # Private Helper Methods
    # =========================================================================

    async def _extract_tasks_with_ai(
        self,
        email_subject: str,
        email_body: str,
        email_from: str,
        user_name: str
    ) -> Dict[str, Any]:
        """Use AI to extract actionable tasks from email content."""
        prompt = f"""Analyze this email and extract any actionable tasks, action items, or commitments.

Email Subject: {email_subject}
From: {email_from}
To: {user_name}

Email Body:
{email_body[:10000]}

Extract and return in this JSON format:
{{
    "summary": "Brief one-sentence summary of the email",
    "tasks": [
        {{
            "description": "Clear description of the task",
            "assignee": "Who should do this (use '{user_name}' if assigned to recipient, or the person's name)",
            "assignee_role": "user" or "other",
            "due_date": "Relative date like 'tomorrow', 'next week', 'end of month', or specific date if mentioned",
            "priority": "high", "medium", or "low" based on urgency indicators,
            "source_quote": "The exact phrase from the email that indicates this task"
        }}
    ],
    "commitments": [
        {{
            "description": "Something the sender committed to doing",
            "person": "Who made the commitment",
            "due_date": "When they said they would do it"
        }}
    ],
    "follow_up_needed": true or false,
    "urgency_level": "high", "medium", or "low"
}}

Rules:
- Only extract clear, actionable items (not vague mentions)
- Tasks should be specific enough to be tracked
- Set priority based on language like "urgent", "ASAP", "by end of day", etc.
- If no tasks are found, return empty arrays
- Be conservative - don't create tasks from casual conversation"""

        try:
            response = self.ai_client.messages.create(
                model=self.model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}]
            )

            content = response.content[0].text

            # Parse JSON from response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            return json.loads(content.strip())

        except Exception as e:
            logger.error(f"AI task extraction error: {e}")
            return {
                "summary": "",
                "tasks": [],
                "commitments": [],
                "follow_up_needed": False,
                "urgency_level": "low"
            }

    async def _generate_email_context_summary(
        self,
        emails: List[Dict],
        meeting_title: str
    ) -> str:
        """Generate AI summary of email context for meeting preparation."""
        # Build email summaries
        email_summaries = []
        for email in emails[:10]:  # Limit to 10 most recent
            body_preview = (email.get("body") or "")[:500]
            email_summaries.append(
                f"Subject: {email.get('subject', 'No subject')}\n"
                f"From: {email.get('from', 'Unknown')}\n"
                f"Type: {email.get('link_type', 'context')}\n"
                f"Content: {body_preview}..."
            )

        prompt = f"""Based on these emails linked to the meeting "{meeting_title}", provide a brief preparation summary.

Linked Emails:
{chr(10).join(email_summaries)}

Generate a 2-3 sentence summary highlighting:
1. Key discussion points from the emails
2. Any pending items or questions to address
3. Important context the user should remember

Keep it concise and actionable."""

        try:
            response = self.ai_client.messages.create(
                model=self.model,
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text.strip()

        except Exception as e:
            logger.error(f"Email context summary error: {e}")
            return ""

    def _parse_relative_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse relative date strings into datetime objects."""
        if not date_str:
            return None

        date_str = date_str.lower().strip()
        now = datetime.utcnow()

        mapping = {
            "today": now.replace(hour=17, minute=0, second=0, microsecond=0),
            "tomorrow": (now + timedelta(days=1)).replace(hour=17, minute=0, second=0, microsecond=0),
            "next week": now + timedelta(weeks=1),
            "end of week": now + timedelta(days=(4 - now.weekday()) % 7),
            "end of month": now.replace(day=28) + timedelta(days=4),
            "asap": now + timedelta(hours=4),
        }

        for key, value in mapping.items():
            if key in date_str:
                return value

        # Try parsing specific dates
        from dateutil import parser as date_parser
        try:
            return date_parser.parse(date_str)
        except Exception:
            return None

    def _build_summary_email_html(
        self,
        meeting: Meeting,
        summary: MeetingSummary,
        action_items: List[ActionItem],
        commitments: List[Commitment],
        custom_message: Optional[str],
        user_name: str
    ) -> str:
        """Build HTML content for meeting summary email."""
        meeting_title = meeting.title or "Meeting"
        meeting_date = meeting.started_at.strftime("%B %d, %Y at %H:%M") if meeting.started_at else "Unknown"

        # Build action items HTML
        action_items_html = ""
        if action_items:
            items_list = "".join([
                f'<li style="color: #a0a0a0; margin-bottom: 8px;">'
                f'<strong>{self.email_service._sanitize_string(item.assignee)}:</strong> '
                f'{self.email_service._sanitize_string(item.description)}'
                f'{" (Due: " + item.due_date.strftime("%B %d") + ")" if item.due_date else ""}'
                f'</li>'
                for item in action_items[:10]
            ])
            action_items_html = f'''
            <div style="margin-top: 24px;">
                <p style="color: #d4af37; margin-bottom: 12px;"><strong>Action Items:</strong></p>
                <ul style="padding-left: 20px; margin: 0;">
                    {items_list}
                </ul>
            </div>
            '''

        # Build commitments HTML
        commitments_html = ""
        if commitments:
            items_list = "".join([
                f'<li style="color: #a0a0a0; margin-bottom: 8px;">'
                f'{self.email_service._sanitize_string(c.description)}'
                f'{" (Due: " + c.due_date.strftime("%B %d") + ")" if c.due_date else ""}'
                f'</li>'
                for c in commitments[:10]
            ])
            commitments_html = f'''
            <div style="margin-top: 24px;">
                <p style="color: #d4af37; margin-bottom: 12px;"><strong>Commitments:</strong></p>
                <ul style="padding-left: 20px; margin: 0;">
                    {items_list}
                </ul>
            </div>
            '''

        # Build key points HTML
        key_points_html = ""
        if summary.key_points:
            points_list = "".join([
                f'<li style="color: #a0a0a0; margin-bottom: 8px;">'
                f'{self.email_service._sanitize_string(point)}</li>'
                for point in summary.key_points[:5]
            ])
            key_points_html = f'''
            <div style="margin-top: 24px;">
                <p style="color: #d4af37; margin-bottom: 12px;"><strong>Key Points:</strong></p>
                <ul style="padding-left: 20px; margin: 0;">
                    {points_list}
                </ul>
            </div>
            '''

        # Custom message section
        custom_msg_html = ""
        if custom_message:
            custom_msg_html = f'''
            <div style="background-color: #252525; border-radius: 8px; padding: 16px; margin-bottom: 20px;">
                <p style="color: #ffffff; margin: 0;">{self.email_service._sanitize_string(custom_message)}</p>
            </div>
            '''

        dashboard_url = f"{APP_URL}/dashboard/meetings/{meeting.id}"

        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #0a0a0a;">
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #0a0a0a;">
                <tr>
                    <td align="center" style="padding: 40px 20px;">
                        <table role="presentation" width="600" cellspacing="0" cellpadding="0" style="max-width: 600px; background-color: #1a1a1a; border-radius: 16px; border: 1px solid #333;">
                            <tr>
                                <td style="padding: 32px 40px; text-align: center; border-bottom: 1px solid #333;">
                                    <div style="font-size: 28px; font-weight: 700; color: #ffffff;">
                                        ReadIn <span style="color: #d4af37;">AI</span>
                                    </div>
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 40px;">
                                    <h1 style="margin: 0 0 8px; color: #ffffff; font-size: 24px;">Meeting Summary</h1>
                                    <p style="color: #888; margin: 0 0 24px; font-size: 14px;">{self.email_service._sanitize_string(meeting_title)} - {meeting_date}</p>

                                    {custom_msg_html}

                                    <div style="background-color: #252525; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
                                        <p style="color: #a0a0a0; margin: 0; line-height: 1.6;">
                                            {self.email_service._sanitize_string(summary.summary_text)}
                                        </p>
                                    </div>

                                    {key_points_html}
                                    {action_items_html}
                                    {commitments_html}

                                    <div style="text-align: center; margin: 30px 0;">
                                        <a href="{dashboard_url}" style="display: inline-block; padding: 14px 32px; background: linear-gradient(135deg, #d4af37, #c5a028); color: #1a1a1a; text-decoration: none; border-radius: 8px; font-weight: 600;">
                                            View Full Details
                                        </a>
                                    </div>
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 24px 40px; border-top: 1px solid #333; text-align: center;">
                                    <p style="margin: 0; color: #666; font-size: 12px;">
                                        Sent via ReadIn AI by {self.email_service._sanitize_string(user_name)}
                                    </p>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        '''


def _email_link_to_dict(link: EmailMeetingLink) -> Dict[str, Any]:
    """Convert EmailMeetingLink model to dictionary."""
    return {
        "id": link.id,
        "user_id": link.user_id,
        "meeting_id": link.meeting_id,
        "email_id": link.email_id,
        "email_subject": link.email_subject,
        "email_from": link.email_from,
        "email_date": link.email_date.isoformat() if link.email_date else None,
        "email_thread_id": link.email_thread_id,
        "email_provider": link.email_provider,
        "link_type": link.link_type,
        "notes": link.notes,
        "created_at": link.created_at.isoformat() if link.created_at else None,
    }
