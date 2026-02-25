"""
Enhanced Cross-Platform Audio Capture for ReadIn AI.

HIGH-QUALITY AUDIO CAPTURE WITH TRUE STEALTH MODE:
- Windows: WASAPI Loopback (captures all system audio without Stereo Mix)
- macOS: BlackHole/Soundflower support
- Linux: PulseAudio monitor devices

STEALTH MODE COMPATIBLE:
- Captures system audio output (what you hear)
- No microphone access needed for meeting audio
- Invisible to other meeting participants
- No "Recording" indicator shown to others
"""

import threading
import queue
import time
import struct
from typing import Callable, Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum

import numpy as np

from config import AUDIO_SAMPLE_RATE, AUDIO_CHUNK_DURATION, IS_WINDOWS, IS_MACOS, IS_LINUX
from src.logger import get_logger

logger = get_logger("audio_capture_enhanced")


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
    is_input: bool
    is_output: bool
    is_default: bool
    host_api: str = ""
    host_api_index: int = 0
    latency: float = 0.0


class AudioPreprocessor:
    """Audio preprocessing for better transcription quality."""

    def __init__(
        self,
        noise_gate_threshold: float = 0.008,
        normalize: bool = True,
        remove_dc_offset: bool = True,
        high_pass_cutoff: float = 80.0,
    ):
        self.noise_gate_threshold = noise_gate_threshold
        self.normalize = normalize
        self.remove_dc_offset = remove_dc_offset
        self.high_pass_cutoff = high_pass_cutoff
        self._prev_sample = 0.0

    def process(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """Apply preprocessing to audio chunk."""
        if len(audio) == 0:
            return audio

        # Remove DC offset
        if self.remove_dc_offset:
            audio = audio - np.mean(audio)

        # Simple high-pass filter (remove low frequency rumble)
        if self.high_pass_cutoff > 0:
            rc = 1.0 / (2.0 * np.pi * self.high_pass_cutoff)
            dt = 1.0 / sample_rate
            alpha = rc / (rc + dt)

            filtered = np.zeros_like(audio)
            prev_in = 0.0
            prev_out = self._prev_sample

            for i in range(len(audio)):
                filtered[i] = alpha * (prev_out + audio[i] - prev_in)
                prev_in = audio[i]
                prev_out = filtered[i]

            self._prev_sample = prev_out
            audio = filtered

        # Noise gate - reduce very quiet sections
        if self.noise_gate_threshold > 0:
            rms = np.sqrt(np.mean(audio ** 2))
            if rms < self.noise_gate_threshold:
                audio = audio * 0.1

        # Normalize to prevent clipping
        if self.normalize:
            max_val = np.abs(audio).max()
            if max_val > 0.01:
                target_level = 0.75
                audio = audio * (target_level / max_val)

        return np.clip(audio, -1.0, 1.0).astype(np.float32)


class EnhancedAudioCapture:
    """
    High-quality audio capture with true WASAPI loopback support.

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
        # Bounded circular buffer: max ~10 seconds of audio
        self._max_buffer_samples = int(10 * self.sample_rate)
        self._audio_buffer = np.array([], dtype=np.float32)
        self._buffer_lock = threading.Lock()  # Thread safety for buffer access
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
        self._wasapi_loopback = False
        self._capture_thread: Optional[threading.Thread] = None
        self._stream_lock = threading.Lock()

        # Preprocessing
        self._preprocessor = AudioPreprocessor() if enable_preprocessing else None

        # Performance tracking
        self._chunks_processed = 0
        self._start_time = 0.0

    @staticmethod
    def _check_wasapi_loopback_support() -> bool:
        """Check if WASAPI loopback is available and working (pyaudiowpatch).

        NOTE: pyaudiowpatch has compatibility issues with Python 3.13+
        that cause segmentation faults. Disabled until fixed upstream.
        """
        # Temporarily disabled due to Python 3.13 segfault issues
        # TODO: Re-enable once pyaudiowpatch is compatible with Python 3.13
        import sys
        if sys.version_info >= (3, 13):
            return False

        try:
            import pyaudiowpatch as pa_wpatch
            # Test that it actually works
            test_pa = pa_wpatch.PyAudio()
            test_pa.terminate()
            return True
        except ImportError:
            return False
        except Exception:
            return False

    @staticmethod
    def get_available_devices(capture_mode: CaptureMode = CaptureMode.SYSTEM_LOOPBACK) -> List[AudioDevice]:
        """Get available audio devices filtered by capture mode."""
        if IS_WINDOWS:
            return EnhancedAudioCapture._get_windows_devices(capture_mode)
        else:
            return EnhancedAudioCapture._get_unix_devices(capture_mode)

    @staticmethod
    def _get_windows_devices(capture_mode: CaptureMode) -> List[AudioDevice]:
        """Get Windows audio devices with proper WASAPI loopback detection."""
        devices = []

        # First try pyaudiowpatch for true WASAPI loopback
        has_wpatch = EnhancedAudioCapture._check_wasapi_loopback_support()

        try:
            if has_wpatch:
                import pyaudiowpatch as pyaudio
            else:
                import pyaudio

            pa = pyaudio.PyAudio()

            # Get default devices
            default_input_idx = -1
            default_output_idx = -1
            try:
                default_input_idx = pa.get_default_input_device_info()['index']
            except:
                pass
            try:
                default_output_idx = pa.get_default_output_device_info()['index']
            except:
                pass

            for i in range(pa.get_device_count()):
                try:
                    info = pa.get_device_info_by_index(i)
                    name = info.get('name', f'Device {i}')
                    name_lower = name.lower()

                    max_input = int(info.get('maxInputChannels', 0))
                    max_output = int(info.get('maxOutputChannels', 0))

                    # Get host API info
                    host_api = ""
                    host_api_idx = int(info.get('hostApi', 0))
                    try:
                        host_info = pa.get_host_api_info_by_index(host_api_idx)
                        host_api = host_info.get('name', '')
                    except:
                        pass

                    # Determine device type
                    is_input = max_input > 0
                    is_output = max_output > 0

                    # Detect true loopback devices
                    is_loopback = False

                    # With pyaudiowpatch, output devices can be used as loopback
                    if has_wpatch and is_output and 'wasapi' in host_api.lower():
                        is_loopback = True

                    # Traditional loopback detection
                    if is_input:
                        loopback_keywords = ['stereo mix', 'what u hear', 'loopback',
                                           'wave out mix', 'mono mix', 'rec. playback']
                        if any(kw in name_lower for kw in loopback_keywords):
                            is_loopback = True

                    # Determine if this device should be included
                    include = False
                    if capture_mode == CaptureMode.SYSTEM_LOOPBACK:
                        include = is_loopback or (has_wpatch and is_output)
                    elif capture_mode == CaptureMode.MICROPHONE:
                        include = is_input and not is_loopback
                    else:  # MIXED
                        include = is_input

                    if include:
                        channels = max_input if is_input else max_output
                        devices.append(AudioDevice(
                            index=i,
                            name=name,
                            channels=max(1, min(channels, 2)),
                            sample_rate=int(info.get('defaultSampleRate', AUDIO_SAMPLE_RATE)),
                            is_loopback=is_loopback,
                            is_input=is_input,
                            is_output=is_output,
                            is_default=(i == default_input_idx or i == default_output_idx),
                            host_api=host_api,
                            host_api_index=host_api_idx,
                            latency=float(info.get('defaultLowInputLatency', 0.0)),
                        ))
                except Exception:
                    continue

            pa.terminate()

        except Exception as e:
            logger.error(f"Error listing Windows devices: {e}")

        return devices

    @staticmethod
    def _get_unix_devices(capture_mode: CaptureMode) -> List[AudioDevice]:
        """Get macOS/Linux audio devices."""
        devices = []
        try:
            import sounddevice as sd

            default_input = sd.default.device[0]

            for i, dev in enumerate(sd.query_devices()):
                name = dev.get('name', f'Device {i}')
                name_lower = name.lower()

                max_input = int(dev.get('max_input_channels', 0))
                max_output = int(dev.get('max_output_channels', 0))

                is_input = max_input > 0
                is_output = max_output > 0

                # Detect loopback devices
                is_loopback = False
                if is_input:
                    loopback_keywords = ['monitor', 'blackhole', 'loopback',
                                        'soundflower', 'vb-audio', 'virtual']
                    if any(kw in name_lower for kw in loopback_keywords):
                        is_loopback = True

                # Filter by capture mode
                include = False
                if capture_mode == CaptureMode.SYSTEM_LOOPBACK:
                    include = is_loopback
                elif capture_mode == CaptureMode.MICROPHONE:
                    include = is_input and not is_loopback
                else:
                    include = is_input

                if include:
                    devices.append(AudioDevice(
                        index=i,
                        name=name,
                        channels=min(max_input, 2),
                        sample_rate=int(dev.get('default_samplerate', AUDIO_SAMPLE_RATE)),
                        is_loopback=is_loopback,
                        is_input=is_input,
                        is_output=is_output,
                        is_default=(i == default_input),
                        host_api=str(dev.get('hostapi', '')),
                        latency=float(dev.get('default_low_input_latency', 0.0)),
                    ))

        except Exception as e:
            logger.error(f"Error listing audio devices: {e}")

        return devices

    @staticmethod
    def get_recommended_device(capture_mode: CaptureMode = CaptureMode.SYSTEM_LOOPBACK) -> Optional[AudioDevice]:
        """Get the best device for the capture mode."""
        devices = EnhancedAudioCapture.get_available_devices(capture_mode)

        if not devices:
            return None

        if capture_mode == CaptureMode.SYSTEM_LOOPBACK:
            # Priority for loopback: WASAPI output > Stereo Mix > BlackHole > Monitor
            # First check for WASAPI loopback (output devices that can be captured)
            for dev in devices:
                if dev.is_output and 'wasapi' in dev.host_api.lower():
                    if dev.is_default:
                        return dev

            for dev in devices:
                if dev.is_output and 'wasapi' in dev.host_api.lower():
                    return dev

            # Then check for Stereo Mix type devices
            for dev in devices:
                if dev.is_loopback and dev.is_input:
                    return dev

        elif capture_mode == CaptureMode.MICROPHONE:
            # Priority: Default mic > First available mic
            for dev in devices:
                if dev.is_default:
                    return dev

            for dev in devices:
                if dev.is_input:
                    return dev

        return devices[0] if devices else None

    @staticmethod
    def get_setup_instructions() -> Dict[str, str]:
        """Get platform-specific setup instructions."""
        return {
            "windows": """
WINDOWS SYSTEM AUDIO CAPTURE SETUP:

RECOMMENDED: Install pyaudiowpatch for best quality:
  pip install pyaudiowpatch
  (Enables true WASAPI loopback - no configuration needed!)

ALTERNATIVE: Enable Stereo Mix
1. Right-click speaker icon > Sound settings
2. Click "More sound settings" (or Sound Control Panel)
3. Recording tab > Right-click > Show Disabled Devices
4. Right-click "Stereo Mix" > Enable
5. Right-click "Stereo Mix" > Set as Default Device

FALLBACK: VB-Audio Virtual Cable (free)
  https://vb-audio.com/Cable/
""",
            "macos": """
macOS SYSTEM AUDIO CAPTURE SETUP:

RECOMMENDED: BlackHole (Free)
1. brew install blackhole-2ch
2. Open Audio MIDI Setup (in Utilities)
3. Click + > Create Multi-Output Device
4. Check your speakers AND BlackHole 2ch
5. Set Multi-Output as system output
6. Select "BlackHole 2ch" in ReadIn AI

ALTERNATIVE: Loopback by Rogue Amoeba
  https://rogueamoeba.com/loopback/
""",
            "linux": """
LINUX SYSTEM AUDIO CAPTURE SETUP:

PulseAudio:
1. sudo apt install pavucontrol
2. Open pavucontrol > Recording tab
3. Select "Monitor of [output device]"

PipeWire (newer distros):
  Monitor devices should auto-appear
  Look for "Monitor of Built-in Audio"
""",
        }

    def _high_quality_resample(self, audio: np.ndarray, source_rate: int, target_rate: int) -> np.ndarray:
        """High-quality resampling."""
        if source_rate == target_rate:
            return audio

        try:
            from scipy import signal
            gcd = np.gcd(source_rate, target_rate)
            up = target_rate // gcd
            down = source_rate // gcd
            return signal.resample_poly(audio, up, down).astype(np.float32)
        except ImportError:
            # Linear interpolation fallback
            duration = len(audio) / source_rate
            target_samples = int(duration * target_rate)
            if target_samples <= 0:
                return audio
            indices = np.linspace(0, len(audio) - 1, target_samples)
            return np.interp(indices, np.arange(len(audio)), audio).astype(np.float32)

    def _convert_to_mono(self, audio: np.ndarray, channels: int) -> np.ndarray:
        """Convert multi-channel audio to mono."""
        if channels <= 1:
            return audio.flatten()

        # Reshape if needed
        if len(audio.shape) == 1 and channels > 1:
            try:
                audio = audio.reshape(-1, channels)
            except:
                return audio.flatten()

        if len(audio.shape) > 1:
            return audio.mean(axis=1).astype(np.float32)

        return audio.flatten()

    def _calculate_audio_level(self, audio: np.ndarray) -> float:
        """Calculate RMS audio level (0.0 to 1.0)."""
        if len(audio) == 0:
            return 0.0
        rms = np.sqrt(np.mean(audio ** 2))
        return float(min(1.0, rms * 3.0))

    def _process_audio(self):
        """Process buffered audio and emit chunks."""
        while self._running:
            try:
                raw_data = self._buffer_queue.get(timeout=0.1)

                # Convert to float32 numpy array
                if isinstance(raw_data, bytes):
                    audio = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32) / 32768.0
                elif isinstance(raw_data, np.ndarray):
                    audio = raw_data.astype(np.float32)
                    if audio.dtype == np.int16 or np.abs(audio).max() > 2.0:
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

                # Calculate level
                self._current_audio_level = self._calculate_audio_level(audio)
                if self.on_audio_level:
                    self.on_audio_level(self._current_audio_level)

                # Buffer and emit chunks with thread safety
                with self._buffer_lock:
                    self._audio_buffer = np.concatenate([self._audio_buffer, audio])

                    # Enforce bounded buffer: drop oldest samples if buffer exceeds max size
                    if len(self._audio_buffer) > self._max_buffer_samples:
                        excess = len(self._audio_buffer) - self._max_buffer_samples
                        self._audio_buffer = self._audio_buffer[excess:]

                    while len(self._audio_buffer) >= self._samples_per_chunk:
                        chunk = self._audio_buffer[:self._samples_per_chunk]
                        self._audio_buffer = self._audio_buffer[self._samples_per_chunk:]
                        self.on_audio_chunk(chunk)
                        self._chunks_processed += 1

            except queue.Empty:
                continue
            except Exception as e:
                self._error_count += 1
                if self._error_count <= 3:
                    logger.error(f"Audio processing error: {e}")

    def _audio_callback(self, in_data, frame_count, time_info, status):
        """Audio stream callback (backup method)."""
        if self._running:
            try:
                self._buffer_queue.put_nowait(in_data)
            except queue.Full:
                pass

        if IS_WINDOWS:
            import pyaudio
            return (None, pyaudio.paContinue)
        return None

    def _capture_loop(self):
        """Polling-based audio capture loop (more reliable than callbacks on Windows)."""
        consecutive_errors = 0
        max_consecutive_errors = 50  # Allow more errors before giving up

        # Wait a moment for stream to be ready
        time.sleep(0.1)

        # Calculate frames per read (50ms chunks)
        frames_per_read = int(self._source_sample_rate * 0.05)

        while self._running:
            stream = None
            with self._stream_lock:
                stream = self._stream

            if stream is None:
                time.sleep(0.01)
                continue

            try:
                # Check if stream is active
                if hasattr(stream, 'is_active'):
                    if not stream.is_active():
                        time.sleep(0.01)
                        continue

                # Read audio data (blocking call - do NOT hold lock during read)
                data = stream.read(frames_per_read, exception_on_overflow=False)

                if data and len(data) > 0:
                    try:
                        self._buffer_queue.put_nowait(data)
                        consecutive_errors = 0
                    except queue.Full:
                        pass  # Queue full, skip this chunk
                else:
                    consecutive_errors += 1

            except Exception as read_error:
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    logger.error(f"Capture loop error after {consecutive_errors} errors: {read_error}")
                    break
                time.sleep(0.01)

        # End of loop
        if self._running:
            logger.warning("Capture loop ended unexpectedly")

    def _start_windows_wasapi_loopback(self, pa, device: AudioDevice) -> bool:
        """Start WASAPI loopback capture (captures output device audio)."""
        try:
            import pyaudiowpatch as pyaudio

            # Try to get WASAPI loopback device info
            loopback_device = None

            # First, try to get the default WASAPI loopback device
            try:
                loopback_device = pa.get_default_wasapi_loopback()
                logger.info(f"Found default WASAPI loopback: {loopback_device['name']}")
            except Exception as e:
                logger.debug(f"No default WASAPI loopback: {e}")

            # If no default loopback, search for one
            if loopback_device is None:
                for i in range(pa.get_device_count()):
                    try:
                        dev_info = pa.get_device_info_by_index(i)
                        if dev_info.get('isLoopbackDevice', False):
                            loopback_device = dev_info
                            logger.info(f"Found loopback device: {dev_info['name']}")
                            break
                    except:
                        continue

            if loopback_device is None:
                logger.warning("No WASAPI loopback device available")
                return False

            # Configure stream parameters from loopback device
            channels = int(loopback_device['maxInputChannels'])
            sample_rate = int(loopback_device['defaultSampleRate'])
            device_index = int(loopback_device['index'])

            # Buffer size - smaller for lower latency polling
            buffer_size = int(sample_rate * 0.05)  # 50ms buffer

            self._source_sample_rate = sample_rate
            self._source_channels = channels

            # Open stream in blocking mode (no callback) for reliable capture
            self._stream = pa.open(
                format=pyaudio.paInt16,
                channels=channels,
                rate=sample_rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=buffer_size,
            )
            self._stream.start_stream()

            self._wasapi_loopback = True
            self._current_device_name = loopback_device['name']

            # Start capture thread for polling
            self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self._capture_thread.start()

            logger.info(f"WASAPI Loopback ACTIVE (polling): {loopback_device['name']} ({channels}ch @ {sample_rate}Hz)")
            return True

        except Exception as e:
            logger.error(f"WASAPI loopback failed: {e}", exc_info=True)
            return False

    def _start_windows(self):
        """Start Windows audio capture with robust fallback system."""
        # Try pyaudiowpatch first for WASAPI loopback
        has_wpatch = self._check_wasapi_loopback_support()

        try:
            if has_wpatch:
                import pyaudiowpatch as pyaudio
            else:
                import pyaudio
        except ImportError as e:
            self._emit_error(f"PyAudio not installed: {e}")
            self._running = False
            return

        self._pa = pyaudio.PyAudio()

        # STRATEGY 1: For SYSTEM_LOOPBACK mode, try WASAPI loopback first
        if self.capture_mode == CaptureMode.SYSTEM_LOOPBACK and has_wpatch:
            if self._start_windows_wasapi_loopback(self._pa, None):
                return
            logger.info("WASAPI loopback unavailable, trying alternatives...")

        # STRATEGY 2: For SYSTEM_LOOPBACK, try Stereo Mix or similar
        if self.capture_mode == CaptureMode.SYSTEM_LOOPBACK:
            loopback_device = self._find_stereo_mix_device()
            if loopback_device and self._start_input_device(loopback_device):
                return

        # STRATEGY 3: Use specified device or default input
        device = None

        if self._device_index is not None:
            try:
                info = self._pa.get_device_info_by_index(self._device_index)
                if info.get('maxInputChannels', 0) > 0:
                    device = self._create_device_from_info(info, self._device_index)
            except:
                pass

        # STRATEGY 4: Get default input device
        if device is None:
            try:
                info = self._pa.get_default_input_device_info()
                device = self._create_device_from_info(info, info['index'])
            except:
                pass

        if device is None:
            self._emit_error("No audio input device found!")
            self._running = False
            return

        # Start capture on the device
        if self._start_input_device(device):
            if self.capture_mode == CaptureMode.SYSTEM_LOOPBACK:
                logger.warning(
                    "System audio loopback not available. Using microphone instead. "
                    "For stealth mode: Enable 'Stereo Mix' in Windows sound settings "
                    "or install VB-Audio Virtual Cable."
                )
            return

        self._emit_error("Failed to open audio stream")
        self._running = False

    def _create_device_from_info(self, info: dict, index: int) -> AudioDevice:
        """Create AudioDevice from PyAudio device info."""
        return AudioDevice(
            index=index,
            name=info.get('name', f'Device {index}'),
            channels=max(1, min(int(info.get('maxInputChannels', 1)), 2)),
            sample_rate=int(info.get('defaultSampleRate', self.sample_rate)),
            is_loopback=False,
            is_input=info.get('maxInputChannels', 0) > 0,
            is_output=info.get('maxOutputChannels', 0) > 0,
            is_default=False,
        )

    def _find_stereo_mix_device(self) -> Optional[AudioDevice]:
        """Find Stereo Mix or similar loopback input device.

        Note: 'PC Speaker' devices on modern Windows don't actually work as
        loopback devices despite the name. Only true Stereo Mix works.
        """
        # Keywords that indicate a TRUE loopback device (not PC Speaker which doesn't work)
        loopback_keywords = ['stereo mix', 'what u hear', 'wave out mix', 'rec. playback', 'mono mix']
        # PC Speaker and similar names DON'T work as loopback
        exclude_keywords = ['pc speaker', 'speaker']

        for i in range(self._pa.get_device_count()):
            try:
                info = self._pa.get_device_info_by_index(i)
                if info.get('maxInputChannels', 0) > 0:
                    name_lower = info['name'].lower()
                    # Check for true loopback device
                    if any(kw in name_lower for kw in loopback_keywords):
                        # Make sure it's not an excluded device
                        if not any(ex in name_lower for ex in exclude_keywords):
                            logger.info(f"Found loopback device: {info['name']}")
                            return self._create_device_from_info(info, i)
            except:
                continue

        # No true loopback found - provide guidance
        logger.info(
            "No Stereo Mix device found. To enable system audio capture: "
            "1. Right-click speaker icon > Sound settings > More sound settings, "
            "2. Recording tab > Right-click > Show Disabled Devices, "
            "3. Right-click 'Stereo Mix' > Enable"
        )
        return None

    def _start_input_device(self, device: AudioDevice) -> bool:
        """Start capture from an input device using polling (more reliable than callbacks)."""
        try:
            if self._check_wasapi_loopback_support():
                import pyaudiowpatch as pyaudio
            else:
                import pyaudio
        except:
            import pyaudio

        self._source_channels = device.channels
        self._source_sample_rate = device.sample_rate
        self._emit_device_change(device.name)

        buffer_size = int(device.sample_rate * 0.05)  # 50ms buffer

        # Try multiple sample rates
        rates = [device.sample_rate, 48000, 44100, 16000]
        rates = list(dict.fromkeys(rates))

        for rate in rates:
            try:
                # Open stream in blocking mode (no callback) for reliable capture
                self._stream = self._pa.open(
                    format=pyaudio.paInt16,
                    channels=device.channels,
                    rate=rate,
                    input=True,
                    input_device_index=device.index,
                    frames_per_buffer=buffer_size,
                )
                self._stream.start_stream()
                self._source_sample_rate = rate

                # Start capture thread for polling
                self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
                self._capture_thread.start()

                logger.info(f"Audio capture started (polling): {device.name} ({device.channels}ch @ {rate}Hz)")
                return True
            except Exception as e:
                if self._stream:
                    try:
                        self._stream.close()
                    except:
                        pass
                    self._stream = None
                continue

        return False

    def _start_unix(self):
        """Start macOS/Linux audio capture."""
        try:
            import sounddevice as sd
        except ImportError:
            self._emit_error("sounddevice not installed")
            self._running = False
            return

        def callback(indata, frames, time_info, status):
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
                    channels=int(info.get('max_input_channels', 1)),
                    sample_rate=int(info.get('default_samplerate', self.sample_rate)),
                    is_loopback=False,
                    is_input=True,
                    is_output=False,
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
        self._source_sample_rate = int(device.sample_rate)
        self._emit_device_change(device.name)

        buffer_size = int(device.sample_rate * (0.05 if self.low_latency else 0.1))

        try:
            self._stream = sd.InputStream(
                device=device.index,
                samplerate=device.sample_rate,
                channels=self._source_channels,
                dtype=np.float32,
                callback=callback,
                blocksize=buffer_size,
            )
            self._stream.start()
            logger.info(f"Audio capture started: {device.name} ({self._source_channels}ch @ {device.sample_rate}Hz)")
        except Exception as e:
            # Ensure stream is closed on error
            if self._stream:
                try:
                    self._stream.close()
                except:
                    pass
                self._stream = None
            self._emit_error(f"Failed to start capture: {e}")
            self._running = False

    def _emit_error(self, message: str):
        """Emit error message."""
        logger.error(f"AudioCapture: {message}")
        if self.on_error:
            self.on_error(message)

    def _emit_device_change(self, name: str):
        """Emit device change notification."""
        self._current_device_name = name
        if self.on_device_change:
            self.on_device_change(name)

    def start(self) -> bool:
        """Start audio capture. Returns True if started successfully."""
        if self._running:
            return True

        self._running = True
        self._audio_buffer = np.array([], dtype=np.float32)
        self._error_count = 0
        self._chunks_processed = 0
        self._start_time = time.time()
        self._wasapi_loopback = False

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

        return self._running

    def stop(self):
        """Stop audio capture and release all resources."""
        self._running = False

        # Clear the buffer queue before stopping threads
        while not self._buffer_queue.empty():
            try:
                self._buffer_queue.get_nowait()
            except queue.Empty:
                break

        # Wait for capture thread to finish
        if self._capture_thread:
            self._capture_thread.join(timeout=2.0)
            self._capture_thread = None

        # Close stream with lock
        with self._stream_lock:
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

        # Clear audio buffer
        with self._buffer_lock:
            self._audio_buffer = np.array([], dtype=np.float32)

    def __del__(self):
        """Cleanup resources on deletion."""
        self._cleanup_resources()

    def _cleanup_resources(self):
        """Release all audio resources."""
        self._running = False

        # Clear the buffer queue
        while not self._buffer_queue.empty():
            try:
                self._buffer_queue.get_nowait()
            except queue.Empty:
                break

        # Close audio stream with lock
        with self._stream_lock:
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

        # Terminate PyAudio instance
        if self._pa:
            try:
                self._pa.terminate()
            except:
                pass
            self._pa = None

        # Clear audio buffer
        with self._buffer_lock:
            self._audio_buffer = np.array([], dtype=np.float32)

    def set_device(self, device_index: Optional[int]) -> bool:
        """Set audio device. Restarts capture if running."""
        was_running = self._running
        if was_running:
            self.stop()

        self._device_index = device_index

        if was_running:
            return self.start()
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
            "wasapi_loopback": self._wasapi_loopback,
            "preprocessing_enabled": self._preprocessor is not None,
            "low_latency_mode": self.low_latency,
        }


def list_audio_devices(capture_mode: CaptureMode = CaptureMode.SYSTEM_LOOPBACK):
    """List available audio devices for the given capture mode."""
    mode_name = {
        CaptureMode.SYSTEM_LOOPBACK: "STEALTH MODE (System Audio)",
        CaptureMode.MICROPHONE: "MICROPHONE MODE",
        CaptureMode.MIXED: "MIXED MODE",
    }

    logger.info(f"Available devices for {mode_name.get(capture_mode, capture_mode.value)}:")

    devices = EnhancedAudioCapture.get_available_devices(capture_mode)

    if not devices:
        logger.warning("No suitable devices found!")
        instructions = EnhancedAudioCapture.get_setup_instructions()
        if IS_WINDOWS:
            logger.info(instructions["windows"])
        elif IS_MACOS:
            logger.info(instructions["macos"])
        else:
            logger.info(instructions["linux"])
        return

    recommended = EnhancedAudioCapture.get_recommended_device(capture_mode)

    for dev in devices:
        flags = []
        if dev.is_loopback:
            flags.append("LOOPBACK")
        if dev.is_default:
            flags.append("DEFAULT")
        if recommended and dev.index == recommended.index:
            flags.append("RECOMMENDED")

        flag_str = f" [{', '.join(flags)}]" if flags else ""
        logger.info(f"  [{dev.index}] {dev.name} - {dev.channels}ch @ {dev.sample_rate}Hz | {dev.host_api}{flag_str}")


def test_audio_capture():
    """Test audio capture functionality."""
    logger.info("=" * 60)
    logger.info("AUDIO CAPTURE TEST")
    logger.info("=" * 60)

    chunks_received = []
    peak_level = [0.0]

    def on_chunk(chunk):
        chunks_received.append(chunk)
        peak = np.abs(chunk).max()
        if peak > peak_level[0]:
            peak_level[0] = peak

    def on_level(level):
        pass

    def on_device(name):
        logger.info(f"  Device: {name}")

    # Test 1: Microphone mode
    logger.info("TEST 1: MICROPHONE MODE")
    logger.info("-" * 40)
    chunks_received.clear()
    peak_level[0] = 0.0

    capture = EnhancedAudioCapture(
        on_audio_chunk=on_chunk,
        capture_mode=CaptureMode.MICROPHONE,
        on_device_change=on_device,
        on_audio_level=on_level,
    )

    if capture.start():
        logger.info(f"  Started: {capture.is_running()}")
        logger.info("  Capturing for 3 seconds... (speak into mic)")

        for i in range(30):  # 3 seconds
            time.sleep(0.1)
            if i % 10 == 0:
                logger.info(f"  Level: {capture.get_audio_level():.4f} | Chunks: {len(chunks_received)}")

        capture.stop()
        logger.info(f"  MIC RESULT: {len(chunks_received)} chunks, Peak={peak_level[0]:.4f}")
    else:
        logger.error("  [FAIL] Could not start microphone capture")

    # Test 2: System loopback mode
    logger.info("TEST 2: SYSTEM LOOPBACK MODE")
    logger.info("-" * 40)
    chunks_received.clear()
    peak_level[0] = 0.0

    capture = EnhancedAudioCapture(
        on_audio_chunk=on_chunk,
        capture_mode=CaptureMode.SYSTEM_LOOPBACK,
        on_device_change=on_device,
        on_audio_level=on_level,
    )

    if capture.start():
        logger.info(f"  Started: {capture.is_running()}")
        logger.info("  Capturing for 3 seconds... (play some audio on your system)")

        for i in range(30):  # 3 seconds
            time.sleep(0.1)
            if i % 10 == 0:
                status = capture.get_status()
                logger.info(f"  Level: {capture.get_audio_level():.4f} | Chunks: {len(chunks_received)} | WASAPI: {status['wasapi_loopback']}")

        capture.stop()
        logger.info(f"  LOOPBACK RESULT: {len(chunks_received)} chunks, Peak={peak_level[0]:.4f}")
        logger.info(f"  WASAPI Loopback: {status['wasapi_loopback']}")
    else:
        logger.error("  [FAIL] Could not start loopback capture")

    logger.info("=" * 60)
    logger.info("TEST COMPLETE")
    logger.info("=" * 60)

    if len(chunks_received) > 0:
        logger.info("[SUCCESS] Audio capture is working!")
    else:
        logger.warning("[WARNING] No audio chunks received. Check device configuration.")


if __name__ == "__main__":
    import sys

    logger.info("ReadIn AI Audio Capture - Device Detection")

    # Check WASAPI support
    if IS_WINDOWS:
        if EnhancedAudioCapture._check_wasapi_loopback_support():
            logger.info("[OK] pyaudiowpatch available - True WASAPI loopback supported!")
        else:
            logger.warning("[!!] pyaudiowpatch not installed - Install for best quality: pip install pyaudiowpatch")

    list_audio_devices(CaptureMode.SYSTEM_LOOPBACK)
    list_audio_devices(CaptureMode.MICROPHONE)

    # Run test if --test flag provided
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        test_audio_capture()
