"""Translation API routes for real-time translation support.

Provides endpoints for:
- Translating text to target languages
- Translating entire meeting transcripts
- Getting translated transcripts by language
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models import Meeting, Conversation, User
from auth import get_current_user
from services.translation_service import (
    TranslationService,
    get_supported_translation_languages,
    is_supported_translation_language,
    get_language_name,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/translation", tags=["Translation"])


# =============================================================================
# SCHEMAS
# =============================================================================

class TranslateTextRequest(BaseModel):
    """Request schema for text translation."""
    text: str = Field(..., min_length=1, max_length=50000, description="Text to translate")
    target_language: str = Field(..., min_length=2, max_length=5, description="Target language code (e.g., 'es', 'fr', 'zh')")
    source_language: Optional[str] = Field(None, min_length=2, max_length=5, description="Source language code (optional, auto-detect if not provided)")
    context: Optional[str] = Field(None, max_length=500, description="Additional context to help with translation accuracy")


class TranslateTextResponse(BaseModel):
    """Response schema for text translation."""
    original_text: str
    translated_text: str
    target_language: str
    target_language_name: str
    source_language: Optional[str]
    cached: bool


class TranslateBatchRequest(BaseModel):
    """Request schema for batch text translation."""
    texts: List[str] = Field(..., min_length=1, max_length=100, description="List of texts to translate (max 100)")
    target_language: str = Field(..., min_length=2, max_length=5, description="Target language code")
    source_language: Optional[str] = Field(None, min_length=2, max_length=5, description="Source language code (optional)")
    context: Optional[str] = Field(None, max_length=500, description="Additional context for translation")


class TranslateBatchResponse(BaseModel):
    """Response schema for batch translation."""
    translations: List[TranslateTextResponse]
    total_translated: int
    cached_count: int
    target_language: str
    target_language_name: str


class TranslatedSegment(BaseModel):
    """Schema for a translated transcript segment."""
    id: int
    speaker: str
    timestamp: Optional[str]
    original_text: str
    translated_text: str
    cached: bool


class TranslateMeetingResponse(BaseModel):
    """Response schema for meeting transcript translation."""
    meeting_id: int
    meeting_title: Optional[str]
    target_language: str
    target_language_name: str
    translated_segments: List[TranslatedSegment]
    total_segments: int
    translated_at: str


class LanguageInfo(BaseModel):
    """Schema for language information."""
    code: str
    name: str
    native_name: str


class SupportedLanguagesResponse(BaseModel):
    """Response schema for supported languages."""
    languages: List[LanguageInfo]
    total: int


class DetectLanguageRequest(BaseModel):
    """Request schema for language detection."""
    text: str = Field(..., min_length=1, max_length=5000, description="Text to analyze for language detection")


class DetectLanguageResponse(BaseModel):
    """Response schema for language detection."""
    language_code: Optional[str]
    language_name: Optional[str]
    confidence: float
    error: Optional[str] = None


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/languages", response_model=SupportedLanguagesResponse)
def get_supported_languages():
    """
    Get list of supported languages for translation.

    Returns all languages that can be used as source or target for translation.
    """
    languages = get_supported_translation_languages()
    return SupportedLanguagesResponse(
        languages=[
            LanguageInfo(
                code=code,
                name=info["name"],
                native_name=info["native_name"]
            )
            for code, info in languages.items()
        ],
        total=len(languages)
    )


@router.post("/translate", response_model=TranslateTextResponse)
async def translate_text(
    request: TranslateTextRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Translate text to a target language using Claude AI.

    This endpoint translates any text to one of the supported languages.
    Translations are cached for 24 hours to improve performance and reduce API costs.

    Supported languages:
    - English (en)
    - Spanish (es)
    - French (fr)
    - German (de)
    - Portuguese (pt)
    - Chinese (zh)
    - Japanese (ja)
    - Korean (ko)
    - Arabic (ar)
    - Hindi (hi)
    - Swahili (sw)
    """
    # Validate target language
    if not is_supported_translation_language(request.target_language):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported target language: {request.target_language}. "
                   f"Use GET /translation/languages to see supported languages."
        )

    # Validate source language if provided
    if request.source_language and not is_supported_translation_language(request.source_language):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported source language: {request.source_language}. "
                   f"Use GET /translation/languages to see supported languages."
        )

    try:
        translation_service = TranslationService(db)
        result = await translation_service.translate_text(
            text=request.text,
            target_language=request.target_language,
            source_language=request.source_language,
            context=request.context,
            use_cache=True,
        )

        return TranslateTextResponse(
            original_text=result["original_text"],
            translated_text=result["translated_text"],
            target_language=result["target_language"],
            target_language_name=get_language_name(result["target_language"]),
            source_language=result["source_language"],
            cached=result["cached"],
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except RuntimeError as e:
        logger.error(f"Translation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Translation service temporarily unavailable. Please try again."
        )


@router.post("/translate/batch", response_model=TranslateBatchResponse)
async def translate_batch(
    request: TranslateBatchRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Translate multiple texts to a target language in a single request.

    This endpoint is more efficient than making multiple single translation requests.
    Up to 100 texts can be translated in a single batch.
    Translations are cached individually for 24 hours.
    """
    # Validate text count
    if len(request.texts) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 100 texts per batch request"
        )

    if len(request.texts) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one text is required"
        )

    # Validate target language
    if not is_supported_translation_language(request.target_language):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported target language: {request.target_language}"
        )

    try:
        translation_service = TranslationService(db)
        results = await translation_service.translate_batch(
            texts=request.texts,
            target_language=request.target_language,
            source_language=request.source_language,
            context=request.context,
            use_cache=True,
        )

        translations = [
            TranslateTextResponse(
                original_text=r["original_text"],
                translated_text=r["translated_text"],
                target_language=r["target_language"],
                target_language_name=get_language_name(r["target_language"]),
                source_language=r["source_language"],
                cached=r["cached"],
            )
            for r in results
        ]

        cached_count = sum(1 for r in results if r["cached"])

        return TranslateBatchResponse(
            translations=translations,
            total_translated=len(translations),
            cached_count=cached_count,
            target_language=request.target_language,
            target_language_name=get_language_name(request.target_language),
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except RuntimeError as e:
        logger.error(f"Batch translation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Translation service temporarily unavailable. Please try again."
        )


@router.post("/meetings/{meeting_id}/translate", response_model=TranslateMeetingResponse)
async def translate_meeting_transcript(
    meeting_id: int,
    target_language: str = Query(..., min_length=2, max_length=5, description="Target language code"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Translate an entire meeting transcript to the target language.

    This endpoint translates all conversation segments in a meeting to the specified language.
    Each segment's translation is cached individually for efficient subsequent requests.
    """
    # Validate target language
    if not is_supported_translation_language(target_language):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported target language: {target_language}. "
                   f"Use GET /translation/languages to see supported languages."
        )

    # Verify meeting exists and belongs to user
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.user_id == user.id
    ).first()

    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )

    try:
        translation_service = TranslationService(db)
        result = await translation_service.translate_meeting_transcript(
            meeting_id=meeting_id,
            target_language=target_language,
            user_id=user.id,
        )

        return TranslateMeetingResponse(
            meeting_id=result["meeting_id"],
            meeting_title=result["meeting_title"],
            target_language=result["target_language"],
            target_language_name=result["target_language_name"],
            translated_segments=[
                TranslatedSegment(
                    id=seg["id"],
                    speaker=seg["speaker"],
                    timestamp=seg["timestamp"],
                    original_text=seg["original_text"],
                    translated_text=seg["translated_text"],
                    cached=seg["cached"],
                )
                for seg in result["translated_segments"]
            ],
            total_segments=result["total_segments"],
            translated_at=result["translated_at"],
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except RuntimeError as e:
        logger.error(f"Meeting translation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Translation service temporarily unavailable. Please try again."
        )


@router.get("/meetings/{meeting_id}/transcript/{language}", response_model=TranslateMeetingResponse)
async def get_translated_transcript(
    meeting_id: int,
    language: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a meeting transcript translated to the specified language.

    This endpoint retrieves (and translates if needed) the meeting transcript
    in the requested language. If the transcript has been previously translated,
    cached translations will be used for faster response.

    This is a convenience endpoint that combines transcript retrieval and translation.
    """
    # Validate language
    if not is_supported_translation_language(language):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported language: {language}. "
                   f"Use GET /translation/languages to see supported languages."
        )

    # Verify meeting exists and belongs to user
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.user_id == user.id
    ).first()

    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )

    # Get conversations
    conversations = db.query(Conversation).filter(
        Conversation.meeting_id == meeting_id
    ).order_by(Conversation.timestamp).all()

    if not conversations:
        return TranslateMeetingResponse(
            meeting_id=meeting_id,
            meeting_title=meeting.title,
            target_language=language,
            target_language_name=get_language_name(language),
            translated_segments=[],
            total_segments=0,
            translated_at="",
        )

    try:
        translation_service = TranslationService(db)
        result = await translation_service.translate_meeting_transcript(
            meeting_id=meeting_id,
            target_language=language,
            user_id=user.id,
        )

        return TranslateMeetingResponse(
            meeting_id=result["meeting_id"],
            meeting_title=result["meeting_title"],
            target_language=result["target_language"],
            target_language_name=result["target_language_name"],
            translated_segments=[
                TranslatedSegment(
                    id=seg["id"],
                    speaker=seg["speaker"],
                    timestamp=seg["timestamp"],
                    original_text=seg["original_text"],
                    translated_text=seg["translated_text"],
                    cached=seg["cached"],
                )
                for seg in result["translated_segments"]
            ],
            total_segments=result["total_segments"],
            translated_at=result["translated_at"],
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except RuntimeError as e:
        logger.error(f"Translated transcript retrieval failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Translation service temporarily unavailable. Please try again."
        )


@router.post("/detect", response_model=DetectLanguageResponse)
async def detect_language(
    request: DetectLanguageRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Detect the language of a text using AI.

    This endpoint analyzes the provided text and returns the detected language
    along with a confidence score.
    """
    try:
        translation_service = TranslationService(db)
        result = await translation_service.detect_language(request.text)

        return DetectLanguageResponse(
            language_code=result.get("language_code"),
            language_name=result.get("language_name"),
            confidence=result.get("confidence", 0.0),
            error=result.get("error"),
        )

    except Exception as e:
        logger.error(f"Language detection failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Language detection service temporarily unavailable."
        )
