"""Transcript Editing Service for ReadIn AI.

This service handles:
- Saving original text when first edited
- Tracking edit history
- AI-powered transcription correction suggestions
- Reverting to original text
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

import anthropic
from sqlalchemy.orm import Session
from sqlalchemy import desc

from models import Conversation, Meeting, User


logger = logging.getLogger(__name__)


# AI prompt for transcription correction suggestions
CORRECTION_SUGGESTION_PROMPT = """You are an expert transcription editor. Analyze this transcript text and suggest corrections for:
1. Misheard words or phrases (homophones, similar-sounding words)
2. Technical terminology that may have been misrecognized
3. Proper nouns (names, companies, products) that may be incorrectly transcribed
4. Grammar and punctuation issues typical of speech-to-text errors
5. Incomplete sentences or fragmented thoughts

Original transcript text:
"{text}"

Context (if available):
- Meeting type: {meeting_type}
- Speaker: {speaker}

Provide your suggestions in the following JSON format:
{{
    "corrected_text": "The full corrected version of the text",
    "corrections": [
        {{
            "original": "original word or phrase",
            "suggested": "corrected word or phrase",
            "reason": "brief explanation of why this correction is suggested",
            "confidence": 0.0-1.0
        }}
    ],
    "overall_confidence": 0.0-1.0,
    "notes": "Any additional notes about the transcription quality"
}}

Important:
- Only suggest corrections you are confident about
- Preserve the speaker's intent and meaning
- Don't change style or rephrase - only fix transcription errors
- If the text looks correct, return it unchanged with an empty corrections array
"""


class TranscriptService:
    """Service for transcript editing and correction.

    Provides functionality for:
    - Editing transcript text with original preservation
    - Reverting edits to original
    - AI-powered correction suggestions
    - Edit history tracking
    """

    def __init__(self, db: Session):
        self.db = db
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = os.getenv("TRANSCRIPT_CORRECTION_MODEL", "claude-sonnet-4-20250514")

    def edit_transcript(
        self,
        conversation_id: int,
        edited_text: str,
        user_id: int
    ) -> Conversation:
        """Edit a transcript line.

        Saves the original text on first edit and updates with new text.

        Args:
            conversation_id: The conversation/transcript ID to edit
            edited_text: The new edited text
            user_id: The user making the edit (for authorization)

        Returns:
            Updated Conversation object

        Raises:
            ValueError: If conversation not found or user not authorized
        """
        # Get conversation with meeting for authorization check
        conversation = (
            self.db.query(Conversation)
            .join(Meeting)
            .filter(
                Conversation.id == conversation_id,
                Meeting.user_id == user_id
            )
            .first()
        )

        if not conversation:
            raise ValueError("Transcript not found or access denied")

        # Save original text on first edit
        if not conversation.is_edited:
            conversation.original_text = conversation.heard_text
            logger.info(
                f"Saving original text for transcript {conversation_id}: "
                f"{conversation.heard_text[:50]}..."
            )

        # Update with edited text
        conversation.edited_text = edited_text
        conversation.heard_text = edited_text  # Also update main text field
        conversation.is_edited = True
        conversation.edited_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(conversation)

        logger.info(f"Transcript {conversation_id} edited by user {user_id}")

        return conversation

    def revert_transcript(
        self,
        conversation_id: int,
        user_id: int
    ) -> Conversation:
        """Revert a transcript to its original text.

        Args:
            conversation_id: The conversation/transcript ID to revert
            user_id: The user making the request (for authorization)

        Returns:
            Reverted Conversation object

        Raises:
            ValueError: If conversation not found, not edited, or user not authorized
        """
        # Get conversation with meeting for authorization check
        conversation = (
            self.db.query(Conversation)
            .join(Meeting)
            .filter(
                Conversation.id == conversation_id,
                Meeting.user_id == user_id
            )
            .first()
        )

        if not conversation:
            raise ValueError("Transcript not found or access denied")

        if not conversation.is_edited or not conversation.original_text:
            raise ValueError("Transcript has not been edited")

        # Revert to original
        conversation.heard_text = conversation.original_text
        conversation.edited_text = None
        conversation.is_edited = False
        conversation.edited_at = None
        # Keep original_text for history

        self.db.commit()
        self.db.refresh(conversation)

        logger.info(f"Transcript {conversation_id} reverted by user {user_id}")

        return conversation

    def get_meeting_transcript_changes(
        self,
        meeting_id: int,
        user_id: int
    ) -> List[Dict[str, Any]]:
        """Get all edited transcripts for a meeting.

        Args:
            meeting_id: The meeting ID to get changes for
            user_id: The user making the request (for authorization)

        Returns:
            List of edited transcript entries with original and edited text

        Raises:
            ValueError: If meeting not found or user not authorized
        """
        # Verify meeting belongs to user
        meeting = (
            self.db.query(Meeting)
            .filter(Meeting.id == meeting_id, Meeting.user_id == user_id)
            .first()
        )

        if not meeting:
            raise ValueError("Meeting not found or access denied")

        # Get all edited conversations for this meeting
        edited_conversations = (
            self.db.query(Conversation)
            .filter(
                Conversation.meeting_id == meeting_id,
                Conversation.is_edited == True
            )
            .order_by(Conversation.timestamp)
            .all()
        )

        changes = []
        for conv in edited_conversations:
            changes.append({
                "id": conv.id,
                "meeting_id": conv.meeting_id,
                "speaker": conv.speaker,
                "original_text": conv.original_text,
                "edited_text": conv.edited_text,
                "current_text": conv.heard_text,
                "edited_at": conv.edited_at.isoformat() if conv.edited_at else None,
                "timestamp": conv.timestamp.isoformat() if conv.timestamp else None,
            })

        return changes

    async def suggest_correction(
        self,
        conversation_id: int,
        user_id: int,
        additional_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get AI-powered correction suggestions for a transcript.

        Uses Claude AI to analyze the transcript and suggest corrections
        for common transcription errors.

        Args:
            conversation_id: The conversation/transcript ID to analyze
            user_id: The user making the request (for authorization)
            additional_context: Optional additional context to help the AI

        Returns:
            Dictionary with corrected text and list of corrections

        Raises:
            ValueError: If conversation not found or user not authorized
        """
        # Get conversation with meeting for authorization and context
        conversation = (
            self.db.query(Conversation)
            .join(Meeting)
            .filter(
                Conversation.id == conversation_id,
                Meeting.user_id == user_id
            )
            .first()
        )

        if not conversation:
            raise ValueError("Transcript not found or access denied")

        meeting = conversation.meeting

        # Build the prompt
        prompt = CORRECTION_SUGGESTION_PROMPT.format(
            text=conversation.heard_text,
            meeting_type=meeting.meeting_type if meeting else "unknown",
            speaker=conversation.speaker or "unknown"
        )

        if additional_context:
            prompt += f"\n\nAdditional context from user: {additional_context}"

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )

            content = response.content[0].text

            # Parse JSON from response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            result = json.loads(content.strip())

            # Add metadata
            result["transcript_id"] = conversation_id
            result["original_text"] = conversation.heard_text
            result["suggested_at"] = datetime.utcnow().isoformat()

            logger.info(
                f"Generated {len(result.get('corrections', []))} correction suggestions "
                f"for transcript {conversation_id}"
            )

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI correction response: {e}")
            return {
                "transcript_id": conversation_id,
                "original_text": conversation.heard_text,
                "corrected_text": conversation.heard_text,
                "corrections": [],
                "overall_confidence": 0.0,
                "notes": "Unable to generate suggestions at this time",
                "error": "Failed to parse AI response"
            }
        except Exception as e:
            logger.error(f"Failed to generate correction suggestions: {e}")
            return {
                "transcript_id": conversation_id,
                "original_text": conversation.heard_text,
                "corrected_text": conversation.heard_text,
                "corrections": [],
                "overall_confidence": 0.0,
                "notes": "Unable to generate suggestions at this time",
                "error": str(e)
            }

    def apply_correction_suggestion(
        self,
        conversation_id: int,
        corrected_text: str,
        user_id: int
    ) -> Conversation:
        """Apply an AI-suggested correction to a transcript.

        This is a convenience method that applies the corrected text
        from suggest_correction().

        Args:
            conversation_id: The conversation/transcript ID to update
            corrected_text: The AI-suggested corrected text
            user_id: The user applying the correction

        Returns:
            Updated Conversation object
        """
        return self.edit_transcript(conversation_id, corrected_text, user_id)

    def get_transcript_stats(
        self,
        meeting_id: int,
        user_id: int
    ) -> Dict[str, Any]:
        """Get statistics about transcript edits for a meeting.

        Args:
            meeting_id: The meeting ID to get stats for
            user_id: The user making the request

        Returns:
            Dictionary with edit statistics
        """
        # Verify meeting belongs to user
        meeting = (
            self.db.query(Meeting)
            .filter(Meeting.id == meeting_id, Meeting.user_id == user_id)
            .first()
        )

        if not meeting:
            raise ValueError("Meeting not found or access denied")

        # Get counts
        total_transcripts = (
            self.db.query(Conversation)
            .filter(Conversation.meeting_id == meeting_id)
            .count()
        )

        edited_transcripts = (
            self.db.query(Conversation)
            .filter(
                Conversation.meeting_id == meeting_id,
                Conversation.is_edited == True
            )
            .count()
        )

        # Get last edit time
        last_edited = (
            self.db.query(Conversation)
            .filter(
                Conversation.meeting_id == meeting_id,
                Conversation.is_edited == True
            )
            .order_by(desc(Conversation.edited_at))
            .first()
        )

        return {
            "meeting_id": meeting_id,
            "total_transcripts": total_transcripts,
            "edited_transcripts": edited_transcripts,
            "unedited_transcripts": total_transcripts - edited_transcripts,
            "edit_percentage": (
                (edited_transcripts / total_transcripts * 100)
                if total_transcripts > 0 else 0
            ),
            "last_edited_at": (
                last_edited.edited_at.isoformat()
                if last_edited and last_edited.edited_at else None
            ),
        }
