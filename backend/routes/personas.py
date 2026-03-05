"""
AI Personas API routes.

Endpoints for managing AI response personas/styles.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List
from pydantic import BaseModel

from services.ai_personas import (
    get_persona, get_all_personas, list_persona_options, Persona
)
from auth import get_current_user
from models import User
from database import get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/personas", tags=["personas"])


class PersonaResponse(BaseModel):
    """Persona response model."""
    id: str
    name: str
    description: str
    icon: str

    class Config:
        from_attributes = True


class PersonaListResponse(BaseModel):
    """List of personas response."""
    personas: List[PersonaResponse]


class SetPersonaRequest(BaseModel):
    """Request to set user's persona."""
    persona_id: str


class UserPersonaResponse(BaseModel):
    """User's current persona."""
    persona_id: str
    persona: PersonaResponse


@router.get("", response_model=PersonaListResponse)
async def list_personas(
    current_user: User = Depends(get_current_user)
):
    """
    List all available AI personas.

    Returns all persona options the user can choose from.
    """
    personas = list_persona_options()
    return PersonaListResponse(
        personas=[PersonaResponse(**p) for p in personas]
    )


@router.get("/{persona_id}", response_model=PersonaResponse)
async def get_persona_details(
    persona_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get details for a specific persona.
    """
    persona = get_persona(persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")

    return PersonaResponse(
        id=persona.id,
        name=persona.name,
        description=persona.description,
        icon=persona.icon
    )


@router.get("/user/current", response_model=UserPersonaResponse)
async def get_user_persona(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the current user's selected persona.
    """
    # Get from user preferences or default to professional
    persona_id = getattr(current_user, 'ai_persona', None) or "professional"
    persona = get_persona(persona_id)

    if not persona:
        persona = get_persona("professional")

    return UserPersonaResponse(
        persona_id=persona.id,
        persona=PersonaResponse(
            id=persona.id,
            name=persona.name,
            description=persona.description,
            icon=persona.icon
        )
    )


@router.put("/user/current", response_model=UserPersonaResponse)
async def set_user_persona(
    request: SetPersonaRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Set the user's preferred AI persona.
    """
    persona = get_persona(request.persona_id)
    if not persona:
        raise HTTPException(status_code=400, detail="Invalid persona ID")

    # Update user's persona preference
    current_user.ai_persona = request.persona_id
    db.commit()

    return UserPersonaResponse(
        persona_id=persona.id,
        persona=PersonaResponse(
            id=persona.id,
            name=persona.name,
            description=persona.description,
            icon=persona.icon
        )
    )
