"""Profession API routes - Career selection and profession-tailored AI."""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import Profession, User
from schemas import (
    ProfessionResponse, ProfessionList, ProfessionCategory,
    ProfessionCreate
)
from auth import get_current_user

router = APIRouter(prefix="/professions", tags=["Professions"])


@router.get("", response_model=ProfessionList)
def list_professions(
    category: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List all available professions for user registration.

    - Filter by category (Legal, Medical, Technology, etc.)
    - Search by profession name
    - Used during registration to select user's career
    """
    query = db.query(Profession).filter(Profession.is_active == True)

    if category:
        query = query.filter(Profession.category == category)

    if search:
        query = query.filter(Profession.name.ilike(f"%{search}%"))

    total = query.count()
    professions = query.order_by(Profession.category, Profession.name).offset(skip).limit(limit).all()

    return ProfessionList(
        professions=[ProfessionResponse.model_validate(p) for p in professions],
        total=total
    )


@router.get("/categories", response_model=List[str])
def list_categories(db: Session = Depends(get_db)):
    """Get all profession categories for filtering."""
    categories = db.query(Profession.category).distinct().filter(
        Profession.is_active == True,
        Profession.category.isnot(None)
    ).all()
    return sorted([c[0] for c in categories if c[0]])


@router.get("/by-category", response_model=List[ProfessionCategory])
def professions_by_category(db: Session = Depends(get_db)):
    """
    Get all professions grouped by category.
    Useful for registration UI with category dropdowns.
    """
    professions = db.query(Profession).filter(
        Profession.is_active == True
    ).order_by(Profession.category, Profession.name).all()

    # Group by category
    categories = {}
    for p in professions:
        cat = p.category or "Other"
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(ProfessionResponse.model_validate(p))

    return [
        ProfessionCategory(category=cat, professions=profs)
        for cat, profs in sorted(categories.items())
    ]


@router.get("/{profession_id}", response_model=ProfessionResponse)
def get_profession(profession_id: int, db: Session = Depends(get_db)):
    """Get a specific profession by ID."""
    profession = db.query(Profession).filter(
        Profession.id == profession_id,
        Profession.is_active == True
    ).first()

    if not profession:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profession not found"
        )

    return ProfessionResponse.model_validate(profession)


@router.get("/{profession_id}/system-prompt")
def get_profession_prompt(
    profession_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the AI system prompt additions for a profession.
    Used by desktop app to customize AI responses.
    """
    profession = db.query(Profession).filter(Profession.id == profession_id).first()

    if not profession:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profession not found"
        )

    return {
        "profession_id": profession.id,
        "profession_name": profession.name,
        "system_prompt_additions": profession.system_prompt_additions,
        "terminology": profession.terminology or {},
        "communication_style": profession.communication_style,
        "common_topics": profession.common_topics or []
    }


@router.get("/user/current")
def get_user_profession(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the current user's profession with full AI customization data.
    Desktop app uses this to tailor AI responses.
    """
    if not user.profession_id:
        return {
            "has_profession": False,
            "message": "No profession selected. Please update your profile."
        }

    profession = db.query(Profession).filter(Profession.id == user.profession_id).first()

    if not profession:
        return {
            "has_profession": False,
            "message": "Profession not found. Please update your profile."
        }

    return {
        "has_profession": True,
        "profession_id": profession.id,
        "profession_name": profession.name,
        "specialization": user.specialization,
        "years_experience": user.years_experience,
        "system_prompt_additions": profession.system_prompt_additions,
        "terminology": profession.terminology or {},
        "communication_style": profession.communication_style,
        "common_topics": profession.common_topics or []
    }


@router.put("/user/update")
def update_user_profession(
    profession_id: int,
    specialization: Optional[str] = None,
    years_experience: Optional[int] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update the current user's profession."""
    # Verify profession exists
    profession = db.query(Profession).filter(
        Profession.id == profession_id,
        Profession.is_active == True
    ).first()

    if not profession:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profession not found"
        )

    # Update user
    user.profession_id = profession_id
    if specialization is not None:
        user.specialization = specialization
    if years_experience is not None:
        user.years_experience = years_experience

    db.commit()
    db.refresh(user)

    return {
        "message": "Profession updated successfully",
        "profession_name": profession.name,
        "specialization": user.specialization,
        "years_experience": user.years_experience
    }
