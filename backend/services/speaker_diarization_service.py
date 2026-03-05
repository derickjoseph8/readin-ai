"""Speaker Diarization Backend Service.

Handles speaker profile management, voice enrollment, and speaker identification.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_
import numpy as np
import json

logger = logging.getLogger(__name__)


class SpeakerDiarizationService:
    """Backend service for speaker management and diarization."""

    def __init__(self, db: Session):
        self.db = db

    def get_speakers_for_meeting(self, meeting_id: int) -> List[Dict[str, Any]]:
        """Get all speakers detected in a meeting.

        Args:
            meeting_id: The meeting ID

        Returns:
            List of speaker dictionaries with statistics
        """
        from models import Conversation

        # Get unique speakers from conversations
        conversations = self.db.query(Conversation).filter(
            Conversation.meeting_id == meeting_id,
            Conversation.speaker_id.isnot(None)
        ).all()

        speakers: Dict[str, Dict[str, Any]] = {}

        for conv in conversations:
            speaker_id = conv.speaker_id
            if speaker_id not in speakers:
                speakers[speaker_id] = {
                    "speaker_id": speaker_id,
                    "display_name": conv.speaker_name or speaker_id,
                    "message_count": 0,
                    "total_characters": 0,
                    "first_message_at": conv.timestamp.isoformat() if conv.timestamp else None,
                    "last_message_at": conv.timestamp.isoformat() if conv.timestamp else None,
                }

            speakers[speaker_id]["message_count"] += 1
            speakers[speaker_id]["total_characters"] += len(conv.heard_text or "")
            if conv.timestamp:
                speakers[speaker_id]["last_message_at"] = conv.timestamp.isoformat()

        return list(speakers.values())

    def get_user_speakers(
        self,
        user_id: int,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get all known speakers for a user across meetings.

        Args:
            user_id: The user ID
            limit: Maximum number of speakers to return

        Returns:
            List of speaker profiles
        """
        from models import Speaker

        speakers = self.db.query(Speaker).filter(
            Speaker.user_id == user_id
        ).order_by(Speaker.last_seen.desc()).limit(limit).all()

        return [
            {
                "id": s.id,
                "speaker_id": s.speaker_id,
                "display_name": s.display_name or s.speaker_id,
                "total_meetings": s.total_meetings,
                "total_speaking_time": s.total_speaking_time,
                "first_seen": s.first_seen.isoformat() if s.first_seen else None,
                "last_seen": s.last_seen.isoformat() if s.last_seen else None,
                "has_voice_profile": s.voice_embedding is not None,
                "metadata": s.metadata or {}
            }
            for s in speakers
        ]

    def create_or_update_speaker(
        self,
        user_id: int,
        speaker_id: str,
        display_name: Optional[str] = None,
        voice_embedding: Optional[List[float]] = None,
        meeting_id: Optional[int] = None,
        speaking_time: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create or update a speaker profile.

        Args:
            user_id: The user ID
            speaker_id: The speaker identifier (e.g., "SPEAKER_00")
            display_name: Human-readable name
            voice_embedding: Voice embedding vector
            meeting_id: Associated meeting ID
            speaking_time: Speaking time to add
            metadata: Additional metadata

        Returns:
            The speaker profile
        """
        from models import Speaker

        # Find existing speaker
        speaker = self.db.query(Speaker).filter(
            Speaker.user_id == user_id,
            Speaker.speaker_id == speaker_id
        ).first()

        now = datetime.utcnow()

        if speaker:
            # Update existing
            if display_name:
                speaker.display_name = display_name
            if voice_embedding:
                speaker.voice_embedding = json.dumps(voice_embedding)
            if speaking_time > 0:
                speaker.total_speaking_time = (speaker.total_speaking_time or 0) + speaking_time
            if meeting_id:
                speaker.total_meetings = (speaker.total_meetings or 0) + 1
            if metadata:
                existing_meta = speaker.metadata or {}
                existing_meta.update(metadata)
                speaker.metadata = existing_meta
            speaker.last_seen = now
            speaker.updated_at = now
        else:
            # Create new speaker
            speaker = Speaker(
                user_id=user_id,
                speaker_id=speaker_id,
                display_name=display_name,
                voice_embedding=json.dumps(voice_embedding) if voice_embedding else None,
                total_meetings=1 if meeting_id else 0,
                total_speaking_time=speaking_time,
                first_seen=now,
                last_seen=now,
                metadata=metadata or {},
                created_at=now,
                updated_at=now
            )
            self.db.add(speaker)

        self.db.commit()
        self.db.refresh(speaker)

        return {
            "id": speaker.id,
            "speaker_id": speaker.speaker_id,
            "display_name": speaker.display_name or speaker.speaker_id,
            "total_meetings": speaker.total_meetings,
            "total_speaking_time": speaker.total_speaking_time,
            "has_voice_profile": speaker.voice_embedding is not None
        }

    def rename_speaker(
        self,
        user_id: int,
        speaker_id: str,
        new_name: str,
        update_conversations: bool = True
    ) -> bool:
        """Rename a speaker.

        Args:
            user_id: The user ID
            speaker_id: The speaker identifier
            new_name: New display name
            update_conversations: Whether to update all conversation records

        Returns:
            True if successful
        """
        from models import Speaker, Conversation, Meeting

        # Update speaker profile
        speaker = self.db.query(Speaker).filter(
            Speaker.user_id == user_id,
            Speaker.speaker_id == speaker_id
        ).first()

        if speaker:
            speaker.display_name = new_name
            speaker.updated_at = datetime.utcnow()

        # Update conversations if requested
        if update_conversations:
            # Get all meeting IDs for this user
            meeting_ids = self.db.query(Meeting.id).filter(
                Meeting.user_id == user_id
            ).all()
            meeting_ids = [m[0] for m in meeting_ids]

            # Update conversations
            self.db.query(Conversation).filter(
                Conversation.meeting_id.in_(meeting_ids),
                Conversation.speaker_id == speaker_id
            ).update(
                {"speaker_name": new_name},
                synchronize_session=False
            )

        self.db.commit()
        return True

    def merge_speakers(
        self,
        user_id: int,
        source_speaker_id: str,
        target_speaker_id: str
    ) -> bool:
        """Merge two speaker profiles (e.g., same person detected as different speakers).

        Args:
            user_id: The user ID
            source_speaker_id: Speaker to merge from (will be deleted)
            target_speaker_id: Speaker to merge into

        Returns:
            True if successful
        """
        from models import Speaker, Conversation, Meeting

        source = self.db.query(Speaker).filter(
            Speaker.user_id == user_id,
            Speaker.speaker_id == source_speaker_id
        ).first()

        target = self.db.query(Speaker).filter(
            Speaker.user_id == user_id,
            Speaker.speaker_id == target_speaker_id
        ).first()

        if not target:
            # Create target if doesn't exist
            target = Speaker(
                user_id=user_id,
                speaker_id=target_speaker_id,
                created_at=datetime.utcnow()
            )
            self.db.add(target)

        # Merge stats
        if source:
            target.total_meetings = (target.total_meetings or 0) + (source.total_meetings or 0)
            target.total_speaking_time = (target.total_speaking_time or 0) + (source.total_speaking_time or 0)

            # Keep earlier first_seen
            if source.first_seen and (not target.first_seen or source.first_seen < target.first_seen):
                target.first_seen = source.first_seen

            # Keep later last_seen
            if source.last_seen and (not target.last_seen or source.last_seen > target.last_seen):
                target.last_seen = source.last_seen

            # Merge voice embeddings (average them)
            if source.voice_embedding and target.voice_embedding:
                try:
                    source_emb = np.array(json.loads(source.voice_embedding))
                    target_emb = np.array(json.loads(target.voice_embedding))
                    merged_emb = (source_emb + target_emb) / 2
                    target.voice_embedding = json.dumps(merged_emb.tolist())
                except Exception as e:
                    logger.warning(f"Failed to merge embeddings: {e}")
            elif source.voice_embedding:
                target.voice_embedding = source.voice_embedding

        # Update all conversations
        meeting_ids = self.db.query(Meeting.id).filter(
            Meeting.user_id == user_id
        ).all()
        meeting_ids = [m[0] for m in meeting_ids]

        self.db.query(Conversation).filter(
            Conversation.meeting_id.in_(meeting_ids),
            Conversation.speaker_id == source_speaker_id
        ).update(
            {
                "speaker_id": target_speaker_id,
                "speaker_name": target.display_name
            },
            synchronize_session=False
        )

        # Delete source speaker
        if source:
            self.db.delete(source)

        target.updated_at = datetime.utcnow()
        self.db.commit()

        return True

    def find_similar_speaker(
        self,
        user_id: int,
        voice_embedding: List[float],
        threshold: float = 0.75
    ) -> Optional[Dict[str, Any]]:
        """Find a speaker with similar voice embedding.

        Args:
            user_id: The user ID
            voice_embedding: Voice embedding to match
            threshold: Similarity threshold (0-1)

        Returns:
            Best matching speaker or None
        """
        from models import Speaker

        speakers = self.db.query(Speaker).filter(
            Speaker.user_id == user_id,
            Speaker.voice_embedding.isnot(None)
        ).all()

        if not speakers:
            return None

        query_emb = np.array(voice_embedding)
        best_match = None
        best_similarity = threshold

        for speaker in speakers:
            try:
                speaker_emb = np.array(json.loads(speaker.voice_embedding))
                similarity = self._cosine_similarity(query_emb, speaker_emb)

                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = {
                        "id": speaker.id,
                        "speaker_id": speaker.speaker_id,
                        "display_name": speaker.display_name,
                        "similarity": similarity
                    }
            except Exception as e:
                logger.warning(f"Failed to compare embedding for speaker {speaker.id}: {e}")

        return best_match

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    def get_speaker_timeline(
        self,
        meeting_id: int
    ) -> List[Dict[str, Any]]:
        """Get speaker timeline for a meeting.

        Args:
            meeting_id: The meeting ID

        Returns:
            List of speaker segments in chronological order
        """
        from models import Conversation

        conversations = self.db.query(Conversation).filter(
            Conversation.meeting_id == meeting_id
        ).order_by(Conversation.timestamp).all()

        timeline = []
        for conv in conversations:
            timeline.append({
                "speaker_id": conv.speaker_id or "UNKNOWN",
                "speaker_name": conv.speaker_name or conv.speaker_id or "Unknown",
                "text": conv.heard_text,
                "timestamp": conv.timestamp.isoformat() if conv.timestamp else None,
                "start_time": conv.start_time,
                "end_time": conv.end_time
            })

        return timeline

    def get_speaker_statistics(
        self,
        meeting_id: int
    ) -> Dict[str, Any]:
        """Get speaking statistics for a meeting.

        Args:
            meeting_id: The meeting ID

        Returns:
            Statistics including talk time, turn count, etc.
        """
        from models import Conversation

        conversations = self.db.query(Conversation).filter(
            Conversation.meeting_id == meeting_id
        ).all()

        stats: Dict[str, Dict[str, Any]] = {}
        total_messages = len(conversations)
        total_characters = 0

        for conv in conversations:
            speaker_id = conv.speaker_id or "UNKNOWN"
            char_count = len(conv.heard_text or "")
            total_characters += char_count

            if speaker_id not in stats:
                stats[speaker_id] = {
                    "speaker_id": speaker_id,
                    "speaker_name": conv.speaker_name or speaker_id,
                    "message_count": 0,
                    "character_count": 0,
                    "estimated_duration": 0.0,  # Based on character count
                }

            stats[speaker_id]["message_count"] += 1
            stats[speaker_id]["character_count"] += char_count

        # Calculate percentages and estimated duration
        for speaker_id in stats:
            s = stats[speaker_id]
            s["message_percentage"] = (s["message_count"] / total_messages * 100) if total_messages > 0 else 0
            s["character_percentage"] = (s["character_count"] / total_characters * 100) if total_characters > 0 else 0
            # Estimate ~150 words per minute, ~5 chars per word
            s["estimated_duration"] = s["character_count"] / 5 / 150 * 60  # seconds

        return {
            "total_messages": total_messages,
            "total_characters": total_characters,
            "speaker_count": len(stats),
            "speakers": list(stats.values())
        }

    def delete_speaker(
        self,
        user_id: int,
        speaker_id: str,
        anonymize_conversations: bool = True
    ) -> bool:
        """Delete a speaker profile.

        Args:
            user_id: The user ID
            speaker_id: The speaker identifier
            anonymize_conversations: Replace speaker in conversations with "UNKNOWN"

        Returns:
            True if successful
        """
        from models import Speaker, Conversation, Meeting

        # Delete speaker profile
        speaker = self.db.query(Speaker).filter(
            Speaker.user_id == user_id,
            Speaker.speaker_id == speaker_id
        ).first()

        if speaker:
            self.db.delete(speaker)

        # Anonymize conversations
        if anonymize_conversations:
            meeting_ids = self.db.query(Meeting.id).filter(
                Meeting.user_id == user_id
            ).all()
            meeting_ids = [m[0] for m in meeting_ids]

            self.db.query(Conversation).filter(
                Conversation.meeting_id.in_(meeting_ids),
                Conversation.speaker_id == speaker_id
            ).update(
                {
                    "speaker_id": "UNKNOWN",
                    "speaker_name": "Unknown Speaker"
                },
                synchronize_session=False
            )

        self.db.commit()
        return True
