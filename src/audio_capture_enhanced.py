"""
Enhanced Cross-Platform Audio Capture for ReadIn AI.

IMPROVEMENTS OVER ORIGINAL:
- WASAPI loopback mode for Windows (captures all system audio reliably)
- Automatic virtual audio device setup guidance
- Audio preprocessing (noise gate, normalization, DC offset removal)
- Better sample rate handling with high-quality resampling
- Integration with calendar-based meeting detection
- Reduced latency capture mode

STEALTH MODE COMPATIBLE:
- Captures system audio output (what you hear)
- No microphone access needed for meeting audio
- Invisible to other meeting participants
"""

import threading
import queue
import time
from typing import Callable, Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

import numpy as np

from config import AUDIO_SAMPLE_RATE, AUDIO_CHUNK_DURATION, IS_WINDOWS, IS_MACOS, IS_LINUX


class CaptureMode(Enum):
    """Audio capture modes."""
    SYSTEM_LOOPBACK = "loopback"  # Capture system audio output (stealth)
    MICROPHONE = "microphone"     # Capture microphone input
    MIXED = "mixed"               # Capture both (for local speaker + remote audio)


@dataclass
class AudioDevice:
    """Audio device information."""
    index: int
    name: str
    channels: int
    sample_rate: int
    is_loopback: bool
    is_default: bool
    host_api: str = ""
    latency: float = 0.0


class AudioPreprocessor:
    """Audio preprocessing for better transcription quality."""

    def __init__(
        self,
        noise_gate_threshold: float = 0.01,
        normalize: bool = True,
        remove_dc_offset: bool = True,
        high_pass_cutoff: float = 80.0,  # Hz - remove rumble
    ):
        self.noise_gate_threshold = noise_gate_threshold
        self.normalize = normalize
        self.remove_dc_offset = remove_dc_offset
        self.high_pass_cutoff = high_pass_cutoff
        self._prev_sample = 0.0  # For high-pass filter

    def process(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """Apply preprocessing to audio chunk."""
        if len(audio) == 0:
            return audio

        # Remove DC offset
        if self.remove_dc_offset:
            audio = audio - np.mean(audio)

        # Simple high-pass filter (remove low frequency rumble)
        if self.high_pass_cutoff > 0:
            alpha = 1.0 / (1.0 + (2.0 * np.pi * self.high_pass_cutoff / sample_rate))
            filtered = np.zeros_like(audio)
            prev = self._prev_sample
            for i, sample in enumerate(audio):
                filtered[i] = alpha * (prev + sample - (audio[i-1] if i > 0 else 0))
                prev = filtered[i]
            self._prev_sample = prev
            audio = filtered

        # Noise gate - silence very quiet sections
        if self.noise_gate_threshold > 0:
            rms = np.sqrt(np.mean(audio ** 2))
            if rms < self.noise_gate_threshold:
                audio = audio * 0.1  # Reduce but don't eliminate

        # Normalize to prevent clipping while maintaining dynamics
        if self.normalize:
            max_val = np.abs(audio).max()
            if max_val > 0.01:  # Only normalize if there's actual audio
                target_level = 0.7
                audio = audio * (target_level / max_val)

        return audio.astype(np.float32)


class EnhancedAudioCapture:
    """
    Enhanced audio capture with better quality and stealth mode support.

    STEALTH MODE: Captures system audio (what you hear) without accessing
    the microphone. Other meeting participants cannot detect this capture.
    """

    def __init__(
        self,
        on_audio_chunk: Callable[[np.ndarray], None],
        device_index: Optional[int] = None,
        capture_mode: CaptureMode = CaptureMode.SYSTEM_LOOPBACK,
        on_device_change: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
        on_audio_level: Optional[Callable[[float], None]] = None,
        enable_preprocessing: bool = True,
        low_latency: bool = False,
    ):
        self.on_audio_chunk = on_audio_chunk
        self.on_device_change = on_device_change
        self.on_error = on_error
        self.on_audio_level = on_audio_level
        self.capture_mode = capture_mode
        self.enable_preprocessing = enable_preprocessing
        self.low_latency = low_latency

        self.sample_rate = AUDIO_SAMPLE_RATE
        self.chunk_duration = AUDIO_CHUNK_DURATION

        self._running = False
        self._processor_thread: Optional[threading.Thread] = None
        self._audio_buffer = np.array([], dtype=np.float32)
        self._samples_per_chunk = int(self.sample_rate * self.chunk_duration)
        self._buffer_queue: queue.Queue = queue.Queue(maxsize=100)
        self._device_index = device_index
        self._current_device_name = ""
        self._current_audio_level = 0.0
        self._error_count = 0
        self._source_sample_rate: Optional[int] = None
        self._source_channels: int = 1

        # Platform-specific
        self._pa = None
        self._stream = None

        # Preprocessing
        self._preprocessor = AudioPreprocessor() if enable_preprocessing else None

        # Performance tracking
        self._chunks_processed = 0
        self._start_time = 0.0

    @staticmethod
    def get_available_devices(capture_mode: CaptureMode = CaptureMode.SYSTEM_LOOPBACK) -> List[AudioDevice]:
        """
        Get available audio devices filtered by capture mode.

        For STEALTH MODE (SYSTEM_LOOPBACK): Returns loopback/monitor devices
        that capture system audio without accessing microphone.
        """
        devices = []

        if IS_WINDOWS:
            devices = EnhancedAudioCapture._get_windows_devices()
        else:
            devices = EnhancedAudioCapture._get_unix_devices()

        # Filter by capture mode
        if capture_mode == CaptureMode.SYSTEM_LOOPBACK:
            # Prioritize loopback devices for stealth mode
            loopback_devices = [d for d in devices if d.is_loopback]
            if loopback_devices:
                return loopback_devices
            # If no loopback found, return all with warning
            print("WARNING: No loopback device found. System audio capture may not work.")
            print("  Windows: Enable 'Stereo Mix' in Sound settings")
            print("  macOS: Install BlackHole (brew install blackhole-2ch)")
            print("  Linux: Use PulseAudio monitor device")

        return devices

    @staticmethod
    def _get_windows_devices() -> List[AudioDevice]:
        """Get Windows audio devices with WASAPI info."""
        devices = []
        try:
            import pyaudio
            pa = pyaudio.PyAudio()

            default_input = None
            try:
                default_input = pa.get_default_input_device_info()
            except:
                pass
            default_index = default_input['index'] if default_input else -1

            for i in range(pa.get_device_count()):
                try:
                    info = pa.get_device_info_by_index(i)
                    if info['maxInputChannels'] > 0:
                        name = info['name']
                        name_lower = name.lower()

                        # Detect loopback devices
                        is_loopback = any(kw in name_lower for kw in [
                            'loopback', 'stereo mix', 'what u hear',
                            'wave out', 'wasapi', 'output'
                        ])

                        # Get host API name
                        host_api = ""
                        try:
                            host_info = pa.get_host_api_info_by_index(info['hostApi'])
                            host_api = host_info.get('name', '')
                        except:
                            pass

                        devices.append(AudioDevice(
                            index=i,
                            name=name,
                            channels=int(info['maxInputChannels']),
                            sample_rate=int(info.get('defaultSampleRate', AUDIO_SAMPLE_RATE)),
                            is_loopback=is_loopback,
                            is_default=(i == default_index),
                            host_api=host_api,
                            latency=info.get('defaultLowInputLatency', 0.0),
                        ))
                except Exception as e:
                    continue

            pa.terminate()
        except Exception as e:
            print(f"Error listing Windows devices: {e}")

        return devices

    @staticmethod
    def _get_unix_devices() -> List[AudioDevice]:
        """Get macOS/Linux audio devices."""
        devices = []
        try:
            import sounddevice as sd

            default_input = sd.default.device[0]

            for i, dev in enumerate(sd.query_devices()):
                if dev['max_input_channels'] > 0:
                    name = dev['name']
                    name_lower = name.lower()

                    is_loopback = any(kw in name_lower for kw in [
                        'monitor', 'blackhole', 'loopback', 'soundflower',
                        'virtual', 'vb-audio', 'output'
                    ])

                    devices.append(AudioDevice(
                        index=i,
                        name=name,
                        channels=int(dev['max_input_channels']),
                        sample_rate=int(dev.get('default_samplerate', AUDIO_SAMPLE_RATE)),
                        is_loopback=is_loopback,
                        is_default=(i == default_input),
                        host_api=dev.get('hostapi', ''),
                        latency=dev.get('default_low_input_latency', 0.0),
                    ))
        except Exception as e:
            print(f"Error listing audio devices: {e}")

        return devices

    @staticmethod
    def get_recommended_device(capture_mode: CaptureMode = CaptureMode.SYSTEM_LOOPBACK) -> Optional[AudioDevice]:
        """
        Get the best device for the capture mode.

        For STEALTH MODE: Returns the best loopback device.
        """
        devices = EnhancedAudioCapture.get_available_devices(capture_mode)

        if not devices:
            return None

        # For loopback mode, prefer WASAPI loopback on Windows
        if capture_mode == CaptureMode.SYSTEM_LOOPBACK:
            # Priority: WASAPI loopback > Stereo Mix > BlackHole > Monitor
            priority_keywords = ['wasapi', 'loopback', 'stereo mix', 'blackhole', 'monitor']

            for keyword in priority_keywords:
                for device in devices:
                    if keyword in device.name.lower() or keyword in device.host_api.lower():
                        return device

        # Return first loopback device, or first device
        for device in devices:
            if device.is_loopback:
                return device

        return devices[0] if devices else None

    @staticmethod
    def get_setup_instructions() -> Dict[str, str]:
        """Get platform-specific setup instructions for system audio capture."""
        return {
            "windows": """
WINDOWS SETUP FOR SYSTEM AUDIO CAPTURE:

Option 1: Enable Stereo Mix (Recommended)
1. Right-click speaker icon in system tray
2. Select "Sound settings" or "Sounds"
3. Go to Recording tab
4. Right-click empty area, check "Show Disabled Devices"
5. Right-click "Stereo Mix" and enable it

Option 2: WASAPI Loopback (Advanced)
- Automatically available if your audio driver supports it
- Look for devices with "WASAPI" or "Loopback" in the name

Option 3: Virtual Audio Cable
- Install VB-Audio Virtual Cable (free)
- Set it as default playback device
- Use it as capture input in ReadIn AI
            """,
            "macos": """
macOS SETUP FOR SYSTEM AUDIO CAPTURE:

Option 1: BlackHole (Recommended - Free)
1. Install: brew install blackhole-2ch
2. Open Audio MIDI Setup (in Utilities)
3. Click "+" and create Multi-Output Device
4. Check both your speakers AND BlackHole 2ch
5. Set Multi-Output as system output
6. Select "BlackHole 2ch" in ReadIn AI

Option 2: Loopback by Rogue Amoeba (Paid)
- More user-friendly
- Download from rogueamoeba.com/loopback
            """,
            "linux": """
LINUX SETUP FOR SYSTEM AUDIO CAPTURE:

PulseAudio (Most distros):
1. Install pavucontrol: sudo apt install pavucontrol
2. Open PulseAudio Volume Control
3. Go to Recording tab
4. While ReadIn AI is capturing, change input to
   "Monitor of [your output device]"

PipeWire (Fedora, newer Ubuntu):
- Monitor devices should appear automatically
- Look for devices with "Monitor" in the name
            """,
        }

    def _high_quality_resample(self, audio: np.ndarray, source_rate: int, target_rate: int) -> np.ndarray:
        """High-quality resampling using scipy if available, otherwise linear."""
        if source_rate == target_rate:
            return audio

        try:
            from scipy import signal
            # Use polyphase resampling for better quality
            gcd = np.gcd(source_rate, target_rate)
            up = target_rate // gcd
            down = source_rate // gcd
            return signal.resample_poly(audio, up, down).astype(np.float32)
        except ImportError:
            # Fallback to linear interpolation
            duration = len(audio) / source_rate
            target_samples = int(duration * target_rate)
            if target_samples <= 0:
                return audio
            indices = np.linspace(0, len(audio) - 1, target_samples)
            return np.interp(indices, np.arange(len(audio)), audio).astype(np.float32)

    def _convert_to_mono(self, audio: np.ndarray, channels: int) -> np.ndarray:
        """Convert multi-channel audio to mono."""
        if channels <= 1 or len(audio.shape) == 1:
            return audio.flatten()

        if len(audio.shape) == 1 and channels > 1:
            audio = audio.reshape(-1, channels)

        return audio.mean(axis=1).astype(np.float32)

    def _calculate_audio_level(self, audio: np.ndarray) -> float:
        """Calculate RMS audio level (0.0 to 1.0)."""
        if len(audio) == 0:
            return 0.0
        rms = np.sqrt(np.mean(audio ** 2))
        # Map to 0-1 range with some headroom
        level = min(1.0, rms * 3.0)
        return float(level)

    def _process_audio(self):
        """Process buffered audio and emit chunks."""
        while self._running:
            try:
                raw_data = self._buffer_queue.get(timeout=0.1)

                # Convert to float32
                if isinstance(raw_data, bytes):
                    audio = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32) / 32768.0
                elif isinstance(raw_data, np.ndarray):
                    audio = raw_data.astype(np.float32)
                    if np.abs(audio).max() > 1.5:
                        audio = audio / 32768.0
                else:
                    continue

                # Convert to mono
                if self._source_channels > 1:
                    audio = self._convert_to_mono(audio, self._source_channels)
                else:
                    audio = audio.flatten()

                # Resample if needed
                if self._source_sample_rate and self._source_sample_rate != self.sample_rate:
                    audio = self._high_quality_resample(audio, self._source_sample_rate, self.sample_rate)

                # Apply preprocessing
                if self._preprocessor:
                    audio = self._preprocessor.process(audio, self.sample_rate)

                # Calculate and emit level
                self._current_audio_level = self._calculate_audio_level(audio)
                if self.on_audio_level:
                    self.on_audio_level(self._current_audio_level)

                # Buffer and emit chunks
                self._audio_buffer = np.concatenate([self._audio_buffer, audio])

                while len(self._audio_buffer) >= self._samples_per_chunk:
                    chunk = self._audio_buffer[:self._samples_per_chunk]
                    self._audio_buffer = self._audio_buffer[self._samples_per_chunk:]
                    self.on_audio_chunk(chunk)
                    self._chunks_processed += 1

            except queue.Empty:
                continue
            except Exception as e:
                self._error_count += 1
                if self._error_count % 10 == 1:
                    print(f"Audio processing error: {e}")

    def _audio_callback_pyaudio(self, in_data, frame_count, time_info, status):
        """PyAudio stream callback."""
        import pyaudio
        if self._running:
            try:
                self._buffer_queue.put_nowait(in_data)
            except queue.Full:
                pass  # Drop frame if buffer full
        return (None, pyaudio.paContinue)

    def _start_windows(self):
        """Start Windows audio capture with WASAPI support."""
        import pyaudio

        if self._pa is None:
            self._pa = pyaudio.PyAudio()

        device = None
        if self._device_index is not None:
            # Use specified device
            try:
                info = self._pa.get_device_info_by_index(self._device_index)
                device = AudioDevice(
                    index=self._device_index,
                    name=info['name'],
                    channels=int(info['maxInputChannels']),
                    sample_rate=int(info.get('defaultSampleRate', self.sample_rate)),
                    is_loopback=False,
                    is_default=False,
                )
            except:
                pass

        if device is None:
            # Auto-select best device
            device = self.get_recommended_device(self.capture_mode)

        if device is None:
            self._emit_error("No suitable audio device found!")
            self._running = False
            return

        self._source_channels = min(device.channels, 2)
        self._source_sample_rate = device.sample_rate

        print(f"Using device: {device.name} ({self._source_channels}ch @ {device.sample_rate}Hz)")
        self._emit_device_change(device.name)

        # Buffer size based on latency setting
        buffer_size = int(device.sample_rate * (0.05 if self.low_latency else 0.1))

        # Try to open stream
        sample_rates = [device.sample_rate, 48000, 44100, self.sample_rate]
        sample_rates = list(dict.fromkeys(sample_rates))  # Remove duplicates

        for rate in sample_rates:
            try:
                self._stream = self._pa.open(
                    format=pyaudio.paInt16,
                    channels=self._source_channels,
                    rate=rate,
                    input=True,
                    input_device_index=device.index,
                    frames_per_buffer=buffer_size,
                    stream_callback=self._audio_callback_pyaudio,
                )
                self._stream.start_stream()
                self._source_sample_rate = rate
                print(f"Audio capture started at {rate}Hz (buffer: {buffer_size})")
                return
            except Exception as e:
                print(f"Failed at {rate}Hz: {e}")
                if self._stream:
                    try:
                        self._stream.close()
                    except:
                        pass
                    self._stream = None

        self._emit_error("Failed to open audio stream")
        self._running = False

    def _start_unix(self):
        """Start macOS/Linux audio capture."""
        import sounddevice as sd

        def callback(indata, frames, time_info, status):
            if status:
                pass  # Ignore status messages in production
            if self._running:
                try:
                    self._buffer_queue.put_nowait(indata.copy())
                except queue.Full:
                    pass

        device = None
        if self._device_index is not None:
            try:
                info = sd.query_devices(self._device_index)
                device = AudioDevice(
                    index=self._device_index,
                    name=info['name'],
                    channels=int(info['max_input_channels']),
                    sample_rate=int(info.get('default_samplerate', self.sample_rate)),
                    is_loopback=False,
                    is_default=False,
                )
            except:
                pass

        if device is None:
            device = self.get_recommended_device(self.capture_mode)

        if device is None:
            self._emit_error("No suitable audio device found!")
            if IS_MACOS:
                print("Install BlackHole: brew install blackhole-2ch")
            self._running = False
            return

        self._source_channels = min(device.channels, 2)
        self._source_sample_rate = device.sample_rate

        print(f"Using device: {device.name}")
        self._emit_device_change(device.name)

        buffer_size = int(device.sample_rate * (0.05 if self.low_latency else 0.1))

        sample_rates = [device.sample_rate, 48000, 44100, self.sample_rate]
        sample_rates = list(dict.fromkeys(sample_rates))

        for rate in sample_rates:
            try:
                self._stream = sd.InputStream(
                    device=device.index,
                    samplerate=rate,
                    channels=self._source_channels,
                    dtype=np.float32,
                    callback=callback,
                    blocksize=buffer_size,
                )
                self._stream.start()
                self._source_sample_rate = rate
                print(f"Audio capture started at {rate}Hz")
                return
            except Exception as e:
                print(f"Failed at {rate}Hz: {e}")
                if self._stream:
                    try:
                        self._stream.close()
                    except:
                        pass
                    self._stream = None

        self._emit_error("Failed to open audio stream")
        self._running = False

    def _emit_error(self, message: str):
        """Emit error message."""
        print(f"Audio error: {message}")
        if self.on_error:
            self.on_error(message)

    def _emit_device_change(self, name: str):
        """Emit device change notification."""
        self._current_device_name = name
        if self.on_device_change:
            self.on_device_change(name)

    def start(self):
        """Start audio capture."""
        if self._running:
            return

        self._running = True
        self._audio_buffer = np.array([], dtype=np.float32)
        self._error_count = 0
        self._chunks_processed = 0
        self._start_time = time.time()

        # Clear queue
        while not self._buffer_queue.empty():
            try:
                self._buffer_queue.get_nowait()
            except queue.Empty:
                break

        # Start processor thread
        self._processor_thread = threading.Thread(target=self._process_audio, daemon=True)
        self._processor_thread.start()

        # Platform-specific capture
        if IS_WINDOWS:
            self._start_windows()
        else:
            self._start_unix()

    def stop(self):
        """Stop audio capture."""
        self._running = False

        if self._stream:
            try:
                if IS_WINDOWS:
                    self._stream.stop_stream()
                    self._stream.close()
                else:
                    self._stream.stop()
                    self._stream.close()
            except:
                pass
            self._stream = None

        if self._pa:
            try:
                self._pa.terminate()
            except:
                pass
            self._pa = None

        if self._processor_thread:
            self._processor_thread.join(timeout=1.0)
            self._processor_thread = None

    def set_device(self, device_index: Optional[int]) -> bool:
        """Set audio device. Restarts capture if running."""
        was_running = self._running
        if was_running:
            self.stop()

        self._device_index = device_index

        if was_running:
            self.start()
            return self._running
        return True

    def is_running(self) -> bool:
        """Check if capture is active."""
        return self._running

    def get_audio_level(self) -> float:
        """Get current audio level (0.0 to 1.0)."""
        return self._current_audio_level

    def get_status(self) -> Dict[str, Any]:
        """Get detailed capture status."""
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        return {
            "is_running": self._running,
            "capture_mode": self.capture_mode.value,
            "device_index": self._device_index,
            "device_name": self._current_device_name,
            "source_sample_rate": self._source_sample_rate,
            "target_sample_rate": self.sample_rate,
            "source_channels": self._source_channels,
            "audio_level": self._current_audio_level,
            "chunks_processed": self._chunks_processed,
            "uptime_seconds": uptime,
            "preprocessing_enabled": self._preprocessor is not None,
            "low_latency_mode": self.low_latency,
        }


# Convenience function for backward compatibility
def list_audio_devices():
    """List all available audio devices."""
    devices = EnhancedAudioCapture.get_available_devices(CaptureMode.SYSTEM_LOOPBACK)
    print("\nAvailable audio devices for STEALTH MODE (system audio capture):")
    print("-" * 60)

    if not devices:
        print("No loopback devices found!")
        instructions = EnhancedAudioCapture.get_setup_instructions()
        if IS_WINDOWS:
            print(instructions["windows"])
        elif IS_MACOS:
            print(instructions["macos"])
        else:
            print(instructions["linux"])
        return

    for device in devices:
        flags = []
        if device.is_loopback:
            flags.append("LOOPBACK")
        if device.is_default:
            flags.append("DEFAULT")
        flag_str = f" [{', '.join(flags)}]" if flags else ""
        print(f"  [{device.index}] {device.name}")
        print(f"       {device.channels}ch @ {device.sample_rate}Hz{flag_str}")


if __name__ == "__main__":
    list_audio_devices()
