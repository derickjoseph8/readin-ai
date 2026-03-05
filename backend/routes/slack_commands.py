"""
Slack Slash Commands handler.

Handles /readin commands from Slack.
"""

import hmac
import hashlib
import time
import logging
from fastapi import APIRouter, Request, HTTPException, Form
from typing import Optional
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/slack", tags=["slack"])


def verify_slack_signature(
    signature: str,
    timestamp: str,
    body: bytes
) -> bool:
    """Verify Slack request signature."""
    if not settings.SLACK_SIGNING_SECRET:
        logger.warning("SLACK_SIGNING_SECRET not configured")
        return True  # Allow in development

    # Check timestamp to prevent replay attacks
    if abs(time.time() - int(timestamp)) > 60 * 5:
        return False

    sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
    my_signature = 'v0=' + hmac.new(
        settings.SLACK_SIGNING_SECRET.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(my_signature, signature)


@router.post("/commands")
async def handle_slash_command(
    request: Request,
    command: str = Form(...),
    text: str = Form(""),
    user_id: str = Form(...),
    user_name: str = Form(...),
    team_id: str = Form(...),
    channel_id: str = Form(...),
    response_url: str = Form(...)
):
    """
    Handle Slack slash commands.

    Commands:
    - /readin summary - Get last meeting summary
    - /readin meetings - List recent meetings
    - /readin action-items - List pending action items
    - /readin search <query> - Search meetings
    - /readin help - Show help
    """
    # Verify signature
    body = await request.body()
    signature = request.headers.get("X-Slack-Signature", "")
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")

    if not verify_slack_signature(signature, timestamp, body):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse subcommand
    parts = text.strip().split(maxsplit=1)
    subcommand = parts[0].lower() if parts else "help"
    args = parts[1] if len(parts) > 1 else ""

    # Handle commands
    if subcommand == "help":
        return _help_response()

    elif subcommand == "summary":
        return await _summary_command(user_id, team_id)

    elif subcommand == "meetings":
        return await _meetings_command(user_id, team_id)

    elif subcommand in ["action-items", "actions", "tasks"]:
        return await _action_items_command(user_id, team_id)

    elif subcommand == "search":
        if not args:
            return {
                "response_type": "ephemeral",
                "text": "Please provide a search query: `/readin search <query>`"
            }
        return await _search_command(user_id, team_id, args)

    else:
        return {
            "response_type": "ephemeral",
            "text": f"Unknown command: `{subcommand}`. Use `/readin help` for available commands."
        }


def _help_response():
    """Return help message."""
    return {
        "response_type": "ephemeral",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*ReadIn AI Commands*"
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        "`/readin summary` - Get your last meeting summary\n"
                        "`/readin meetings` - List your recent meetings\n"
                        "`/readin action-items` - List pending action items\n"
                        "`/readin search <query>` - Search your meetings\n"
                        "`/readin help` - Show this help message"
                    )
                }
            }
        ]
    }


async def _summary_command(slack_user_id: str, team_id: str):
    """Get last meeting summary."""
    from database import SessionLocal
    from models import Meeting, SlackIntegration

    db = SessionLocal()
    try:
        # Find user by Slack integration
        integration = db.query(SlackIntegration).filter(
            SlackIntegration.slack_team_id == team_id,
            SlackIntegration.slack_user_id == slack_user_id
        ).first()

        if not integration:
            return {
                "response_type": "ephemeral",
                "text": "Your Slack account is not connected to ReadIn AI. Please connect in the web dashboard."
            }

        # Get last meeting
        meeting = db.query(Meeting).filter(
            Meeting.user_id == integration.user_id,
            Meeting.status == "ended"
        ).order_by(Meeting.end_time.desc()).first()

        if not meeting:
            return {
                "response_type": "ephemeral",
                "text": "No completed meetings found."
            }

        return {
            "response_type": "ephemeral",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{meeting.title or 'Meeting'}*\n{meeting.start_time.strftime('%b %d, %Y at %I:%M %p')}"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Summary:*\n{meeting.summary or 'No summary available.'}"
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "View Full Details"},
                            "url": f"{settings.FRONTEND_URL}/meetings/{meeting.id}",
                            "action_id": "view_meeting"
                        }
                    ]
                }
            ]
        }
    finally:
        db.close()


async def _meetings_command(slack_user_id: str, team_id: str):
    """List recent meetings."""
    from database import SessionLocal
    from models import Meeting, SlackIntegration

    db = SessionLocal()
    try:
        integration = db.query(SlackIntegration).filter(
            SlackIntegration.slack_team_id == team_id,
            SlackIntegration.slack_user_id == slack_user_id
        ).first()

        if not integration:
            return {
                "response_type": "ephemeral",
                "text": "Slack account not connected. Connect in the web dashboard."
            }

        meetings = db.query(Meeting).filter(
            Meeting.user_id == integration.user_id
        ).order_by(Meeting.start_time.desc()).limit(5).all()

        if not meetings:
            return {"response_type": "ephemeral", "text": "No meetings found."}

        blocks = [
            {"type": "section", "text": {"type": "mrkdwn", "text": "*Your Recent Meetings*"}},
            {"type": "divider"}
        ]

        for m in meetings:
            status_emoji = "" if m.status == "ended" else ""
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{status_emoji} *{m.title or 'Meeting'}*\n{m.start_time.strftime('%b %d at %I:%M %p')}"
                },
                "accessory": {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "View"},
                    "url": f"{settings.FRONTEND_URL}/meetings/{m.id}",
                    "action_id": f"view_meeting_{m.id}"
                }
            })

        return {"response_type": "ephemeral", "blocks": blocks}
    finally:
        db.close()


async def _action_items_command(slack_user_id: str, team_id: str):
    """List pending action items."""
    from database import SessionLocal
    from models import ActionItem, SlackIntegration

    db = SessionLocal()
    try:
        integration = db.query(SlackIntegration).filter(
            SlackIntegration.slack_team_id == team_id,
            SlackIntegration.slack_user_id == slack_user_id
        ).first()

        if not integration:
            return {
                "response_type": "ephemeral",
                "text": "Slack account not connected."
            }

        items = db.query(ActionItem).filter(
            ActionItem.user_id == integration.user_id,
            ActionItem.status.in_(["pending", "in_progress"])
        ).order_by(ActionItem.due_date).limit(10).all()

        if not items:
            return {"response_type": "ephemeral", "text": "No pending action items!"}

        blocks = [
            {"type": "section", "text": {"type": "mrkdwn", "text": "*Pending Action Items*"}},
            {"type": "divider"}
        ]

        for item in items:
            priority_emoji = {"urgent": "", "high": "", "medium": "", "low": ""}.get(item.priority, "")
            due = f" (Due: {item.due_date.strftime('%b %d')})" if item.due_date else ""

            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{priority_emoji} {item.title}{due}"
                },
                "accessory": {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Complete"},
                    "style": "primary",
                    "action_id": f"complete_action_{item.id}"
                }
            })

        return {"response_type": "ephemeral", "blocks": blocks}
    finally:
        db.close()


async def _search_command(slack_user_id: str, team_id: str, query: str):
    """Search meetings."""
    from database import SessionLocal
    from models import Meeting, SlackIntegration

    db = SessionLocal()
    try:
        integration = db.query(SlackIntegration).filter(
            SlackIntegration.slack_team_id == team_id,
            SlackIntegration.slack_user_id == slack_user_id
        ).first()

        if not integration:
            return {"response_type": "ephemeral", "text": "Slack account not connected."}

        # Simple search
        meetings = db.query(Meeting).filter(
            Meeting.user_id == integration.user_id,
            (Meeting.title.ilike(f"%{query}%") |
             Meeting.summary.ilike(f"%{query}%"))
        ).limit(5).all()

        if not meetings:
            return {"response_type": "ephemeral", "text": f"No meetings found for '{query}'"}

        blocks = [
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*Search Results for '{query}'*"}},
            {"type": "divider"}
        ]

        for m in meetings:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{m.title or 'Meeting'}*\n{m.start_time.strftime('%b %d, %Y')}"
                },
                "accessory": {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "View"},
                    "url": f"{settings.FRONTEND_URL}/meetings/{m.id}",
                    "action_id": f"view_meeting_{m.id}"
                }
            })

        return {"response_type": "ephemeral", "blocks": blocks}
    finally:
        db.close()
