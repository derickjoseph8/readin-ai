"""
Zapier Actions for ReadIn AI.

Implements actions that Zapier can trigger:
- create_action_item: Create a new action item in a meeting
- add_meeting_note: Add a note to an existing meeting

Actions follow Zapier's action specification:
https://platform.zapier.com/docs/actions
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from models import Meeting, ActionItem, User

logger = logging.getLogger("zapier.actions")


class ActionType(str, Enum):
    """Available Zapier actions."""
    CREATE_ACTION_ITEM = "create_action_item"
    ADD_MEETING_NOTE = "add_meeting_note"


# Action input schemas
class CreateActionItemInput(BaseModel):
    """Input schema for create_action_item action."""
    meeting_id: Optional[int] = Field(
        None,
        description="ID of the meeting to attach the action item to (optional)"
    )
    assignee: str = Field(
        ...,
        description="Name of the person responsible for this action item"
    )
    description: str = Field(
        ...,
        description="Description of the action item"
    )
    due_date: Optional[datetime] = Field(
        None,
        description="Due date for the action item (ISO 8601 format)"
    )
    priority: str = Field(
        "medium",
        description="Priority level: low, medium, high"
    )
    assignee_role: str = Field(
        "other",
        description="Role of assignee: user, other, team"
    )


class AddMeetingNoteInput(BaseModel):
    """Input schema for add_meeting_note action."""
    meeting_id: int = Field(
        ...,
        description="ID of the meeting to add the note to"
    )
    note: str = Field(
        ...,
        description="The note content to add"
    )
    append: bool = Field(
        True,
        description="If true, append to existing notes. If false, replace."
    )


# Action output schemas
class ActionItemOutput(BaseModel):
    """Output schema for action item operations."""
    id: int
    meeting_id: Optional[int]
    assignee: str
    description: str
    due_date: Optional[datetime]
    priority: str
    status: str
    created_at: datetime


class MeetingNoteOutput(BaseModel):
    """Output schema for meeting note operations."""
    meeting_id: int
    meeting_title: Optional[str]
    notes: str
    updated_at: datetime


# Sample input/output for Zapier setup
ACTION_SAMPLES = {
    ActionType.CREATE_ACTION_ITEM: {
        "input": {
            "meeting_id": 12345,
            "assignee": "Jane Smith",
            "description": "Review the Q4 budget proposal and provide feedback",
            "due_date": "2024-01-22T17:00:00Z",
            "priority": "high",
            "assignee_role": "team"
        },
        "output": {
            "id": 67890,
            "meeting_id": 12345,
            "assignee": "Jane Smith",
            "description": "Review the Q4 budget proposal and provide feedback",
            "due_date": "2024-01-22T17:00:00Z",
            "priority": "high",
            "status": "pending",
            "created_at": "2024-01-15T10:30:00Z"
        }
    },
    ActionType.ADD_MEETING_NOTE: {
        "input": {
            "meeting_id": 12345,
            "note": "Follow-up: Need to schedule a separate meeting with the finance team.",
            "append": True
        },
        "output": {
            "meeting_id": 12345,
            "meeting_title": "Weekly Team Standup",
            "notes": "Discussed Q4 progress.\n\nFollow-up: Need to schedule a separate meeting with the finance team.",
            "updated_at": "2024-01-15T11:00:00Z"
        }
    }
}


def get_action_sample(action_type: ActionType) -> Dict[str, Any]:
    """
    Get sample input/output for an action type.

    Args:
        action_type: The action type

    Returns:
        Dictionary with input and output samples
    """
    return ACTION_SAMPLES.get(action_type, {})


class ZapierActionService:
    """
    Service for executing Zapier actions.

    Handles:
    - Action input validation
    - Action execution
    - Response formatting
    """

    def __init__(self, db: Session):
        """
        Initialize the action service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def create_action_item(
        self,
        user_id: int,
        input_data: CreateActionItemInput
    ) -> Dict[str, Any]:
        """
        Create a new action item.

        Args:
            user_id: The user creating the action item
            input_data: The action item data

        Returns:
            Created action item data

        Raises:
            ValueError: If meeting_id is provided but not found
        """
        # Validate meeting if provided
        meeting = None
        if input_data.meeting_id:
            meeting = self.db.query(Meeting).filter(
                Meeting.id == input_data.meeting_id,
                Meeting.user_id == user_id
            ).first()

            if not meeting:
                raise ValueError(f"Meeting {input_data.meeting_id} not found")

        # If no meeting specified, try to find the most recent active/ended meeting
        if not meeting:
            meeting = self.db.query(Meeting).filter(
                Meeting.user_id == user_id,
                Meeting.status.in_(["active", "ended"])
            ).order_by(Meeting.started_at.desc()).first()

        if not meeting:
            raise ValueError("No meeting found to attach action item to")

        # Validate priority
        valid_priorities = ["low", "medium", "high"]
        priority = input_data.priority.lower()
        if priority not in valid_priorities:
            priority = "medium"

        # Validate assignee role
        valid_roles = ["user", "other", "team"]
        assignee_role = input_data.assignee_role.lower()
        if assignee_role not in valid_roles:
            assignee_role = "other"

        # Create action item
        action_item = ActionItem(
            meeting_id=meeting.id,
            user_id=user_id,
            assignee=input_data.assignee,
            assignee_role=assignee_role,
            description=input_data.description,
            due_date=input_data.due_date,
            priority=priority,
            status="pending",
        )

        self.db.add(action_item)
        self.db.commit()
        self.db.refresh(action_item)

        logger.info(
            f"Created action item {action_item.id} via Zapier "
            f"for user {user_id}, meeting {meeting.id}"
        )

        return {
            "id": action_item.id,
            "meeting_id": action_item.meeting_id,
            "assignee": action_item.assignee,
            "assignee_role": action_item.assignee_role,
            "description": action_item.description,
            "due_date": action_item.due_date.isoformat() if action_item.due_date else None,
            "priority": action_item.priority,
            "status": action_item.status,
            "created_at": action_item.created_at.isoformat() if action_item.created_at else None,
        }

    def add_meeting_note(
        self,
        user_id: int,
        input_data: AddMeetingNoteInput
    ) -> Dict[str, Any]:
        """
        Add a note to a meeting.

        Args:
            user_id: The user adding the note
            input_data: The note data

        Returns:
            Updated meeting notes data

        Raises:
            ValueError: If meeting not found or not owned by user
        """
        # Find the meeting
        meeting = self.db.query(Meeting).filter(
            Meeting.id == input_data.meeting_id,
            Meeting.user_id == user_id
        ).first()

        if not meeting:
            raise ValueError(f"Meeting {input_data.meeting_id} not found")

        # Update notes
        if input_data.append and meeting.notes:
            meeting.notes = f"{meeting.notes}\n\n{input_data.note}"
        else:
            meeting.notes = input_data.note

        self.db.commit()
        self.db.refresh(meeting)

        logger.info(
            f"Added note to meeting {meeting.id} via Zapier "
            f"for user {user_id}"
        )

        return {
            "meeting_id": meeting.id,
            "meeting_title": meeting.title,
            "notes": meeting.notes,
            "updated_at": datetime.utcnow().isoformat(),
        }

    def execute_action(
        self,
        action_type: ActionType,
        user_id: int,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute an action by type.

        Args:
            action_type: The type of action to execute
            user_id: The user executing the action
            input_data: The action input data

        Returns:
            Action result data

        Raises:
            ValueError: If action type is invalid or input is invalid
        """
        if action_type == ActionType.CREATE_ACTION_ITEM:
            validated_input = CreateActionItemInput(**input_data)
            return self.create_action_item(user_id, validated_input)

        elif action_type == ActionType.ADD_MEETING_NOTE:
            validated_input = AddMeetingNoteInput(**input_data)
            return self.add_meeting_note(user_id, validated_input)

        else:
            raise ValueError(f"Unknown action type: {action_type}")

    def get_meetings_for_action(
        self,
        user_id: int,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get recent meetings for action item creation dropdown.

        Args:
            user_id: The user ID
            limit: Maximum number of meetings to return

        Returns:
            List of meeting options
        """
        meetings = self.db.query(Meeting).filter(
            Meeting.user_id == user_id
        ).order_by(
            Meeting.started_at.desc()
        ).limit(limit).all()

        return [
            {
                "id": meeting.id,
                "label": f"{meeting.title or 'Untitled Meeting'} ({meeting.started_at.strftime('%Y-%m-%d')})",
            }
            for meeting in meetings
        ]


# Action field definitions for Zapier
ACTION_FIELDS = {
    ActionType.CREATE_ACTION_ITEM: {
        "input_fields": [
            {
                "key": "meeting_id",
                "label": "Meeting",
                "type": "integer",
                "required": False,
                "helpText": "Select a meeting to attach this action item to, or leave blank to use the most recent meeting.",
                "dynamic": "meetings.id.label"
            },
            {
                "key": "assignee",
                "label": "Assignee",
                "type": "string",
                "required": True,
                "helpText": "Name of the person responsible for this action item"
            },
            {
                "key": "description",
                "label": "Description",
                "type": "text",
                "required": True,
                "helpText": "Description of what needs to be done"
            },
            {
                "key": "due_date",
                "label": "Due Date",
                "type": "datetime",
                "required": False,
                "helpText": "When this action item is due"
            },
            {
                "key": "priority",
                "label": "Priority",
                "type": "string",
                "required": False,
                "default": "medium",
                "choices": ["low", "medium", "high"],
                "helpText": "Priority level for this action item"
            },
            {
                "key": "assignee_role",
                "label": "Assignee Role",
                "type": "string",
                "required": False,
                "default": "other",
                "choices": ["user", "other", "team"],
                "helpText": "Role of the assignee"
            }
        ],
        "output_fields": [
            {"key": "id", "label": "Action Item ID", "type": "integer"},
            {"key": "meeting_id", "label": "Meeting ID", "type": "integer"},
            {"key": "assignee", "label": "Assignee", "type": "string"},
            {"key": "description", "label": "Description", "type": "string"},
            {"key": "due_date", "label": "Due Date", "type": "datetime"},
            {"key": "priority", "label": "Priority", "type": "string"},
            {"key": "status", "label": "Status", "type": "string"},
            {"key": "created_at", "label": "Created At", "type": "datetime"},
        ]
    },
    ActionType.ADD_MEETING_NOTE: {
        "input_fields": [
            {
                "key": "meeting_id",
                "label": "Meeting",
                "type": "integer",
                "required": True,
                "helpText": "Select the meeting to add a note to",
                "dynamic": "meetings.id.label"
            },
            {
                "key": "note",
                "label": "Note",
                "type": "text",
                "required": True,
                "helpText": "The note content to add to the meeting"
            },
            {
                "key": "append",
                "label": "Append to Existing Notes",
                "type": "boolean",
                "required": False,
                "default": True,
                "helpText": "If checked, adds to existing notes. If unchecked, replaces existing notes."
            }
        ],
        "output_fields": [
            {"key": "meeting_id", "label": "Meeting ID", "type": "integer"},
            {"key": "meeting_title", "label": "Meeting Title", "type": "string"},
            {"key": "notes", "label": "Updated Notes", "type": "string"},
            {"key": "updated_at", "label": "Updated At", "type": "datetime"},
        ]
    }
}


def get_action_fields(action_type: ActionType) -> Dict[str, Any]:
    """
    Get field definitions for an action.

    Args:
        action_type: The action type

    Returns:
        Dictionary with input_fields and output_fields
    """
    return ACTION_FIELDS.get(action_type, {"input_fields": [], "output_fields": []})
