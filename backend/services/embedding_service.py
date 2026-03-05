"""Embedding Service for semantic search using sentence-transformers."""

import os
import logging
from typing import List, Optional, Dict, Any
from functools import lru_cache

from services.cache_service import cache, CacheKeys

logger = logging.getLogger(__name__)

# Model name - using all-MiniLM-L6-v2 for good balance of speed and quality
# 384-dimensional embeddings, ~23MB model size
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# Lazy-loaded model instance
_model = None


def get_model():
    """Get or initialize the sentence transformer model (lazy loading)."""
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading embedding model: {EMBEDDING_MODEL_NAME}")
            _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
            logger.info(f"Embedding model loaded successfully. Dimension: {_model.get_sentence_embedding_dimension()}")
        except ImportError:
            logger.error("sentence-transformers not installed. Run: pip install sentence-transformers")
            raise ImportError(
                "sentence-transformers is required for semantic search. "
                "Install with: pip install sentence-transformers"
            )
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    return _model


def generate_embedding(text: str) -> List[float]:
    """
    Generate embedding vector for a text string.

    Args:
        text: The text to embed

    Returns:
        List of floats representing the embedding vector (384 dimensions for MiniLM)
    """
    if not text or not text.strip():
        return []

    model = get_model()

    # Clean and truncate text if needed (model has 256 word piece limit)
    text = text.strip()
    if len(text) > 10000:  # Rough character limit
        text = text[:10000]

    try:
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        return []


def generate_embeddings_batch(texts: List[str], batch_size: int = 32) -> List[List[float]]:
    """
    Generate embeddings for multiple texts efficiently.

    Args:
        texts: List of texts to embed
        batch_size: Number of texts to process at once

    Returns:
        List of embedding vectors
    """
    if not texts:
        return []

    model = get_model()

    # Clean texts
    cleaned_texts = []
    for text in texts:
        if text and text.strip():
            t = text.strip()
            if len(t) > 10000:
                t = t[:10000]
            cleaned_texts.append(t)
        else:
            cleaned_texts.append("")  # Placeholder for empty texts

    try:
        embeddings = model.encode(
            cleaned_texts,
            batch_size=batch_size,
            show_progress_bar=False,
            convert_to_numpy=True
        )
        return [emb.tolist() if text else [] for emb, text in zip(embeddings, cleaned_texts)]
    except Exception as e:
        logger.error(f"Error generating batch embeddings: {e}")
        return [[] for _ in texts]


def compute_similarity(embedding1: List[float], embedding2: List[float]) -> float:
    """
    Compute cosine similarity between two embeddings.

    Args:
        embedding1: First embedding vector
        embedding2: Second embedding vector

    Returns:
        Similarity score between 0 and 1
    """
    if not embedding1 or not embedding2:
        return 0.0

    try:
        import numpy as np

        v1 = np.array(embedding1)
        v2 = np.array(embedding2)

        # Cosine similarity
        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))
    except Exception as e:
        logger.error(f"Error computing similarity: {e}")
        return 0.0


def get_embedding_dimension() -> int:
    """Get the dimension of embeddings from the current model."""
    model = get_model()
    return model.get_sentence_embedding_dimension()


def prepare_meeting_text_for_embedding(
    title: Optional[str] = None,
    notes: Optional[str] = None,
    transcript_texts: Optional[List[str]] = None,
    max_length: int = 5000
) -> str:
    """
    Prepare meeting content for embedding by combining title, notes, and transcript.

    Args:
        title: Meeting title
        notes: Meeting notes
        transcript_texts: List of conversation texts from the meeting
        max_length: Maximum character length for the combined text

    Returns:
        Combined text suitable for embedding
    """
    parts = []

    if title and title.strip():
        parts.append(f"Title: {title.strip()}")

    if notes and notes.strip():
        parts.append(f"Notes: {notes.strip()[:1000]}")

    if transcript_texts:
        # Take the most relevant portions of transcript
        transcript = " ".join(t.strip() for t in transcript_texts if t and t.strip())
        if transcript:
            # Truncate to fit within limit
            remaining = max_length - sum(len(p) for p in parts) - 50
            if remaining > 100:
                parts.append(f"Transcript: {transcript[:remaining]}")

    combined = "\n".join(parts)
    return combined[:max_length] if len(combined) > max_length else combined


def prepare_conversation_text_for_embedding(
    heard_text: Optional[str] = None,
    response_text: Optional[str] = None,
    speaker: Optional[str] = None,
    max_length: int = 2000
) -> str:
    """
    Prepare conversation content for embedding.

    Args:
        heard_text: The transcribed text that was heard
        response_text: The AI response text
        speaker: The speaker identifier
        max_length: Maximum character length for the combined text

    Returns:
        Combined text suitable for embedding
    """
    parts = []

    if speaker and speaker.strip():
        parts.append(f"Speaker: {speaker.strip()}")

    if heard_text and heard_text.strip():
        parts.append(f"Said: {heard_text.strip()}")

    if response_text and response_text.strip():
        parts.append(f"Response: {response_text.strip()[:500]}")

    combined = " ".join(parts)
    return combined[:max_length] if len(combined) > max_length else combined


class EmbeddingService:
    """Service class for managing embeddings with database integration."""

    def __init__(self, db_session):
        self.db = db_session

    async def generate_conversation_embedding(self, conversation_id: int) -> Optional[List[float]]:
        """
        Generate and store embedding for a single conversation.

        Args:
            conversation_id: ID of the conversation

        Returns:
            The generated embedding vector or None on error
        """
        from models import Conversation

        conversation = self.db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()

        if not conversation:
            logger.warning(f"Conversation {conversation_id} not found")
            return None

        # Prepare text for embedding
        text = prepare_conversation_text_for_embedding(
            heard_text=conversation.heard_text,
            response_text=conversation.response_text,
            speaker=conversation.speaker
        )

        if not text:
            logger.warning(f"No text to embed for conversation {conversation_id}")
            return None

        # Generate embedding
        embedding = generate_embedding(text)

        if embedding:
            # Store the embedding
            conversation.embedding = embedding
            self.db.commit()
            logger.info(f"Generated and stored embedding for conversation {conversation_id}")

            # Invalidate cached similar conversations for this conversation
            cache.delete_pattern(f"semantic:similar_conversations:{conversation_id}:*")

        return embedding

    async def generate_conversation_embeddings_batch(
        self,
        conversation_ids: List[int]
    ) -> Dict[str, int]:
        """
        Generate embeddings for multiple conversations efficiently.

        Args:
            conversation_ids: List of conversation IDs

        Returns:
            Dict with counts of processed, skipped, and failed conversations
        """
        from models import Conversation

        conversations = self.db.query(Conversation).filter(
            Conversation.id.in_(conversation_ids)
        ).all()

        stats = {"processed": 0, "skipped": 0, "failed": 0}

        # Prepare texts for batch processing
        texts = []
        valid_conversations = []

        for conv in conversations:
            text = prepare_conversation_text_for_embedding(
                heard_text=conv.heard_text,
                response_text=conv.response_text,
                speaker=conv.speaker
            )
            if text:
                texts.append(text)
                valid_conversations.append(conv)
            else:
                stats["skipped"] += 1

        if not texts:
            return stats

        # Generate embeddings in batch
        try:
            embeddings = generate_embeddings_batch(texts)

            for conv, embedding in zip(valid_conversations, embeddings):
                if embedding:
                    conv.embedding = embedding
                    stats["processed"] += 1
                else:
                    stats["failed"] += 1

            self.db.commit()
            logger.info(f"Batch generated embeddings for {stats['processed']} conversations")

        except Exception as e:
            logger.error(f"Batch embedding generation failed: {e}")
            stats["failed"] = len(valid_conversations)

        return stats

    async def generate_embeddings_for_meeting_conversations(
        self,
        meeting_id: int,
        force_regenerate: bool = False
    ) -> Dict[str, int]:
        """
        Generate embeddings for all conversations in a meeting.

        Args:
            meeting_id: Meeting ID
            force_regenerate: If True, regenerate even if embedding exists

        Returns:
            Dict with counts of processed, skipped, and failed conversations
        """
        from models import Conversation

        query = self.db.query(Conversation).filter(
            Conversation.meeting_id == meeting_id
        )

        if not force_regenerate:
            query = query.filter(Conversation.embedding.is_(None))

        conversations = query.all()

        if not conversations:
            return {"processed": 0, "skipped": 0, "failed": 0}

        conversation_ids = [c.id for c in conversations]
        return await self.generate_conversation_embeddings_batch(conversation_ids)

    async def generate_meeting_embedding(self, meeting_id: int) -> Optional[List[float]]:
        """
        Generate and store embedding for a meeting.

        Args:
            meeting_id: ID of the meeting

        Returns:
            The generated embedding vector or None on error
        """
        from models import Meeting, Conversation

        meeting = self.db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            logger.warning(f"Meeting {meeting_id} not found")
            return None

        # Get conversation texts
        conversations = self.db.query(Conversation).filter(
            Conversation.meeting_id == meeting_id
        ).order_by(Conversation.timestamp).all()

        transcript_texts = [c.heard_text for c in conversations if c.heard_text]

        # Prepare text for embedding
        text = prepare_meeting_text_for_embedding(
            title=meeting.title,
            notes=meeting.notes,
            transcript_texts=transcript_texts
        )

        if not text:
            logger.warning(f"No text to embed for meeting {meeting_id}")
            return None

        # Generate embedding
        embedding = generate_embedding(text)

        if embedding:
            # Store the embedding
            meeting.embedding = embedding
            self.db.commit()
            logger.info(f"Generated and stored embedding for meeting {meeting_id}")

            # Invalidate cached similar meetings for this meeting
            cache.delete_pattern(f"semantic:similar_meetings:{meeting_id}:*")
            # Invalidate user's semantic search cache
            cache.delete_pattern(f"semantic:search:{meeting.user_id}:*")
            # Invalidate semantic status cache
            cache.delete(CacheKeys.semantic_search_status(meeting.user_id))

        return embedding

    async def generate_embeddings_for_user_meetings(
        self,
        user_id: int,
        force_regenerate: bool = False
    ) -> Dict[str, int]:
        """
        Generate embeddings for all meetings of a user.

        Args:
            user_id: User ID
            force_regenerate: If True, regenerate even if embedding exists

        Returns:
            Dict with counts of processed, skipped, and failed meetings
        """
        from models import Meeting

        query = self.db.query(Meeting).filter(Meeting.user_id == user_id)

        if not force_regenerate:
            # Only process meetings without embeddings
            query = query.filter(Meeting.embedding.is_(None))

        meetings = query.all()

        stats = {"processed": 0, "skipped": 0, "failed": 0}

        for meeting in meetings:
            try:
                embedding = await self.generate_meeting_embedding(meeting.id)
                if embedding:
                    stats["processed"] += 1
                else:
                    stats["skipped"] += 1
            except Exception as e:
                logger.error(f"Failed to generate embedding for meeting {meeting.id}: {e}")
                stats["failed"] += 1

        return stats

    async def generate_embeddings_for_user_conversations(
        self,
        user_id: int,
        force_regenerate: bool = False
    ) -> Dict[str, int]:
        """
        Generate embeddings for all conversations of a user.

        Args:
            user_id: User ID
            force_regenerate: If True, regenerate even if embedding exists

        Returns:
            Dict with counts of processed, skipped, and failed conversations
        """
        from models import Meeting, Conversation

        # Get all meeting IDs for this user
        meeting_ids = [
            m.id for m in self.db.query(Meeting.id).filter(
                Meeting.user_id == user_id
            ).all()
        ]

        if not meeting_ids:
            return {"processed": 0, "skipped": 0, "failed": 0}

        # Get conversations
        query = self.db.query(Conversation).filter(
            Conversation.meeting_id.in_(meeting_ids)
        )

        if not force_regenerate:
            query = query.filter(Conversation.embedding.is_(None))

        conversations = query.all()

        if not conversations:
            return {"processed": 0, "skipped": 0, "failed": 0}

        conversation_ids = [c.id for c in conversations]
        return await self.generate_conversation_embeddings_batch(conversation_ids)

    async def find_similar_conversations(
        self,
        conversation_id: int,
        user_id: int,
        limit: int = 10,
        min_similarity: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Find conversations similar to a given conversation.

        Args:
            conversation_id: ID of the reference conversation
            user_id: User ID for authorization
            limit: Maximum number of similar conversations to return
            min_similarity: Minimum similarity threshold (0-1)

        Returns:
            List of similar conversations with similarity scores
        """
        from models import Meeting, Conversation

        # Get the reference conversation
        reference = self.db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()

        if not reference:
            logger.warning(f"Conversation {conversation_id} not found")
            return []

        if not reference.embedding:
            logger.warning(f"Conversation {conversation_id} has no embedding")
            return []

        # Verify user owns the meeting containing this conversation
        meeting = self.db.query(Meeting).filter(
            Meeting.id == reference.meeting_id,
            Meeting.user_id == user_id
        ).first()

        if not meeting:
            logger.warning(f"Meeting not found or not owned by user {user_id}")
            return []

        # Get all user's meeting IDs
        meeting_ids = [
            m.id for m in self.db.query(Meeting.id).filter(
                Meeting.user_id == user_id
            ).all()
        ]

        # Get all conversations with embeddings (excluding reference)
        conversations = self.db.query(Conversation).filter(
            Conversation.meeting_id.in_(meeting_ids),
            Conversation.id != conversation_id,
            Conversation.embedding.isnot(None)
        ).all()

        # Compute similarities
        results = []
        for conv in conversations:
            if conv.embedding:
                similarity = compute_similarity(reference.embedding, conv.embedding)
                if similarity >= min_similarity:
                    results.append({
                        "id": conv.id,
                        "meeting_id": conv.meeting_id,
                        "heard_text": conv.heard_text[:500] if conv.heard_text else None,
                        "response_text": conv.response_text[:500] if conv.response_text else None,
                        "timestamp": conv.timestamp.isoformat() if conv.timestamp else None,
                        "speaker": conv.speaker,
                        "similarity_score": round(similarity, 4)
                    })

        # Sort by similarity and limit
        results.sort(key=lambda x: x["similarity_score"], reverse=True)
        return results[:limit]
