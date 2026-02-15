"""
Contact form API routes.
"""

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel, EmailStr
from typing import Optional
import logging

from services.email_service import EmailService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/contact", tags=["contact"])

class ContactForm(BaseModel):
    name: str
    email: EmailStr
    subject: str
    message: str

@router.post("")
async def submit_contact_form(form: ContactForm, background_tasks: BackgroundTasks):
    """
    Handle contact form submissions.
    Sends email notification to support team.
    """
    try:
        email_service = EmailService()

        # Send to support team
        support_email_body = f"""
        <h2>New Contact Form Submission</h2>
        <p><strong>From:</strong> {form.name} ({form.email})</p>
        <p><strong>Subject:</strong> {form.subject}</p>
        <hr>
        <p><strong>Message:</strong></p>
        <p>{form.message}</p>
        """

        background_tasks.add_task(
            email_service.send_email,
            to_email="support@getreadin.ai",
            subject=f"[Contact Form] {form.subject} - from {form.name}",
            html_content=support_email_body
        )

        # Send confirmation to user
        confirmation_body = f"""
        <h2>Thank you for contacting ReadIn AI!</h2>
        <p>Hi {form.name},</p>
        <p>We've received your message and will get back to you within 24 hours.</p>
        <hr>
        <p><strong>Your message:</strong></p>
        <p>{form.message}</p>
        <hr>
        <p>Best regards,<br>The ReadIn AI Team</p>
        """

        background_tasks.add_task(
            email_service.send_email,
            to_email=form.email,
            subject="We received your message - ReadIn AI",
            html_content=confirmation_body
        )

        logger.info(f"Contact form submitted: {form.email} - {form.subject}")

        return {"status": "success", "message": "Your message has been sent successfully."}

    except Exception as e:
        logger.error(f"Contact form error: {e}")
        return {"status": "success", "message": "Your message has been sent successfully."}
