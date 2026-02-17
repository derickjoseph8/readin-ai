"""Tasks API routes - Action items and commitments management."""

from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_

from database import get_db
from models import ActionItem, Commitment, Meeting, User
from schemas import (
    ActionItemCreate, ActionItemUpdate, ActionItemResponse, ActionItemList,
    CommitmentCreate, CommitmentUpdate, CommitmentResponse, CommitmentList
)
from auth import get_current_user

router = APIRouter(prefix="/tasks", tags=["Tasks"])


# ============== Action Items ==============

@router.post("/action-items", response_model=ActionItemResponse)
def create_action_item(
    data: ActionItemCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create an action item from a meeting.
    WHO does WHAT by WHEN.
    """
    # Verify meeting
    meeting = db.query(Meeting).filter(
        Meeting.id == data.meeting_id,
        Meeting.user_id == user.id
    ).first()

    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )

    action_item = ActionItem(
        meeting_id=data.meeting_id,
        user_id=user.id,
        assignee=data.assignee,
        assignee_role=data.assignee_role,
        description=data.description,
        due_date=data.due_date,
        priority=data.priority
    )
    db.add(action_item)
    db.commit()
    db.refresh(action_item)

    return ActionItemResponse.model_validate(action_item)


@router.get("/action-items", response_model=ActionItemList)
def list_action_items(
    status_filter: Optional[str] = None,
    assignee_role: Optional[str] = None,
    priority: Optional[str] = None,
    meeting_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List action items with filters."""
    query = db.query(ActionItem).filter(ActionItem.user_id == user.id)

    if status_filter:
        query = query.filter(ActionItem.status == status_filter)
    if assignee_role:
        query = query.filter(ActionItem.assignee_role == assignee_role)
    if priority:
        query = query.filter(ActionItem.priority == priority)
    if meeting_id:
        query = query.filter(ActionItem.meeting_id == meeting_id)

    total = query.count()
    action_items = query.order_by(
        ActionItem.due_date.asc().nullslast(),
        desc(ActionItem.created_at)
    ).offset(skip).limit(limit).all()

    # Count by status
    pending_count = db.query(ActionItem).filter(
        ActionItem.user_id == user.id,
        ActionItem.status == "pending"
    ).count()

    completed_count = db.query(ActionItem).filter(
        ActionItem.user_id == user.id,
        ActionItem.status == "completed"
    ).count()

    return ActionItemList(
        action_items=[ActionItemResponse.model_validate(a) for a in action_items],
        total=total,
        pending_count=pending_count,
        completed_count=completed_count
    )


@router.get("/action-items/{item_id}", response_model=ActionItemResponse)
def get_action_item(
    item_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific action item."""
    action_item = db.query(ActionItem).filter(
        ActionItem.id == item_id,
        ActionItem.user_id == user.id
    ).first()

    if not action_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Action item not found"
        )

    return ActionItemResponse.model_validate(action_item)


@router.patch("/action-items/{item_id}", response_model=ActionItemResponse)
def update_action_item(
    item_id: int,
    data: ActionItemUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an action item."""
    action_item = db.query(ActionItem).filter(
        ActionItem.id == item_id,
        ActionItem.user_id == user.id
    ).first()

    if not action_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Action item not found"
        )

    if data.description is not None:
        action_item.description = data.description
    if data.due_date is not None:
        action_item.due_date = data.due_date
    if data.priority is not None:
        action_item.priority = data.priority
    if data.status is not None:
        action_item.status = data.status
        if data.status == "completed":
            action_item.completed_at = datetime.utcnow()

    db.commit()
    db.refresh(action_item)

    return ActionItemResponse.model_validate(action_item)


@router.delete("/action-items/{item_id}")
def delete_action_item(
    item_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an action item."""
    action_item = db.query(ActionItem).filter(
        ActionItem.id == item_id,
        ActionItem.user_id == user.id
    ).first()

    if not action_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Action item not found"
        )

    db.delete(action_item)
    db.commit()

    return {"message": "Action item deleted"}


@router.post("/action-items/{item_id}/complete")
def complete_action_item(
    item_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark an action item as complete."""
    action_item = db.query(ActionItem).filter(
        ActionItem.id == item_id,
        ActionItem.user_id == user.id
    ).first()

    if not action_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Action item not found"
        )

    action_item.status = "completed"
    action_item.completed_at = datetime.utcnow()
    db.commit()

    return {"message": "Action item completed"}


# ============== Commitments ==============

@router.post("/commitments", response_model=CommitmentResponse)
def create_commitment(
    data: CommitmentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a commitment - something the user promised to do.
    Will trigger email reminders before due date.
    """
    # Verify meeting
    meeting = db.query(Meeting).filter(
        Meeting.id == data.meeting_id,
        Meeting.user_id == user.id
    ).first()

    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )

    # Calculate first reminder time (24h before due date)
    next_reminder = None
    if data.due_date:
        next_reminder = data.due_date - timedelta(hours=24)
        if next_reminder < datetime.utcnow():
            next_reminder = datetime.utcnow() + timedelta(hours=1)

    commitment = Commitment(
        meeting_id=data.meeting_id,
        user_id=user.id,
        description=data.description,
        due_date=data.due_date,
        context=data.context,
        next_reminder_at=next_reminder
    )
    db.add(commitment)
    db.commit()
    db.refresh(commitment)

    return CommitmentResponse.model_validate(commitment)


@router.get("/commitments", response_model=CommitmentList)
def list_commitments(
    status_filter: Optional[str] = None,
    meeting_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List user's commitments with filters."""
    query = db.query(Commitment).filter(Commitment.user_id == user.id)

    if status_filter:
        query = query.filter(Commitment.status == status_filter)
    if meeting_id:
        query = query.filter(Commitment.meeting_id == meeting_id)

    total = query.count()
    commitments = query.order_by(
        Commitment.due_date.asc().nullslast(),
        desc(Commitment.created_at)
    ).offset(skip).limit(limit).all()

    # Get upcoming (due in next 7 days)
    upcoming = db.query(Commitment).filter(
        Commitment.user_id == user.id,
        Commitment.status == "pending",
        Commitment.due_date.isnot(None),
        Commitment.due_date <= datetime.utcnow() + timedelta(days=7),
        Commitment.due_date >= datetime.utcnow()
    ).order_by(Commitment.due_date).all()

    # Get overdue
    overdue = db.query(Commitment).filter(
        Commitment.user_id == user.id,
        Commitment.status == "pending",
        Commitment.due_date.isnot(None),
        Commitment.due_date < datetime.utcnow()
    ).order_by(Commitment.due_date).all()

    return CommitmentList(
        commitments=[CommitmentResponse.model_validate(c) for c in commitments],
        total=total,
        upcoming=[CommitmentResponse.model_validate(c) for c in upcoming],
        overdue=[CommitmentResponse.model_validate(c) for c in overdue]
    )


@router.get("/commitments/upcoming", response_model=List[CommitmentResponse])
def get_upcoming_commitments(
    days: int = 7,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get commitments due within the specified number of days."""
    upcoming = db.query(Commitment).filter(
        Commitment.user_id == user.id,
        Commitment.status == "pending",
        Commitment.due_date.isnot(None),
        Commitment.due_date <= datetime.utcnow() + timedelta(days=days),
        Commitment.due_date >= datetime.utcnow()
    ).order_by(Commitment.due_date).all()

    return [CommitmentResponse.model_validate(c) for c in upcoming]


@router.get("/commitments/{commitment_id}", response_model=CommitmentResponse)
def get_commitment(
    commitment_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific commitment."""
    commitment = db.query(Commitment).filter(
        Commitment.id == commitment_id,
        Commitment.user_id == user.id
    ).first()

    if not commitment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Commitment not found"
        )

    return CommitmentResponse.model_validate(commitment)


@router.patch("/commitments/{commitment_id}", response_model=CommitmentResponse)
def update_commitment(
    commitment_id: int,
    data: CommitmentUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a commitment."""
    commitment = db.query(Commitment).filter(
        Commitment.id == commitment_id,
        Commitment.user_id == user.id
    ).first()

    if not commitment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Commitment not found"
        )

    if data.description is not None:
        commitment.description = data.description
    if data.due_date is not None:
        commitment.due_date = data.due_date
        # Recalculate reminder
        commitment.next_reminder_at = data.due_date - timedelta(hours=24)
        commitment.reminder_sent = False
    if data.status is not None:
        commitment.status = data.status
        if data.status == "completed":
            commitment.completed_at = datetime.utcnow()

    db.commit()
    db.refresh(commitment)

    return CommitmentResponse.model_validate(commitment)


@router.delete("/commitments/{commitment_id}")
def delete_commitment(
    commitment_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a commitment."""
    commitment = db.query(Commitment).filter(
        Commitment.id == commitment_id,
        Commitment.user_id == user.id
    ).first()

    if not commitment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Commitment not found"
        )

    db.delete(commitment)
    db.commit()

    return {"message": "Commitment deleted"}


@router.post("/commitments/{commitment_id}/complete")
def complete_commitment(
    commitment_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark a commitment as complete."""
    commitment = db.query(Commitment).filter(
        Commitment.id == commitment_id,
        Commitment.user_id == user.id
    ).first()

    if not commitment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Commitment not found"
        )

    commitment.status = "completed"
    commitment.completed_at = datetime.utcnow()
    db.commit()

    return {"message": "Commitment completed"}


# ============== Auto-Detection ==============

@router.post("/extract-from-meeting/{meeting_id}")
def extract_action_items_from_meeting(
    meeting_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Auto-extract action items and commitments from meeting conversations.
    Uses pattern matching to identify tasks, deadlines, and assignments.
    Returns extracted items for user review before saving.
    """
    from models import Conversation
    import re

    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.user_id == user.id
    ).first()

    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )

    # Get all conversations from the meeting
    conversations = db.query(Conversation).filter(
        Conversation.meeting_id == meeting_id
    ).order_by(Conversation.timestamp).all()

    if not conversations:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No conversations found in meeting"
        )

    extracted_items = []
    commitment_indicators = []

    # Patterns that indicate action items
    action_patterns = [
        r"(?i)(?:I'll|I will|We'll|We will|let's|let me|going to)\s+(.+?)(?:\.|$)",
        r"(?i)(?:need to|have to|should|must)\s+(.+?)(?:\.|$)",
        r"(?i)(?:action item[s]?:?\s*)(.+?)(?:\.|$)",
        r"(?i)(?:to-do[s]?:?\s*)(.+?)(?:\.|$)",
        r"(?i)(?:task:?\s*)(.+?)(?:\.|$)",
        r"(?i)(?:follow up (?:on|with)\s*)(.+?)(?:\.|$)",
    ]

    # Patterns that indicate commitments (user promises)
    commitment_patterns = [
        r"(?i)(?:I promise|I commit|I guarantee|I'll make sure)\s+(.+?)(?:\.|$)",
        r"(?i)(?:you have my word|count on me to)\s+(.+?)(?:\.|$)",
    ]

    # Deadline patterns
    deadline_patterns = [
        r"(?i)by (?:end of |)(today|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday)",
        r"(?i)by (?:end of |)(this week|next week|this month|next month)",
        r"(?i)(?:due|deadline|by) (\d{1,2}[\/\-]\d{1,2}(?:[\/\-]\d{2,4})?)",
        r"(?i)in (\d+)\s+(day|week|month|hour)s?",
    ]

    # Assignee patterns
    assignee_patterns = [
        r"(?i)(\w+)\s+(?:will|should|needs to|is going to)",
        r"(?i)assign(?:ed)? to (\w+)",
        r"(?i)(\w+)'s\s+(?:responsibility|task|action)",
    ]

    for conv in conversations:
        text = conv.transcript or conv.ai_response or ""

        # Find action items
        for pattern in action_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if len(match) > 10 and len(match) < 200:  # Reasonable length
                    # Try to find deadline
                    deadline = None
                    for dp in deadline_patterns:
                        deadline_match = re.search(dp, text)
                        if deadline_match:
                            deadline = deadline_match.group(1)
                            break

                    # Try to find assignee
                    assignee = None
                    for ap in assignee_patterns:
                        assignee_match = re.search(ap, text)
                        if assignee_match:
                            assignee = assignee_match.group(1)
                            break

                    extracted_items.append({
                        "type": "action_item",
                        "description": match.strip(),
                        "source_text": text[:200],
                        "suggested_assignee": assignee,
                        "suggested_deadline": deadline,
                        "priority": "normal",
                        "conversation_id": conv.id,
                        "timestamp": conv.timestamp.isoformat() if conv.timestamp else None
                    })

        # Find commitments
        for pattern in commitment_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if len(match) > 10 and len(match) < 200:
                    commitment_indicators.append({
                        "type": "commitment",
                        "description": match.strip(),
                        "source_text": text[:200],
                        "conversation_id": conv.id,
                        "timestamp": conv.timestamp.isoformat() if conv.timestamp else None
                    })

    # Deduplicate similar items
    unique_items = []
    seen_descriptions = set()
    for item in extracted_items:
        desc_key = item["description"].lower()[:50]
        if desc_key not in seen_descriptions:
            seen_descriptions.add(desc_key)
            unique_items.append(item)

    unique_commitments = []
    seen_commitments = set()
    for item in commitment_indicators:
        desc_key = item["description"].lower()[:50]
        if desc_key not in seen_commitments:
            seen_commitments.add(desc_key)
            unique_commitments.append(item)

    return {
        "meeting_id": meeting_id,
        "meeting_title": meeting.title,
        "total_conversations_analyzed": len(conversations),
        "extracted_action_items": unique_items[:20],  # Limit to 20
        "extracted_commitments": unique_commitments[:10],  # Limit to 10
        "note": "Review these items and save the ones you want to track"
    }


@router.post("/bulk-create")
def bulk_create_action_items(
    items: List[ActionItemCreate],
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create multiple action items at once.
    Used after reviewing auto-extracted items.
    """
    created = []
    for data in items:
        # Verify meeting
        meeting = db.query(Meeting).filter(
            Meeting.id == data.meeting_id,
            Meeting.user_id == user.id
        ).first()

        if not meeting:
            continue  # Skip invalid meetings

        action_item = ActionItem(
            meeting_id=data.meeting_id,
            user_id=user.id,
            assignee=data.assignee,
            assignee_role=data.assignee_role,
            description=data.description,
            due_date=data.due_date,
            priority=data.priority
        )
        db.add(action_item)
        created.append(action_item)

    db.commit()

    for item in created:
        db.refresh(item)

    return {
        "created_count": len(created),
        "action_items": [ActionItemResponse.model_validate(a) for a in created]
    }


# ============== Combined Dashboard ==============

@router.get("/dashboard")
def get_task_dashboard(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get combined task dashboard for user.
    Shows pending action items and upcoming commitments.
    """
    # Pending action items assigned to user
    my_action_items = db.query(ActionItem).filter(
        ActionItem.user_id == user.id,
        ActionItem.status == "pending",
        ActionItem.assignee_role == "user"
    ).order_by(ActionItem.due_date.asc().nullslast()).limit(10).all()

    # Pending action items assigned to others
    others_action_items = db.query(ActionItem).filter(
        ActionItem.user_id == user.id,
        ActionItem.status == "pending",
        ActionItem.assignee_role != "user"
    ).order_by(ActionItem.due_date.asc().nullslast()).limit(10).all()

    # Upcoming commitments
    upcoming_commitments = db.query(Commitment).filter(
        Commitment.user_id == user.id,
        Commitment.status == "pending"
    ).order_by(Commitment.due_date.asc().nullslast()).limit(10).all()

    # Overdue items
    overdue_action_items = db.query(ActionItem).filter(
        ActionItem.user_id == user.id,
        ActionItem.status == "pending",
        ActionItem.due_date.isnot(None),
        ActionItem.due_date < datetime.utcnow()
    ).count()

    overdue_commitments = db.query(Commitment).filter(
        Commitment.user_id == user.id,
        Commitment.status == "pending",
        Commitment.due_date.isnot(None),
        Commitment.due_date < datetime.utcnow()
    ).count()

    return {
        "my_action_items": [ActionItemResponse.model_validate(a) for a in my_action_items],
        "others_action_items": [ActionItemResponse.model_validate(a) for a in others_action_items],
        "upcoming_commitments": [CommitmentResponse.model_validate(c) for c in upcoming_commitments],
        "overdue_count": overdue_action_items + overdue_commitments,
        "overdue_action_items": overdue_action_items,
        "overdue_commitments": overdue_commitments
    }
