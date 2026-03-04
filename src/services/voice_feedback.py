"""
Voice Feedback Service

Provides text-to-speech functionality using pyttsx3 to speak AI responses aloud.
Runs speech synthesis in a background thread to avoid blocking the UI.
"""

import logging
import threading
import queue
from typing import Optional, Callable

logger = logging.getLogger(__name__)

# Check if pyttsx3 is available
PYTTSX3_AVAILABLE = False
try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    logger.info("pyttsx3 not installed - voice feedback will be unavailable")


def is_voice_feedback_available() -> bool:
    """Check if voice feedback is available on this system."""
    return PYTTSX3_AVAILABLE


class VoiceFeedback:
    """
    Text-to-speech service for speaking AI responses aloud.

    Uses pyttsx3 for cross-platform text-to-speech synthesis.
    Speech is processed in a background thread to avoid blocking.
    """

    def __init__(
        self,
        rate: int = 150,
        volume: float = 0.8,
        on_speech_started: Optional[Callable[[], None]] = None,
        on_speech_finished: Optional[Callable[[], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ):
        """
        Initialize voice feedback service.

        Args:
            rate: Speech rate in words per minute (50-300)
            volume: Speech volume (0.0-1.0)
            on_speech_started: Callback when speech starts
            on_speech_finished: Callback when speech finishes
            on_error: Callback for error handling
        """
        self._rate = max(50, min(300, rate))
        self._volume = max(0.0, min(1.0, volume))
        self._enabled = False
        self._is_running = False
        self._is_speaking = False

        # Callbacks
        self._on_speech_started = on_speech_started
        self._on_speech_finished = on_speech_finished
        self._on_error = on_error

        # Thread-safe queue for speech requests
        self._speech_queue: queue.Queue = queue.Queue()
        self._worker_thread: Optional[threading.Thread] = None
        self._engine = None
        self._stop_event = threading.Event()

        # Lock for engine access
        self._engine_lock = threading.Lock()

    @property
    def is_available(self) -> bool:
        """Check if voice feedback is available."""
        return PYTTSX3_AVAILABLE

    @property
    def is_running(self) -> bool:
        """Check if the service is running."""
        return self._is_running

    @property
    def is_speaking(self) -> bool:
        """Check if currently speaking."""
        return self._is_speaking

    @property
    def is_enabled(self) -> bool:
        """Check if voice feedback is enabled."""
        return self._enabled

    def set_enabled(self, enabled: bool):
        """Enable or disable voice feedback."""
        self._enabled = enabled
        if enabled and not self._is_running:
            self.start()
        logger.info(f"Voice feedback {'enabled' if enabled else 'disabled'}")

    def set_rate(self, rate: int):
        """
        Set speech rate.

        Args:
            rate: Words per minute (50-300)
        """
        self._rate = max(50, min(300, rate))
        # Update engine if running
        with self._engine_lock:
            if self._engine:
                try:
                    self._engine.setProperty('rate', self._rate)
                except Exception as e:
                    logger.warning(f"Failed to set speech rate: {e}")
        logger.debug(f"Voice feedback rate set to {self._rate}")

    def set_volume(self, volume: float):
        """
        Set speech volume.

        Args:
            volume: Volume level (0.0-1.0)
        """
        self._volume = max(0.0, min(1.0, volume))
        # Update engine if running
        with self._engine_lock:
            if self._engine:
                try:
                    self._engine.setProperty('volume', self._volume)
                except Exception as e:
                    logger.warning(f"Failed to set speech volume: {e}")
        logger.debug(f"Voice feedback volume set to {self._volume}")

    def start(self) -> bool:
        """
        Start the voice feedback service.

        Returns:
            True if started successfully, False otherwise.
        """
        if not PYTTSX3_AVAILABLE:
            logger.warning("Cannot start voice feedback - pyttsx3 not available")
            return False

        if self._is_running:
            return True

        self._stop_event.clear()
        self._is_running = True

        # Start worker thread
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name="VoiceFeedbackWorker"
        )
        self._worker_thread.start()

        logger.info("Voice feedback service started")
        return True

    def stop(self):
        """Stop the voice feedback service."""
        if not self._is_running:
            return

        self._is_running = False
        self._stop_event.set()

        # Clear the queue
        while not self._speech_queue.empty():
            try:
                self._speech_queue.get_nowait()
            except queue.Empty:
                break

        # Stop current speech
        self.stop_speaking()

        # Wait for worker thread
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2.0)

        self._worker_thread = None
        logger.info("Voice feedback service stopped")

    def speak(self, text: str, interrupt: bool = False):
        """
        Queue text to be spoken.

        Args:
            text: Text to speak
            interrupt: If True, stop current speech and speak immediately
        """
        if not self._enabled or not self._is_running:
            return

        if not text or not text.strip():
            return

        # Clean up text for speech
        clean_text = self._clean_text_for_speech(text)
        if not clean_text:
            return

        if interrupt:
            # Clear queue and stop current speech
            while not self._speech_queue.empty():
                try:
                    self._speech_queue.get_nowait()
                except queue.Empty:
                    break
            self.stop_speaking()

        # Add to queue
        self._speech_queue.put(clean_text)
        logger.debug(f"Queued speech: {clean_text[:50]}...")

    def stop_speaking(self):
        """Stop current speech immediately."""
        with self._engine_lock:
            if self._engine and self._is_speaking:
                try:
                    self._engine.stop()
                except Exception as e:
                    logger.debug(f"Error stopping speech: {e}")

    def _clean_text_for_speech(self, text: str) -> str:
        """
        Clean text for better speech synthesis.

        Args:
            text: Raw text

        Returns:
            Cleaned text suitable for speech
        """
        import re

        # Remove bullet points and list markers
        text = re.sub(r'^[\s]*[-*]\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'^[\s]*\d+\.\s*', '', text, flags=re.MULTILINE)

        # Remove markdown formatting
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # Bold
        text = re.sub(r'\*([^*]+)\*', r'\1', text)  # Italic
        text = re.sub(r'`([^`]+)`', r'\1', text)  # Code
        text = re.sub(r'#{1,6}\s*', '', text)  # Headers

        # Remove URLs
        text = re.sub(r'https?://\S+', '', text)

        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()

        return text

    def _worker_loop(self):
        """Background worker loop for speech synthesis."""
        # Initialize engine in worker thread (pyttsx3 requirement)
        try:
            self._engine = pyttsx3.init()
            self._engine.setProperty('rate', self._rate)
            self._engine.setProperty('volume', self._volume)
            logger.debug("pyttsx3 engine initialized")
        except Exception as e:
            error_msg = f"Failed to initialize pyttsx3 engine: {e}"
            logger.error(error_msg)
            if self._on_error:
                self._on_error(error_msg)
            self._is_running = False
            return

        while self._is_running and not self._stop_event.is_set():
            try:
                # Wait for speech request with timeout
                try:
                    text = self._speech_queue.get(timeout=0.5)
                except queue.Empty:
                    continue

                if not text or self._stop_event.is_set():
                    continue

                # Speak the text
                self._is_speaking = True

                if self._on_speech_started:
                    try:
                        self._on_speech_started()
                    except Exception as e:
                        logger.debug(f"Error in speech started callback: {e}")

                try:
                    with self._engine_lock:
                        if self._engine and not self._stop_event.is_set():
                            self._engine.say(text)
                            self._engine.runAndWait()
                except Exception as e:
                    error_msg = f"Speech synthesis error: {e}"
                    logger.error(error_msg)
                    if self._on_error:
                        try:
                            self._on_error(error_msg)
                        except Exception:
                            pass
                finally:
                    self._is_speaking = False

                    if self._on_speech_finished:
                        try:
                            self._on_speech_finished()
                        except Exception as e:
                            logger.debug(f"Error in speech finished callback: {e}")

            except Exception as e:
                logger.error(f"Voice feedback worker error: {e}")
                self._is_speaking = False

        # Cleanup engine
        with self._engine_lock:
            if self._engine:
                try:
                    self._engine.stop()
                except Exception:
                    pass
                self._engine = None

        logger.debug("Voice feedback worker stopped")

    def get_available_voices(self) -> list:
        """
        Get list of available voices.

        Returns:
            List of voice dictionaries with 'id', 'name', and 'languages' keys.
        """
        voices = []

        if not PYTTSX3_AVAILABLE:
            return voices

        try:
            # Create temporary engine to query voices
            temp_engine = pyttsx3.init()
            engine_voices = temp_engine.getProperty('voices')

            for voice in engine_voices:
                voices.append({
                    'id': voice.id,
                    'name': voice.name,
                    'languages': getattr(voice, 'languages', []),
                })

            temp_engine.stop()
        except Exception as e:
            logger.warning(f"Failed to get available voices: {e}")

        return voices

    def get_status(self) -> dict:
        """
        Get current service status.

        Returns:
            Dictionary with status information.
        """
        return {
            'available': PYTTSX3_AVAILABLE,
            'enabled': self._enabled,
            'is_running': self._is_running,
            'is_speaking': self._is_speaking,
            'rate': self._rate,
            'volume': self._volume,
            'queue_size': self._speech_queue.qsize(),
        }


# Module-level singleton instance
_voice_feedback_instance: Optional[VoiceFeedback] = None
_instance_lock = threading.Lock()


def get_voice_feedback() -> VoiceFeedback:
    """
    Get or create the singleton VoiceFeedback instance.

    Returns:
        VoiceFeedback instance.
    """
    global _voice_feedback_instance

    with _instance_lock:
        if _voice_feedback_instance is None:
            _voice_feedback_instance = VoiceFeedback()
        return _voice_feedback_instance
