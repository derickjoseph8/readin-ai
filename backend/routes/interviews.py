"""Interviews API routes - Job application and interview tracking."""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from database import get_db
from models import JobApplication, Interview, Meeting, User
from schemas import (
    JobApplicationCreate, JobApplicationUpdate, JobApplicationResponse,
    JobApplicationDetail, JobApplicationList,
    InterviewCreate, InterviewUpdate, InterviewResponse, InterviewLinkMeeting
)
from auth import get_current_user

router = APIRouter(prefix="/interviews", tags=["Interviews"])


# ============== Job Applications ==============

@router.post("/applications", response_model=JobApplicationResponse)
def create_application(
    data: JobApplicationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new job application to track."""
    application = JobApplication(
        user_id=user.id,
        company=data.company,
        position=data.position,
        job_description=data.job_description,
        job_url=data.job_url,
        salary_range=data.salary_range,
        notes=data.notes,
        applied_at=data.applied_at
    )
    db.add(application)
    db.commit()
    db.refresh(application)

    return JobApplicationResponse(
        **{k: v for k, v in application.__dict__.items() if not k.startswith('_')},
        interview_count=0
    )


@router.get("/applications", response_model=JobApplicationList)
def list_applications(
    status_filter: Optional[str] = None,
    company: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all job applications."""
    query = db.query(JobApplication).filter(JobApplication.user_id == user.id)

    if status_filter:
        query = query.filter(JobApplication.status == status_filter)
    if company:
        query = query.filter(JobApplication.company.ilike(f"%{company}%"))

    total = query.count()
    applications = query.order_by(desc(JobApplication.created_at)).offset(skip).limit(limit).all()

    # Get interview counts
    app_ids = [a.id for a in applications]
    interview_counts = {}
    if app_ids:
        counts = db.query(
            Interview.job_application_id,
            func.count(Interview.id)
        ).filter(
            Interview.job_application_id.in_(app_ids)
        ).group_by(Interview.job_application_id).all()
        interview_counts = dict(counts)

    # Status distribution
    status_counts = db.query(
        JobApplication.status,
        func.count(JobApplication.id)
    ).filter(JobApplication.user_id == user.id).group_by(JobApplication.status).all()

    return JobApplicationList(
        applications=[
            JobApplicationResponse(
                id=a.id,
                company=a.company,
                position=a.position,
                status=a.status,
                job_description=a.job_description,
                job_url=a.job_url,
                salary_range=a.salary_range,
                notes=a.notes,
                applied_at=a.applied_at,
                interview_count=interview_counts.get(a.id, 0),
                created_at=a.created_at,
                updated_at=a.updated_at
            )
            for a in applications
        ],
        total=total,
        by_status=dict(status_counts)
    )


@router.get("/applications/{app_id}", response_model=JobApplicationDetail)
def get_application(
    app_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get job application with all interviews."""
    application = db.query(JobApplication).filter(
        JobApplication.id == app_id,
        JobApplication.user_id == user.id
    ).first()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )

    interviews = db.query(Interview).filter(
        Interview.job_application_id == app_id
    ).order_by(Interview.round_number).all()

    # Generate improvement suggestions based on interviews
    improvement_suggestions = []
    for interview in interviews:
        if interview.weak_answers:
            for weak in interview.weak_answers[:2]:
                improvement_suggestions.append(f"Practice: {weak}")

    return JobApplicationDetail(
        id=application.id,
        company=application.company,
        position=application.position,
        status=application.status,
        job_description=application.job_description,
        job_url=application.job_url,
        salary_range=application.salary_range,
        notes=application.notes,
        applied_at=application.applied_at,
        interview_count=len(interviews),
        created_at=application.created_at,
        updated_at=application.updated_at,
        interviews=[InterviewResponse.model_validate(i) for i in interviews],
        improvement_suggestions=improvement_suggestions[:5]
    )


@router.patch("/applications/{app_id}", response_model=JobApplicationResponse)
def update_application(
    app_id: int,
    data: JobApplicationUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a job application."""
    application = db.query(JobApplication).filter(
        JobApplication.id == app_id,
        JobApplication.user_id == user.id
    ).first()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )

    if data.company is not None:
        application.company = data.company
    if data.position is not None:
        application.position = data.position
    if data.status is not None:
        application.status = data.status
    if data.job_description is not None:
        application.job_description = data.job_description
    if data.salary_range is not None:
        application.salary_range = data.salary_range
    if data.notes is not None:
        application.notes = data.notes

    db.commit()
    db.refresh(application)

    interview_count = db.query(Interview).filter(
        Interview.job_application_id == app_id
    ).count()

    return JobApplicationResponse(
        id=application.id,
        company=application.company,
        position=application.position,
        status=application.status,
        job_description=application.job_description,
        job_url=application.job_url,
        salary_range=application.salary_range,
        notes=application.notes,
        applied_at=application.applied_at,
        interview_count=interview_count,
        created_at=application.created_at,
        updated_at=application.updated_at
    )


@router.delete("/applications/{app_id}")
def delete_application(
    app_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a job application and all interviews."""
    application = db.query(JobApplication).filter(
        JobApplication.id == app_id,
        JobApplication.user_id == user.id
    ).first()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )

    db.delete(application)
    db.commit()

    return {"message": "Application deleted"}


# ============== Interviews ==============

@router.post("/applications/{app_id}/interviews", response_model=InterviewResponse)
def create_interview(
    app_id: int,
    data: InterviewCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add an interview to a job application."""
    application = db.query(JobApplication).filter(
        JobApplication.id == app_id,
        JobApplication.user_id == user.id
    ).first()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )

    # Get next round number
    last_interview = db.query(Interview).filter(
        Interview.job_application_id == app_id
    ).order_by(desc(Interview.round_number)).first()

    round_number = (last_interview.round_number + 1) if last_interview else 1

    interview = Interview(
        job_application_id=app_id,
        interview_type=data.interview_type,
        round_number=round_number,
        interviewer_name=data.interviewer_name,
        interviewer_role=data.interviewer_role,
        scheduled_at=data.scheduled_at,
        duration_minutes=data.duration_minutes
    )
    db.add(interview)
    db.commit()
    db.refresh(interview)

    return InterviewResponse.model_validate(interview)


@router.get("/applications/{app_id}/interviews", response_model=List[InterviewResponse])
def list_interviews(
    app_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all interviews for a job application."""
    application = db.query(JobApplication).filter(
        JobApplication.id == app_id,
        JobApplication.user_id == user.id
    ).first()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )

    interviews = db.query(Interview).filter(
        Interview.job_application_id == app_id
    ).order_by(Interview.round_number).all()

    return [InterviewResponse.model_validate(i) for i in interviews]


@router.get("/interviews/{interview_id}", response_model=InterviewResponse)
def get_interview(
    interview_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific interview."""
    interview = db.query(Interview).join(JobApplication).filter(
        Interview.id == interview_id,
        JobApplication.user_id == user.id
    ).first()

    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found"
        )

    return InterviewResponse.model_validate(interview)


@router.patch("/interviews/{interview_id}", response_model=InterviewResponse)
def update_interview(
    interview_id: int,
    data: InterviewUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an interview."""
    interview = db.query(Interview).join(JobApplication).filter(
        Interview.id == interview_id,
        JobApplication.user_id == user.id
    ).first()

    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found"
        )

    if data.interview_type is not None:
        interview.interview_type = data.interview_type
    if data.interviewer_name is not None:
        interview.interviewer_name = data.interviewer_name
    if data.interviewer_role is not None:
        interview.interviewer_role = data.interviewer_role
    if data.scheduled_at is not None:
        interview.scheduled_at = data.scheduled_at
    if data.duration_minutes is not None:
        interview.duration_minutes = data.duration_minutes
    if data.user_feeling is not None:
        interview.user_feeling = data.user_feeling
    if data.status is not None:
        interview.status = data.status
    if data.outcome is not None:
        interview.outcome = data.outcome

    db.commit()
    db.refresh(interview)

    return InterviewResponse.model_validate(interview)


@router.post("/interviews/{interview_id}/link-meeting", response_model=InterviewResponse)
def link_meeting_to_interview(
    interview_id: int,
    data: InterviewLinkMeeting,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Link a meeting session to an interview for analysis."""
    interview = db.query(Interview).join(JobApplication).filter(
        Interview.id == interview_id,
        JobApplication.user_id == user.id
    ).first()

    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found"
        )

    meeting = db.query(Meeting).filter(
        Meeting.id == data.meeting_id,
        Meeting.user_id == user.id
    ).first()

    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )

    interview.meeting_id = meeting.id
    interview.status = "completed"

    # TODO: Trigger async interview analysis
    # analyze_interview.delay(interview.id)

    db.commit()
    db.refresh(interview)

    return InterviewResponse.model_validate(interview)


@router.get("/interviews/{interview_id}/improvement")
def get_improvement_suggestions(
    interview_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get ML-powered improvement suggestions for an interview.
    Analyzes conversation patterns and suggests areas to improve.
    """
    interview = db.query(Interview).join(JobApplication).filter(
        Interview.id == interview_id,
        JobApplication.user_id == user.id
    ).first()

    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found"
        )

    if not interview.meeting_id:
        return {
            "has_analysis": False,
            "message": "Link a meeting to this interview first for analysis"
        }

    # TODO: Use AI to analyze and generate suggestions
    return {
        "has_analysis": True,
        "performance_score": interview.performance_score,
        "strong_answers": interview.strong_answers or [],
        "weak_answers": interview.weak_answers or [],
        "improvement_notes": interview.improvement_notes or [],
        "questions_asked": interview.questions_asked or []
    }


@router.post("/interviews/{interview_id}/analyze")
def trigger_interview_analysis(
    interview_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Trigger ML analysis of an interview.
    Extracts questions, evaluates responses, and generates improvement suggestions.
    """
    interview = db.query(Interview).join(JobApplication).filter(
        Interview.id == interview_id,
        JobApplication.user_id == user.id
    ).first()

    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found"
        )

    if not interview.meeting_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Link a meeting to this interview first"
        )

    # TODO: Trigger async analysis with Claude
    # analyze_interview.delay(interview.id)

    return {
        "message": "Interview analysis queued",
        "interview_id": interview_id
    }


@router.get("/analytics")
def interview_analytics(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get overall interview performance analytics."""
    # Total applications
    total_apps = db.query(JobApplication).filter(
        JobApplication.user_id == user.id
    ).count()

    # Applications by status
    status_counts = db.query(
        JobApplication.status,
        func.count(JobApplication.id)
    ).filter(JobApplication.user_id == user.id).group_by(JobApplication.status).all()

    # Total interviews
    total_interviews = db.query(Interview).join(JobApplication).filter(
        JobApplication.user_id == user.id
    ).count()

    # Average performance score
    avg_score = db.query(func.avg(Interview.performance_score)).join(JobApplication).filter(
        JobApplication.user_id == user.id,
        Interview.performance_score.isnot(None)
    ).scalar()

    # Success rate (offers / total)
    offers = db.query(JobApplication).filter(
        JobApplication.user_id == user.id,
        JobApplication.status.in_(["offer", "accepted"])
    ).count()

    success_rate = (offers / total_apps * 100) if total_apps > 0 else None

    return {
        "total_applications": total_apps,
        "by_status": dict(status_counts),
        "total_interviews": total_interviews,
        "average_performance_score": float(avg_score) if avg_score else None,
        "success_rate": success_rate,
        "offers_received": offers
    }
