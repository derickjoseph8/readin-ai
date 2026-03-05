"""
Slack Interactive Components handler.

Handles button clicks, modals, and other interactive elements.
"""

import json
import hmac
import hashlib
import time
import logging
from fastapi import APIRouter, Request, HTTPException, Form
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/slack", tags=["slack"])


def verify_slack_signature(signature: str, timestamp: str, body: bytes) -> bool:
    """Verify Slack request signature."""
    if not settings.SLACK_SIGNING_SECRET:
        return True

    if abs(time.time() - int(timestamp)) > 60 * 5:
        return False

    sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
    my_signature = 'v0=' + hmac.new(
        settings.SLACK_SIGNING_SECRET.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(my_signature, signature)


@router.post("/interactive")
async def handle_interactive(
    request: Request,
    payload: str = Form(...)
):
    """
    Handle Slack interactive component payloads.

    Handles:
    - Button clicks (complete action item, view meeting)
    - Modal submissions
    - Shortcut triggers
    """
    body = await request.body()
    signature = request.headers.get("X-Slack-Signature", "")
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")

    if not verify_slack_signature(signature, timestamp, body):
        raise HTTPException(status_code=401, detail="Invalid signature")

    data = json.loads(payload)
    action_type = data.get("type")

    if action_type == "block_actions":
        return await handle_block_actions(data)

    elif action_type == "view_submission":
        return await handle_modal_submission(data)

    elif action_type == "shortcut":
        return await handle_shortcut(data)

    return {"ok": True}


async def handle_block_actions(data: dict):
    """Handle button and select menu actions."""
    actions = data.get("actions", [])
    user = data.get("user", {})
    slack_user_id = user.get("id")

    for action in actions:
        action_id = action.get("action_id", "")

        # Complete action item
        if action_id.startswith("complete_action_"):
            item_id = action_id.replace("complete_action_", "")
            return await complete_action_item(item_id, slack_user_id)

        # View meeting (handled by URL, no server action needed)

    return {"ok": True}


async def complete_action_item(item_id: str, slack_user_id: str):
    """Mark action item as completed."""
    from database import SessionLocal
    from models import ActionItem, SlackIntegration
    from uuid import UUID

    db = SessionLocal()
    try:
        # Find user
        integration = db.query(SlackIntegration).filter(
            SlackIntegration.slack_user_id == slack_user_id
        ).first()

        if not integration:
            return {
                "response_action": "update",
                "view": {
                    "type": "modal",
                    "title": {"type": "plain_text", "text": "Error"},
                    "blocks": [
                        {"type": "section", "text": {"type": "mrkdwn", "text": "Account not connected."}}
                    ]
                }
            }

        # Mark complete
        item = db.query(ActionItem).filter(
            ActionItem.id == UUID(item_id),
            ActionItem.user_id == integration.user_id
        ).first()

        if item:
            item.status = "completed"
            db.commit()

        return {
            "response_action": "update",
            "view": None  # Removes the message
        }
    finally:
        db.close()


async def handle_modal_submission(data: dict):
    """Handle modal form submissions."""
    view = data.get("view", {})
    callback_id = view.get("callback_id", "")
    values = view.get("state", {}).get("values", {})
    user = data.get("user", {})

    if callback_id == "add_note_modal":
        return await save_note_from_modal(values, user)

    return {"response_action": "clear"}


async def save_note_from_modal(values: dict, user: dict):
    """Save note from modal submission."""
    # Extract values from modal
    note_content = ""
    meeting_id = None

    for block_id, block_values in values.items():
        for action_id, action_value in block_values.items():
            if action_id == "note_content":
                note_content = action_value.get("value", "")
            elif action_id == "meeting_select":
                meeting_id = action_value.get("selected_option", {}).get("value")

    if not note_content or not meeting_id:
        return {
            "response_action": "errors",
            "errors": {
                "note_content_block": "Please enter note content",
                "meeting_select_block": "Please select a meeting"
            }
        }

    # Save note
    from database import SessionLocal
    from models import SharedNote, SlackIntegration
    from uuid import UUID

    db = SessionLocal()
    try:
        integration = db.query(SlackIntegration).filter(
            SlackIntegration.slack_user_id == user.get("id")
        ).first()

        if integration:
            note = SharedNote(
                meeting_id=UUID(meeting_id),
                created_by=integration.user_id,
                content=note_content
            )
            db.add(note)
            db.commit()

        return {"response_action": "clear"}
    finally:
        db.close()


async def handle_shortcut(data: dict):
    """Handle global and message shortcuts."""
    callback_id = data.get("callback_id", "")
    trigger_id = data.get("trigger_id", "")

    if callback_id == "add_meeting_note":
        return await open_add_note_modal(trigger_id)

    return {"ok": True}


async def open_add_note_modal(trigger_id: str):
    """Open modal for adding a meeting note."""
    import httpx

    modal = {
        "type": "modal",
        "callback_id": "add_note_modal",
        "title": {"type": "plain_text", "text": "Add Meeting Note"},
        "submit": {"type": "plain_text", "text": "Save"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "input",
                "block_id": "meeting_select_block",
                "element": {
                    "type": "external_select",
                    "action_id": "meeting_select",
                    "placeholder": {"type": "plain_text", "text": "Select a meeting"},
                    "min_query_length": 0
                },
                "label": {"type": "plain_text", "text": "Meeting"}
            },
            {
                "type": "input",
                "block_id": "note_content_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "note_content",
                    "multiline": True,
                    "placeholder": {"type": "plain_text", "text": "Enter your note..."}
                },
                "label": {"type": "plain_text", "text": "Note"}
            }
        ]
    }

    # Open modal via Slack API
    async with httpx.AsyncClient() as client:
        await client.post(
            "https://slack.com/api/views.open",
            headers={"Authorization": f"Bearer {settings.SLACK_BOT_TOKEN}"},
            json={"trigger_id": trigger_id, "view": modal}
        )

    return {"ok": True}
