"""
Audio capture service abstraction.

Provides:
- Unified interface for audio capture
- Device management
- Audio streaming
"""

import logging
from typing import Optional, Callable, List, Dict, Any
from dataclasses import dataclass
from enum import Enum, auto
import threading
import queue

logger = logging.getLogger(__name__)


class AudioSource(Enum):
    """Audio source types."""
    MICROPHONE = auto()
    SYSTEM_AUDIO = auto()
    BOTH = auto()


@dataclass
class AudioDevice:
    """Audio device information."""
    id: str
    name: str
    is_input: bool
    is_default: bool
    sample_rate: int = 16000
    channels: int = 1


@dataclass
class AudioChunk:
    """Audio data chunk."""
    data: bytes
    timestamp: float
    source: AudioSource
    sample_rate: int
    channels: int


class AudioService:
    """
    Service for audio capture and management.

    Abstracts audio capture to provide a clean interface
    for the rest of the application.
    """

    def __init__(self):
        """Initialize audio service."""
        self._is_capturing = False
        self._audio_queue: queue.Queue = queue.Queue()
        self._capture_thread: Optional[threading.Thread] = None
        self._listeners: List[Callable[[AudioChunk], None]] = []
        self._selected_device: Optional[AudioDevice] = None
        self._source = AudioSource.SYSTEM_AUDIO

    @property
    def is_capturing(self) -> bool:
        """Check if audio capture is active."""
        return self._is_capturing

    @property
    def selected_device(self) -> Optional[AudioDevice]:
        """Get currently selected audio device."""
        return self._selected_device

    def list_devices(self) -> List[AudioDevice]:
        """
        List available audio devices.

        Returns:
            List of available audio devices
        """
        devices = []

        try:
            import pyaudio
            pa = pyaudio.PyAudio()

            for i in range(pa.get_device_count()):
                info = pa.get_device_info_by_index(i)

                # Only include input devices
                if info.get("maxInputChannels", 0) > 0:
                    devices.append(AudioDevice(
                        id=str(i),
                        name=info.get("name", f"Device {i}"),
                        is_input=True,
                        is_default=(i == pa.get_default_input_device_info().get("index")),
                        sample_rate=int(info.get("defaultSampleRate", 16000)),
                        channels=min(info.get("maxInputChannels", 1), 2),
                    ))

            pa.terminate()

        except Exception as e:
            logger.error(f"Failed to list audio devices: {e}")

        return devices

    def select_device(self, device_id: str) -> bool:
        """
        Select an audio device for capture.

        Args:
            device_id: Device ID to select

        Returns:
            True if device was selected successfully
        """
        devices = self.list_devices()
        for device in devices:
            if device.id == device_id:
                self._selected_device = device
                logger.info(f"Selected audio device: {device.name}")
                return True

        logger.warning(f"Audio device not found: {device_id}")
        return False

    def set_source(self, source: AudioSource):
        """
        Set the audio source type.

        Args:
            source: Audio source to capture from
        """
        self._source = source
        logger.info(f"Audio source set to: {source.name}")

    def add_listener(self, callback: Callable[[AudioChunk], None]):
        """Add audio chunk listener."""
        self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[AudioChunk], None]):
        """Remove audio chunk listener."""
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify_listeners(self, chunk: AudioChunk):
        """Notify listeners of new audio chunk."""
        for listener in self._listeners:
            try:
                listener(chunk)
            except Exception as e:
                logger.error(f"Error in audio listener: {e}")

    def start_capture(self) -> bool:
        """
        Start audio capture.

        Returns:
            True if capture started successfully
        """
        if self._is_capturing:
            logger.warning("Audio capture already running")
            return True

        try:
            self._is_capturing = True
            self._capture_thread = threading.Thread(
                target=self._capture_loop,
                daemon=True
            )
            self._capture_thread.start()
            logger.info("Audio capture started")
            return True

        except Exception as e:
            logger.error(f"Failed to start audio capture: {e}")
            self._is_capturing = False
            return False

    def stop_capture(self):
        """Stop audio capture."""
        self._is_capturing = False

        if self._capture_thread and self._capture_thread.is_alive():
            self._capture_thread.join(timeout=2.0)

        self._capture_thread = None
        logger.info("Audio capture stopped")

    def _capture_loop(self):
        """Audio capture loop (runs in separate thread)."""
        try:
            import pyaudio
            import time

            pa = pyaudio.PyAudio()

            # Get device index
            device_index = None
            if self._selected_device:
                device_index = int(self._selected_device.id)

            # Open stream
            stream = pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=1024,
            )

            while self._is_capturing:
                try:
                    data = stream.read(1024, exception_on_overflow=False)

                    chunk = AudioChunk(
                        data=data,
                        timestamp=time.time(),
                        source=self._source,
                        sample_rate=16000,
                        channels=1,
                    )

                    self._notify_listeners(chunk)

                except Exception as e:
                    if self._is_capturing:
                        logger.error(f"Audio capture error: {e}")
                    break

            stream.stop_stream()
            stream.close()
            pa.terminate()

        except Exception as e:
            logger.error(f"Audio capture loop error: {e}")
            self._is_capturing = False

    def get_audio_level(self) -> float:
        """
        Get current audio level (0.0 - 1.0).

        Returns:
            Current audio level
        """
        # Placeholder - would compute RMS of recent audio
        return 0.0

    def get_status(self) -> Dict[str, Any]:
        """Get audio service status."""
        return {
            "is_capturing": self._is_capturing,
            "source": self._source.name,
            "device": self._selected_device.name if self._selected_device else None,
            "device_id": self._selected_device.id if self._selected_device else None,
        }
