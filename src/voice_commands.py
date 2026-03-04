"""Voice command handler for ReadIn AI.

Provides wake word detection and voice command execution for hands-free control.
Uses speech_recognition library for command detection.
"""

import threading
import queue
import time
from typing import Callable, Dict, Optional, List, Any
from enum import Enum

try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False
    sr = None

from src.logger import get_logger

logger = get_logger("voice_commands")


class VoiceCommandState(Enum):
    """State of the voice command handler."""
    IDLE = "idle"
    LISTENING_FOR_WAKE_WORD = "listening_wake_word"
    LISTENING_FOR_COMMAND = "listening_command"
    PROCESSING = "processing"
    ERROR = "error"


class VoiceCommandHandler:
    """Handles voice commands for ReadIn AI with wake word detection.

    Listens for the wake word ("Hey ReadIn" or similar variants) and then
    processes the following command. Commands include:
    - summarize: Summarize recent conversation
    - repeat: Repeat the last AI response
    - action items: List recent action items
    - stop listening / stop: Toggle audio capture off
    - start listening / start: Toggle audio capture on
    - clear: Clear conversation context

    The handler runs in a background thread and is designed to work
    alongside the main audio capture without interference.
    """

    # Wake word variants (case-insensitive matching)
    WAKE_WORDS = [
        "hey readin",
        "hey read in",
        "hey reading",
        "ok readin",
        "ok read in",
        "hi readin",
        "hi read in",
    ]

    # Command definitions with aliases
    COMMAND_ALIASES = {
        "summarize": ["summarize", "summary", "summarise", "sum up", "wrap up"],
        "repeat": ["repeat", "say again", "what was that", "repeat that", "again"],
        "action_items": ["action items", "action item", "actions", "to do", "todo", "to-do", "tasks"],
        "stop": ["stop listening", "stop", "pause", "mute", "stop listening please"],
        "start": ["start listening", "start", "resume", "unmute", "listen", "start listening please"],
        "clear": ["clear", "clear context", "reset", "start over", "new conversation"],
    }

    # Timeout settings
    WAKE_WORD_TIMEOUT = 5.0  # Seconds to listen for wake word before cycling
    COMMAND_TIMEOUT = 5.0  # Seconds to wait for command after wake word
    COOLDOWN_PERIOD = 1.0  # Seconds between wake word detections

    def __init__(
        self,
        on_summarize: Optional[Callable[[], None]] = None,
        on_repeat: Optional[Callable[[], None]] = None,
        on_action_items: Optional[Callable[[], None]] = None,
        on_stop_listening: Optional[Callable[[], None]] = None,
        on_start_listening: Optional[Callable[[], None]] = None,
        on_clear: Optional[Callable[[], None]] = None,
        on_wake_word_detected: Optional[Callable[[], None]] = None,
        on_command_recognized: Optional[Callable[[str], None]] = None,
        on_state_changed: Optional[Callable[[VoiceCommandState], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
        device_index: Optional[int] = None,
    ):
        """Initialize the voice command handler.

        Args:
            on_summarize: Callback when "summarize" command is recognized
            on_repeat: Callback when "repeat" command is recognized
            on_action_items: Callback when "action items" command is recognized
            on_stop_listening: Callback when "stop listening" command is recognized
            on_start_listening: Callback when "start listening" command is recognized
            on_clear: Callback when "clear" command is recognized
            on_wake_word_detected: Callback when wake word is detected
            on_command_recognized: Callback with command name when any command is recognized
            on_state_changed: Callback when handler state changes
            on_error: Callback for error reporting
            device_index: Microphone device index (None for default)
        """
        if not SPEECH_RECOGNITION_AVAILABLE:
            logger.warning("speech_recognition not available - voice commands disabled")

        # Callbacks
        self.on_summarize = on_summarize
        self.on_repeat = on_repeat
        self.on_action_items = on_action_items
        self.on_stop_listening = on_stop_listening
        self.on_start_listening = on_start_listening
        self.on_clear = on_clear
        self.on_wake_word_detected = on_wake_word_detected
        self.on_command_recognized = on_command_recognized
        self.on_state_changed = on_state_changed
        self.on_error = on_error

        # State
        self._state = VoiceCommandState.IDLE
        self._running = False
        self._device_index = device_index
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._last_wake_time = 0.0

        # Speech recognition
        self._recognizer: Optional["sr.Recognizer"] = None
        self._microphone: Optional["sr.Microphone"] = None

        # Build command lookup for fast matching
        self._command_lookup: Dict[str, str] = {}
        for command, aliases in self.COMMAND_ALIASES.items():
            for alias in aliases:
                self._command_lookup[alias.lower()] = command

    @property
    def state(self) -> VoiceCommandState:
        """Get current handler state."""
        with self._lock:
            return self._state

    def _set_state(self, state: VoiceCommandState):
        """Set handler state and notify callback."""
        with self._lock:
            if self._state != state:
                self._state = state
                if self.on_state_changed:
                    try:
                        self.on_state_changed(state)
                    except Exception as e:
                        logger.error(f"Error in state change callback: {e}")

    def is_available(self) -> bool:
        """Check if voice commands are available (speech_recognition installed)."""
        return SPEECH_RECOGNITION_AVAILABLE

    def is_running(self) -> bool:
        """Check if the handler is currently running."""
        with self._lock:
            return self._running

    def set_device(self, device_index: Optional[int]):
        """Set the microphone device index.

        Args:
            device_index: Device index or None for default
        """
        self._device_index = device_index

    def start(self):
        """Start listening for voice commands."""
        if not SPEECH_RECOGNITION_AVAILABLE:
            logger.warning("Cannot start voice commands - speech_recognition not available")
            return

        with self._lock:
            if self._running:
                return
            self._running = True

        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        logger.info("Voice command handler started")

    def stop(self):
        """Stop listening for voice commands."""
        with self._lock:
            if not self._running:
                return
            self._running = False

        self._set_state(VoiceCommandState.IDLE)

        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

        logger.info("Voice command handler stopped")

    def _init_recognizer(self):
        """Initialize the speech recognizer and microphone."""
        if self._recognizer is None:
            self._recognizer = sr.Recognizer()
            # Adjust for ambient noise
            self._recognizer.dynamic_energy_threshold = True
            self._recognizer.energy_threshold = 300  # Minimum threshold
            self._recognizer.pause_threshold = 0.8  # Seconds of silence before phrase is complete

    def _listen_loop(self):
        """Main listening loop for wake word and command detection."""
        self._init_recognizer()

        while self._running:
            try:
                # Listen for wake word
                self._set_state(VoiceCommandState.LISTENING_FOR_WAKE_WORD)

                with sr.Microphone(device_index=self._device_index) as source:
                    # Adjust for ambient noise periodically
                    self._recognizer.adjust_for_ambient_noise(source, duration=0.5)

                    try:
                        # Listen for audio
                        audio = self._recognizer.listen(
                            source,
                            timeout=self.WAKE_WORD_TIMEOUT,
                            phrase_time_limit=3.0
                        )

                        # Recognize speech
                        text = self._recognize_speech(audio)

                        if text:
                            text_lower = text.lower().strip()
                            logger.debug(f"Heard: {text_lower}")

                            # Check for wake word
                            if self._contains_wake_word(text_lower):
                                # Check cooldown
                                current_time = time.time()
                                if current_time - self._last_wake_time < self.COOLDOWN_PERIOD:
                                    continue
                                self._last_wake_time = current_time

                                logger.info("Wake word detected!")
                                if self.on_wake_word_detected:
                                    self.on_wake_word_detected()

                                # Extract command from same phrase if present
                                command = self._extract_command_from_wake_phrase(text_lower)
                                if command:
                                    self._execute_command(command)
                                else:
                                    # Listen for command
                                    self._listen_for_command(source)

                    except sr.WaitTimeoutError:
                        # No speech detected, continue listening
                        continue
                    except sr.UnknownValueError:
                        # Could not understand audio, continue
                        continue

            except sr.RequestError as e:
                logger.error(f"Speech recognition service error: {e}")
                self._set_state(VoiceCommandState.ERROR)
                if self.on_error:
                    self.on_error(f"Speech recognition error: {e}")
                time.sleep(2.0)  # Wait before retrying

            except Exception as e:
                logger.error(f"Error in voice command loop: {e}")
                self._set_state(VoiceCommandState.ERROR)
                if self.on_error:
                    self.on_error(str(e))
                time.sleep(1.0)

    def _listen_for_command(self, source: "sr.Microphone"):
        """Listen for a command after wake word is detected.

        Args:
            source: The microphone source to listen on
        """
        self._set_state(VoiceCommandState.LISTENING_FOR_COMMAND)

        try:
            audio = self._recognizer.listen(
                source,
                timeout=self.COMMAND_TIMEOUT,
                phrase_time_limit=4.0
            )

            text = self._recognize_speech(audio)

            if text:
                text_lower = text.lower().strip()
                logger.debug(f"Command phrase: {text_lower}")

                command = self._match_command(text_lower)
                if command:
                    self._execute_command(command)
                else:
                    logger.debug(f"Unrecognized command: {text_lower}")

        except sr.WaitTimeoutError:
            logger.debug("No command received after wake word")
        except sr.UnknownValueError:
            logger.debug("Could not understand command")

    def _recognize_speech(self, audio: "sr.AudioData") -> Optional[str]:
        """Recognize speech from audio data.

        Uses Google's free speech recognition API.

        Args:
            audio: Audio data to recognize

        Returns:
            Recognized text or None if recognition failed
        """
        try:
            # Use Google's free API (no key required)
            text = self._recognizer.recognize_google(audio)
            return text
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            logger.error(f"Could not request results from speech service: {e}")
            raise

    def _contains_wake_word(self, text: str) -> bool:
        """Check if text contains the wake word.

        Args:
            text: Lowercase text to check

        Returns:
            True if wake word is present
        """
        for wake_word in self.WAKE_WORDS:
            if wake_word in text:
                return True
        return False

    def _extract_command_from_wake_phrase(self, text: str) -> Optional[str]:
        """Extract a command from a phrase containing the wake word.

        Handles cases like "Hey ReadIn, summarize" where both wake word
        and command are in the same phrase.

        Args:
            text: Lowercase text containing wake word

        Returns:
            Command name if found, None otherwise
        """
        # Find the wake word and get text after it
        for wake_word in self.WAKE_WORDS:
            if wake_word in text:
                # Get everything after the wake word
                idx = text.find(wake_word) + len(wake_word)
                remaining = text[idx:].strip()
                remaining = remaining.lstrip(',').strip()

                if remaining:
                    return self._match_command(remaining)

        return None

    def _match_command(self, text: str) -> Optional[str]:
        """Match text to a command.

        Args:
            text: Lowercase text to match

        Returns:
            Command name if matched, None otherwise
        """
        # Direct lookup
        if text in self._command_lookup:
            return self._command_lookup[text]

        # Check if text starts with or contains any command alias
        for alias, command in self._command_lookup.items():
            if text.startswith(alias) or alias in text:
                return command

        return None

    def _execute_command(self, command: str):
        """Execute a recognized command.

        Args:
            command: Command name to execute
        """
        self._set_state(VoiceCommandState.PROCESSING)
        logger.info(f"Executing command: {command}")

        if self.on_command_recognized:
            try:
                self.on_command_recognized(command)
            except Exception as e:
                logger.error(f"Error in command recognized callback: {e}")

        # Execute the appropriate callback
        callback_map = {
            "summarize": self.on_summarize,
            "repeat": self.on_repeat,
            "action_items": self.on_action_items,
            "stop": self.on_stop_listening,
            "start": self.on_start_listening,
            "clear": self.on_clear,
        }

        callback = callback_map.get(command)
        if callback:
            try:
                callback()
            except Exception as e:
                logger.error(f"Error executing command '{command}': {e}")
                if self.on_error:
                    self.on_error(f"Command error: {e}")

    @staticmethod
    def list_microphones() -> List[Dict[str, Any]]:
        """List available microphone devices.

        Returns:
            List of dicts with 'index' and 'name' keys
        """
        if not SPEECH_RECOGNITION_AVAILABLE:
            return []

        try:
            mics = []
            for i, name in enumerate(sr.Microphone.list_microphone_names()):
                mics.append({"index": i, "name": name})
            return mics
        except Exception as e:
            logger.error(f"Error listing microphones: {e}")
            return []

    def get_supported_commands(self) -> Dict[str, List[str]]:
        """Get dictionary of supported commands and their aliases.

        Returns:
            Dict mapping command names to list of aliases
        """
        return self.COMMAND_ALIASES.copy()

    def get_wake_words(self) -> List[str]:
        """Get list of supported wake words.

        Returns:
            List of wake word phrases
        """
        return self.WAKE_WORDS.copy()


# Convenience function for checking availability
def is_voice_commands_available() -> bool:
    """Check if voice commands are available on this system.

    Returns:
        True if speech_recognition library is installed
    """
    return SPEECH_RECOGNITION_AVAILABLE
