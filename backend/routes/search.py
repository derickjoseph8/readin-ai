"""Search API endpoints with full-text search support."""

from datetime import datetime, date
from typing import List, Optional
from enum import Enum

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_, and_, func
from sqlalchemy.orm import Session

from database import get_db
from models import User, Meeting, Conversation, ActionItem, Topic
from auth import get_current_user
from pagination import PaginationParams, paginate, PaginatedResponse

router = APIRouter(prefix="/search", tags=["Search"])


# =============================================================================
# SCHEMAS
# =============================================================================

class SearchScope(str, Enum):
    """Search scope options."""
    ALL = "all"
    MEETINGS = "meetings"
    CONVERSATIONS = "conversations"
    TASKS = "tasks"
    TOPICS = "topics"


class MeetingSearchResult(BaseModel):
    """Meeting search result."""
    id: int
    title: Optional[str]
    meeting_type: str
    meeting_app: Optional[str]
    started_at: Optional[datetime]
    status: str
    match_type: str  # title, notes, conversation
    snippet: Optional[str] = None

    class Config:
        from_attributes = True


class ConversationSearchResult(BaseModel):
    """Conversation search result."""
    id: int
    meeting_id: int
    meeting_title: Optional[str]
    heard_text: str
    response_text: Optional[str]
    timestamp: Optional[datetime]
    snippet: Optional[str] = None

    class Config:
        from_attributes = True


class TaskSearchResult(BaseModel):
    """Task/action item search result."""
    id: int
    meeting_id: int
    description: str
    assignee: str
    status: str
    due_date: Optional[datetime]
    snippet: Optional[str] = None

    class Config:
        from_attributes = True


class SearchResponse(BaseModel):
    """Combined search response."""
    query: str
    total_results: int
    meetings: List[MeetingSearchResult] = []
    conversations: List[ConversationSearchResult] = []
    tasks: List[TaskSearchResult] = []


# =============================================================================
# SEARCH ENDPOINTS
# =============================================================================

@router.get("", response_model=SearchResponse)
def search(
    q: str = Query(..., min_length=2, max_length=200, description="Search query"),
    scope: SearchScope = Query(default=SearchScope.ALL, description="Search scope"),
    meeting_type: Optional[str] = Query(default=None, description="Filter by meeting type"),
    date_from: Optional[date] = Query(default=None, description="Filter from date"),
    date_to: Optional[date] = Query(default=None, description="Filter to date"),
    status: Optional[str] = Query(default=None, description="Filter by status"),
    limit: int = Query(default=20, ge=1, le=100, description="Results per category"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Search across meetings, conversations, and tasks.

    Supports:
    - Full-text search in titles, notes, and transcript text
    - Filtering by date range, meeting type, and status
    - Scoped search (all, meetings, conversations, tasks)
    """
    results = SearchResponse(query=q, total_results=0)
    search_term = f"%{q.lower()}%"

    # Search meetings
    if scope in [SearchScope.ALL, SearchScope.MEETINGS]:
        meeting_query = db.query(Meeting).filter(
            Meeting.user_id == user.id,
            or_(
                func.lower(Meeting.title).like(search_term),
                func.lower(Meeting.notes).like(search_term),
            )
        )

        # Apply filters
        if meeting_type:
            meeting_query = meeting_query.filter(Meeting.meeting_type == meeting_type)
        if date_from:
            meeting_query = meeting_query.filter(Meeting.started_at >= datetime.combine(date_from, datetime.min.time()))
        if date_to:
            meeting_query = meeting_query.filter(Meeting.started_at <= datetime.combine(date_to, datetime.max.time()))
        if status:
            meeting_query = meeting_query.filter(Meeting.status == status)

        meetings = meeting_query.order_by(Meeting.started_at.desc()).limit(limit).all()

        for m in meetings:
            match_type = "title" if m.title and q.lower() in m.title.lower() else "notes"
            snippet = None
            if m.notes and q.lower() in m.notes.lower():
                # Extract snippet around match
                idx = m.notes.lower().find(q.lower())
                start = max(0, idx - 50)
                end = min(len(m.notes), idx + len(q) + 50)
                snippet = "..." + m.notes[start:end] + "..."

            results.meetings.append(MeetingSearchResult(
                id=m.id,
                title=m.title,
                meeting_type=m.meeting_type,
                meeting_app=m.meeting_app,
                started_at=m.started_at,
                status=m.status,
                match_type=match_type,
                snippet=snippet,
            ))

    # Search conversations
    if scope in [SearchScope.ALL, SearchScope.CONVERSATIONS]:
        conv_query = db.query(Conversation).join(Meeting).filter(
            Meeting.user_id == user.id,
            or_(
                func.lower(Conversation.heard_text).like(search_term),
                func.lower(Conversation.response_text).like(search_term),
            )
        )

        # Apply date filters via meeting
        if date_from:
            conv_query = conv_query.filter(Meeting.started_at >= datetime.combine(date_from, datetime.min.time()))
        if date_to:
            conv_query = conv_query.filter(Meeting.started_at <= datetime.combine(date_to, datetime.max.time()))

        conversations = conv_query.order_by(Conversation.timestamp.desc()).limit(limit).all()

        for c in conversations:
            # Create snippet
            text = c.heard_text or c.response_text or ""
            if q.lower() in text.lower():
                idx = text.lower().find(q.lower())
                start = max(0, idx - 50)
                end = min(len(text), idx + len(q) + 50)
                snippet = "..." + text[start:end] + "..."
            else:
                snippet = text[:100] + "..." if len(text) > 100 else text

            results.conversations.append(ConversationSearchResult(
                id=c.id,
                meeting_id=c.meeting_id,
                meeting_title=c.meeting.title if c.meeting else None,
                heard_text=c.heard_text[:200] if c.heard_text else "",
                response_text=c.response_text[:200] if c.response_text else None,
                timestamp=c.timestamp,
                snippet=snippet,
            ))

    # Search tasks
    if scope in [SearchScope.ALL, SearchScope.TASKS]:
        task_query = db.query(ActionItem).filter(
            ActionItem.user_id == user.id,
            func.lower(ActionItem.description).like(search_term),
        )

        if status:
            task_query = task_query.filter(ActionItem.status == status)

        tasks = task_query.order_by(ActionItem.created_at.desc()).limit(limit).all()

        for t in tasks:
            snippet = None
            if q.lower() in t.description.lower():
                idx = t.description.lower().find(q.lower())
                start = max(0, idx - 50)
                end = min(len(t.description), idx + len(q) + 50)
                snippet = "..." + t.description[start:end] + "..."

            results.tasks.append(TaskSearchResult(
                id=t.id,
                meeting_id=t.meeting_id,
                description=t.description[:200],
                assignee=t.assignee,
                status=t.status,
                due_date=t.due_date,
                snippet=snippet,
            ))

    results.total_results = len(results.meetings) + len(results.conversations) + len(results.tasks)

    return results


@router.get("/meetings")
def search_meetings(
    q: str = Query(..., min_length=2, max_length=200),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    meeting_type: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Search meetings with pagination.
    """
    search_term = f"%{q.lower()}%"

    query = db.query(Meeting).filter(
        Meeting.user_id == user.id,
        or_(
            func.lower(Meeting.title).like(search_term),
            func.lower(Meeting.notes).like(search_term),
        )
    )

    if meeting_type:
        query = query.filter(Meeting.meeting_type == meeting_type)
    if date_from:
        query = query.filter(Meeting.started_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        query = query.filter(Meeting.started_at <= datetime.combine(date_to, datetime.max.time()))

    # Get total count
    total = query.count()

    # Get page
    offset = (page - 1) * page_size
    meetings = query.order_by(Meeting.started_at.desc()).offset(offset).limit(page_size).all()

    items = [
        MeetingSearchResult(
            id=m.id,
            title=m.title,
            meeting_type=m.meeting_type,
            meeting_app=m.meeting_app,
            started_at=m.started_at,
            status=m.status,
            match_type="title" if m.title and q.lower() in m.title.lower() else "notes",
        )
        for m in meetings
    ]

    return paginate(items, page, page_size, total)


@router.get("/topics")
def search_topics(
    q: str = Query(..., min_length=2, max_length=100),
    limit: int = Query(default=20, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Search user's discussion topics.
    """
    search_term = f"%{q.lower()}%"

    topics = db.query(Topic).filter(
        Topic.user_id == user.id,
        func.lower(Topic.name).like(search_term),
    ).order_by(Topic.frequency.desc()).limit(limit).all()

    return {
        "query": q,
        "topics": [
            {
                "id": t.id,
                "name": t.name,
                "category": t.category,
                "frequency": t.frequency,
                "last_discussed": t.last_discussed.isoformat() if t.last_discussed else None,
            }
            for t in topics
        ],
    }


@router.get("/suggestions")
def search_suggestions(
    q: str = Query(..., min_length=1, max_length=50),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get search suggestions based on partial query.

    Returns suggestions from:
    - Recent meeting titles
    - Frequent topics
    """
    search_term = f"{q.lower()}%"  # Prefix match

    suggestions = []

    # Recent meeting titles
    meeting_titles = db.query(Meeting.title).filter(
        Meeting.user_id == user.id,
        func.lower(Meeting.title).like(search_term),
        Meeting.title.isnot(None),
    ).distinct().limit(5).all()

    for (title,) in meeting_titles:
        if title:
            suggestions.append({"type": "meeting", "value": title})

    # Frequent topics
    topics = db.query(Topic.name).filter(
        Topic.user_id == user.id,
        func.lower(Topic.name).like(search_term),
    ).order_by(Topic.frequency.desc()).limit(5).all()

    for (name,) in topics:
        suggestions.append({"type": "topic", "value": name})

    return {
        "query": q,
        "suggestions": suggestions[:10],  # Limit total suggestions
    }
