"""Semantic Search Service using pgvector for similarity search."""

import logging
import hashlib
from typing import List, Optional, Dict, Any
from datetime import datetime, date

from sqlalchemy import text, and_, or_
from sqlalchemy.orm import Session

from services.embedding_service import generate_embedding, compute_similarity
from services.cache_service import cache, CacheKeys, CacheTTL

logger = logging.getLogger(__name__)


def _hash_search_params(query: str, **kwargs) -> str:
    """Generate a hash for search parameters for caching."""
    params_str = f"{query}:{sorted(kwargs.items())}"
    return hashlib.md5(params_str.encode(), usedforsecurity=False).hexdigest()[:16]


class SemanticSearchService:
    """Service for semantic search across meetings and transcripts."""

    def __init__(self, db: Session):
        self.db = db

    async def semantic_search(
        self,
        query: str,
        user_id: int,
        limit: int = 10,
        meeting_type: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        min_similarity: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search on meetings using embedding similarity.

        Args:
            query: Search query text
            user_id: User ID to filter results
            limit: Maximum number of results
            meeting_type: Optional filter by meeting type
            date_from: Optional filter from date
            date_to: Optional filter to date
            min_similarity: Minimum similarity threshold (0-1)

        Returns:
            List of meetings with similarity scores
        """
        from models import Meeting, Conversation

        # Check cache first
        query_hash = _hash_search_params(
            query,
            limit=limit,
            meeting_type=meeting_type,
            date_from=str(date_from) if date_from else None,
            date_to=str(date_to) if date_to else None,
            min_similarity=min_similarity
        )
        cache_key = CacheKeys.semantic_search(user_id, query_hash)
        cached_results = cache.get(cache_key)
        if cached_results is not None:
            logger.debug(f"Semantic search cache hit for user {user_id}")
            return cached_results

        # Generate embedding for the query
        query_embedding = generate_embedding(query)

        if not query_embedding:
            logger.warning("Failed to generate query embedding")
            return []

        # Check if pgvector is available
        if self._is_pgvector_available():
            results = await self._pgvector_search(
                query_embedding=query_embedding,
                user_id=user_id,
                limit=limit,
                meeting_type=meeting_type,
                date_from=date_from,
                date_to=date_to,
                min_similarity=min_similarity
            )
        else:
            # Fallback to in-memory similarity search
            results = await self._fallback_search(
                query_embedding=query_embedding,
                user_id=user_id,
                limit=limit,
                meeting_type=meeting_type,
                date_from=date_from,
                date_to=date_to,
                min_similarity=min_similarity
            )

        # Cache results
        cache.set(cache_key, results, CacheTTL.SEMANTIC_SEARCH)

        return results

    def _is_pgvector_available(self) -> bool:
        """Check if pgvector extension is available in the database."""
        try:
            # Check if we're using PostgreSQL
            from config import DATABASE_URL
            if not DATABASE_URL.startswith("postgresql"):
                return False

            # Check if pgvector extension is installed
            result = self.db.execute(text(
                "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
            )).scalar()
            return result
        except Exception:
            return False

    async def _pgvector_search(
        self,
        query_embedding: List[float],
        user_id: int,
        limit: int,
        meeting_type: Optional[str],
        date_from: Optional[date],
        date_to: Optional[date],
        min_similarity: float
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search using pgvector's built-in functions.
        Uses L2 distance for similarity ranking.
        """
        from models import Meeting

        # Build the query with pgvector distance function
        # Lower distance = more similar, so we use ORDER BY ASC
        embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

        # Base query with vector similarity
        sql = text("""
            SELECT
                m.id,
                m.title,
                m.meeting_type,
                m.meeting_app,
                m.started_at,
                m.ended_at,
                m.status,
                m.notes,
                m.participant_count,
                1 - (m.embedding <=> :embedding::vector) as similarity
            FROM meetings m
            WHERE m.user_id = :user_id
                AND m.embedding IS NOT NULL
                AND 1 - (m.embedding <=> :embedding::vector) >= :min_similarity
                {type_filter}
                {date_from_filter}
                {date_to_filter}
            ORDER BY m.embedding <=> :embedding::vector
            LIMIT :limit
        """.format(
            type_filter="AND m.meeting_type = :meeting_type" if meeting_type else "",
            date_from_filter="AND m.started_at >= :date_from" if date_from else "",
            date_to_filter="AND m.started_at <= :date_to" if date_to else ""
        ))

        params = {
            "embedding": embedding_str,
            "user_id": user_id,
            "limit": limit,
            "min_similarity": min_similarity
        }

        if meeting_type:
            params["meeting_type"] = meeting_type
        if date_from:
            params["date_from"] = datetime.combine(date_from, datetime.min.time())
        if date_to:
            params["date_to"] = datetime.combine(date_to, datetime.max.time())

        try:
            result = self.db.execute(sql, params)
            rows = result.fetchall()

            meetings = []
            for row in rows:
                meetings.append({
                    "id": row.id,
                    "title": row.title,
                    "meeting_type": row.meeting_type,
                    "meeting_app": row.meeting_app,
                    "started_at": row.started_at.isoformat() if row.started_at else None,
                    "ended_at": row.ended_at.isoformat() if row.ended_at else None,
                    "status": row.status,
                    "notes_preview": row.notes[:200] + "..." if row.notes and len(row.notes) > 200 else row.notes,
                    "participant_count": row.participant_count,
                    "similarity_score": round(float(row.similarity), 4)
                })

            return meetings

        except Exception as e:
            logger.error(f"pgvector search error: {e}")
            # Fall back to in-memory search
            return await self._fallback_search(
                query_embedding, user_id, limit, meeting_type, date_from, date_to, min_similarity
            )

    async def _fallback_search(
        self,
        query_embedding: List[float],
        user_id: int,
        limit: int,
        meeting_type: Optional[str],
        date_from: Optional[date],
        date_to: Optional[date],
        min_similarity: float
    ) -> List[Dict[str, Any]]:
        """
        Fallback in-memory similarity search when pgvector is not available.
        Less efficient but works with any database.
        """
        from models import Meeting

        # Build query
        query = self.db.query(Meeting).filter(
            Meeting.user_id == user_id,
            Meeting.embedding.isnot(None)
        )

        if meeting_type:
            query = query.filter(Meeting.meeting_type == meeting_type)
        if date_from:
            query = query.filter(Meeting.started_at >= datetime.combine(date_from, datetime.min.time()))
        if date_to:
            query = query.filter(Meeting.started_at <= datetime.combine(date_to, datetime.max.time()))

        meetings = query.all()

        # Compute similarities in memory
        results = []
        for meeting in meetings:
            if meeting.embedding:
                similarity = compute_similarity(query_embedding, meeting.embedding)
                if similarity >= min_similarity:
                    results.append({
                        "id": meeting.id,
                        "title": meeting.title,
                        "meeting_type": meeting.meeting_type,
                        "meeting_app": meeting.meeting_app,
                        "started_at": meeting.started_at.isoformat() if meeting.started_at else None,
                        "ended_at": meeting.ended_at.isoformat() if meeting.ended_at else None,
                        "status": meeting.status,
                        "notes_preview": meeting.notes[:200] + "..." if meeting.notes and len(meeting.notes) > 200 else meeting.notes,
                        "participant_count": meeting.participant_count,
                        "similarity_score": round(similarity, 4)
                    })

        # Sort by similarity (descending) and limit
        results.sort(key=lambda x: x["similarity_score"], reverse=True)
        return results[:limit]

    async def find_similar_meetings(
        self,
        meeting_id: int,
        user_id: int,
        limit: int = 5,
        exclude_same_type: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Find meetings similar to a given meeting.

        Args:
            meeting_id: ID of the reference meeting
            user_id: User ID for authorization
            limit: Maximum number of similar meetings to return
            exclude_same_type: If True, exclude meetings of the same type

        Returns:
            List of similar meetings with similarity scores
        """
        from models import Meeting

        # Check cache first
        cache_key = f"{CacheKeys.similar_meetings(meeting_id)}:{limit}:{exclude_same_type}"
        cached_results = cache.get(cache_key)
        if cached_results is not None:
            logger.debug(f"Similar meetings cache hit for meeting {meeting_id}")
            return cached_results

        # Get the reference meeting
        reference = self.db.query(Meeting).filter(
            Meeting.id == meeting_id,
            Meeting.user_id == user_id
        ).first()

        if not reference:
            logger.warning(f"Meeting {meeting_id} not found for user {user_id}")
            return []

        if not reference.embedding:
            logger.warning(f"Meeting {meeting_id} has no embedding")
            return []

        # Search for similar meetings
        if self._is_pgvector_available():
            results = await self._pgvector_similar_meetings(
                reference_embedding=reference.embedding,
                reference_id=meeting_id,
                reference_type=reference.meeting_type if exclude_same_type else None,
                user_id=user_id,
                limit=limit
            )
        else:
            results = await self._fallback_similar_meetings(
                reference_embedding=reference.embedding,
                reference_id=meeting_id,
                reference_type=reference.meeting_type if exclude_same_type else None,
                user_id=user_id,
                limit=limit
            )

        # Cache results
        cache.set(cache_key, results, CacheTTL.SIMILAR_ITEMS)

        return results

    async def _pgvector_similar_meetings(
        self,
        reference_embedding: List[float],
        reference_id: int,
        reference_type: Optional[str],
        user_id: int,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Find similar meetings using pgvector."""
        embedding_str = "[" + ",".join(str(x) for x in reference_embedding) + "]"

        sql = text("""
            SELECT
                m.id,
                m.title,
                m.meeting_type,
                m.meeting_app,
                m.started_at,
                m.status,
                1 - (m.embedding <=> :embedding::vector) as similarity
            FROM meetings m
            WHERE m.user_id = :user_id
                AND m.id != :reference_id
                AND m.embedding IS NOT NULL
                {type_filter}
            ORDER BY m.embedding <=> :embedding::vector
            LIMIT :limit
        """.format(
            type_filter="AND m.meeting_type != :reference_type" if reference_type else ""
        ))

        params = {
            "embedding": embedding_str,
            "user_id": user_id,
            "reference_id": reference_id,
            "limit": limit
        }

        if reference_type:
            params["reference_type"] = reference_type

        try:
            result = self.db.execute(sql, params)
            rows = result.fetchall()

            return [
                {
                    "id": row.id,
                    "title": row.title,
                    "meeting_type": row.meeting_type,
                    "meeting_app": row.meeting_app,
                    "started_at": row.started_at.isoformat() if row.started_at else None,
                    "status": row.status,
                    "similarity_score": round(float(row.similarity), 4)
                }
                for row in rows
            ]
        except Exception as e:
            logger.error(f"pgvector similar meetings error: {e}")
            return await self._fallback_similar_meetings(
                reference_embedding, reference_id, reference_type, user_id, limit
            )

    async def _fallback_similar_meetings(
        self,
        reference_embedding: List[float],
        reference_id: int,
        reference_type: Optional[str],
        user_id: int,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Fallback for finding similar meetings without pgvector."""
        from models import Meeting

        query = self.db.query(Meeting).filter(
            Meeting.user_id == user_id,
            Meeting.id != reference_id,
            Meeting.embedding.isnot(None)
        )

        if reference_type:
            query = query.filter(Meeting.meeting_type != reference_type)

        meetings = query.all()

        results = []
        for meeting in meetings:
            if meeting.embedding:
                similarity = compute_similarity(reference_embedding, meeting.embedding)
                results.append({
                    "id": meeting.id,
                    "title": meeting.title,
                    "meeting_type": meeting.meeting_type,
                    "meeting_app": meeting.meeting_app,
                    "started_at": meeting.started_at.isoformat() if meeting.started_at else None,
                    "status": meeting.status,
                    "similarity_score": round(similarity, 4)
                })

        results.sort(key=lambda x: x["similarity_score"], reverse=True)
        return results[:limit]

    async def search_conversations(
        self,
        query: str,
        user_id: int,
        limit: int = 20,
        meeting_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Search conversations semantically.

        Args:
            query: Search query
            user_id: User ID
            limit: Maximum results
            meeting_id: Optional filter to specific meeting

        Returns:
            List of matching conversations with similarity scores
        """
        from models import Meeting, Conversation

        query_embedding = generate_embedding(query)
        if not query_embedding:
            return []

        # Get meetings for user (optionally filtered)
        meeting_query = self.db.query(Meeting).filter(Meeting.user_id == user_id)
        if meeting_id:
            meeting_query = meeting_query.filter(Meeting.id == meeting_id)

        meeting_ids = [m.id for m in meeting_query.all()]

        if not meeting_ids:
            return []

        # Get conversations with embeddings
        conversations = self.db.query(Conversation).filter(
            Conversation.meeting_id.in_(meeting_ids),
            Conversation.embedding.isnot(None)
        ).all()

        # Compute similarities
        results = []
        for conv in conversations:
            if conv.embedding:
                similarity = compute_similarity(query_embedding, conv.embedding)
                if similarity >= 0.3:  # Minimum threshold
                    results.append({
                        "id": conv.id,
                        "meeting_id": conv.meeting_id,
                        "heard_text": conv.heard_text[:500] if conv.heard_text else None,
                        "response_text": conv.response_text[:500] if conv.response_text else None,
                        "timestamp": conv.timestamp.isoformat() if conv.timestamp else None,
                        "speaker": conv.speaker,
                        "similarity_score": round(similarity, 4)
                    })

        results.sort(key=lambda x: x["similarity_score"], reverse=True)
        return results[:limit]
