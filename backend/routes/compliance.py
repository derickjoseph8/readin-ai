"""Compliance API routes - CCPA, GDPR, SOC2."""

from fastapi import APIRouter, Depends, Request
from typing import Optional
from uuid import UUID
from pydantic import BaseModel
from datetime import date
from routes.auth import get_current_user
from models import User
from database import get_db
from sqlalchemy.orm import Session
from services.compliance_service import ComplianceService

router = APIRouter(prefix="/compliance", tags=["compliance"])

class ConsentUpdateRequest(BaseModel):
    consent_type: str
    granted: bool

@router.post("/ccpa/access-request")
async def ccpa_access(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = ComplianceService(db)
    return await service.process_ccpa_request(current_user.id, "access")

@router.post("/ccpa/deletion-request")
async def ccpa_delete(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = ComplianceService(db)
    return await service.process_ccpa_request(current_user.id, "delete")

@router.post("/ccpa/opt-out")
async def ccpa_opt_out(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = ComplianceService(db)
    return await service.process_ccpa_request(current_user.id, "opt-out")

@router.get("/consent")
async def get_consent(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = ComplianceService(db)
    return await service.get_consent_status(current_user.id)

@router.put("/consent")
async def update_consent(request: ConsentUpdateRequest, req: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = ComplianceService(db)
    return await service.update_consent(current_user.id, request.consent_type, request.granted, req.client.host)

@router.get("/data-inventory")
async def data_inventory(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = ComplianceService(db)
    return await service.get_data_inventory(current_user.id)
