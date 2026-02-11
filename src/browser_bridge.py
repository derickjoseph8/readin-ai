"""
Browser Extension Bridge for ReadIn AI

WebSocket server that receives audio data from the browser extension
and forwards it to the transcription pipeline.
"""

import asyncio
import json
import struct
import threading
from typing import Callable, Optional
import numpy as np

try:
    import websockets
    from websockets.server import serve
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    print("Warning: websockets library not installed. Browser extension support disabled.")


class BrowserBridge:
    """WebSocket server for browser extension communication."""

    def __init__(
        self,
        on_audio_chunk: Callable[[np.ndarray], None] = None,
        on_meeting_detected: Callable[[str, str], None] = None,
        on_capture_started: Callable[[], None] = None,
        on_capture_stopped: Callable[[], None] = None,
        port: int = 8765
    ):
        """
        Initialize the browser bridge.

        Args:
            on_audio_chunk: Callback for audio data (numpy array of float32 samples)
            on_meeting_detected: Callback when extension detects a meeting (name, url)
            on_capture_started: Callback when extension starts capturing
            on_capture_stopped: Callback when extension stops capturing
            port: WebSocket server port
        """
        self.on_audio_chunk = on_audio_chunk
        self.on_meeting_detected = on_meeting_detected
        self.on_capture_started = on_capture_started
        self.on_capture_stopped = on_capture_stopped
        self.port = port

        self._server = None
        self._loop = None
        self._thread = None
        self._running = False
        self._connected_clients = set()
        self._is_capturing = False

    def start(self):
        """Start the WebSocket server in a background thread."""
        if not WEBSOCKETS_AVAILABLE:
            print("Cannot start browser bridge: websockets not installed")
            return False

        if self._running:
            return True

        self._running = True
        self._thread = threading.Thread(target=self._run_server, daemon=True)
        self._thread.start()
        print(f"Browser bridge starting on ws://localhost:{self.port}")
        return True

    def stop(self):
        """Stop the WebSocket server."""
        self._running = False

        if self._loop:
            # Schedule server shutdown
            asyncio.run_coroutine_threadsafe(self._shutdown(), self._loop)

        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

        print("Browser bridge stopped")

    def is_running(self) -> bool:
        """Check if server is running."""
        return self._running and self._thread is not None and self._thread.is_alive()

    def is_extension_connected(self) -> bool:
        """Check if any browser extension is connected."""
        return len(self._connected_clients) > 0

    def is_capturing(self) -> bool:
        """Check if extension is currently capturing audio."""
        return self._is_capturing

    def request_start_capture(self):
        """Request the extension to start capturing audio."""
        if self._connected_clients:
            asyncio.run_coroutine_threadsafe(
                self._broadcast({'type': 'start_capture'}),
                self._loop
            )

    def request_stop_capture(self):
        """Request the extension to stop capturing audio."""
        if self._connected_clients:
            asyncio.run_coroutine_threadsafe(
                self._broadcast({'type': 'stop_capture'}),
                self._loop
            )

    def request_status(self):
        """Request status from the extension."""
        if self._connected_clients:
            asyncio.run_coroutine_threadsafe(
                self._broadcast({'type': 'status_request'}),
                self._loop
            )

    def _run_server(self):
        """Run the WebSocket server (in background thread)."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        try:
            self._loop.run_until_complete(self._serve())
        except Exception as e:
            print(f"Browser bridge error: {e}")
        finally:
            self._loop.close()
            self._loop = None

    async def _serve(self):
        """Start the WebSocket server."""
        async with serve(self._handle_client, "localhost", self.port):
            print(f"Browser bridge listening on ws://localhost:{self.port}")
            while self._running:
                await asyncio.sleep(0.1)

    async def _shutdown(self):
        """Shutdown the server gracefully."""
        # Close all client connections
        for client in list(self._connected_clients):
            await client.close()
        self._connected_clients.clear()

    async def _broadcast(self, message: dict):
        """Send message to all connected clients."""
        data = json.dumps(message)
        for client in list(self._connected_clients):
            try:
                await client.send(data)
            except Exception:
                pass

    async def _handle_client(self, websocket):
        """Handle a WebSocket client connection."""
        print(f"Browser extension connected from {websocket.remote_address}")
        self._connected_clients.add(websocket)

        try:
            async for message in websocket:
                await self._process_message(message, websocket)
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            print(f"Browser bridge client error: {e}")
        finally:
            self._connected_clients.discard(websocket)
            print("Browser extension disconnected")

            # If capturing was active, notify about stop
            if self._is_capturing:
                self._is_capturing = False
                if self.on_capture_stopped:
                    self.on_capture_stopped()

    async def _process_message(self, message, websocket):
        """Process a message from the browser extension."""
        # Check if it's binary audio data
        if isinstance(message, bytes):
            self._handle_audio_data(message)
            return

        # Parse JSON message
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            print(f"Invalid JSON from extension: {message[:100]}")
            return

        msg_type = data.get('type')

        if msg_type == 'handshake':
            # Extension connected, send acknowledgment
            print(f"Extension handshake: {data.get('source')} v{data.get('version')}")
            await websocket.send(json.dumps({
                'type': 'handshake_ack',
                'version': '1.0.0'
            }))

        elif msg_type == 'capture_started':
            print(f"Extension started capture: {data.get('meetingName')} at {data.get('url')}")
            self._is_capturing = True
            if self.on_capture_started:
                self.on_capture_started()
            if self.on_meeting_detected and data.get('meetingName'):
                self.on_meeting_detected(data.get('meetingName'), data.get('url', ''))

        elif msg_type == 'capture_stopped':
            print("Extension stopped capture")
            self._is_capturing = False
            if self.on_capture_stopped:
                self.on_capture_stopped()

        elif msg_type == 'status':
            print(f"Extension status: capturing={data.get('isCapturing')}, tab={data.get('currentTabId')}")

        elif msg_type == 'audio':
            # Audio data sent as JSON array (fallback)
            if 'data' in data:
                self._handle_audio_array(data['data'], data.get('sampleRate', 16000))

        elif msg_type == 'AUDIO_DATA':
            # Audio data from popup forwarded through background script
            if 'data' in data:
                self._handle_audio_array(data['data'], data.get('sampleRate', 16000))

    def _handle_audio_data(self, audio_bytes: bytes):
        """Handle binary audio data from the extension."""
        if not self.on_audio_chunk:
            return

        try:
            # Audio is sent as Int16 PCM, convert to float32
            int16_array = np.frombuffer(audio_bytes, dtype=np.int16)
            float_array = int16_array.astype(np.float32) / 32768.0
            self.on_audio_chunk(float_array)
        except Exception as e:
            print(f"Error processing audio data: {e}")

    def _handle_audio_array(self, audio_data: list, sample_rate: int):
        """Handle audio data sent as JSON array."""
        if not self.on_audio_chunk:
            return

        try:
            # Convert list of Int16 values to numpy float32 array
            int16_array = np.array(audio_data, dtype=np.int16)
            float_array = int16_array.astype(np.float32) / 32768.0
            self.on_audio_chunk(float_array)
        except Exception as e:
            print(f"Error processing audio array: {e}")


# Simple test
if __name__ == "__main__":
    def on_audio(chunk):
        print(f"Received audio chunk: {len(chunk)} samples")

    def on_meeting(name, url):
        print(f"Meeting detected: {name} at {url}")

    bridge = BrowserBridge(
        on_audio_chunk=on_audio,
        on_meeting_detected=on_meeting
    )

    bridge.start()

    try:
        print("Browser bridge running. Press Ctrl+C to stop.")
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        bridge.stop()
