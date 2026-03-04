"""Semantic Search API endpoints using embeddings and pgvector."""

import logging
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models import User, Meeting
from auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search/semantic", tags=["Semantic Search"])


# =============================================================================
# SCHEMAS
# =============================================================================

class SemanticSearchResult(BaseModel):
    """Single semantic search result."""
    id: int
    title: Optional[str]
    meeting_type: str
    meeting_app: Optional[str]
    started_at: Optional[str]
    ended_at: Optional[str]
    status: str
    notes_preview: Optional[str]
    participant_count: Optional[int]
    similarity_score: float

    class Config:
        from_attributes = True


class SemanticSearchResponse(BaseModel):
    """Semantic search response."""
    query: str
    total_results: int
    results: List[SemanticSearchResult]
    search_mode: str = Field(description="'pgvector' or 'fallback'")


class SimilarMeetingResult(BaseModel):
    """Similar meeting result."""
    id: int
    title: Optional[str]
    meeting_type: str
    meeting_app: Optional[str]
    started_at: Optional[str]
    status: str
    similarity_score: float


class SimilarMeetingsResponse(BaseModel):
    """Response for similar meetings."""
    reference_meeting_id: int
    similar_meetings: List[SimilarMeetingResult]


class EmbeddingGenerationResponse(BaseModel):
    """Response for embedding generation."""
    processed: int
    skipped: int
    failed: int
    message: str


class ConversationSearchResult(BaseModel):
    """Conversation search result."""
    id: int
    meeting_id: int
    heard_text: Optional[str]
    response_text: Optional[str]
    timestamp: Optional[str]
    speaker: Optional[str]
    similarity_score: float


class ConversationSearchResponse(BaseModel):
    """Response for conversation semantic search."""
    query: str
    total_results: int
    results: List[ConversationSearchResult]


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("", response_model=SemanticSearchResponse)
async def semantic_search(
    q: str = Query(..., min_length=2, max_length=500, description="Search query"),
    limit: int = Query(default=10, ge=1, le=50, description="Maximum results"),
    meeting_type: Optional[str] = Query(default=None, description="Filter by meeting type"),
    date_from: Optional[date] = Query(default=None, description="Filter from date"),
    date_to: Optional[date] = Query(default=None, description="Filter to date"),
    min_similarity: float = Query(default=0.3, ge=0.0, le=1.0, description="Minimum similarity score"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Perform semantic search on meetings using AI embeddings.

    This endpoint uses sentence transformer embeddings to find meetings
    semantically similar to the query, even if they don't contain
    the exact search terms.

    Example queries:
    - "discussions about quarterly targets"
    - "meetings with product team about new features"
    - "conversations about customer complaints"
    """
    from services.semantic_search_service import SemanticSearchService

    search_service = SemanticSearchService(db)

    try:
        results = await search_service.semantic_search(
            query=q,
            user_id=user.id,
            limit=limit,
            meeting_type=meeting_type,
            date_from=date_from,
            date_to=date_to,
            min_similarity=min_similarity
        )

        # Determine search mode
        search_mode = "pgvector" if search_service._is_pgvector_available() else "fallback"

        return SemanticSearchResponse(
            query=q,
            total_results=len(results),
            results=[SemanticSearchResult(**r) for r in results],
            search_mode=search_mode
        )

    except Exception as e:
        logger.error(f"Semantic search error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to perform semantic search"
        )


@router.get("/conversations", response_model=ConversationSearchResponse)
async def search_conversations(
    q: str = Query(..., min_length=2, max_length=500, description="Search query"),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum results"),
    meeting_id: Optional[int] = Query(default=None, description="Filter to specific meeting"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Semantic search on conversation content.

    Searches through meeting transcripts to find relevant discussions.
    """
    from services.semantic_search_service import SemanticSearchService

    search_service = SemanticSearchService(db)

    try:
        results = await search_service.search_conversations(
            query=q,
            user_id=user.id,
            limit=limit,
            meeting_id=meeting_id
        )

        return ConversationSearchResponse(
            query=q,
            total_results=len(results),
            results=[ConversationSearchResult(**r) for r in results]
        )

    except Exception as e:
        logger.error(f"Conversation search error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to search conversations"
        )


@router.get("/meetings/{meeting_id}/similar", response_model=SimilarMeetingsResponse)
async def get_similar_meetings(
    meeting_id: int,
    limit: int = Query(default=5, ge=1, le=20, description="Maximum similar meetings"),
    exclude_same_type: bool = Query(default=False, description="Exclude same meeting type"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Find meetings similar to a given meeting.

    Uses embedding similarity to find other meetings with similar content
    or discussion topics.
    """
    from services.semantic_search_service import SemanticSearchService

    # Verify meeting exists and belongs to user
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.user_id == user.id
    ).first()

    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if not meeting.embedding:
        raise HTTPException(
            status_code=400,
            detail="Meeting has no embedding. Generate embeddings first using POST /search/semantic/embeddings/generate"
        )

    search_service = SemanticSearchService(db)

    try:
        similar = await search_service.find_similar_meetings(
            meeting_id=meeting_id,
            user_id=user.id,
            limit=limit,
            exclude_same_type=exclude_same_type
        )

        return SimilarMeetingsResponse(
            reference_meeting_id=meeting_id,
            similar_meetings=[SimilarMeetingResult(**m) for m in similar]
        )

    except Exception as e:
        logger.error(f"Similar meetings error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to find similar meetings"
        )


@router.post("/embeddings/generate", response_model=EmbeddingGenerationResponse)
async def generate_embeddings(
    background_tasks: BackgroundTasks,
    force_regenerate: bool = Query(default=False, description="Regenerate existing embeddings"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate embeddings for user's meetings.

    This is typically run once to backfill embeddings for existing meetings.
    New meetings automatically get embeddings when they end.

    Note: This runs in the background and returns immediately.
    """
    from services.embedding_service import EmbeddingService

    embedding_service = EmbeddingService(db)

    # Count meetings needing embeddings
    query = db.query(Meeting).filter(Meeting.user_id == user.id)
    if not force_regenerate:
        query = query.filter(Meeting.embedding.is_(None))
    count = query.count()

    if count == 0:
        return EmbeddingGenerationResponse(
            processed=0,
            skipped=0,
            failed=0,
            message="All meetings already have embeddings"
        )

    # For small number of meetings, process synchronously
    if count <= 10:
        try:
            stats = await embedding_service.generate_embeddings_for_user_meetings(
                user_id=user.id,
                force_regenerate=force_regenerate
            )
            return EmbeddingGenerationResponse(
                processed=stats["processed"],
                skipped=stats["skipped"],
                failed=stats["failed"],
                message=f"Generated embeddings for {stats['processed']} meetings"
            )
        except Exception as e:
            logger.error(f"Embedding generation error: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to generate embeddings"
            )
    else:
        # For larger datasets, run in background
        async def generate_in_background():
            try:
                await embedding_service.generate_embeddings_for_user_meetings(
                    user_id=user.id,
                    force_regenerate=force_regenerate
                )
            except Exception as e:
                logger.error(f"Background embedding generation error: {e}")

        background_tasks.add_task(generate_in_background)

        return EmbeddingGenerationResponse(
            processed=0,
            skipped=0,
            failed=0,
            message=f"Generating embeddings for {count} meetings in background. This may take a few minutes."
        )


@router.post("/meetings/{meeting_id}/embedding", response_model=dict)
async def generate_meeting_embedding(
    meeting_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate or regenerate embedding for a specific meeting.
    """
    from services.embedding_service import EmbeddingService

    # Verify meeting exists and belongs to user
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.user_id == user.id
    ).first()

    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    embedding_service = EmbeddingService(db)

    try:
        embedding = await embedding_service.generate_meeting_embedding(meeting_id)

        if embedding:
            return {
                "meeting_id": meeting_id,
                "embedding_generated": True,
                "embedding_dimension": len(embedding)
            }
        else:
            return {
                "meeting_id": meeting_id,
                "embedding_generated": False,
                "message": "No content to generate embedding from"
            }

    except Exception as e:
        logger.error(f"Meeting embedding generation error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate meeting embedding"
        )


@router.get("/status")
async def get_semantic_search_status(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get status of semantic search capabilities.

    Returns information about:
    - Whether pgvector is available
    - Number of meetings with/without embeddings
    - Embedding model info
    """
    from services.semantic_search_service import SemanticSearchService
    from services.embedding_service import get_embedding_dimension, EMBEDDING_MODEL_NAME

    search_service = SemanticSearchService(db)

    # Count meetings
    total_meetings = db.query(Meeting).filter(Meeting.user_id == user.id).count()
    meetings_with_embeddings = db.query(Meeting).filter(
        Meeting.user_id == user.id,
        Meeting.embedding.isnot(None)
    ).count()

    try:
        embedding_dim = get_embedding_dimension()
    except Exception:
        embedding_dim = None

    return {
        "pgvector_available": search_service._is_pgvector_available(),
        "search_mode": "pgvector" if search_service._is_pgvector_available() else "fallback",
        "embedding_model": EMBEDDING_MODEL_NAME,
        "embedding_dimension": embedding_dim,
        "total_meetings": total_meetings,
        "meetings_with_embeddings": meetings_with_embeddings,
        "meetings_without_embeddings": total_meetings - meetings_with_embeddings,
        "coverage_percentage": round(
            (meetings_with_embeddings / total_meetings * 100) if total_meetings > 0 else 0, 1
        )
    }
