"""Embedding Service for semantic search using sentence-transformers."""

import os
import logging
from typing import List, Optional, Dict, Any
from functools import lru_cache

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


class EmbeddingService:
    """Service class for managing embeddings with database integration."""

    def __init__(self, db_session):
        self.db = db_session

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
