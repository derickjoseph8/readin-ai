"""Cross-platform system audio capture with device selection."""

import threading
import queue
import time
from typing import Callable, Optional, List, Tuple, Dict, Any

import numpy as np

from config import AUDIO_SAMPLE_RATE, AUDIO_CHUNK_DURATION, IS_WINDOWS, IS_MACOS, IS_LINUX


class AudioCapture:
    """Captures system audio for real-time processing (cross-platform)."""

    def __init__(
        self,
        on_audio_chunk: Callable[[np.ndarray], None],
        device_index: Optional[int] = None,
        on_device_change: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
        on_audio_level: Optional[Callable[[float], None]] = None
    ):
        self.on_audio_chunk = on_audio_chunk
        self.on_device_change = on_device_change
        self.on_error = on_error
        self.on_audio_level = on_audio_level  # Callback for real-time audio level
        self.sample_rate = AUDIO_SAMPLE_RATE
        self.chunk_duration = AUDIO_CHUNK_DURATION
        self._running = False
        self._processor_thread: Optional[threading.Thread] = None
        self._capture_thread: Optional[threading.Thread] = None
        self._audio_buffer = np.array([], dtype=np.float32)
        self._samples_per_chunk = int(self.sample_rate * self.chunk_duration)
        self._buffer_queue: queue.Queue = queue.Queue()
        self._device_index = device_index
        self._current_device_name = ""
        self._current_audio_level = 0.0
        self._last_error_time = 0.0
        self._error_count = 0
        self._source_sample_rate: Optional[int] = None  # Track source sample rate for resampling
        self._source_channels: int = 1

        # Platform-specific audio backends
        self._pa = None  # PyAudio instance (Windows)
        self._stream = None

    @staticmethod
    def get_available_devices() -> List[Dict[str, Any]]:
        """Get list of available audio input devices.

        Returns:
            List of dicts with keys: index, name, channels, is_loopback, is_default
        """
        devices = []

        if IS_WINDOWS:
            try:
                import pyaudio
                pa = pyaudio.PyAudio()
                default_input = pa.get_default_input_device_info()
                default_index = default_input['index'] if default_input else -1

                for i in range(pa.get_device_count()):
                    info = pa.get_device_info_by_index(i)
                    if info['maxInputChannels'] > 0:
                        name = info['name']
                        name_lower = name.lower()
                        is_loopback = (
                            'loopback' in name_lower or
                            'stereo mix' in name_lower or
                            'what u hear' in name_lower
                        )
                        devices.append({
                            'index': i,
                            'name': name,
                            'channels': info['maxInputChannels'],
                            'is_loopback': is_loopback,
                            'is_default': i == default_index,
                            'sample_rate': int(info.get('defaultSampleRate', AUDIO_SAMPLE_RATE)),
                        })
                pa.terminate()
            except Exception as e:
                print(f"Error listing Windows audio devices: {e}")
        else:
            try:
                import sounddevice as sd
                default_input = sd.default.device[0]

                for i, device in enumerate(sd.query_devices()):
                    if device['max_input_channels'] > 0:
                        name = device['name']
                        name_lower = name.lower()
                        is_loopback = (
                            'monitor' in name_lower or
                            'blackhole' in name_lower or
                            'loopback' in name_lower
                        )
                        devices.append({
                            'index': i,
                            'name': name,
                            'channels': device['max_input_channels'],
                            'is_loopback': is_loopback,
                            'is_default': i == default_input,
                            'sample_rate': int(device.get('default_samplerate', AUDIO_SAMPLE_RATE)),
                        })
            except Exception as e:
                print(f"Error listing audio devices: {e}")

        return devices

    @staticmethod
    def get_recommended_device() -> Optional[int]:
        """Get the recommended device index (loopback first, then default)."""
        devices = AudioCapture.get_available_devices()

        # Prefer loopback devices
        for device in devices:
            if device['is_loopback']:
                return device['index']

        # Fall back to default input
        for device in devices:
            if device['is_default']:
                return device['index']

        # Fall back to first available
        if devices:
            return devices[0]['index']

        return None

    def set_device(self, device_index: Optional[int]) -> bool:
        """Set the audio device to use. If currently running, restarts capture.

        Args:
            device_index: Device index or None for auto-detection

        Returns:
            True if successful, False otherwise
        """
        was_running = self._running
        if was_running:
            self.stop()

        self._device_index = device_index

        if was_running:
            self.start()
            return self._running

        return True

    def get_current_device(self) -> Tuple[Optional[int], str]:
        """Get the current device index and name."""
        return self._device_index, self._current_device_name

    def _emit_error(self, message: str):
        """Emit an error message."""
        print(f"Audio error: {message}")
        if self.on_error:
            self.on_error(message)

    def _emit_device_change(self, device_name: str):
        """Emit device change notification."""
        self._current_device_name = device_name
        if self.on_device_change:
            self.on_device_change(device_name)

    def _find_loopback_device_windows(self) -> Optional[int]:
        """Find WASAPI loopback or stereo mix device on Windows."""
        import pyaudio

        if self._pa is None:
            self._pa = pyaudio.PyAudio()

        for i in range(self._pa.get_device_count()):
            info = self._pa.get_device_info_by_index(i)
            name = info['name'].lower()

            if info['maxInputChannels'] > 0:
                if 'loopback' in name or 'stereo mix' in name or 'what u hear' in name:
                    print(f"Found loopback device: [{i}] {info['name']}")
                    return i

        return None

    def _find_input_device_windows(self) -> Optional[int]:
        """Find any available input device on Windows."""
        import pyaudio

        if self._pa is None:
            self._pa = pyaudio.PyAudio()

        for i in range(self._pa.get_device_count()):
            info = self._pa.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                print(f"Fallback input: [{i}] {info['name']}")
                return i
        return None

    def _convert_to_mono(self, audio: np.ndarray, channels: int) -> np.ndarray:
        """Convert multi-channel audio to mono with proper mixing."""
        if channels <= 1 or len(audio.shape) == 1:
            return audio.flatten()

        # Reshape to (samples, channels) if needed
        if len(audio.shape) == 1 and channels > 1:
            audio = audio.reshape(-1, channels)

        # Average all channels for mono
        return audio.mean(axis=1).astype(np.float32)

    def _resample_audio(self, audio: np.ndarray, source_rate: int, target_rate: int) -> np.ndarray:
        """Resample audio to target sample rate."""
        if source_rate == target_rate:
            return audio

        # Simple linear interpolation resampling
        duration = len(audio) / source_rate
        target_samples = int(duration * target_rate)

        if target_samples <= 0:
            return audio

        indices = np.linspace(0, len(audio) - 1, target_samples)
        return np.interp(indices, np.arange(len(audio)), audio).astype(np.float32)

    def _calculate_audio_level(self, audio: np.ndarray) -> float:
        """Calculate RMS audio level (0.0 to 1.0)."""
        if len(audio) == 0:
            return 0.0
        rms = np.sqrt(np.mean(audio ** 2))
        # Normalize to 0-1 range (typical speech is around 0.01-0.1)
        level = min(1.0, rms * 5.0)
        return float(level)

    def _process_audio(self):
        """Process buffered audio and emit chunks."""
        while self._running:
            try:
                raw_data = self._buffer_queue.get(timeout=0.1)

                # Convert based on format
                if isinstance(raw_data, bytes):
                    audio = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32) / 32768.0
                elif isinstance(raw_data, np.ndarray):
                    audio = raw_data.astype(np.float32)
                    # Normalize if needed (int16 range)
                    if np.abs(audio).max() > 1.5:
                        audio = audio / 32768.0
                else:
                    continue

                # Convert stereo to mono if needed
                if self._source_channels > 1:
                    audio = self._convert_to_mono(audio, self._source_channels)
                else:
                    audio = audio.flatten()

                # Resample if source rate differs from target
                if self._source_sample_rate and self._source_sample_rate != self.sample_rate:
                    audio = self._resample_audio(audio, self._source_sample_rate, self.sample_rate)

                # Calculate and emit audio level
                self._current_audio_level = self._calculate_audio_level(audio)
                if self.on_audio_level:
                    self.on_audio_level(self._current_audio_level)

                self._audio_buffer = np.concatenate([self._audio_buffer, audio])

                while len(self._audio_buffer) >= self._samples_per_chunk:
                    chunk = self._audio_buffer[:self._samples_per_chunk]
                    self._audio_buffer = self._audio_buffer[self._samples_per_chunk:]
                    self.on_audio_chunk(chunk)

            except queue.Empty:
                continue
            except Exception as e:
                self._error_count += 1
                current_time = time.time()
                # Rate limit error logging
                if current_time - self._last_error_time > 5.0:
                    print(f"Audio processing error: {e}")
                    self._last_error_time = current_time
                # If too many errors, try to recover
                if self._error_count > 10:
                    print("Too many audio errors, attempting recovery...")
                    self._error_count = 0
                    self._audio_buffer = np.array([], dtype=np.float32)

    def _audio_callback_pyaudio(self, in_data, frame_count, time_info, status):
        """PyAudio stream callback."""
        import pyaudio
        if self._running:
            self._buffer_queue.put(in_data)
        return (None, pyaudio.paContinue)

    def _start_windows(self):
        """Start audio capture on Windows using PyAudio."""
        import pyaudio

        if self._pa is None:
            self._pa = pyaudio.PyAudio()

        # Use specified device or auto-detect
        device_index = self._device_index
        if device_index is None:
            device_index = self._find_loopback_device_windows()
            if device_index is None:
                device_index = self._find_input_device_windows()

        if device_index is None:
            self._emit_error("No audio input device found!")
            self._running = False
            return

        try:
            info = self._pa.get_device_info_by_index(device_index)
        except Exception as e:
            self._emit_error(f"Invalid device index {device_index}: {e}")
            self._running = False
            return

        channels = min(int(info['maxInputChannels']), 2)
        device_name = info['name']
        device_sample_rate = int(info.get('defaultSampleRate', self.sample_rate))

        # Store source info for processing
        self._source_channels = channels
        self._source_sample_rate = device_sample_rate

        print(f"Using device: {device_name} ({channels}ch @ {device_sample_rate}Hz)")
        self._emit_device_change(device_name)

        # Try with device's native sample rate first, then fall back
        sample_rates_to_try = [device_sample_rate, self.sample_rate, 44100, 48000]
        seen = set()
        sample_rates_to_try = [x for x in sample_rates_to_try if not (x in seen or seen.add(x))]

        for try_rate in sample_rates_to_try:
            try:
                self._stream = self._pa.open(
                    format=pyaudio.paInt16,
                    channels=channels,
                    rate=try_rate,
                    input=True,
                    input_device_index=device_index,
                    frames_per_buffer=int(try_rate * 0.1),
                    stream_callback=self._audio_callback_pyaudio,
                )
                self._stream.start_stream()
                self._source_sample_rate = try_rate
                print(f"Audio capture started (Windows) at {try_rate}Hz")
                return
            except Exception as e:
                print(f"Failed to start at {try_rate}Hz: {e}")
                if self._stream:
                    try:
                        self._stream.close()
                    except:
                        pass
                    self._stream = None
                continue

        # If all sample rates fail, try default device
        if self._device_index is not None:
            self._emit_error("Failed to start with selected device. Trying default...")
            try:
                self._source_channels = 1
                self._source_sample_rate = self.sample_rate
                self._stream = self._pa.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=self.sample_rate,
                    input=True,
                    frames_per_buffer=int(self.sample_rate * 0.1),
                    stream_callback=self._audio_callback_pyaudio,
                )
                self._stream.start_stream()
                self._emit_device_change("Default Input")
                print("Audio capture started (default device)")
            except Exception as e2:
                self._emit_error(f"Audio capture failed: {e2}")
                self._running = False
        else:
            self._emit_error("Audio capture failed: Could not open any audio stream")
            self._running = False

    def _start_macos(self):
        """Start audio capture on macOS using sounddevice."""
        import sounddevice as sd

        def callback(indata, frames, time_info, status):
            if status:
                print(f"Audio status: {status}")
            if self._running:
                # Put raw data in queue - processing thread handles conversion
                self._buffer_queue.put(indata.copy())

        try:
            device_index = self._device_index
            device_name = "Default Input"
            channels = 1
            device_sample_rate = self.sample_rate

            if device_index is not None:
                try:
                    device_info = sd.query_devices(device_index)
                    device_name = device_info['name']
                    channels = min(int(device_info['max_input_channels']), 2)
                    device_sample_rate = int(device_info.get('default_samplerate', self.sample_rate))
                    if channels == 0:
                        raise ValueError(f"Device {device_name} has no input channels")
                except Exception as e:
                    print(f"Device {device_index} error: {e}, falling back to default")
                    device_index = None

            # If no device specified, try to find BlackHole or loopback
            if device_index is None:
                for i, dev in enumerate(sd.query_devices()):
                    if dev['max_input_channels'] > 0:
                        name_lower = dev['name'].lower()
                        if 'blackhole' in name_lower or 'loopback' in name_lower:
                            device_index = i
                            device_name = dev['name']
                            channels = min(int(dev['max_input_channels']), 2)
                            device_sample_rate = int(dev.get('default_samplerate', self.sample_rate))
                            print(f"Auto-selected loopback device: {device_name}")
                            break

            # Store source info for processing
            self._source_channels = channels
            self._source_sample_rate = device_sample_rate

            # Try with device's native sample rate first
            sample_rates_to_try = [device_sample_rate, self.sample_rate, 44100, 48000]
            seen = set()
            sample_rates_to_try = [x for x in sample_rates_to_try if not (x in seen or seen.add(x))]

            for try_rate in sample_rates_to_try:
                try:
                    self._stream = sd.InputStream(
                        device=device_index,
                        samplerate=try_rate,
                        channels=channels,
                        dtype=np.float32,
                        callback=callback,
                        blocksize=int(try_rate * 0.1),
                    )
                    self._stream.start()
                    self._source_sample_rate = try_rate
                    self._emit_device_change(device_name)
                    print(f"Audio capture started (macOS) - {device_name} at {try_rate}Hz")
                    if device_index is None:
                        print("Tip: Install BlackHole (brew install blackhole-2ch) for system audio capture")
                    return
                except Exception as e:
                    print(f"Failed to start at {try_rate}Hz: {e}")
                    if self._stream:
                        try:
                            self._stream.close()
                        except:
                            pass
                        self._stream = None
                    continue

            self._emit_error("Failed to start audio capture with any sample rate")
            self._running = False

        except Exception as e:
            self._emit_error(f"Failed to start audio: {e}")
            self._running = False

    def _start_linux(self):
        """Start audio capture on Linux using sounddevice with PulseAudio."""
        import sounddevice as sd

        def callback(indata, frames, time_info, status):
            if status:
                print(f"Audio status: {status}")
            if self._running:
                # Put raw data in queue - processing thread handles conversion
                self._buffer_queue.put(indata.copy())

        try:
            device_index = self._device_index
            device_name = "Default Input"
            channels = 1
            device_sample_rate = self.sample_rate

            if device_index is not None:
                try:
                    device_info = sd.query_devices(device_index)
                    device_name = device_info['name']
                    channels = min(int(device_info['max_input_channels']), 2)
                    device_sample_rate = int(device_info.get('default_samplerate', self.sample_rate))
                    if channels == 0:
                        raise ValueError(f"Device {device_name} has no input channels")
                except Exception as e:
                    print(f"Device {device_index} error: {e}, falling back to default")
                    device_index = None

            # If no device specified, try to find PulseAudio monitor
            if device_index is None:
                for i, dev in enumerate(sd.query_devices()):
                    if dev['max_input_channels'] > 0:
                        name_lower = dev['name'].lower()
                        # PulseAudio monitor devices contain "monitor" in name
                        if 'monitor' in name_lower:
                            device_index = i
                            device_name = dev['name']
                            channels = min(int(dev['max_input_channels']), 2)
                            device_sample_rate = int(dev.get('default_samplerate', self.sample_rate))
                            print(f"Auto-selected monitor device: {device_name}")
                            break

            # Store source info for processing
            self._source_channels = channels
            self._source_sample_rate = device_sample_rate

            # Try with device's native sample rate first
            sample_rates_to_try = [device_sample_rate, self.sample_rate, 44100, 48000]
            seen = set()
            sample_rates_to_try = [x for x in sample_rates_to_try if not (x in seen or seen.add(x))]

            for try_rate in sample_rates_to_try:
                try:
                    self._stream = sd.InputStream(
                        device=device_index,
                        samplerate=try_rate,
                        channels=channels,
                        dtype=np.float32,
                        callback=callback,
                        blocksize=int(try_rate * 0.1),
                    )
                    self._stream.start()
                    self._source_sample_rate = try_rate
                    self._emit_device_change(device_name)
                    print(f"Audio capture started (Linux) - {device_name} at {try_rate}Hz")
                    if device_index is None:
                        print("Tip: Select 'Monitor of [speaker]' device for system audio capture")
                    return
                except Exception as e:
                    print(f"Failed to start at {try_rate}Hz: {e}")
                    if self._stream:
                        try:
                            self._stream.close()
                        except:
                            pass
                        self._stream = None
                    continue

            self._emit_error("Failed to start audio capture with any sample rate")
            self._running = False

        except Exception as e:
            self._emit_error(f"Failed to start audio: {e}")
            self._running = False

    def start(self):
        """Start capturing audio."""
        if self._running:
            return

        self._running = True
        self._audio_buffer = np.array([], dtype=np.float32)
        self._error_count = 0
        self._last_error_time = 0.0
        self._current_audio_level = 0.0

        # Clear any stale data from queue
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
        elif IS_MACOS:
            self._start_macos()
        elif IS_LINUX:
            self._start_linux()
        else:
            print(f"Unsupported platform: {__import__('sys').platform}")
            self._running = False

    def stop(self):
        """Stop capturing audio."""
        self._running = False

        if self._stream:
            try:
                if IS_WINDOWS:
                    self._stream.stop_stream()
                    self._stream.close()
                else:
                    self._stream.stop()
                    self._stream.close()
            except Exception:
                pass
            self._stream = None

        if self._pa:
            try:
                self._pa.terminate()
            except Exception:
                pass
            self._pa = None

        if self._processor_thread:
            self._processor_thread.join(timeout=1.0)
            self._processor_thread = None

    def is_running(self) -> bool:
        """Check if audio capture is active."""
        return self._running

    def get_audio_level(self) -> float:
        """Get current audio level (0.0 to 1.0)."""
        return self._current_audio_level

    def get_status(self) -> Dict[str, Any]:
        """Get detailed audio capture status."""
        return {
            "is_running": self._running,
            "device_index": self._device_index,
            "device_name": self._current_device_name,
            "source_sample_rate": self._source_sample_rate,
            "target_sample_rate": self.sample_rate,
            "source_channels": self._source_channels,
            "audio_level": self._current_audio_level,
            "error_count": self._error_count,
        }

    @staticmethod
    def list_devices():
        """List available audio devices for debugging."""
        devices = AudioCapture.get_available_devices()
        print("Available audio input devices:")
        for device in devices:
            flags = []
            if device['is_loopback']:
                flags.append("LOOPBACK")
            if device['is_default']:
                flags.append("DEFAULT")
            flag_str = f" [{', '.join(flags)}]" if flags else ""
            print(f"  [{device['index']}] {device['name']} ({device['channels']} ch){flag_str}")
