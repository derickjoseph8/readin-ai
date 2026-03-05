"""Voice command handler for ReadIn AI Desktop App.

Provides wake word detection and voice command execution for hands-free control.
Uses speech_recognition library for command detection and integrates with the
hotkey manager for seamless control alongside keyboard shortcuts.

Features:
- Wake word detection ("Hey ReadIn" or "ReadIn")
- Commands: summarize, repeat, action items, what did they say, stop listening, start listening
- Integration with HotkeyManager for unified control
- Optional text-to-speech feedback for command confirmation
"""

import threading
import queue
import time
import re
from typing import Callable, Dict, Optional, List, Any, Tuple
from enum import Enum
from dataclasses import dataclass

# Check for speech_recognition availability
try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False
    sr = None

# Try to get logger from src, fall back to logging module
try:
    from src.logger import get_logger
    logger = get_logger("voice_commands")
except ImportError:
    import logging
    logger = logging.getLogger("voice_commands")


def is_voice_commands_available() -> bool:
    """Check if voice commands are available on this system.

    Returns:
        True if speech_recognition library is installed
    """
    return SPEECH_RECOGNITION_AVAILABLE


class VoiceCommandState(Enum):
    """State of the voice command handler."""
    IDLE = "idle"
    LISTENING_FOR_WAKE_WORD = "listening_wake_word"
    LISTENING_FOR_COMMAND = "listening_command"
    PROCESSING = "processing"
    ERROR = "error"


@dataclass
class VoiceCommandConfig:
    """Configuration for voice command handler."""
    # Wake word settings
    wake_words: List[str] = None
    wake_word_timeout: float = 5.0  # Seconds to listen for wake word before cycling
    command_timeout: float = 5.0  # Seconds to wait for command after wake word
    cooldown_period: float = 1.0  # Seconds between wake word detections

    # Audio settings
    device_index: Optional[int] = None  # None = default microphone
    energy_threshold: int = 300  # Minimum audio energy threshold
    pause_threshold: float = 0.8  # Seconds of silence before phrase is complete
    dynamic_energy: bool = True  # Automatically adjust for ambient noise

    # Feedback settings
    enable_tts_feedback: bool = False  # Speak confirmation of commands
    tts_rate: int = 150  # Words per minute for TTS
    tts_volume: float = 0.8  # Volume for TTS (0.0-1.0)

    def __post_init__(self):
        if self.wake_words is None:
            self.wake_words = [
                "hey readin",
                "hey read in",
                "hey reading",
                "readin",
                "read in",
                "ok readin",
                "ok read in",
                "hi readin",
                "hi read in",
            ]


class VoiceCommandHandler:
    """Handles voice commands for ReadIn AI with wake word detection.

    Listens for the wake word ("Hey ReadIn" or similar variants) and then
    processes the following command. Commands include:
    - summarize: Summarize recent conversation
    - repeat: Repeat the last AI response
    - action items: List recent action items
    - what did they say: Repeat the last heard transcription
    - stop listening / stop: Toggle audio capture off
    - start listening / start: Toggle audio capture on
    - clear: Clear conversation context

    The handler runs in a background thread and is designed to work
    alongside the main audio capture without interference.
    """

    # Command definitions with aliases
    COMMAND_ALIASES = {
        "summarize": [
            "summarize", "summary", "summarise", "sum up", "wrap up",
            "give me a summary", "what happened"
        ],
        "repeat": [
            "repeat", "say again", "what was that", "repeat that", "again",
            "say that again", "one more time"
        ],
        "action_items": [
            "action items", "action item", "actions", "to do", "todo",
            "to-do", "tasks", "what are the action items", "list action items"
        ],
        "what_did_they_say": [
            "what did they say", "what was said", "last thing said",
            "what did he say", "what did she say", "repeat what they said"
        ],
        "stop": [
            "stop listening", "stop", "pause", "mute", "stop listening please",
            "pause listening", "turn off"
        ],
        "start": [
            "start listening", "start", "resume", "unmute", "listen",
            "start listening please", "resume listening", "turn on"
        ],
        "clear": [
            "clear", "clear context", "reset", "start over", "new conversation",
            "clear history", "forget everything"
        ],
    }

    # Feedback messages for each command
    COMMAND_FEEDBACK = {
        "summarize": "Generating summary",
        "repeat": "Repeating last response",
        "action_items": "Getting action items",
        "what_did_they_say": "Repeating last transcription",
        "stop": "Stopping",
        "start": "Starting",
        "clear": "Context cleared",
    }

    def __init__(
        self,
        on_summarize: Optional[Callable[[], None]] = None,
        on_repeat: Optional[Callable[[], None]] = None,
        on_action_items: Optional[Callable[[], None]] = None,
        on_what_did_they_say: Optional[Callable[[], None]] = None,
        on_stop_listening: Optional[Callable[[], None]] = None,
        on_start_listening: Optional[Callable[[], None]] = None,
        on_clear: Optional[Callable[[], None]] = None,
        on_wake_word_detected: Optional[Callable[[], None]] = None,
        on_command_recognized: Optional[Callable[[str], None]] = None,
        on_state_changed: Optional[Callable[[VoiceCommandState], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
        device_index: Optional[int] = None,
        config: Optional[VoiceCommandConfig] = None,
        hotkey_manager: Optional[Any] = None,
    ):
        """Initialize the voice command handler.

        Args:
            on_summarize: Callback when "summarize" command is recognized
            on_repeat: Callback when "repeat" command is recognized
            on_action_items: Callback when "action items" command is recognized
            on_what_did_they_say: Callback when "what did they say" command is recognized
            on_stop_listening: Callback when "stop listening" command is recognized
            on_start_listening: Callback when "start listening" command is recognized
            on_clear: Callback when "clear" command is recognized
            on_wake_word_detected: Callback when wake word is detected
            on_command_recognized: Callback with command name when any command is recognized
            on_state_changed: Callback when handler state changes
            on_error: Callback for error reporting
            device_index: Microphone device index (None for default)
            config: VoiceCommandConfig object for advanced settings
            hotkey_manager: Optional HotkeyManager instance for integration
        """
        if not SPEECH_RECOGNITION_AVAILABLE:
            logger.warning("speech_recognition not available - voice commands disabled")

        # Configuration
        self._config = config or VoiceCommandConfig()
        if device_index is not None:
            self._config.device_index = device_index

        # Callbacks
        self.on_summarize = on_summarize
        self.on_repeat = on_repeat
        self.on_action_items = on_action_items
        self.on_what_did_they_say = on_what_did_they_say
        self.on_stop_listening = on_stop_listening
        self.on_start_listening = on_start_listening
        self.on_clear = on_clear
        self.on_wake_word_detected = on_wake_word_detected
        self.on_command_recognized = on_command_recognized
        self.on_state_changed = on_state_changed
        self.on_error = on_error

        # HotkeyManager integration
        self._hotkey_manager = hotkey_manager

        # State
        self._state = VoiceCommandState.IDLE
        self._running = False
        self._enabled = True
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._last_wake_time = 0.0

        # Speech recognition
        self._recognizer: Optional["sr.Recognizer"] = None
        self._microphone: Optional["sr.Microphone"] = None

        # TTS feedback
        self._tts_engine = None
        self._tts_lock = threading.Lock()

        # Build command lookup for fast matching
        self._command_lookup: Dict[str, str] = {}
        for command, aliases in self.COMMAND_ALIASES.items():
            for alias in aliases:
                self._command_lookup[alias.lower()] = command

        # Custom commands that can be added dynamically
        self._custom_commands: Dict[str, Tuple[List[str], Callable]] = {}

    @property
    def state(self) -> VoiceCommandState:
        """Get current handler state."""
        with self._lock:
            return self._state

    @property
    def is_enabled(self) -> bool:
        """Check if voice commands are enabled."""
        with self._lock:
            return self._enabled

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

    def set_enabled(self, enabled: bool):
        """Enable or disable voice command processing.

        When disabled, the handler stops listening but can be re-enabled.

        Args:
            enabled: True to enable, False to disable
        """
        with self._lock:
            self._enabled = enabled

        if enabled and not self.is_running():
            self.start()
        elif not enabled and self.is_running():
            self.stop()

        logger.info(f"Voice commands {'enabled' if enabled else 'disabled'}")

    def set_device(self, device_index: Optional[int]):
        """Set the microphone device index.

        Args:
            device_index: Device index or None for default
        """
        self._config.device_index = device_index

    def set_config(self, config: VoiceCommandConfig):
        """Update the handler configuration.

        Args:
            config: New configuration to apply
        """
        self._config = config

    def add_custom_command(
        self,
        command_name: str,
        aliases: List[str],
        callback: Callable[[], None],
        feedback_message: Optional[str] = None
    ):
        """Add a custom voice command.

        Args:
            command_name: Internal name for the command
            aliases: List of phrases that trigger this command
            callback: Function to call when command is recognized
            feedback_message: Optional TTS feedback message
        """
        self._custom_commands[command_name] = (aliases, callback)
        for alias in aliases:
            self._command_lookup[alias.lower()] = command_name

        if feedback_message:
            self.COMMAND_FEEDBACK[command_name] = feedback_message

        logger.info(f"Added custom command: {command_name} with {len(aliases)} aliases")

    def remove_custom_command(self, command_name: str):
        """Remove a custom voice command.

        Args:
            command_name: Name of the command to remove
        """
        if command_name in self._custom_commands:
            aliases, _ = self._custom_commands[command_name]
            for alias in aliases:
                if alias.lower() in self._command_lookup:
                    del self._command_lookup[alias.lower()]
            del self._custom_commands[command_name]

            if command_name in self.COMMAND_FEEDBACK:
                del self.COMMAND_FEEDBACK[command_name]

            logger.info(f"Removed custom command: {command_name}")

    def integrate_with_hotkey_manager(self, hotkey_manager):
        """Integrate with a HotkeyManager instance.

        This allows voice commands to trigger the same actions as keyboard
        shortcuts, providing a unified control experience.

        Args:
            hotkey_manager: HotkeyManager instance
        """
        self._hotkey_manager = hotkey_manager
        logger.info("Voice commands integrated with HotkeyManager")

    def start(self):
        """Start listening for voice commands."""
        if not SPEECH_RECOGNITION_AVAILABLE:
            logger.warning("Cannot start voice commands - speech_recognition not available")
            return

        with self._lock:
            if self._running:
                return
            self._running = True

        # Initialize TTS if enabled
        if self._config.enable_tts_feedback:
            self._init_tts()

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

        # Cleanup TTS
        self._cleanup_tts()

        logger.info("Voice command handler stopped")

    def _init_recognizer(self):
        """Initialize the speech recognizer."""
        if self._recognizer is None:
            self._recognizer = sr.Recognizer()
            self._recognizer.dynamic_energy_threshold = self._config.dynamic_energy
            self._recognizer.energy_threshold = self._config.energy_threshold
            self._recognizer.pause_threshold = self._config.pause_threshold

    def _init_tts(self):
        """Initialize text-to-speech engine for feedback."""
        if self._tts_engine is not None:
            return

        try:
            import pyttsx3
            self._tts_engine = pyttsx3.init()
            self._tts_engine.setProperty('rate', self._config.tts_rate)
            self._tts_engine.setProperty('volume', self._config.tts_volume)
            logger.debug("TTS engine initialized for voice feedback")
        except ImportError:
            logger.debug("pyttsx3 not available - TTS feedback disabled")
        except Exception as e:
            logger.warning(f"Failed to initialize TTS: {e}")

    def _cleanup_tts(self):
        """Cleanup TTS engine."""
        with self._tts_lock:
            if self._tts_engine:
                try:
                    self._tts_engine.stop()
                except Exception:
                    pass
                self._tts_engine = None

    def _speak_feedback(self, message: str):
        """Speak feedback message using TTS.

        Args:
            message: Message to speak
        """
        if not self._config.enable_tts_feedback or not self._tts_engine:
            return

        def speak():
            with self._tts_lock:
                if self._tts_engine:
                    try:
                        self._tts_engine.say(message)
                        self._tts_engine.runAndWait()
                    except Exception as e:
                        logger.debug(f"TTS error: {e}")

        # Run in background thread to avoid blocking
        threading.Thread(target=speak, daemon=True).start()

    def _listen_loop(self):
        """Main listening loop for wake word and command detection."""
        self._init_recognizer()

        while self._running:
            try:
                # Check if enabled
                if not self._enabled:
                    time.sleep(0.5)
                    continue

                # Listen for wake word
                self._set_state(VoiceCommandState.LISTENING_FOR_WAKE_WORD)

                with sr.Microphone(device_index=self._config.device_index) as source:
                    # Adjust for ambient noise periodically
                    self._recognizer.adjust_for_ambient_noise(source, duration=0.5)

                    try:
                        # Listen for audio
                        audio = self._recognizer.listen(
                            source,
                            timeout=self._config.wake_word_timeout,
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
                                if current_time - self._last_wake_time < self._config.cooldown_period:
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
                timeout=self._config.command_timeout,
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
        for wake_word in self._config.wake_words:
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
        for wake_word in self._config.wake_words:
            if wake_word in text:
                # Get everything after the wake word
                idx = text.find(wake_word) + len(wake_word)
                remaining = text[idx:].strip()
                # Remove common separators
                remaining = re.sub(r'^[,.\s]+', '', remaining)

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

        # Notify command recognized callback
        if self.on_command_recognized:
            try:
                self.on_command_recognized(command)
            except Exception as e:
                logger.error(f"Error in command recognized callback: {e}")

        # Speak feedback if enabled
        if command in self.COMMAND_FEEDBACK:
            self._speak_feedback(self.COMMAND_FEEDBACK[command])

        # Built-in command callbacks
        callback_map = {
            "summarize": self.on_summarize,
            "repeat": self.on_repeat,
            "action_items": self.on_action_items,
            "what_did_they_say": self.on_what_did_they_say,
            "stop": self.on_stop_listening,
            "start": self.on_start_listening,
            "clear": self.on_clear,
        }

        callback = callback_map.get(command)

        # Check custom commands if not a built-in
        if callback is None and command in self._custom_commands:
            _, callback = self._custom_commands[command]

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
        commands = self.COMMAND_ALIASES.copy()
        # Add custom commands
        for name, (aliases, _) in self._custom_commands.items():
            commands[name] = aliases
        return commands

    def get_wake_words(self) -> List[str]:
        """Get list of supported wake words.

        Returns:
            List of wake word phrases
        """
        return self._config.wake_words.copy()

    def set_wake_words(self, wake_words: List[str]):
        """Set custom wake words.

        Args:
            wake_words: List of wake word phrases
        """
        self._config.wake_words = [w.lower() for w in wake_words]
        logger.info(f"Wake words updated: {self._config.wake_words}")

    def set_tts_feedback(self, enabled: bool, rate: int = 150, volume: float = 0.8):
        """Configure text-to-speech feedback.

        Args:
            enabled: Whether to enable TTS feedback
            rate: Speech rate (words per minute)
            volume: Volume level (0.0-1.0)
        """
        self._config.enable_tts_feedback = enabled
        self._config.tts_rate = max(50, min(300, rate))
        self._config.tts_volume = max(0.0, min(1.0, volume))

        if enabled and self._running:
            self._init_tts()
        elif not enabled:
            self._cleanup_tts()

        logger.info(f"TTS feedback {'enabled' if enabled else 'disabled'}")

    def get_status(self) -> Dict[str, Any]:
        """Get current status of the voice command handler.

        Returns:
            Dict with status information
        """
        return {
            "available": SPEECH_RECOGNITION_AVAILABLE,
            "running": self.is_running(),
            "enabled": self.is_enabled,
            "state": self.state.value,
            "device_index": self._config.device_index,
            "tts_enabled": self._config.enable_tts_feedback,
            "wake_words": self._config.wake_words,
            "commands": list(self.get_supported_commands().keys()),
        }


class VoiceCommandManager:
    """Manager class for voice commands with settings integration.

    Provides a higher-level interface for managing voice commands,
    including settings persistence and hotkey integration.
    """

    def __init__(self, settings_manager=None, hotkey_manager=None):
        """Initialize the voice command manager.

        Args:
            settings_manager: Optional SettingsManager instance for persistence
            hotkey_manager: Optional HotkeyManager instance for integration
        """
        self._settings = settings_manager
        self._hotkey_manager = hotkey_manager
        self._handler: Optional[VoiceCommandHandler] = None
        self._callbacks: Dict[str, Callable] = {}

    def setup(
        self,
        on_summarize: Optional[Callable[[], None]] = None,
        on_repeat: Optional[Callable[[], None]] = None,
        on_action_items: Optional[Callable[[], None]] = None,
        on_what_did_they_say: Optional[Callable[[], None]] = None,
        on_stop_listening: Optional[Callable[[], None]] = None,
        on_start_listening: Optional[Callable[[], None]] = None,
        on_clear: Optional[Callable[[], None]] = None,
    ):
        """Setup voice commands with the given callbacks.

        Args:
            on_summarize: Callback for summarize command
            on_repeat: Callback for repeat command
            on_action_items: Callback for action items command
            on_what_did_they_say: Callback for "what did they say" command
            on_stop_listening: Callback for stop listening command
            on_start_listening: Callback for start listening command
            on_clear: Callback for clear command
        """
        self._callbacks = {
            "summarize": on_summarize,
            "repeat": on_repeat,
            "action_items": on_action_items,
            "what_did_they_say": on_what_did_they_say,
            "stop": on_stop_listening,
            "start": on_start_listening,
            "clear": on_clear,
        }

        # Load settings
        config = self._load_config_from_settings()

        self._handler = VoiceCommandHandler(
            on_summarize=on_summarize,
            on_repeat=on_repeat,
            on_action_items=on_action_items,
            on_what_did_they_say=on_what_did_they_say,
            on_stop_listening=on_stop_listening,
            on_start_listening=on_start_listening,
            on_clear=on_clear,
            config=config,
            hotkey_manager=self._hotkey_manager,
        )

        logger.info("VoiceCommandManager setup complete")

    def _load_config_from_settings(self) -> VoiceCommandConfig:
        """Load configuration from settings manager.

        Returns:
            VoiceCommandConfig with settings values
        """
        config = VoiceCommandConfig()

        if self._settings:
            config.device_index = self._settings.get("voice_command_device_index")
            config.enable_tts_feedback = self._settings.get("voice_feedback_enabled", False)
            config.tts_rate = self._settings.get("voice_feedback_rate", 150)
            config.tts_volume = self._settings.get("voice_feedback_volume", 0.8)

            # Load custom wake words if configured
            custom_wake_words = self._settings.get("voice_command_wake_words")
            if custom_wake_words:
                config.wake_words = custom_wake_words

        return config

    def start(self) -> bool:
        """Start voice command listening.

        Returns:
            True if started successfully
        """
        if not self._handler:
            logger.warning("VoiceCommandManager not setup - call setup() first")
            return False

        if not is_voice_commands_available():
            logger.warning("Voice commands not available - speech_recognition not installed")
            return False

        self._handler.start()
        return True

    def stop(self):
        """Stop voice command listening."""
        if self._handler:
            self._handler.stop()

    def is_running(self) -> bool:
        """Check if voice commands are currently running."""
        return self._handler.is_running() if self._handler else False

    def is_available(self) -> bool:
        """Check if voice commands are available."""
        return is_voice_commands_available()

    def get_handler(self) -> Optional[VoiceCommandHandler]:
        """Get the underlying handler instance."""
        return self._handler

    def update_settings(self):
        """Reload settings and apply to handler."""
        if self._handler and self._settings:
            config = self._load_config_from_settings()
            self._handler.set_config(config)
            logger.info("Voice command settings updated")


# Module-level singleton instance
_voice_command_manager: Optional[VoiceCommandManager] = None


def get_voice_command_manager() -> VoiceCommandManager:
    """Get or create the singleton VoiceCommandManager instance.

    Returns:
        VoiceCommandManager instance
    """
    global _voice_command_manager

    if _voice_command_manager is None:
        _voice_command_manager = VoiceCommandManager()

    return _voice_command_manager
