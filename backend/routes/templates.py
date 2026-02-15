"""Template management API endpoints."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models import User, Template, TemplateType
from auth import get_current_user
from services.template_service import TemplateService

router = APIRouter(prefix="/templates", tags=["Templates"])


# =============================================================================
# SCHEMAS
# =============================================================================

class TemplateCreate(BaseModel):
    """Request to create a new template."""
    name: str = Field(..., min_length=1, max_length=100)
    template_type: str = Field(..., description="briefing, summary, response, email")
    content: str = Field(..., min_length=1)
    description: Optional[str] = None
    is_default: bool = False


class TemplateUpdate(BaseModel):
    """Request to update a template."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    content: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


class TemplateResponse(BaseModel):
    """Template response."""
    id: int
    name: str
    template_type: str
    description: Optional[str]
    content: str
    variables: List[str]
    is_default: bool
    is_system: bool
    is_active: bool
    version: int

    class Config:
        from_attributes = True


class TemplateRenderRequest(BaseModel):
    """Request to render a template with variables."""
    template_id: Optional[int] = None
    template_type: Optional[str] = None
    variables: dict


class TemplateRenderResponse(BaseModel):
    """Rendered template response."""
    rendered: str
    template_name: str


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("", response_model=List[TemplateResponse])
def list_templates(
    template_type: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all templates available to the user.

    Returns both user's custom templates and system templates.
    """
    service = TemplateService(db)
    templates = service.get_user_templates(user.id, template_type)
    return [TemplateResponse.model_validate(t) for t in templates]


@router.get("/types")
def list_template_types():
    """List available template types."""
    return {
        "types": [
            {"value": TemplateType.BRIEFING, "label": "Pre-Meeting Briefing"},
            {"value": TemplateType.SUMMARY, "label": "Meeting Summary"},
            {"value": TemplateType.RESPONSE, "label": "AI Response Style"},
            {"value": TemplateType.EMAIL, "label": "Email Notification"},
            {"value": TemplateType.ACTION_ITEM, "label": "Action Item Format"},
        ]
    }


@router.get("/{template_id}", response_model=TemplateResponse)
def get_template(
    template_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific template."""
    template = db.query(Template).filter(
        Template.id == template_id,
        (Template.user_id == user.id) | (Template.is_system == True),
    ).first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    return TemplateResponse.model_validate(template)


@router.post("", response_model=TemplateResponse)
def create_template(
    request: TemplateCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new custom template."""
    service = TemplateService(db)

    # Check for duplicate name
    existing = db.query(Template).filter(
        Template.user_id == user.id,
        Template.name == request.name,
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Template with this name already exists",
        )

    template = service.create_template(
        user_id=user.id,
        name=request.name,
        template_type=request.template_type,
        content=request.content,
        description=request.description,
        is_default=request.is_default,
        organization_id=user.organization_id,
    )

    return TemplateResponse.model_validate(template)


@router.put("/{template_id}", response_model=TemplateResponse)
def update_template(
    template_id: int,
    request: TemplateUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a custom template."""
    service = TemplateService(db)

    template = service.update_template(
        template_id=template_id,
        user_id=user.id,
        **request.model_dump(exclude_unset=True),
    )

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found or cannot be modified",
        )

    return TemplateResponse.model_validate(template)


@router.delete("/{template_id}")
def delete_template(
    template_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a custom template."""
    service = TemplateService(db)

    if not service.delete_template(template_id, user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found or cannot be deleted",
        )

    return {"message": "Template deleted successfully"}


@router.post("/{template_id}/duplicate", response_model=TemplateResponse)
def duplicate_template(
    template_id: int,
    new_name: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Duplicate an existing template (including system templates)."""
    original = db.query(Template).filter(
        Template.id == template_id,
        (Template.user_id == user.id) | (Template.is_system == True),
    ).first()

    if not original:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    service = TemplateService(db)
    template = service.create_template(
        user_id=user.id,
        name=new_name,
        template_type=original.template_type,
        content=original.content,
        description=f"Copy of {original.name}",
        variables=original.variables,
    )

    return TemplateResponse.model_validate(template)


@router.post("/render", response_model=TemplateRenderResponse)
def render_template(
    request: TemplateRenderRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Render a template with provided variables.

    Provide either template_id or template_type (to use default).
    """
    service = TemplateService(db)

    if request.template_id:
        template = db.query(Template).filter(
            Template.id == request.template_id,
            (Template.user_id == user.id) | (Template.is_system == True),
        ).first()
    elif request.template_type:
        template = service.get_template(
            template_type=request.template_type,
            user_id=user.id,
            organization_id=user.organization_id,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either template_id or template_type",
        )

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    rendered = service.render_template(template, request.variables)

    return TemplateRenderResponse(
        rendered=rendered,
        template_name=template.name,
    )


@router.post("/{template_id}/set-default")
def set_default_template(
    template_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Set a template as the default for its type."""
    template = db.query(Template).filter(
        Template.id == template_id,
        Template.user_id == user.id,
    ).first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    # Unset other defaults of same type
    db.query(Template).filter(
        Template.user_id == user.id,
        Template.template_type == template.template_type,
        Template.is_default == True,
    ).update({"is_default": False})

    # Set this as default
    template.is_default = True
    db.commit()

    return {"message": f"Template '{template.name}' set as default for {template.template_type}"}
