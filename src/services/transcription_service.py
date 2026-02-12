"""
Transcription service for speech-to-text.

Provides:
- Local Whisper transcription using faster-whisper
- Streaming transcription support
- Language detection
- VAD (Voice Activity Detection)
"""

import logging
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass
from enum import Enum, auto
import threading
import queue
import time

import numpy as np

logger = logging.getLogger(__name__)


class TranscriptionModel(Enum):
    """Available transcription models (faster-whisper format)."""
    TINY = "tiny"
    TINY_EN = "tiny.en"
    BASE = "base"
    BASE_EN = "base.en"
    SMALL = "small"
    SMALL_EN = "small.en"
    MEDIUM = "medium"
    MEDIUM_EN = "medium.en"
    LARGE = "large-v2"
    LARGE_V3 = "large-v3"


@dataclass
class TranscriptionResult:
    """Transcription result."""
    text: str
    language: str
    confidence: float
    timestamp: float
    duration: float
    is_final: bool
    segments: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.segments is None:
            self.segments = []


class TranscriptionService:
    """
    Service for speech-to-text transcription.

    Uses local faster-whisper model for privacy-first transcription.
    """

    def __init__(self, model: TranscriptionModel = TranscriptionModel.BASE_EN):
        """
        Initialize transcription service.

        Args:
            model: Whisper model to use
        """
        self._model_name = model.value
        self._model = None
        self._is_running = False
        self._audio_queue: queue.Queue = queue.Queue()
        self._process_thread: Optional[threading.Thread] = None
        self._listeners: List[Callable[[TranscriptionResult], None]] = []
        self._language = "en"
        self._min_confidence = 0.3  # Lowered for faster-whisper
        self._use_vad = True
        self._compute_type = "int8"  # Faster on CPU
        self._device = "cpu"

    @property
    def is_running(self) -> bool:
        """Check if transcription is running."""
        return self._is_running

    def set_language(self, language: str):
        """Set transcription language."""
        self._language = language
        logger.info(f"Transcription language set to: {language}")

    def set_min_confidence(self, confidence: float):
        """Set minimum confidence threshold."""
        self._min_confidence = max(0.0, min(1.0, confidence))

    def add_listener(self, callback: Callable[[TranscriptionResult], None]):
        """Add transcription result listener."""
        self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[TranscriptionResult], None]):
        """Remove transcription result listener."""
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify_listeners(self, result: TranscriptionResult):
        """Notify listeners of transcription result."""
        for listener in self._listeners:
            try:
                listener(result)
            except Exception as e:
                logger.error(f"Error in transcription listener: {e}")

    def set_vad_enabled(self, enabled: bool):
        """Enable or disable Voice Activity Detection."""
        self._use_vad = enabled
        logger.info(f"VAD {'enabled' if enabled else 'disabled'}")

    def set_compute_type(self, compute_type: str):
        """Set compute type (int8, float16, float32)."""
        self._compute_type = compute_type

    def set_device(self, device: str):
        """Set device (cpu, cuda, auto)."""
        self._device = device

    def load_model(self) -> bool:
        """
        Load the faster-whisper model.

        Returns:
            True if model loaded successfully
        """
        if self._model is not None:
            return True

        try:
            from faster_whisper import WhisperModel

            logger.info(f"Loading faster-whisper model: {self._model_name}")

            # Determine device
            device = self._device
            if device == "auto":
                try:
                    import torch
                    device = "cuda" if torch.cuda.is_available() else "cpu"
                except ImportError:
                    device = "cpu"

            self._model = WhisperModel(
                self._model_name,
                device=device,
                compute_type=self._compute_type
            )
            logger.info(f"faster-whisper model loaded successfully (device: {device})")
            return True

        except ImportError:
            logger.error("faster-whisper not installed. Run: pip install faster-whisper")
            return False
        except Exception as e:
            logger.error(f"Failed to load faster-whisper model: {e}")
            return False

    def start(self) -> bool:
        """
        Start transcription service.

        Returns:
            True if started successfully
        """
        if self._is_running:
            return True

        if not self.load_model():
            return False

        self._is_running = True
        self._process_thread = threading.Thread(
            target=self._process_loop,
            daemon=True
        )
        self._process_thread.start()

        logger.info("Transcription service started")
        return True

    def stop(self):
        """Stop transcription service."""
        self._is_running = False

        if self._process_thread and self._process_thread.is_alive():
            self._process_thread.join(timeout=2.0)

        self._process_thread = None
        logger.info("Transcription service stopped")

    def process_audio(self, audio_data: bytes, sample_rate: int = 16000):
        """
        Add audio data for transcription.

        Args:
            audio_data: Raw audio bytes
            sample_rate: Audio sample rate
        """
        if self._is_running:
            self._audio_queue.put((audio_data, sample_rate, time.time()))

    def _process_loop(self):
        """Transcription processing loop using faster-whisper."""
        audio_buffer = []
        buffer_duration = 0
        min_duration = 2.0  # Minimum audio duration to process (faster-whisper works better with more context)
        max_duration = 30.0  # Maximum audio duration
        sample_rate = 16000

        while self._is_running:
            try:
                # Get audio from queue
                try:
                    audio_data, sr, timestamp = self._audio_queue.get(timeout=0.1)
                    sample_rate = sr

                    # Convert to numpy array if bytes
                    if isinstance(audio_data, bytes):
                        audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
                    elif isinstance(audio_data, np.ndarray):
                        audio_np = audio_data.astype(np.float32)
                        if np.abs(audio_np).max() > 1.5:
                            audio_np = audio_np / 32768.0
                    else:
                        continue

                    audio_buffer.append(audio_np.flatten())
                    buffer_duration += len(audio_np.flatten()) / sample_rate

                except queue.Empty:
                    continue

                # Process when we have enough audio
                if buffer_duration >= min_duration:
                    # Concatenate buffer
                    full_audio = np.concatenate(audio_buffer)

                    # Skip if audio is too quiet (silence)
                    if np.abs(full_audio).max() < 0.01:
                        audio_buffer = []
                        buffer_duration = 0
                        continue

                    # Transcribe with faster-whisper
                    transcribe_options = {
                        "beam_size": 1,  # Faster
                        "best_of": 1,
                        "without_timestamps": True,
                    }

                    # Add VAD if enabled
                    if self._use_vad:
                        transcribe_options["vad_filter"] = True
                        transcribe_options["vad_parameters"] = {
                            "min_silence_duration_ms": 500,
                            "speech_pad_ms": 200,
                        }

                    # Add language if specified (None for auto-detect)
                    if self._language and self._language != "auto":
                        transcribe_options["language"] = self._language

                    segments, info = self._model.transcribe(
                        full_audio,
                        **transcribe_options
                    )

                    # Collect text from segments
                    text_parts = []
                    segment_data = []
                    total_prob = 0
                    segment_count = 0

                    for segment in segments:
                        text = segment.text.strip()
                        if text:
                            text_parts.append(text)
                            segment_data.append({
                                "start": segment.start,
                                "end": segment.end,
                                "text": text,
                                "avg_logprob": segment.avg_logprob,
                            })
                            total_prob += segment.avg_logprob
                            segment_count += 1

                    if text_parts:
                        full_text = " ".join(text_parts)

                        # Calculate confidence from average log probability
                        if segment_count > 0:
                            avg_prob = total_prob / segment_count
                            # Convert log prob to 0-1 scale (log probs typically -0.5 to 0)
                            confidence = min(1.0, max(0.0, 1.0 + avg_prob))
                        else:
                            confidence = 0.5

                        if confidence >= self._min_confidence:
                            transcription = TranscriptionResult(
                                text=full_text,
                                language=info.language if info.language else self._language,
                                confidence=confidence,
                                timestamp=timestamp,
                                duration=buffer_duration,
                                is_final=True,
                                segments=segment_data,
                            )

                            self._notify_listeners(transcription)

                    # Reset buffer
                    audio_buffer = []
                    buffer_duration = 0

                # Prevent buffer from growing too large
                if buffer_duration > max_duration:
                    # Keep last portion
                    keep_duration = max_duration * 0.3
                    keep_samples = int(keep_duration * sample_rate)
                    combined = np.concatenate(audio_buffer)
                    audio_buffer = [combined[-keep_samples:]]
                    buffer_duration = keep_duration

            except Exception as e:
                logger.error(f"Transcription error: {e}")
                audio_buffer = []
                buffer_duration = 0

    def transcribe_file(self, file_path: str) -> Optional[TranscriptionResult]:
        """
        Transcribe an audio file using faster-whisper.

        Args:
            file_path: Path to audio file

        Returns:
            Transcription result or None on error
        """
        if not self.load_model():
            return None

        try:
            start_time = time.time()

            # Transcribe options
            transcribe_options = {
                "beam_size": 5,  # More accurate for files
                "best_of": 5,
            }

            if self._use_vad:
                transcribe_options["vad_filter"] = True

            if self._language and self._language != "auto":
                transcribe_options["language"] = self._language

            segments, info = self._model.transcribe(
                file_path,
                **transcribe_options
            )

            # Collect all segments
            text_parts = []
            segment_data = []
            total_prob = 0
            segment_count = 0

            for segment in segments:
                text = segment.text.strip()
                if text:
                    text_parts.append(text)
                    segment_data.append({
                        "start": segment.start,
                        "end": segment.end,
                        "text": text,
                        "avg_logprob": segment.avg_logprob,
                    })
                    total_prob += segment.avg_logprob
                    segment_count += 1

            full_text = " ".join(text_parts)
            confidence = 0.8
            if segment_count > 0:
                avg_prob = total_prob / segment_count
                confidence = min(1.0, max(0.0, 1.0 + avg_prob))

            return TranscriptionResult(
                text=full_text,
                language=info.language if info.language else self._language,
                confidence=confidence,
                timestamp=start_time,
                duration=time.time() - start_time,
                is_final=True,
                segments=segment_data,
            )

        except Exception as e:
            logger.error(f"File transcription error: {e}")
            return None

    def get_status(self) -> Dict[str, Any]:
        """Get transcription service status."""
        return {
            "is_running": self._is_running,
            "model": self._model_name,
            "model_loaded": self._model is not None,
            "language": self._language,
            "min_confidence": self._min_confidence,
            "queue_size": self._audio_queue.qsize(),
            "vad_enabled": self._use_vad,
            "compute_type": self._compute_type,
            "device": self._device,
        }
