"""Real-time speech-to-text using faster-whisper."""

import threading
import queue
from typing import Callable, Optional

import numpy as np

from config import WHISPER_MODEL


class Transcriber:
    """Real-time transcription using faster-whisper."""

    def __init__(self, on_transcription: Callable[[str], None]):
        self.on_transcription = on_transcription
        self._model = None
        self._audio_queue: queue.Queue = queue.Queue()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def _load_model(self):
        """Load the Whisper model (lazy loading)."""
        if self._model is None:
            from faster_whisper import WhisperModel
            # Use CPU by default, can switch to CUDA if available
            self._model = WhisperModel(
                WHISPER_MODEL,
                device="cpu",
                compute_type="int8"  # Faster on CPU
            )

    def _transcribe_loop(self):
        """Main transcription loop."""
        self._load_model()

        while self._running:
            try:
                audio_chunk = self._audio_queue.get(timeout=0.5)

                # Skip silent audio
                if np.abs(audio_chunk).max() < 0.01:
                    continue

                # Transcribe
                segments, info = self._model.transcribe(
                    audio_chunk,
                    beam_size=1,  # Faster
                    language="en",
                    vad_filter=True,  # Filter out non-speech
                    vad_parameters=dict(
                        min_silence_duration_ms=500,
                        speech_pad_ms=200,
                    )
                )

                # Collect transcription
                text_parts = []
                for segment in segments:
                    text = segment.text.strip()
                    if text:
                        text_parts.append(text)

                if text_parts:
                    full_text = " ".join(text_parts)
                    self.on_transcription(full_text)

            except queue.Empty:
                continue
            except Exception as e:
                print(f"Transcription error: {e}")

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
