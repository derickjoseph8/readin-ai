"""Translation Service using Claude AI.

Provides real-time translation support for meeting transcripts and text content.
Features:
- Multi-language translation using Claude AI
- Translation caching to avoid redundant API calls
- Batch translation support for efficiency
- Support for major world languages
"""

import os
import json
import hashlib
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

import anthropic
from sqlalchemy.orm import Session

from services.cache_service import cache, CacheTTL

logger = logging.getLogger("translation_service")


# Supported languages for translation
SUPPORTED_LANGUAGES: Dict[str, Dict[str, str]] = {
    "en": {
        "name": "English",
        "native_name": "English",
        "code": "en",
    },
    "es": {
        "name": "Spanish",
        "native_name": "Espanol",
        "code": "es",
    },
    "fr": {
        "name": "French",
        "native_name": "Francais",
        "code": "fr",
    },
    "de": {
        "name": "German",
        "native_name": "Deutsch",
        "code": "de",
    },
    "pt": {
        "name": "Portuguese",
        "native_name": "Portugues",
        "code": "pt",
    },
    "zh": {
        "name": "Chinese",
        "native_name": "Chinese",
        "code": "zh",
    },
    "ja": {
        "name": "Japanese",
        "native_name": "Japanese",
        "code": "ja",
    },
    "ko": {
        "name": "Korean",
        "native_name": "Korean",
        "code": "ko",
    },
    "ar": {
        "name": "Arabic",
        "native_name": "Arabic",
        "code": "ar",
    },
    "hi": {
        "name": "Hindi",
        "native_name": "Hindi",
        "code": "hi",
    },
    "sw": {
        "name": "Swahili",
        "native_name": "Kiswahili",
        "code": "sw",
    },
}


def get_supported_translation_languages() -> Dict[str, Dict[str, str]]:
    """Get all supported languages for translation.

    Returns:
        Dictionary of supported languages with metadata
    """
    return SUPPORTED_LANGUAGES.copy()


def is_supported_translation_language(language_code: str) -> bool:
    """Check if a language code is supported for translation.

    Args:
        language_code: The language code to check

    Returns:
        True if the language is supported
    """
    return language_code.lower() in SUPPORTED_LANGUAGES


def get_language_name(language_code: str) -> Optional[str]:
    """Get the display name for a language code.

    Args:
        language_code: The language code

    Returns:
        The display name or None if not supported
    """
    lang = SUPPORTED_LANGUAGES.get(language_code.lower())
    return lang["name"] if lang else None


class TranslationService:
    """AI-powered translation service using Claude.

    Provides translation capabilities for:
    - Single text translation
    - Batch text translation
    - Meeting transcript translation
    - Cached translations for efficiency
    """

    def __init__(self, db: Session):
        """Initialize the translation service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = os.getenv("TRANSLATION_MODEL", "claude-sonnet-4-20250514")
        self.cache_ttl = CacheTTL.DAY  # Cache translations for 24 hours

    def _generate_cache_key(self, text: str, target_language: str, source_language: Optional[str] = None) -> str:
        """Generate a cache key for a translation.

        Args:
            text: The text to translate
            target_language: Target language code
            source_language: Source language code (optional)

        Returns:
            A unique cache key
        """
        # Create a hash of the text for the cache key
        text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
        source = source_language or "auto"
        return f"translation:{source}:{target_language}:{text_hash}"

    def _get_cached_translation(self, text: str, target_language: str, source_language: Optional[str] = None) -> Optional[str]:
        """Get a cached translation if available.

        Args:
            text: The text to translate
            target_language: Target language code
            source_language: Source language code (optional)

        Returns:
            Cached translation or None
        """
        cache_key = self._generate_cache_key(text, target_language, source_language)
        cached = cache.get(cache_key)
        if cached:
            logger.debug(f"Cache hit for translation to {target_language}")
            return cached.get("translated_text")
        return None

    def _cache_translation(
        self,
        text: str,
        translated_text: str,
        target_language: str,
        source_language: Optional[str] = None
    ) -> None:
        """Cache a translation result.

        Args:
            text: The original text
            translated_text: The translated text
            target_language: Target language code
            source_language: Source language code (optional)
        """
        cache_key = self._generate_cache_key(text, target_language, source_language)
        cache.set(
            cache_key,
            {
                "translated_text": translated_text,
                "target_language": target_language,
                "source_language": source_language,
                "cached_at": datetime.utcnow().isoformat(),
            },
            self.cache_ttl
        )

    async def translate_text(
        self,
        text: str,
        target_language: str,
        source_language: Optional[str] = None,
        context: Optional[str] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """Translate text to the target language using Claude AI.

        Args:
            text: The text to translate
            target_language: Target language code (e.g., 'es', 'fr', 'zh')
            source_language: Source language code (optional, auto-detect if not provided)
            context: Additional context to help with translation accuracy
            use_cache: Whether to use cached translations

        Returns:
            Dictionary with translated text and metadata

        Raises:
            ValueError: If target language is not supported
        """
        # Validate target language
        if not is_supported_translation_language(target_language):
            raise ValueError(
                f"Unsupported target language: {target_language}. "
                f"Supported languages: {', '.join(SUPPORTED_LANGUAGES.keys())}"
            )

        # Check cache first
        if use_cache:
            cached_translation = self._get_cached_translation(text, target_language, source_language)
            if cached_translation:
                return {
                    "original_text": text,
                    "translated_text": cached_translation,
                    "target_language": target_language,
                    "source_language": source_language,
                    "cached": True,
                }

        # Build the translation prompt
        target_lang_name = get_language_name(target_language)
        source_info = ""
        if source_language:
            source_lang_name = get_language_name(source_language)
            if source_lang_name:
                source_info = f"The source text is in {source_lang_name}. "

        context_info = ""
        if context:
            context_info = f"\n\nContext for translation: {context}"

        prompt = f"""You are an expert translator. Translate the following text to {target_lang_name}.
{source_info}
Provide ONLY the translated text without any explanations, notes, or the original text.
Maintain the original formatting, tone, and meaning as accurately as possible.
{context_info}

Text to translate:
{text}

Translated text:"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )

            translated_text = response.content[0].text.strip()

            # Cache the translation
            if use_cache:
                self._cache_translation(text, translated_text, target_language, source_language)

            logger.info(f"Translated text to {target_language} ({len(text)} chars -> {len(translated_text)} chars)")

            return {
                "original_text": text,
                "translated_text": translated_text,
                "target_language": target_language,
                "source_language": source_language,
                "cached": False,
            }

        except Exception as e:
            logger.error(f"Translation error: {e}")
            raise RuntimeError(f"Translation failed: {str(e)}")

    async def translate_batch(
        self,
        texts: List[str],
        target_language: str,
        source_language: Optional[str] = None,
        context: Optional[str] = None,
        use_cache: bool = True,
    ) -> List[Dict[str, Any]]:
        """Translate multiple texts to the target language.

        Args:
            texts: List of texts to translate
            target_language: Target language code
            source_language: Source language code (optional)
            context: Additional context for translation
            use_cache: Whether to use cached translations

        Returns:
            List of translation results
        """
        # Validate target language
        if not is_supported_translation_language(target_language):
            raise ValueError(
                f"Unsupported target language: {target_language}. "
                f"Supported languages: {', '.join(SUPPORTED_LANGUAGES.keys())}"
            )

        # Check cache for each text
        results = []
        texts_to_translate = []
        indices_to_translate = []

        for i, text in enumerate(texts):
            if use_cache:
                cached = self._get_cached_translation(text, target_language, source_language)
                if cached:
                    results.append({
                        "original_text": text,
                        "translated_text": cached,
                        "target_language": target_language,
                        "source_language": source_language,
                        "cached": True,
                        "index": i,
                    })
                    continue

            texts_to_translate.append(text)
            indices_to_translate.append(i)
            results.append(None)  # Placeholder

        # If all texts were cached, return early
        if not texts_to_translate:
            # Remove index field and sort by original order
            return [r for r in results if r is not None]

        # Build batch translation prompt
        target_lang_name = get_language_name(target_language)
        source_info = ""
        if source_language:
            source_lang_name = get_language_name(source_language)
            if source_lang_name:
                source_info = f"The source texts are in {source_lang_name}. "

        context_info = ""
        if context:
            context_info = f"\n\nContext for translations: {context}"

        # Format texts with numbers for batch processing
        numbered_texts = "\n".join(
            f"[{i+1}] {text}" for i, text in enumerate(texts_to_translate)
        )

        prompt = f"""You are an expert translator. Translate each of the following numbered texts to {target_lang_name}.
{source_info}
Provide ONLY the translated texts in the same numbered format without any explanations or the original text.
Maintain the original formatting, tone, and meaning as accurately as possible.
{context_info}

Texts to translate:
{numbered_texts}

Translated texts:"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=8192,  # Larger limit for batch
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = response.content[0].text.strip()

            # Parse the numbered responses
            translations = self._parse_numbered_translations(response_text, len(texts_to_translate))

            # Fill in the results
            for i, (original_idx, text, translation) in enumerate(
                zip(indices_to_translate, texts_to_translate, translations)
            ):
                # Cache each translation
                if use_cache:
                    self._cache_translation(text, translation, target_language, source_language)

                results[original_idx] = {
                    "original_text": text,
                    "translated_text": translation,
                    "target_language": target_language,
                    "source_language": source_language,
                    "cached": False,
                }

            logger.info(f"Batch translated {len(texts_to_translate)} texts to {target_language}")

            # Remove None placeholders and return
            return [r for r in results if r is not None]

        except Exception as e:
            logger.error(f"Batch translation error: {e}")
            raise RuntimeError(f"Batch translation failed: {str(e)}")

    def _parse_numbered_translations(self, response: str, expected_count: int) -> List[str]:
        """Parse numbered translations from Claude's response.

        Args:
            response: The response text from Claude
            expected_count: Expected number of translations

        Returns:
            List of translated texts
        """
        translations = []
        lines = response.strip().split("\n")
        current_translation = []
        current_number = 0

        for line in lines:
            # Check if this is a new numbered item
            if line.strip().startswith("[") and "]" in line:
                # Save previous translation if any
                if current_translation and current_number > 0:
                    translations.append(" ".join(current_translation).strip())

                # Extract the number and start new translation
                try:
                    bracket_end = line.index("]")
                    current_number = int(line[1:bracket_end])
                    current_translation = [line[bracket_end + 1:].strip()]
                except (ValueError, IndexError):
                    current_translation.append(line)
            else:
                current_translation.append(line)

        # Don't forget the last translation
        if current_translation:
            translations.append(" ".join(current_translation).strip())

        # If parsing failed, try simpler approach
        if len(translations) != expected_count:
            # Split by double newlines as fallback
            translations = [t.strip() for t in response.split("\n\n") if t.strip()]

        # Ensure we have the right count
        while len(translations) < expected_count:
            translations.append("[Translation failed]")

        return translations[:expected_count]

    async def translate_meeting_transcript(
        self,
        meeting_id: int,
        target_language: str,
        user_id: int,
    ) -> Dict[str, Any]:
        """Translate an entire meeting transcript to the target language.

        Args:
            meeting_id: The meeting ID
            target_language: Target language code
            user_id: The user ID (for authorization)

        Returns:
            Dictionary with translated transcript segments
        """
        from models import Meeting, Conversation

        # Validate target language
        if not is_supported_translation_language(target_language):
            raise ValueError(
                f"Unsupported target language: {target_language}. "
                f"Supported languages: {', '.join(SUPPORTED_LANGUAGES.keys())}"
            )

        # Get meeting and verify ownership
        meeting = self.db.query(Meeting).filter(
            Meeting.id == meeting_id,
            Meeting.user_id == user_id
        ).first()

        if not meeting:
            raise ValueError(f"Meeting {meeting_id} not found")

        # Get all conversations
        conversations = self.db.query(Conversation).filter(
            Conversation.meeting_id == meeting_id
        ).order_by(Conversation.timestamp).all()

        if not conversations:
            return {
                "meeting_id": meeting_id,
                "target_language": target_language,
                "translated_segments": [],
                "total_segments": 0,
            }

        # Extract texts to translate
        texts = [conv.heard_text for conv in conversations]

        # Context for better translation
        context = f"Meeting transcript: {meeting.title or 'Meeting'}, Type: {meeting.meeting_type or 'general'}"

        # Batch translate
        translations = await self.translate_batch(
            texts=texts,
            target_language=target_language,
            context=context,
            use_cache=True,
        )

        # Build result with conversation metadata
        translated_segments = []
        for conv, trans in zip(conversations, translations):
            translated_segments.append({
                "id": conv.id,
                "speaker": conv.speaker,
                "timestamp": conv.timestamp.isoformat() if conv.timestamp else None,
                "original_text": conv.heard_text,
                "translated_text": trans["translated_text"],
                "cached": trans["cached"],
            })

        logger.info(f"Translated meeting {meeting_id} transcript ({len(conversations)} segments) to {target_language}")

        return {
            "meeting_id": meeting_id,
            "meeting_title": meeting.title,
            "target_language": target_language,
            "target_language_name": get_language_name(target_language),
            "translated_segments": translated_segments,
            "total_segments": len(translated_segments),
            "translated_at": datetime.utcnow().isoformat(),
        }

    async def detect_language(self, text: str) -> Dict[str, Any]:
        """Detect the language of a text using Claude AI.

        Args:
            text: The text to analyze

        Returns:
            Dictionary with detected language information
        """
        prompt = f"""Analyze the following text and determine what language it is written in.
Return ONLY a JSON object with the following format:
{{"language_code": "xx", "language_name": "Language Name", "confidence": 0.95}}

Use ISO 639-1 language codes (e.g., en, es, fr, de, zh, ja, ko, ar, hi, sw).
The confidence should be a number between 0 and 1.

Text to analyze:
{text[:1000]}"""  # Limit text length for detection

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=256,
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = response.content[0].text.strip()

            # Parse JSON response
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]

            result = json.loads(response_text.strip())

            logger.info(f"Detected language: {result.get('language_code')} with confidence {result.get('confidence')}")

            return result

        except json.JSONDecodeError:
            logger.warning("Failed to parse language detection response")
            return {
                "language_code": "en",
                "language_name": "English",
                "confidence": 0.0,
                "error": "Could not parse detection response",
            }
        except Exception as e:
            logger.error(f"Language detection error: {e}")
            return {
                "language_code": None,
                "language_name": None,
                "confidence": 0.0,
                "error": str(e),
            }
