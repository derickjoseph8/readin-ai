"""
Browser Extension Bridge for ReadIn AI

WebSocket server that receives audio data from the browser extension
and forwards it to the transcription pipeline.
"""

import asyncio
import json
import logging
import os
import secrets
import struct
import threading
import time
from collections import defaultdict
from typing import Callable, Dict, Optional, Set
import numpy as np

try:
    import websockets
    from websockets.server import serve
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    print("Warning: websockets library not installed. Browser extension support disabled.")

# Configure logging
logger = logging.getLogger(__name__)

# Security constants
MAX_MESSAGE_SIZE = 10 * 1024 * 1024  # 10MB max message size
MAX_AUDIO_ARRAY_SIZE = 5 * 1024 * 1024  # 5MB max audio array size (approx 2.5 minutes at 16kHz)
MAX_CONNECTIONS = 5  # Maximum concurrent connections
AUTH_TIMEOUT_SECONDS = 5  # Time allowed for authentication
MAX_MESSAGES_PER_SECOND = 100  # Rate limit per client
AUTH_TOKEN_LENGTH = 32  # Length of authentication token in bytes


class RateLimiter:
    """Simple token bucket rate limiter per client."""

    def __init__(self, max_tokens: int, refill_rate: float):
        """
        Initialize rate limiter.

        Args:
            max_tokens: Maximum tokens (messages) allowed
            refill_rate: Tokens added per second
        """
        self._max_tokens = max_tokens
        self._refill_rate = refill_rate
        self._tokens: Dict[str, float] = defaultdict(lambda: float(max_tokens))
        self._last_update: Dict[str, float] = defaultdict(time.monotonic)
        self._lock = threading.Lock()

    def allow(self, client_id: str) -> bool:
        """Check if a request from client_id should be allowed."""
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_update[client_id]
            self._last_update[client_id] = now

            # Refill tokens
            self._tokens[client_id] = min(
                self._max_tokens,
                self._tokens[client_id] + elapsed * self._refill_rate
            )

            # Check if we have a token to spend
            if self._tokens[client_id] >= 1:
                self._tokens[client_id] -= 1
                return True
            return False

    def remove_client(self, client_id: str):
        """Remove a client from tracking."""
        with self._lock:
            self._tokens.pop(client_id, None)
            self._last_update.pop(client_id, None)


class BrowserBridge:
    """WebSocket server for browser extension communication."""

    def __init__(
        self,
        on_audio_chunk: Callable[[np.ndarray], None] = None,
        on_meeting_detected: Callable[[str, str], None] = None,
        on_capture_started: Callable[[], None] = None,
        on_capture_stopped: Callable[[], None] = None,
        port: int = 8765,
        token_file_path: Optional[str] = None
    ):
        """
        Initialize the browser bridge.

        Args:
            on_audio_chunk: Callback for audio data (numpy array of float32 samples)
            on_meeting_detected: Callback when extension detects a meeting (name, url)
            on_capture_started: Callback when extension starts capturing
            on_capture_stopped: Callback when extension stops capturing
            port: WebSocket server port
            token_file_path: Path to store the auth token (defaults to user data dir)
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
        self._connected_clients: Set = set()
        self._authenticated_clients: Set = set()
        self._is_capturing = False

        # Security: Generate authentication token
        self._auth_token = secrets.token_hex(AUTH_TOKEN_LENGTH)
        self._token_file_path = token_file_path or self._get_default_token_path()

        # Security: Rate limiter (100 messages/second per client)
        self._rate_limiter = RateLimiter(
            max_tokens=MAX_MESSAGES_PER_SECOND,
            refill_rate=MAX_MESSAGES_PER_SECOND
        )

        # Track pending authentication
        self._pending_auth: Dict[str, asyncio.Task] = {}

    def _get_default_token_path(self) -> str:
        """Get the default path for storing the auth token."""
        # Use platform-appropriate user data directory
        if os.name == 'nt':  # Windows
            app_data = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
            token_dir = os.path.join(app_data, 'ReadInAI')
        else:  # macOS/Linux
            token_dir = os.path.expanduser('~/.readin-ai')

        os.makedirs(token_dir, exist_ok=True)
        return os.path.join(token_dir, 'bridge_token')

    def _save_auth_token(self):
        """Save the authentication token to a file for the browser extension."""
        try:
            with open(self._token_file_path, 'w') as f:
                f.write(self._auth_token)
            # Restrict file permissions on Unix systems
            if os.name != 'nt':
                os.chmod(self._token_file_path, 0o600)
            logger.info(f"Auth token saved to {self._token_file_path}")
        except Exception as e:
            logger.error(f"Failed to save auth token: {e}")

    def get_auth_token(self) -> str:
        """Get the current authentication token."""
        return self._auth_token

    def get_token_file_path(self) -> str:
        """Get the path to the token file."""
        return self._token_file_path

    def _get_client_id(self, websocket) -> str:
        """Get a unique identifier for a client connection."""
        return f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"

    def start(self):
        """Start the WebSocket server in a background thread."""
        if not WEBSOCKETS_AVAILABLE:
            logger.error("Cannot start browser bridge: websockets not installed")
            return False

        if self._running:
            return True

        # Save authentication token for browser extension to read
        self._save_auth_token()

        self._running = True
        self._thread = threading.Thread(target=self._run_server, daemon=True)
        self._thread.start()
        logger.info(f"Browser bridge starting on ws://localhost:{self.port}")
        return True

    def stop(self):
        """Stop the WebSocket server."""
        self._running = False

        loop = self._loop  # Capture reference to avoid race conditions
        if loop is not None:
            try:
                # Schedule server shutdown
                asyncio.run_coroutine_threadsafe(self._shutdown(), loop)
            except RuntimeError:
                # Loop may have been closed
                pass

        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

        # Clean up token file
        try:
            if os.path.exists(self._token_file_path):
                os.remove(self._token_file_path)
        except Exception as e:
            logger.warning(f"Failed to remove token file: {e}")

        logger.info("Browser bridge stopped")

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
        loop = self._loop  # Capture reference to avoid race conditions
        if self._connected_clients and loop is not None:
            try:
                asyncio.run_coroutine_threadsafe(
                    self._broadcast({'type': 'start_capture'}),
                    loop
                )
            except RuntimeError:
                # Loop may have been closed between the check and use
                pass

    def request_stop_capture(self):
        """Request the extension to stop capturing audio."""
        loop = self._loop  # Capture reference to avoid race conditions
        if self._connected_clients and loop is not None:
            try:
                asyncio.run_coroutine_threadsafe(
                    self._broadcast({'type': 'stop_capture'}),
                    loop
                )
            except RuntimeError:
                # Loop may have been closed between the check and use
                pass

    def request_status(self):
        """Request status from the extension."""
        loop = self._loop  # Capture reference to avoid race conditions
        if self._connected_clients and loop is not None:
            try:
                asyncio.run_coroutine_threadsafe(
                    self._broadcast({'type': 'status_request'}),
                    loop
                )
            except RuntimeError:
                # Loop may have been closed between the check and use
                pass

    def _run_server(self):
        """Run the WebSocket server (in background thread)."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        try:
            self._loop.run_until_complete(self._serve())
        except Exception as e:
            logger.error(f"Browser bridge error: {e}")
        finally:
            self._loop.close()
            self._loop = None

    async def _serve(self):
        """Start the WebSocket server."""
        async with serve(
            self._handle_client,
            "localhost",
            self.port,
            max_size=MAX_MESSAGE_SIZE,  # Enforce message size limit at protocol level
        ):
            logger.info(f"Browser bridge listening on ws://localhost:{self.port}")
            while self._running:
                await asyncio.sleep(0.1)

    async def _shutdown(self):
        """Shutdown the server gracefully."""
        # Cancel pending auth timeouts
        for task in self._pending_auth.values():
            task.cancel()
        self._pending_auth.clear()

        # Close all client connections
        for client in list(self._connected_clients):
            try:
                await client.close()
            except Exception:
                pass
        self._connected_clients.clear()
        self._authenticated_clients.clear()

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
        client_id = self._get_client_id(websocket)
        logger.info(f"Connection attempt from {client_id}")

        # Security: Check connection limit
        if len(self._connected_clients) >= MAX_CONNECTIONS:
            logger.warning(f"Connection rejected from {client_id}: max connections ({MAX_CONNECTIONS}) reached")
            await websocket.close(1008, "Too many connections")
            return

        self._connected_clients.add(websocket)
        logger.info(f"Client connected: {client_id} (total: {len(self._connected_clients)})")

        # Security: Start authentication timeout
        auth_timeout_task = asyncio.create_task(
            self._auth_timeout(websocket, client_id)
        )
        self._pending_auth[client_id] = auth_timeout_task

        try:
            async for message in websocket:
                # Security: Check if client is authenticated (except for auth message)
                if websocket not in self._authenticated_clients:
                    # Only process authentication messages
                    auth_result = await self._handle_auth_message(message, websocket, client_id)
                    if auth_result:
                        # Authentication successful, cancel timeout
                        if client_id in self._pending_auth:
                            self._pending_auth[client_id].cancel()
                            del self._pending_auth[client_id]
                    continue

                # Security: Rate limiting
                if not self._rate_limiter.allow(client_id):
                    logger.warning(f"Rate limit exceeded for {client_id}")
                    continue

                await self._process_message(message, websocket)

        except websockets.exceptions.ConnectionClosed as e:
            logger.info(f"Client {client_id} disconnected: {e.code} {e.reason}")
        except Exception as e:
            logger.error(f"Browser bridge client error for {client_id}: {e}")
        finally:
            # Cleanup
            self._connected_clients.discard(websocket)
            self._authenticated_clients.discard(websocket)
            self._rate_limiter.remove_client(client_id)

            # Cancel auth timeout if still pending
            if client_id in self._pending_auth:
                self._pending_auth[client_id].cancel()
                del self._pending_auth[client_id]

            logger.info(f"Client disconnected: {client_id} (remaining: {len(self._connected_clients)})")

            # If capturing was active, notify about stop
            if self._is_capturing:
                self._is_capturing = False
                if self.on_capture_stopped:
                    self.on_capture_stopped()

    async def _auth_timeout(self, websocket, client_id: str):
        """Disconnect client if not authenticated within timeout."""
        try:
            await asyncio.sleep(AUTH_TIMEOUT_SECONDS)
            if websocket in self._connected_clients and websocket not in self._authenticated_clients:
                logger.warning(f"Authentication timeout for {client_id}")
                await websocket.close(1008, "Authentication timeout")
        except asyncio.CancelledError:
            # Auth succeeded before timeout
            pass

    async def _handle_auth_message(self, message, websocket, client_id: str) -> bool:
        """
        Handle authentication message from client.

        Returns True if authentication was successful.
        """
        # Auth must be JSON
        if isinstance(message, bytes):
            logger.warning(f"Auth failed for {client_id}: binary message before auth")
            return False

        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            logger.warning(f"Auth failed for {client_id}: invalid JSON")
            return False

        # Check for auth message
        if data.get('type') != 'auth':
            logger.warning(f"Auth failed for {client_id}: first message must be auth, got {data.get('type')}")
            return False

        # Validate token
        token = data.get('token', '')
        if not secrets.compare_digest(token, self._auth_token):
            logger.warning(f"Auth failed for {client_id}: invalid token")
            await websocket.send(json.dumps({
                'type': 'auth_response',
                'success': False,
                'error': 'Invalid authentication token'
            }))
            await websocket.close(1008, "Invalid authentication token")
            return False

        # Authentication successful
        self._authenticated_clients.add(websocket)
        logger.info(f"Client authenticated: {client_id}")

        await websocket.send(json.dumps({
            'type': 'auth_response',
            'success': True
        }))
        return True

    def _validate_message_structure(self, data: dict) -> bool:
        """Validate that a message has the expected structure."""
        if not isinstance(data, dict):
            return False

        msg_type = data.get('type')
        if not isinstance(msg_type, str):
            return False

        # Validate specific message types
        valid_types = {
            'handshake', 'capture_started', 'capture_stopped',
            'status', 'audio', 'AUDIO_DATA'
        }

        if msg_type not in valid_types:
            logger.warning(f"Unknown message type: {msg_type}")
            return False

        return True

    async def _process_message(self, message, websocket):
        """Process a message from the browser extension."""
        client_id = self._get_client_id(websocket)

        # Check if it's binary audio data
        if isinstance(message, bytes):
            self._handle_audio_data(message)
            return

        # Parse JSON message
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON from {client_id}: {message[:100]}")
            return

        # Validate message structure
        if not self._validate_message_structure(data):
            logger.warning(f"Invalid message structure from {client_id}")
            return

        msg_type = data.get('type')

        if msg_type == 'handshake':
            # Extension connected, send acknowledgment
            source = data.get('source', 'unknown')
            version = data.get('version', 'unknown')
            logger.info(f"Extension handshake from {client_id}: {source} v{version}")
            await websocket.send(json.dumps({
                'type': 'handshake_ack',
                'version': '1.0.0'
            }))

        elif msg_type == 'capture_started':
            meeting_name = data.get('meetingName', 'Unknown')
            url = data.get('url', '')
            logger.info(f"Extension started capture: {meeting_name} at {url}")
            self._is_capturing = True
            if self.on_capture_started:
                self.on_capture_started()
            if self.on_meeting_detected and data.get('meetingName'):
                self.on_meeting_detected(data.get('meetingName'), data.get('url', ''))

        elif msg_type == 'capture_stopped':
            logger.info("Extension stopped capture")
            self._is_capturing = False
            if self.on_capture_stopped:
                self.on_capture_stopped()

        elif msg_type == 'status':
            logger.debug(f"Extension status: capturing={data.get('isCapturing')}, tab={data.get('currentTabId')}")

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

        # Validate audio data size
        if len(audio_bytes) > MAX_AUDIO_ARRAY_SIZE:
            logger.warning(f"Audio data too large ({len(audio_bytes)} bytes), ignoring")
            return

        try:
            # Audio is sent as Int16 PCM, convert to float32
            int16_array = np.frombuffer(audio_bytes, dtype=np.int16)
            float_array = int16_array.astype(np.float32) / 32768.0
            self.on_audio_chunk(float_array)
        except ValueError as e:
            logger.error(f"Invalid audio data format: {e}")
        except MemoryError as e:
            logger.error(f"Memory error processing audio data: {e}")
        except Exception as e:
            logger.error(f"Error processing audio data: {e}")

    def _handle_audio_array(self, audio_data: list, sample_rate: int):
        """Handle audio data sent as JSON array."""
        if not self.on_audio_chunk:
            return

        # Validate audio data is a list
        if not isinstance(audio_data, list):
            logger.warning("Audio data is not a list, ignoring")
            return

        # Validate audio array size (each int16 is 2 bytes equivalent)
        if len(audio_data) * 2 > MAX_AUDIO_ARRAY_SIZE:
            logger.warning(f"Audio array too large ({len(audio_data)} elements), ignoring")
            return

        try:
            # Convert list of Int16 values to numpy float32 array
            int16_array = np.array(audio_data, dtype=np.int16)
            float_array = int16_array.astype(np.float32) / 32768.0
            self.on_audio_chunk(float_array)
        except ValueError as e:
            logger.error(f"Invalid audio array data: {e}")
        except MemoryError as e:
            logger.error(f"Memory error processing audio array: {e}")
        except Exception as e:
            logger.error(f"Error processing audio array: {e}")


# Simple test
if __name__ == "__main__":
    # Configure logging for test
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    def on_audio(chunk):
        print(f"Received audio chunk: {len(chunk)} samples")

    def on_meeting(name, url):
        print(f"Meeting detected: {name} at {url}")

    bridge = BrowserBridge(
        on_audio_chunk=on_audio,
        on_meeting_detected=on_meeting
    )

    bridge.start()

    print(f"Auth token: {bridge.get_auth_token()}")
    print(f"Token file: {bridge.get_token_file_path()}")

    try:
        print("Browser bridge running. Press Ctrl+C to stop.")
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        bridge.stop()
