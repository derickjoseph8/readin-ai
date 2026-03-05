"""
Collaboration Service - Shared notes, comments, @mentions, handoffs.

Enables team collaboration on meeting notes and action items.
"""

import re
import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class CollaborationService:
    """Service for collaboration features."""

    def __init__(self, db: Session):
        self.db = db

    def parse_mentions(self, content: str) -> List[str]:
        """
        Extract @mentions from content.

        Args:
            content: Text content that may contain @mentions

        Returns:
            List of usernames mentioned (without @)
        """
        # Match @username patterns (alphanumeric, dots, underscores)
        pattern = r'@([a-zA-Z0-9._]+)'
        mentions = re.findall(pattern, content)
        return list(set(mentions))  # Unique mentions

    def parse_mention_uuids(self, content: str, org_members: Dict[str, UUID]) -> List[UUID]:
        """
        Extract @mentions and resolve to user UUIDs.

        Args:
            content: Text content with @mentions
            org_members: Dict mapping username/email to user UUID

        Returns:
            List of user UUIDs that were mentioned
        """
        mentions = self.parse_mentions(content)
        user_ids = []

        for mention in mentions:
            # Try to match by username or email prefix
            mention_lower = mention.lower()
            for key, user_id in org_members.items():
                if key.lower() == mention_lower or key.lower().startswith(mention_lower + "@"):
                    user_ids.append(user_id)
                    break

        return user_ids

    async def create_shared_note(
        self,
        meeting_id: UUID,
        created_by: UUID,
        content: str = "",
        organization_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Create a shared note for a meeting.

        Args:
            meeting_id: ID of the meeting
            created_by: User ID of creator
            content: Initial note content
            organization_id: Optional organization ID for team notes

        Returns:
            Created note data
        """
        from models import SharedNote

        note = SharedNote(
            meeting_id=meeting_id,
            created_by=created_by,
            content=content,
            organization_id=organization_id
        )

        self.db.add(note)
        self.db.commit()
        self.db.refresh(note)

        return {
            "id": str(note.id),
            "meeting_id": str(note.meeting_id),
            "content": note.content,
            "created_by": str(note.created_by),
            "created_at": note.created_at.isoformat()
        }

    async def update_note(
        self,
        note_id: UUID,
        content: str,
        updated_by: UUID
    ) -> Dict[str, Any]:
        """
        Update a shared note's content.

        Args:
            note_id: ID of the note
            content: New content
            updated_by: User making the update

        Returns:
            Updated note data
        """
        from models import SharedNote

        note = self.db.query(SharedNote).filter(SharedNote.id == note_id).first()
        if not note:
            raise ValueError("Note not found")

        note.content = content
        note.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(note)

        # Parse and notify mentioned users
        mentions = self.parse_mentions(content)
        if mentions:
            await self._notify_mentions(note_id, mentions, updated_by)

        return {
            "id": str(note.id),
            "content": note.content,
            "updated_at": note.updated_at.isoformat()
        }

    async def add_comment(
        self,
        note_id: UUID,
        user_id: UUID,
        content: str,
        parent_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Add a comment to a shared note.

        Args:
            note_id: ID of the note
            user_id: Commenter's user ID
            content: Comment content
            parent_id: Optional parent comment for threading

        Returns:
            Created comment data
        """
        from models import NoteComment

        # Parse mentions from comment
        mentions = self.parse_mentions(content)

        comment = NoteComment(
            note_id=note_id,
            user_id=user_id,
            content=content,
            parent_id=parent_id,
            mentions=mentions
        )

        self.db.add(comment)
        self.db.commit()
        self.db.refresh(comment)

        # Notify mentioned users
        if mentions:
            await self._notify_mentions(note_id, mentions, user_id, is_comment=True)

        return {
            "id": str(comment.id),
            "note_id": str(comment.note_id),
            "user_id": str(comment.user_id),
            "content": comment.content,
            "mentions": mentions,
            "parent_id": str(comment.parent_id) if comment.parent_id else None,
            "created_at": comment.created_at.isoformat()
        }

    async def create_handoff(
        self,
        meeting_id: UUID,
        from_user_id: UUID,
        to_user_id: UUID,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a meeting handoff request.

        Args:
            meeting_id: ID of the meeting to hand off
            from_user_id: Current owner
            to_user_id: New owner
            notes: Handoff notes

        Returns:
            Created handoff data
        """
        from models import MeetingHandoff

        handoff = MeetingHandoff(
            meeting_id=meeting_id,
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            notes=notes,
            status="pending"
        )

        self.db.add(handoff)
        self.db.commit()
        self.db.refresh(handoff)

        # Notify recipient
        await self._notify_handoff(handoff)

        return {
            "id": str(handoff.id),
            "meeting_id": str(handoff.meeting_id),
            "from_user_id": str(handoff.from_user_id),
            "to_user_id": str(handoff.to_user_id),
            "notes": handoff.notes,
            "status": handoff.status,
            "created_at": handoff.created_at.isoformat()
        }

    async def respond_to_handoff(
        self,
        handoff_id: UUID,
        user_id: UUID,
        accept: bool
    ) -> Dict[str, Any]:
        """
        Accept or decline a handoff request.

        Args:
            handoff_id: ID of the handoff
            user_id: User responding (must be to_user)
            accept: True to accept, False to decline

        Returns:
            Updated handoff data
        """
        from models import MeetingHandoff, Meeting

        handoff = self.db.query(MeetingHandoff).filter(
            MeetingHandoff.id == handoff_id
        ).first()

        if not handoff:
            raise ValueError("Handoff not found")

        if handoff.to_user_id != user_id:
            raise PermissionError("Not authorized to respond to this handoff")

        if handoff.status != "pending":
            raise ValueError("Handoff already processed")

        handoff.status = "accepted" if accept else "declined"

        # If accepted, transfer meeting ownership
        if accept:
            meeting = self.db.query(Meeting).filter(
                Meeting.id == handoff.meeting_id
            ).first()
            if meeting:
                meeting.user_id = user_id

        self.db.commit()

        return {
            "id": str(handoff.id),
            "status": handoff.status,
            "accepted": accept
        }

    async def _notify_mentions(
        self,
        note_id: UUID,
        mentions: List[str],
        mentioned_by: UUID,
        is_comment: bool = False
    ):
        """Send notifications to mentioned users."""
        try:
            from services.notification_service import NotificationService
            # Implementation would send notifications
            logger.info(f"Notifying {len(mentions)} mentioned users")
        except Exception as e:
            logger.error(f"Failed to notify mentions: {e}")

    async def _notify_handoff(self, handoff):
        """Send notification for handoff request."""
        try:
            from services.notification_service import NotificationService
            logger.info(f"Notifying user of handoff request")
        except Exception as e:
            logger.error(f"Failed to notify handoff: {e}")
