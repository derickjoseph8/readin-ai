"""Cross-platform system audio capture."""

import threading
import queue
from typing import Callable, Optional

import numpy as np

from config import AUDIO_SAMPLE_RATE, AUDIO_CHUNK_DURATION, IS_WINDOWS, IS_MACOS, IS_LINUX


class AudioCapture:
    """Captures system audio for real-time processing (cross-platform)."""

    def __init__(self, on_audio_chunk: Callable[[np.ndarray], None]):
        self.on_audio_chunk = on_audio_chunk
        self.sample_rate = AUDIO_SAMPLE_RATE
        self.chunk_duration = AUDIO_CHUNK_DURATION
        self._running = False
        self._processor_thread: Optional[threading.Thread] = None
        self._capture_thread: Optional[threading.Thread] = None
        self._audio_buffer = np.array([], dtype=np.float32)
        self._samples_per_chunk = int(self.sample_rate * self.chunk_duration)
        self._buffer_queue: queue.Queue = queue.Queue()

        # Platform-specific audio backends
        self._pa = None  # PyAudio instance (Windows)
        self._stream = None

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

    def _process_audio(self):
        """Process buffered audio and emit chunks."""
        while self._running:
            try:
                raw_data = self._buffer_queue.get(timeout=0.1)

                # Convert based on format
                if isinstance(raw_data, bytes):
                    audio = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32) / 32768.0
                else:
                    audio = raw_data.astype(np.float32)
                    if audio.max() > 1.0:
                        audio = audio / 32768.0

                self._audio_buffer = np.concatenate([self._audio_buffer, audio])

                while len(self._audio_buffer) >= self._samples_per_chunk:
                    chunk = self._audio_buffer[:self._samples_per_chunk]
                    self._audio_buffer = self._audio_buffer[self._samples_per_chunk:]
                    self.on_audio_chunk(chunk)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Audio processing error: {e}")

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

        # Try loopback first, then microphone
        device_index = self._find_loopback_device_windows()
        if device_index is None:
            device_index = self._find_input_device_windows()

        if device_index is None:
            print("ERROR: No audio input device found!")
            self._running = False
            return

        info = self._pa.get_device_info_by_index(device_index)
        channels = min(int(info['maxInputChannels']), 2)
        print(f"Using device: {info['name']}")

        try:
            self._stream = self._pa.open(
                format=pyaudio.paInt16,
                channels=channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=int(self.sample_rate * 0.1),
                stream_callback=self._audio_callback_pyaudio,
            )
            self._stream.start_stream()
            print("Audio capture started (Windows)")
        except Exception as e:
            print(f"Failed to start audio: {e}")
            # Try default device
            try:
                self._stream = self._pa.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=self.sample_rate,
                    input=True,
                    frames_per_buffer=int(self.sample_rate * 0.1),
                    stream_callback=self._audio_callback_pyaudio,
                )
                self._stream.start_stream()
                print("Audio capture started (default device)")
            except Exception as e2:
                print(f"Audio capture failed: {e2}")
                self._running = False

    def _start_macos(self):
        """Start audio capture on macOS using sounddevice."""
        import sounddevice as sd

        def callback(indata, frames, time, status):
            if status:
                print(f"Audio status: {status}")
            if self._running:
                # Convert to mono if stereo
                if indata.ndim > 1:
                    audio = indata.mean(axis=1)
                else:
                    audio = indata.flatten()
                self._buffer_queue.put(audio)

        try:
            # On macOS, use default input (microphone)
            # For system audio, user needs to install BlackHole or similar
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype=np.float32,
                callback=callback,
                blocksize=int(self.sample_rate * 0.1),
            )
            self._stream.start()
            print("Audio capture started (macOS)")
            print("Note: For system audio, install BlackHole and set it as input")
        except Exception as e:
            print(f"Failed to start audio: {e}")
            self._running = False

    def _start_linux(self):
        """Start audio capture on Linux using sounddevice with PulseAudio."""
        import sounddevice as sd

        def callback(indata, frames, time, status):
            if status:
                print(f"Audio status: {status}")
            if self._running:
                if indata.ndim > 1:
                    audio = indata.mean(axis=1)
                else:
                    audio = indata.flatten()
                self._buffer_queue.put(audio)

        try:
            # On Linux, use default input
            # For system audio, use PulseAudio monitor device
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype=np.float32,
                callback=callback,
                blocksize=int(self.sample_rate * 0.1),
            )
            self._stream.start()
            print("Audio capture started (Linux)")
            print("Note: For system audio, select PulseAudio monitor as input")
        except Exception as e:
            print(f"Failed to start audio: {e}")
            self._running = False

    def start(self):
        """Start capturing audio."""
        if self._running:
            return

        self._running = True
        self._audio_buffer = np.array([], dtype=np.float32)

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

    @staticmethod
    def list_devices():
        """List available audio devices for debugging."""
        if IS_WINDOWS:
            import pyaudio
            pa = pyaudio.PyAudio()
            print("Available audio devices (Windows):")
            for i in range(pa.get_device_count()):
                info = pa.get_device_info_by_index(i)
                print(f"  [{i}] {info['name']} (in: {info['maxInputChannels']}, out: {info['maxOutputChannels']})")
            pa.terminate()
        else:
            import sounddevice as sd
            print("Available audio devices:")
            print(sd.query_devices())
