"""Real-time speech-to-text using faster-whisper with multi-language support."""

import threading
import queue
from typing import Callable, Optional, List, Tuple

import numpy as np

from config import WHISPER_MODEL


# Supported languages from Whisper
SUPPORTED_LANGUAGES: List[Tuple[str, str]] = [
    ("en", "English"),
    ("es", "Spanish"),
    ("fr", "French"),
    ("de", "German"),
    ("it", "Italian"),
    ("pt", "Portuguese"),
    ("nl", "Dutch"),
    ("pl", "Polish"),
    ("ru", "Russian"),
    ("ja", "Japanese"),
    ("zh", "Chinese"),
    ("ko", "Korean"),
    ("ar", "Arabic"),
    ("hi", "Hindi"),
    ("tr", "Turkish"),
    ("vi", "Vietnamese"),
    ("th", "Thai"),
    ("id", "Indonesian"),
    ("cs", "Czech"),
    ("ro", "Romanian"),
    ("hu", "Hungarian"),
    ("el", "Greek"),
    ("he", "Hebrew"),
    ("sv", "Swedish"),
    ("da", "Danish"),
    ("fi", "Finnish"),
    ("no", "Norwegian"),
    ("uk", "Ukrainian"),
]


class Transcriber:
    """Real-time transcription using faster-whisper with multi-language support."""

    def __init__(
        self,
        on_transcription: Callable[[str], None],
        on_error: Optional[Callable[[str], None]] = None,
        language: str = "en",
        model_name: str = WHISPER_MODEL
    ):
        """Initialize the transcriber.

        Args:
            on_transcription: Callback when transcription is ready
            on_error: Optional callback for errors
            language: Language code (e.g., 'en', 'es') or 'auto' for auto-detection
            model_name: Whisper model to use
        """
        self.on_transcription = on_transcription
        self.on_error = on_error
        self._model = None
        self._model_name = model_name
        self._language = language if language != "auto" else None
        self._audio_queue: queue.Queue = queue.Queue()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._detected_language: Optional[str] = None

    @staticmethod
    def get_supported_languages() -> List[Tuple[str, str]]:
        """Get list of supported languages.

        Returns:
            List of (code, name) tuples
        """
        return SUPPORTED_LANGUAGES.copy()

    def set_language(self, language: str):
        """Set the transcription language.

        Args:
            language: Language code (e.g., 'en') or 'auto' for auto-detection
        """
        self._language = language if language != "auto" else None
        self._detected_language = None

    def get_language(self) -> str:
        """Get the current language setting."""
        return self._language or "auto"

    def get_detected_language(self) -> Optional[str]:
        """Get the auto-detected language (if using auto-detection)."""
        return self._detected_language

    def _load_model(self):
        """Load the Whisper model (lazy loading)."""
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
                # Use CPU by default, can switch to CUDA if available
                self._model = WhisperModel(
                    self._model_name,
                    device="cpu",
                    compute_type="int8"  # Faster on CPU
                )
            except Exception as e:
                error_msg = f"Failed to load Whisper model: {e}"
                print(error_msg)
                if self.on_error:
                    self.on_error(error_msg)
                raise

    def _transcribe_loop(self):
        """Main transcription loop."""
        try:
            self._load_model()
        except Exception:
            self._running = False
            return

        while self._running:
            try:
                audio_chunk = self._audio_queue.get(timeout=0.5)

                # Skip very quiet audio (likely silence)
                # Use RMS instead of max for better silence detection
                rms = np.sqrt(np.mean(audio_chunk ** 2))
                if rms < 0.005:  # Very quiet threshold
                    continue

                # Build transcription options
                transcribe_options = {
                    "beam_size": 1,  # Faster
                    "best_of": 1,
                    "vad_filter": True,  # Filter out non-speech
                    "vad_parameters": {
                        "min_silence_duration_ms": 300,  # Shorter for responsiveness
                        "speech_pad_ms": 150,
                        "threshold": 0.3,  # Lower threshold = more sensitive
                    },
                    "without_timestamps": True,  # Faster
                }

                # Add language if specified
                if self._language:
                    transcribe_options["language"] = self._language

                # Transcribe
                segments, info = self._model.transcribe(
                    audio_chunk,
                    **transcribe_options
                )

                # Store detected language if auto-detecting
                if not self._language and info.language:
                    self._detected_language = info.language

                # Collect transcription
                text_parts = []
                for segment in segments:
                    text = segment.text.strip()
                    # Filter out common Whisper hallucinations
                    if text and not self._is_hallucination(text):
                        text_parts.append(text)

                if text_parts:
                    full_text = " ".join(text_parts)
                    self.on_transcription(full_text)

            except queue.Empty:
                continue
            except Exception as e:
                error_msg = f"Transcription error: {e}"
                print(error_msg)
                if self.on_error:
                    self.on_error(error_msg)

    def _is_hallucination(self, text: str) -> bool:
        """Check if text is a common Whisper hallucination."""
        # Common hallucinations when there's no actual speech
        hallucinations = [
            "thank you",
            "thanks for watching",
            "subscribe",
            "like and subscribe",
            "see you next time",
            "bye",
            "goodbye",
            "[music]",
            "[applause]",
            "(music)",
            "...",
            "you",
        ]
        text_lower = text.lower().strip()
        return text_lower in hallucinations or len(text_lower) < 3

    def process_audio(self, audio_chunk: np.ndarray):
        """Add audio chunk to processing queue."""
        if self._running:
            self._audio_queue.put(audio_chunk)

    def start(self):
        """Start the transcription thread."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._transcribe_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop transcription."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

    def is_running(self) -> bool:
        """Check if transcriber is active."""
        return self._running

    def clear_queue(self):
        """Clear any pending audio in the queue."""
        try:
            while True:
                self._audio_queue.get_nowait()
        except queue.Empty:
            pass
