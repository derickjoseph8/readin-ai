"""
Real-time translation service using Claude Haiku for fast translations.

Provides:
- Support for 12+ languages
- Language auto-detection
- Async translation with callbacks
- Caching to avoid duplicate translations
"""

import logging
import threading
import queue
import time
from typing import Callable, Optional, Dict, List, Tuple
from dataclasses import dataclass
from collections import OrderedDict

logger = logging.getLogger(__name__)

# Translation model - use Haiku for fast, cost-effective translations
TRANSLATION_MODEL = "claude-3-haiku-20240307"

# Supported languages with their codes and native names
SUPPORTED_LANGUAGES: List[Tuple[str, str, str]] = [
    ("en", "English", "English"),
    ("es", "Spanish", "Espanol"),
    ("fr", "French", "Francais"),
    ("de", "German", "Deutsch"),
    ("it", "Italian", "Italiano"),
    ("pt", "Portuguese", "Portugues"),
    ("nl", "Dutch", "Nederlands"),
    ("pl", "Polish", "Polski"),
    ("ru", "Russian", "Russkiy"),
    ("ja", "Japanese", "Nihongo"),
    ("zh", "Chinese", "Zhongwen"),
    ("ko", "Korean", "Hangugeo"),
    ("ar", "Arabic", "Al-Arabiyyah"),
    ("hi", "Hindi", "Hindi"),
    ("tr", "Turkish", "Turkce"),
    ("vi", "Vietnamese", "Tieng Viet"),
    ("th", "Thai", "Phasa Thai"),
    ("id", "Indonesian", "Bahasa Indonesia"),
    ("uk", "Ukrainian", "Ukrayinska"),
    ("cs", "Czech", "Cestina"),
    ("sv", "Swedish", "Svenska"),
    ("da", "Danish", "Dansk"),
    ("fi", "Finnish", "Suomi"),
    ("no", "Norwegian", "Norsk"),
    ("el", "Greek", "Ellinika"),
    ("he", "Hebrew", "Ivrit"),
    ("ro", "Romanian", "Romana"),
    ("hu", "Hungarian", "Magyar"),
]

# Language code to name mapping for quick lookup
LANGUAGE_NAMES: Dict[str, str] = {code: name for code, name, _ in SUPPORTED_LANGUAGES}
LANGUAGE_NATIVE_NAMES: Dict[str, str] = {code: native for code, _, native in SUPPORTED_LANGUAGES}


@dataclass
class TranslationResult:
    """Result of a translation request."""
    original_text: str
    translated_text: str
    source_language: str  # Detected or specified
    target_language: str
    confidence: float
    latency_ms: float
    from_cache: bool = False


class LRUCache:
    """Simple LRU cache for translations."""

    def __init__(self, max_size: int = 500):
        self._cache: OrderedDict = OrderedDict()
        self._max_size = max_size
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[str]:
        """Get item from cache, moving to end (most recently used)."""
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
            return None

    def put(self, key: str, value: str):
        """Put item in cache, evicting oldest if full."""
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            else:
                if len(self._cache) >= self._max_size:
                    self._cache.popitem(last=False)
            self._cache[key] = value

    def clear(self):
        """Clear the cache."""
        with self._lock:
            self._cache.clear()


class TranslationService:
    """
    Real-time translation service using Claude Haiku.

    Provides fast translations with language auto-detection and caching.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize translation service.

        Args:
            api_key: Anthropic API key (optional, uses env if not provided)
        """
        self._api_key = api_key
        self._client = None
        self._is_running = False
        self._is_translating = False
        self._request_queue: queue.Queue = queue.Queue()
        self._process_thread: Optional[threading.Thread] = None
        self._listeners: List[Callable[[TranslationResult], None]] = []
        self._error_listeners: List[Callable[[str], None]] = []
        self._target_language = "en"
        self._enabled = False
        self._show_original = True
        self._cache = LRUCache(max_size=500)
        self._model = TRANSLATION_MODEL
        self._max_tokens = 500  # Enough for most translations

    @property
    def is_running(self) -> bool:
        """Check if translation service is running."""
        return self._is_running

    @property
    def is_enabled(self) -> bool:
        """Check if translation is enabled."""
        return self._enabled

    @property
    def target_language(self) -> str:
        """Get current target language."""
        return self._target_language

    @property
    def show_original(self) -> bool:
        """Check if original text should be shown."""
        return self._show_original

    @staticmethod
    def get_supported_languages() -> List[Tuple[str, str, str]]:
        """Get list of supported languages.

        Returns:
            List of (code, english_name, native_name) tuples
        """
        return SUPPORTED_LANGUAGES.copy()

    @staticmethod
    def get_language_name(code: str) -> str:
        """Get English name for language code."""
        return LANGUAGE_NAMES.get(code, code)

    @staticmethod
    def get_language_native_name(code: str) -> str:
        """Get native name for language code."""
        return LANGUAGE_NATIVE_NAMES.get(code, code)

    def set_enabled(self, enabled: bool):
        """Enable or disable translation."""
        self._enabled = enabled
        logger.info(f"Translation {'enabled' if enabled else 'disabled'}")

    def set_target_language(self, language_code: str):
        """Set the target translation language.

        Args:
            language_code: ISO 639-1 language code (e.g., 'es', 'fr')
        """
        if language_code in LANGUAGE_NAMES:
            self._target_language = language_code
            logger.info(f"Target language set to: {LANGUAGE_NAMES[language_code]}")
        else:
            logger.warning(f"Unknown language code: {language_code}")

    def set_show_original(self, show: bool):
        """Set whether to show original text alongside translation."""
        self._show_original = show

    def add_listener(self, callback: Callable[[TranslationResult], None]):
        """Add translation result listener."""
        self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[TranslationResult], None]):
        """Remove translation result listener."""
        if callback in self._listeners:
            self._listeners.remove(callback)

    def add_error_listener(self, callback: Callable[[str], None]):
        """Add error listener."""
        self._error_listeners.append(callback)

    def remove_error_listener(self, callback: Callable[[str], None]):
        """Remove error listener."""
        if callback in self._error_listeners:
            self._error_listeners.remove(callback)

    def _notify_listeners(self, result: TranslationResult):
        """Notify listeners of translation result."""
        for listener in self._listeners:
            try:
                listener(result)
            except Exception as e:
                logger.error(f"Error in translation listener: {e}")

    def _notify_error(self, error: str):
        """Notify error listeners."""
        for listener in self._error_listeners:
            try:
                listener(error)
            except Exception as e:
                logger.error(f"Error in error listener: {e}")

    def _init_client(self) -> bool:
        """Initialize Anthropic client."""
        if self._client is not None:
            return True

        try:
            from anthropic import Anthropic

            if self._api_key:
                self._client = Anthropic(api_key=self._api_key)
            else:
                # Try to get from environment
                self._client = Anthropic()

            return True

        except ImportError:
            logger.error("Anthropic not installed. Run: pip install anthropic")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic client: {e}")
            return False

    def start(self) -> bool:
        """Start translation service."""
        if self._is_running:
            return True

        if not self._init_client():
            logger.warning("Translation service could not initialize API client")
            return False

        self._is_running = True
        self._process_thread = threading.Thread(
            target=self._process_loop,
            daemon=True
        )
        self._process_thread.start()

        logger.info("Translation service started")
        return True

    def stop(self):
        """Stop translation service."""
        self._is_running = False

        if self._process_thread and self._process_thread.is_alive():
            self._process_thread.join(timeout=2.0)

        self._process_thread = None
        logger.info("Translation service stopped")

    def translate(self, text: str, source_language: Optional[str] = None):
        """
        Request translation of text.

        Args:
            text: Text to translate
            source_language: Source language code (auto-detect if None)
        """
        if not self._enabled or not self._is_running:
            return

        if not text or not text.strip():
            return

        # Skip if target language matches source (if known)
        if source_language and source_language == self._target_language:
            # Still notify with original text
            result = TranslationResult(
                original_text=text,
                translated_text=text,
                source_language=source_language,
                target_language=self._target_language,
                confidence=1.0,
                latency_ms=0,
                from_cache=True
            )
            self._notify_listeners(result)
            return

        self._request_queue.put({
            "text": text,
            "source_language": source_language,
            "timestamp": time.time()
        })

    def _get_cache_key(self, text: str, target_lang: str) -> str:
        """Generate cache key for translation."""
        return f"{target_lang}:{text[:200]}"  # Limit key length

    def _process_loop(self):
        """Translation processing loop."""
        while self._is_running:
            try:
                # Get request from queue
                try:
                    request = self._request_queue.get(timeout=0.1)
                except queue.Empty:
                    continue

                # Check if translation is still needed
                if not self._enabled:
                    continue

                self._is_translating = True
                start_time = time.time()

                try:
                    text = request["text"]
                    source_lang = request.get("source_language")

                    # Check cache first
                    cache_key = self._get_cache_key(text, self._target_language)
                    cached_translation = self._cache.get(cache_key)

                    if cached_translation:
                        latency_ms = (time.time() - start_time) * 1000
                        result = TranslationResult(
                            original_text=text,
                            translated_text=cached_translation,
                            source_language=source_lang or "auto",
                            target_language=self._target_language,
                            confidence=0.95,
                            latency_ms=latency_ms,
                            from_cache=True
                        )
                        self._notify_listeners(result)
                        continue

                    # Perform translation
                    translation_result = self._translate_with_claude(
                        text, source_lang
                    )

                    if translation_result:
                        translated_text, detected_lang = translation_result
                        latency_ms = (time.time() - start_time) * 1000

                        # Cache the result
                        self._cache.put(cache_key, translated_text)

                        result = TranslationResult(
                            original_text=text,
                            translated_text=translated_text,
                            source_language=detected_lang or source_lang or "auto",
                            target_language=self._target_language,
                            confidence=0.9,
                            latency_ms=latency_ms,
                            from_cache=False
                        )
                        self._notify_listeners(result)

                finally:
                    self._is_translating = False

            except Exception as e:
                logger.error(f"Translation processing error: {e}")
                self._is_translating = False
                self._notify_error(str(e))

    def _translate_with_claude(
        self,
        text: str,
        source_language: Optional[str] = None
    ) -> Optional[Tuple[str, Optional[str]]]:
        """
        Translate text using Claude Haiku.

        Args:
            text: Text to translate
            source_language: Source language (auto-detect if None)

        Returns:
            Tuple of (translated_text, detected_language) or None on error
        """
        if not self._client:
            return None

        try:
            target_name = LANGUAGE_NAMES.get(self._target_language, self._target_language)

            # Build translation prompt
            if source_language:
                source_name = LANGUAGE_NAMES.get(source_language, source_language)
                system_prompt = f"""You are a professional translator. Translate the given text from {source_name} to {target_name}.

Rules:
1. Provide ONLY the translation, no explanations or notes
2. Preserve the original meaning and tone
3. Keep formatting (line breaks, punctuation) similar to the original
4. For technical terms or names that shouldn't be translated, keep them as-is
5. Be concise and natural-sounding in the target language"""
            else:
                system_prompt = f"""You are a professional translator with automatic language detection. Translate the given text to {target_name}.

Rules:
1. First, detect the source language
2. Provide ONLY the translation, no explanations or notes
3. Preserve the original meaning and tone
4. Keep formatting (line breaks, punctuation) similar to the original
5. For technical terms or names that shouldn't be translated, keep them as-is
6. Be concise and natural-sounding in the target language
7. If the text is already in {target_name}, return it unchanged"""

            response = self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": f"Translate:\n\n{text}"
                    }
                ]
            )

            translated = response.content[0].text.strip()

            # Try to detect language from response if not specified
            detected_lang = source_language

            return (translated, detected_lang)

        except Exception as e:
            logger.error(f"Translation API error: {e}")
            self._notify_error(f"Translation failed: {str(e)}")
            return None

    def detect_language(self, text: str) -> Optional[str]:
        """
        Detect the language of text using Claude.

        Args:
            text: Text to analyze

        Returns:
            Detected language code or None
        """
        if not self._client or not text.strip():
            return None

        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=10,
                system="""Detect the language of the given text. Respond with ONLY the ISO 639-1 two-letter language code (e.g., 'en', 'es', 'fr', 'de', 'ja', 'zh', 'ko'). Nothing else.""",
                messages=[
                    {
                        "role": "user",
                        "content": text[:500]  # Limit text length for detection
                    }
                ]
            )

            detected = response.content[0].text.strip().lower()

            # Validate it's a known language code
            if detected in LANGUAGE_NAMES:
                return detected

            return None

        except Exception as e:
            logger.error(f"Language detection error: {e}")
            return None

    def clear_cache(self):
        """Clear the translation cache."""
        self._cache.clear()
        logger.info("Translation cache cleared")

    def is_translating(self) -> bool:
        """Check if currently translating."""
        return self._is_translating

    def get_status(self) -> Dict:
        """Get translation service status."""
        return {
            "is_running": self._is_running,
            "is_enabled": self._enabled,
            "is_translating": self._is_translating,
            "has_api_client": self._client is not None,
            "target_language": self._target_language,
            "target_language_name": LANGUAGE_NAMES.get(self._target_language, "Unknown"),
            "show_original": self._show_original,
            "queue_size": self._request_queue.qsize(),
            "model": self._model,
        }


# Convenience function for one-off translations
def translate_text(
    text: str,
    target_language: str,
    source_language: Optional[str] = None,
    api_key: Optional[str] = None
) -> Optional[str]:
    """
    Convenience function for one-off translations.

    Args:
        text: Text to translate
        target_language: Target language code
        source_language: Source language code (auto-detect if None)
        api_key: Anthropic API key (uses env if not provided)

    Returns:
        Translated text or None on error
    """
    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=api_key) if api_key else Anthropic()
        target_name = LANGUAGE_NAMES.get(target_language, target_language)

        response = client.messages.create(
            model=TRANSLATION_MODEL,
            max_tokens=500,
            system=f"Translate the text to {target_name}. Respond with ONLY the translation.",
            messages=[{"role": "user", "content": text}]
        )

        return response.content[0].text.strip()

    except Exception as e:
        logger.error(f"Translation error: {e}")
        return None
