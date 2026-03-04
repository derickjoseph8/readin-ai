"""
Speaker Diarization Service for identifying different speakers in meetings.

Uses pyannote.audio for speaker diarization to identify and label
different speakers in audio transcriptions.

Requires:
- pyannote.audio>=3.1.0
- HUGGINGFACE_TOKEN environment variable for model access
"""

import os
import logging
import threading
import tempfile
import wave
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Callable, Any
from datetime import datetime
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class SpeakerSegment:
    """Represents a segment of audio attributed to a specific speaker."""
    start: float  # Start time in seconds
    end: float  # End time in seconds
    speaker: str  # Speaker label (e.g., "SPEAKER_00", "SPEAKER_01")
    text: Optional[str] = None  # Transcribed text for this segment
    confidence: float = 1.0  # Confidence score (0-1)

    @property
    def duration(self) -> float:
        """Duration of the segment in seconds."""
        return self.end - self.start

    def overlaps(self, other: 'SpeakerSegment') -> bool:
        """Check if this segment overlaps with another."""
        return not (self.end <= other.start or self.start >= other.end)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "start": self.start,
            "end": self.end,
            "speaker": self.speaker,
            "text": self.text,
            "confidence": self.confidence,
            "duration": self.duration
        }


@dataclass
class DiarizationResult:
    """Result of speaker diarization on an audio file or buffer."""
    segments: List[SpeakerSegment] = field(default_factory=list)
    num_speakers: int = 0
    speaker_mapping: Dict[str, str] = field(default_factory=dict)  # Maps speaker IDs to custom names
    processing_time: float = 0.0
    audio_duration: float = 0.0

    def get_speaker_segments(self, speaker: str) -> List[SpeakerSegment]:
        """Get all segments for a specific speaker."""
        speaker_id = self._resolve_speaker(speaker)
        return [s for s in self.segments if s.speaker == speaker_id]

    def get_speaker_duration(self, speaker: str) -> float:
        """Get total speaking time for a speaker in seconds."""
        return sum(s.duration for s in self.get_speaker_segments(speaker))

    def get_speaker_percentage(self, speaker: str) -> float:
        """Get percentage of time a speaker spoke."""
        if self.audio_duration == 0:
            return 0.0
        return (self.get_speaker_duration(speaker) / self.audio_duration) * 100

    def _resolve_speaker(self, speaker: str) -> str:
        """Resolve a speaker name to its ID."""
        # Check if it's already an ID
        if speaker.startswith("SPEAKER_"):
            return speaker
        # Check reverse mapping
        for speaker_id, name in self.speaker_mapping.items():
            if name == speaker:
                return speaker_id
        return speaker

    def get_display_name(self, speaker_id: str) -> str:
        """Get the display name for a speaker ID."""
        return self.speaker_mapping.get(speaker_id, speaker_id)

    def rename_speaker(self, speaker_id: str, name: str) -> None:
        """Rename a speaker."""
        self.speaker_mapping[speaker_id] = name

    def get_all_speakers(self) -> List[str]:
        """Get list of all unique speaker IDs."""
        return list(set(s.speaker for s in self.segments))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "segments": [s.to_dict() for s in self.segments],
            "num_speakers": self.num_speakers,
            "speaker_mapping": self.speaker_mapping,
            "processing_time": self.processing_time,
            "audio_duration": self.audio_duration,
            "speakers": [
                {
                    "id": speaker,
                    "name": self.get_display_name(speaker),
                    "duration": self.get_speaker_duration(speaker),
                    "percentage": self.get_speaker_percentage(speaker)
                }
                for speaker in self.get_all_speakers()
            ]
        }


class SpeakerDiarizer:
    """
    Speaker diarization using pyannote.audio.

    Identifies different speakers in audio and provides speaker labels
    for transcription segments.
    """

    def __init__(
        self,
        huggingface_token: Optional[str] = None,
        num_speakers: Optional[int] = None,
        min_speakers: int = 1,
        max_speakers: int = 10,
        on_progress: Optional[Callable[[float, str], None]] = None,
        on_error: Optional[Callable[[str], None]] = None
    ):
        """
        Initialize the speaker diarizer.

        Args:
            huggingface_token: HuggingFace API token for pyannote.audio models.
                              Falls back to HUGGINGFACE_TOKEN env var if not provided.
            num_speakers: Known number of speakers (if available).
            min_speakers: Minimum expected number of speakers.
            max_speakers: Maximum expected number of speakers.
            on_progress: Callback for progress updates (percentage, message).
            on_error: Callback for error notifications.
        """
        self._token = huggingface_token or os.getenv("HUGGINGFACE_TOKEN")
        self._num_speakers = num_speakers
        self._min_speakers = min_speakers
        self._max_speakers = max_speakers
        self._on_progress = on_progress
        self._on_error = on_error

        self._pipeline = None
        self._model_loaded = False
        self._loading_lock = threading.Lock()

        # Speaker name mapping (persisted across sessions)
        self._speaker_mapping: Dict[str, str] = {}

        # Sample rate for audio processing
        self._sample_rate = 16000

    @property
    def is_model_loaded(self) -> bool:
        """Check if the diarization model is loaded."""
        return self._model_loaded

    def _notify_progress(self, progress: float, message: str):
        """Notify progress to callback."""
        if self._on_progress:
            try:
                self._on_progress(progress, message)
            except Exception as e:
                logger.error(f"Progress callback error: {e}")

    def _notify_error(self, message: str):
        """Notify error to callback."""
        logger.error(message)
        if self._on_error:
            try:
                self._on_error(message)
            except Exception as e:
                logger.error(f"Error callback error: {e}")

    def load_model(self) -> bool:
        """
        Load the pyannote.audio diarization pipeline.

        Returns:
            True if model loaded successfully, False otherwise.
        """
        with self._loading_lock:
            if self._model_loaded:
                return True

            if not self._token:
                self._notify_error(
                    "HUGGINGFACE_TOKEN not set. Please set the environment variable "
                    "or provide the token to enable speaker diarization."
                )
                return False

            self._notify_progress(0.1, "Loading speaker diarization model...")

            try:
                from pyannote.audio import Pipeline

                self._notify_progress(0.3, "Downloading model (first time only)...")

                self._pipeline = Pipeline.from_pretrained(
                    "pyannote/speaker-diarization-3.1",
                    use_auth_token=self._token
                )

                # Try to use GPU if available
                try:
                    import torch
                    if torch.cuda.is_available():
                        self._pipeline = self._pipeline.to(torch.device("cuda"))
                        logger.info("Speaker diarization using GPU")
                    else:
                        logger.info("Speaker diarization using CPU")
                except ImportError:
                    logger.info("Speaker diarization using CPU (PyTorch CUDA not available)")

                self._model_loaded = True
                self._notify_progress(1.0, "Model loaded successfully")
                logger.info("Speaker diarization model loaded")
                return True

            except ImportError as e:
                self._notify_error(
                    f"pyannote.audio not installed. Install with: pip install pyannote.audio>=3.1.0"
                )
                return False
            except Exception as e:
                self._notify_error(f"Failed to load diarization model: {e}")
                return False

    def unload_model(self):
        """Unload the model to free memory."""
        with self._loading_lock:
            if self._pipeline is not None:
                del self._pipeline
                self._pipeline = None
                self._model_loaded = False
                # Force garbage collection
                import gc
                gc.collect()
                logger.info("Speaker diarization model unloaded")

    def diarize(self, audio_path: str) -> Optional[DiarizationResult]:
        """
        Perform speaker diarization on an audio file.

        Args:
            audio_path: Path to the audio file (WAV, MP3, etc.).

        Returns:
            DiarizationResult with speaker segments, or None on error.
        """
        if not self.load_model():
            return None

        start_time = datetime.now()
        self._notify_progress(0.1, "Starting diarization...")

        try:
            # Build diarization options
            diarize_options = {}

            if self._num_speakers is not None:
                diarize_options["num_speakers"] = self._num_speakers
            else:
                diarize_options["min_speakers"] = self._min_speakers
                diarize_options["max_speakers"] = self._max_speakers

            self._notify_progress(0.3, "Analyzing speakers...")

            # Run diarization
            diarization = self._pipeline(audio_path, **diarize_options)

            self._notify_progress(0.8, "Extracting segments...")

            # Extract segments
            segments: List[SpeakerSegment] = []
            speakers_found = set()

            for turn, _, speaker in diarization.itertracks(yield_label=True):
                segment = SpeakerSegment(
                    start=turn.start,
                    end=turn.end,
                    speaker=speaker
                )
                segments.append(segment)
                speakers_found.add(speaker)

            # Sort segments by start time
            segments.sort(key=lambda s: s.start)

            # Get audio duration
            try:
                import wave
                with wave.open(audio_path, 'rb') as wav:
                    frames = wav.getnframes()
                    rate = wav.getframerate()
                    audio_duration = frames / float(rate)
            except Exception:
                # Estimate from last segment
                audio_duration = segments[-1].end if segments else 0.0

            processing_time = (datetime.now() - start_time).total_seconds()

            result = DiarizationResult(
                segments=segments,
                num_speakers=len(speakers_found),
                speaker_mapping=self._speaker_mapping.copy(),
                processing_time=processing_time,
                audio_duration=audio_duration
            )

            self._notify_progress(1.0, f"Found {len(speakers_found)} speakers")
            logger.info(
                f"Diarization complete: {len(segments)} segments, "
                f"{len(speakers_found)} speakers, {processing_time:.2f}s"
            )

            return result

        except Exception as e:
            self._notify_error(f"Diarization failed: {e}")
            return None

    def diarize_buffer(
        self,
        audio_data: np.ndarray,
        sample_rate: int = 16000
    ) -> Optional[DiarizationResult]:
        """
        Perform speaker diarization on audio data in memory.

        Args:
            audio_data: Audio samples as numpy array (float32, -1 to 1 range).
            sample_rate: Sample rate of the audio data.

        Returns:
            DiarizationResult with speaker segments, or None on error.
        """
        # Save to temporary file for pyannote processing
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_path = temp_file.name

                # Convert to int16 for WAV
                if audio_data.dtype == np.float32 or audio_data.dtype == np.float64:
                    audio_int16 = (audio_data * 32767).astype(np.int16)
                else:
                    audio_int16 = audio_data.astype(np.int16)

                # Write WAV file
                with wave.open(temp_path, 'wb') as wav:
                    wav.setnchannels(1)
                    wav.setsampwidth(2)  # 16-bit
                    wav.setframerate(sample_rate)
                    wav.writeframes(audio_int16.tobytes())

                # Diarize the file
                result = self.diarize(temp_path)

                # Clean up
                os.unlink(temp_path)

                return result

        except Exception as e:
            self._notify_error(f"Buffer diarization failed: {e}")
            return None

    def assign_speakers_to_transcription(
        self,
        transcription_segments: List[Dict[str, Any]],
        diarization_result: DiarizationResult
    ) -> List[Dict[str, Any]]:
        """
        Assign speaker labels to transcription segments based on diarization.

        Args:
            transcription_segments: List of transcription segments with 'start', 'end', 'text'.
            diarization_result: Result from diarization.

        Returns:
            Transcription segments with added 'speaker' field.
        """
        for trans_seg in transcription_segments:
            trans_start = trans_seg.get("start", 0)
            trans_end = trans_seg.get("end", 0)
            trans_mid = (trans_start + trans_end) / 2

            # Find the speaker segment that contains the midpoint
            best_speaker = None
            best_overlap = 0

            for diar_seg in diarization_result.segments:
                # Calculate overlap
                overlap_start = max(trans_start, diar_seg.start)
                overlap_end = min(trans_end, diar_seg.end)
                overlap = max(0, overlap_end - overlap_start)

                if overlap > best_overlap:
                    best_overlap = overlap
                    best_speaker = diar_seg.speaker

            if best_speaker:
                trans_seg["speaker"] = best_speaker
                trans_seg["speaker_name"] = diarization_result.get_display_name(best_speaker)
            else:
                trans_seg["speaker"] = "UNKNOWN"
                trans_seg["speaker_name"] = "Unknown Speaker"

        return transcription_segments

    def set_speaker_name(self, speaker_id: str, name: str):
        """
        Set a custom name for a speaker ID.

        Args:
            speaker_id: The speaker identifier (e.g., "SPEAKER_00").
            name: The custom name to use.
        """
        self._speaker_mapping[speaker_id] = name
        logger.info(f"Renamed {speaker_id} to '{name}'")

    def get_speaker_name(self, speaker_id: str) -> str:
        """Get the display name for a speaker ID."""
        return self._speaker_mapping.get(speaker_id, speaker_id)

    def get_speaker_mapping(self) -> Dict[str, str]:
        """Get the current speaker name mapping."""
        return self._speaker_mapping.copy()

    def set_speaker_mapping(self, mapping: Dict[str, str]):
        """Set the speaker name mapping."""
        self._speaker_mapping = mapping.copy()

    def clear_speaker_mapping(self):
        """Clear all custom speaker names."""
        self._speaker_mapping.clear()


class DiarizedTranscriber:
    """
    Combines transcription with speaker diarization.

    Provides real-time transcription with speaker identification.
    """

    def __init__(
        self,
        transcriber,  # Transcriber instance
        diarizer: Optional[SpeakerDiarizer] = None,
        enable_diarization: bool = True,
        diarization_interval: float = 30.0,  # Seconds between diarization runs
        on_segment: Optional[Callable[[SpeakerSegment], None]] = None
    ):
        """
        Initialize the diarized transcriber.

        Args:
            transcriber: Instance of Transcriber class for transcription.
            diarizer: Optional SpeakerDiarizer instance. Created if not provided.
            enable_diarization: Whether to enable speaker diarization.
            diarization_interval: How often to run diarization (seconds).
            on_segment: Callback when a new speaker segment is ready.
        """
        self._transcriber = transcriber
        self._diarizer = diarizer or SpeakerDiarizer()
        self._enable_diarization = enable_diarization
        self._diarization_interval = diarization_interval
        self._on_segment = on_segment

        # Audio buffer for diarization
        self._audio_buffer: List[np.ndarray] = []
        self._buffer_lock = threading.Lock()
        self._last_diarization_time = 0.0

        # Transcription segments waiting for speaker assignment
        self._pending_segments: List[Dict[str, Any]] = []
        self._segments_lock = threading.Lock()

        # Latest diarization result
        self._latest_diarization: Optional[DiarizationResult] = None

        # Running state
        self._running = False
        self._diarization_thread: Optional[threading.Thread] = None

    @property
    def is_diarization_enabled(self) -> bool:
        """Check if diarization is enabled."""
        return self._enable_diarization

    def enable_diarization(self, enable: bool = True):
        """Enable or disable speaker diarization."""
        self._enable_diarization = enable

    def process_audio(self, audio_chunk: np.ndarray):
        """
        Process an audio chunk for both transcription and diarization.

        Args:
            audio_chunk: Audio samples as numpy array.
        """
        # Forward to transcriber
        self._transcriber.process_audio(audio_chunk)

        # Buffer for diarization
        if self._enable_diarization:
            with self._buffer_lock:
                self._audio_buffer.append(audio_chunk.copy())

    def add_transcription_segment(
        self,
        text: str,
        start: float,
        end: float
    ):
        """
        Add a transcription segment for speaker assignment.

        Args:
            text: Transcribed text.
            start: Start time in seconds.
            end: End time in seconds.
        """
        segment = {
            "text": text,
            "start": start,
            "end": end,
            "timestamp": datetime.now().isoformat()
        }

        with self._segments_lock:
            self._pending_segments.append(segment)

        # Try to assign speaker from latest diarization
        if self._latest_diarization:
            self._assign_speaker(segment)

    def _assign_speaker(self, segment: Dict[str, Any]):
        """Assign speaker to a segment using latest diarization."""
        if not self._latest_diarization:
            return

        segments = self._diarizer.assign_speakers_to_transcription(
            [segment],
            self._latest_diarization
        )

        if segments and self._on_segment:
            seg_data = segments[0]
            speaker_segment = SpeakerSegment(
                start=seg_data.get("start", 0),
                end=seg_data.get("end", 0),
                speaker=seg_data.get("speaker", "UNKNOWN"),
                text=seg_data.get("text", "")
            )
            self._on_segment(speaker_segment)

    def start(self):
        """Start transcription and diarization."""
        if self._running:
            return

        self._running = True
        self._transcriber.start()

        # Start diarization thread if enabled
        if self._enable_diarization:
            self._diarization_thread = threading.Thread(
                target=self._diarization_loop,
                daemon=True
            )
            self._diarization_thread.start()

        logger.info("Diarized transcriber started")

    def stop(self):
        """Stop transcription and diarization."""
        self._running = False
        self._transcriber.stop()

        if self._diarization_thread:
            self._diarization_thread.join(timeout=2.0)
            self._diarization_thread = None

        logger.info("Diarized transcriber stopped")

    def _diarization_loop(self):
        """Background loop for periodic diarization."""
        import time

        while self._running:
            try:
                time.sleep(1.0)  # Check every second

                # Check if enough time has passed
                current_time = time.time()
                if current_time - self._last_diarization_time < self._diarization_interval:
                    continue

                # Get buffered audio
                with self._buffer_lock:
                    if not self._audio_buffer:
                        continue
                    audio_data = np.concatenate(self._audio_buffer)
                    # Keep some overlap for context
                    keep_samples = int(self._diarization_interval * 16000 * 0.5)
                    if len(audio_data) > keep_samples:
                        self._audio_buffer = [audio_data[-keep_samples:]]
                    else:
                        self._audio_buffer = []

                # Run diarization
                result = self._diarizer.diarize_buffer(audio_data)
                if result:
                    self._latest_diarization = result
                    self._last_diarization_time = current_time

                    # Assign speakers to pending segments
                    with self._segments_lock:
                        if self._pending_segments:
                            assigned = self._diarizer.assign_speakers_to_transcription(
                                self._pending_segments,
                                result
                            )
                            self._pending_segments = assigned

            except Exception as e:
                logger.error(f"Diarization loop error: {e}")

    def get_diarization_result(self) -> Optional[DiarizationResult]:
        """Get the latest diarization result."""
        return self._latest_diarization

    def get_pending_segments(self) -> List[Dict[str, Any]]:
        """Get all pending transcription segments with speaker info."""
        with self._segments_lock:
            return self._pending_segments.copy()

    def set_speaker_name(self, speaker_id: str, name: str):
        """Set a custom name for a speaker."""
        self._diarizer.set_speaker_name(speaker_id, name)

    def get_speaker_mapping(self) -> Dict[str, str]:
        """Get the speaker name mapping."""
        return self._diarizer.get_speaker_mapping()

    def unload_models(self):
        """Unload models to free memory."""
        self._transcriber.unload_model()
        self._diarizer.unload_model()
