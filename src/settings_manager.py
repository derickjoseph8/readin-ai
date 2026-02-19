"""Settings manager for ReadIn AI with JSON persistence."""

import json
import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from threading import Lock


class SettingsManager:
    """Centralized settings management with file persistence."""

    # Default settings values
    DEFAULTS = {
        # Audio settings
        "audio_device_index": None,  # None = auto-detect
        "audio_device_name": "",

        # AI settings
        "ai_model": "claude-sonnet-4-20250514",
        "system_prompt_preset": "interview_coach",
        "custom_system_prompt": "",
        "context_window_size": 3,
        "transcription_language": "en",

        # Appearance settings
        "theme": "dark_gold",
        "overlay_opacity": 0.92,
        "overlay_width": 450,
        "overlay_height": 300,
        "overlay_position": None,  # (x, y) or None for auto
        "text_size": "normal",  # "normal" or "large"

        # Keyboard shortcuts
        "shortcut_toggle_listen": "ctrl+shift+r",
        "shortcut_show_hide": "ctrl+shift+h",
        "shortcut_clear_context": "ctrl+shift+c",
        "shortcuts_enabled": True,

        # Behavior settings
        "auto_start_on_meeting": True,
        "minimize_to_tray": True,
        "auto_check_updates": True,
        "show_usage_warnings": True,
        "audio_setup_completed": False,  # First-run audio setup flag
        "hide_from_screen_capture": False,  # Screen capture protection (disabled by default for visibility)

        # Export settings
        "export_format": "md",  # "txt", "md", "json"
        "auto_export_on_end": False,
        "export_directory": "",

        # Internal state
        "_minimize_tooltip_shown": False,
        "_first_run": True,
    }

    # System prompt presets
    PROMPT_PRESETS = {
        "interview_coach": {
            "name": "Interview Coach",
            "description": "Optimized for job interviews and professional conversations",
            "prompt": """You are a real-time interview assistant. Generate SHORT talking points that someone can glance at and rephrase in their own words while speaking.

FORMAT RULES:
- Use bullet points (•) for key ideas
- Keep each point to 5-10 words MAX
- 2-4 bullet points total
- NO full sentences - just key phrases
- NO introductions like "Here's what to say"
- Start immediately with the first bullet

The goal is GLANCEABLE content - they need to look, understand in 1 second, and speak naturally."""
        },
        "technical_expert": {
            "name": "Technical Expert",
            "description": "For technical discussions, code reviews, and engineering meetings",
            "prompt": """You are a technical expert assistant. Generate concise technical talking points.

FORMAT RULES:
- Use bullet points (•) for key technical concepts
- Include specific terms, metrics, or examples when relevant
- 2-4 bullet points, 5-10 words each
- NO verbose explanations
- Start immediately with technical substance

Focus on accuracy and precision in technical communication."""
        },
        "sales_professional": {
            "name": "Sales Professional",
            "description": "For sales calls, demos, and client meetings",
            "prompt": """You are a sales communication assistant. Generate persuasive talking points.

FORMAT RULES:
- Use bullet points (•) for key value propositions
- Focus on benefits and outcomes
- 2-4 bullet points, 5-10 words each
- Include action-oriented language
- NO pushy or aggressive language

Aim for confident, benefit-focused responses."""
        },
        "executive_briefing": {
            "name": "Executive Briefing",
            "description": "For board meetings, investor calls, and leadership discussions",
            "prompt": """You are an executive communication assistant. Generate strategic talking points.

FORMAT RULES:
- Use bullet points (•) for key strategic points
- Focus on impact, metrics, and business outcomes
- 2-4 bullet points, 5-10 words each
- Maintain professional, authoritative tone
- NO unnecessary details

Emphasize strategic thinking and leadership perspective."""
        },
        "custom": {
            "name": "Custom",
            "description": "Use your own custom system prompt",
            "prompt": ""
        }
    }

    # Supported transcription languages
    SUPPORTED_LANGUAGES = [
        ("en", "English"),
        ("es", "Spanish"),
        ("fr", "French"),
        ("de", "German"),
        ("it", "Italian"),
        ("pt", "Portuguese"),
        ("nl", "Dutch"),
        ("pl", "Polish"),
        ("ru", "Russian"),
        ("ja", "Japanese"),
        ("zh", "Chinese"),
        ("ko", "Korean"),
        ("ar", "Arabic"),
        ("hi", "Hindi"),
        ("tr", "Turkish"),
        ("vi", "Vietnamese"),
        ("th", "Thai"),
        ("id", "Indonesian"),
        ("auto", "Auto-detect"),
    ]

    # Available AI models
    AVAILABLE_MODELS = [
        ("claude-sonnet-4-20250514", "Claude Sonnet 4 (Recommended)"),
        ("claude-sonnet-4-20250514", "Claude Sonnet 4"),
        ("claude-3-haiku-20240307", "Claude 3 Haiku (Fastest)"),
    ]

    _instance = None
    _lock = Lock()

    def __new__(cls):
        """Singleton pattern for settings manager."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._settings: Dict[str, Any] = {}
        self._callbacks: Dict[str, List[Callable]] = {}
        self._settings_file = self._get_settings_path()
        self._load()
        self._initialized = True

    def _get_settings_path(self) -> Path:
        """Get the settings file path."""
        if os.name == 'nt':  # Windows
            base_dir = Path(os.environ.get('APPDATA', Path.home())) / '.readin'
        else:  # macOS/Linux
            base_dir = Path.home() / '.readin'

        base_dir.mkdir(parents=True, exist_ok=True)
        return base_dir / 'settings.json'

    def _load(self) -> None:
        """Load settings from file, applying defaults for missing values."""
        self._settings = self.DEFAULTS.copy()

        if self._settings_file.exists():
            try:
                with open(self._settings_file, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                    # Merge saved settings, keeping defaults for missing keys
                    for key, value in saved.items():
                        if key in self.DEFAULTS:
                            self._settings[key] = value
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load settings: {e}")

    def _save(self) -> None:
        """Save current settings to file."""
        try:
            with open(self._settings_file, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, indent=2)
        except IOError as e:
            print(f"Warning: Could not save settings: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        if default is None and key in self.DEFAULTS:
            default = self.DEFAULTS[key]
        return self._settings.get(key, default)

    def set(self, key: str, value: Any, save: bool = True) -> None:
        """Set a setting value and optionally save to disk.

        Performs type checking, range validation, and sanitization before saving.
        """
        # Validate and sanitize the value
        validated_value = self._validate_and_sanitize(key, value)
        if validated_value is None and value is not None:
            print(f"Warning: Invalid value for setting '{key}': {value}")
            return

        old_value = self._settings.get(key)
        self._settings[key] = validated_value

        if save:
            self._save()

        # Notify callbacks if value changed
        if old_value != validated_value and key in self._callbacks:
            for callback in self._callbacks[key]:
                try:
                    callback(key, validated_value, old_value)
                except Exception as e:
                    print(f"Warning: Settings callback error: {e}")

    def _validate_and_sanitize(self, key: str, value: Any) -> Any:
        """Validate and sanitize a setting value based on its type and constraints.

        Args:
            key: The setting key
            value: The value to validate

        Returns:
            The validated/sanitized value, or None if validation fails
        """
        # Allow None values if the default is None
        if value is None:
            if key in self.DEFAULTS and self.DEFAULTS[key] is None:
                return None
            return None

        # Type checking against DEFAULTS
        if key in self.DEFAULTS:
            default_value = self.DEFAULTS[key]
            expected_type = type(default_value) if default_value is not None else None

            # Type validation (skip if default is None, meaning any type is allowed)
            if expected_type is not None and not isinstance(value, expected_type):
                # Try type coercion for numeric types
                if expected_type in (int, float) and isinstance(value, (int, float)):
                    value = expected_type(value)
                elif expected_type == bool and isinstance(value, (int, str)):
                    value = bool(value)
                elif expected_type == str and not isinstance(value, str):
                    value = str(value)
                else:
                    print(f"Warning: Type mismatch for '{key}': expected {expected_type.__name__}, got {type(value).__name__}")
                    return None

        # Range validation for numeric settings
        value = self._validate_numeric_range(key, value)
        if value is None:
            return None

        # String sanitization
        if isinstance(value, str):
            value = self._sanitize_string(key, value)

        return value

    def _validate_numeric_range(self, key: str, value: Any) -> Any:
        """Validate numeric values are within acceptable ranges.

        Args:
            key: The setting key
            value: The value to validate

        Returns:
            The clamped value, or None if validation fails
        """
        # Define numeric constraints
        numeric_constraints = {
            "overlay_opacity": (0.5, 1.0),
            "overlay_width": (200, 2000),
            "overlay_height": (150, 1500),
            "context_window_size": (1, 20),
        }

        if key in numeric_constraints and isinstance(value, (int, float)):
            min_val, max_val = numeric_constraints[key]
            if value < min_val or value > max_val:
                # Clamp to valid range
                clamped = max(min_val, min(value, max_val))
                print(f"Warning: Value for '{key}' clamped from {value} to {clamped} (range: {min_val}-{max_val})")
                return clamped

        return value

    def _sanitize_string(self, key: str, value: str) -> str:
        """Sanitize string values to prevent issues.

        Args:
            key: The setting key
            value: The string to sanitize

        Returns:
            The sanitized string
        """
        # Remove null bytes and control characters (except newlines and tabs)
        import re
        value = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', value)

        # Limit string length for certain fields
        max_lengths = {
            "audio_device_name": 256,
            "custom_system_prompt": 10000,
            "export_directory": 500,
            "shortcut_toggle_listen": 50,
            "shortcut_show_hide": 50,
            "shortcut_clear_context": 50,
        }

        if key in max_lengths and len(value) > max_lengths[key]:
            value = value[:max_lengths[key]]
            print(f"Warning: String value for '{key}' truncated to {max_lengths[key]} characters")

        return value

    def set_multiple(self, settings: Dict[str, Any], save: bool = True) -> None:
        """Set multiple settings at once."""
        for key, value in settings.items():
            self.set(key, value, save=False)

        if save:
            self._save()

    def reset(self, key: str) -> None:
        """Reset a setting to its default value."""
        if key in self.DEFAULTS:
            self.set(key, self.DEFAULTS[key])

    def reset_all(self) -> None:
        """Reset all settings to defaults."""
        self._settings = self.DEFAULTS.copy()
        self._save()

    def on_change(self, key: str, callback: Callable[[str, Any, Any], None]) -> None:
        """Register a callback for when a setting changes.

        Callback signature: callback(key, new_value, old_value)
        """
        if key not in self._callbacks:
            self._callbacks[key] = []
        self._callbacks[key].append(callback)

    def remove_callback(self, key: str, callback: Callable) -> None:
        """Remove a change callback."""
        if key in self._callbacks and callback in self._callbacks[key]:
            self._callbacks[key].remove(callback)

    def get_system_prompt(self) -> str:
        """Get the current system prompt based on preset or custom."""
        preset = self.get("system_prompt_preset")

        if preset == "custom":
            custom = self.get("custom_system_prompt")
            if custom:
                return custom
            # Fall back to interview coach if custom is empty
            return self.PROMPT_PRESETS["interview_coach"]["prompt"]

        return self.PROMPT_PRESETS.get(preset, self.PROMPT_PRESETS["interview_coach"])["prompt"]

    def get_all(self) -> Dict[str, Any]:
        """Get all current settings."""
        return self._settings.copy()

    def export_settings(self, path: Path) -> bool:
        """Export settings to a specific file."""
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, indent=2)
            return True
        except IOError:
            return False

    def import_settings(self, path: Path) -> bool:
        """Import settings from a file."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                imported = json.load(f)
                # Validate and merge
                for key, value in imported.items():
                    if key in self.DEFAULTS:
                        self._settings[key] = value
                self._save()
            return True
        except (json.JSONDecodeError, IOError):
            return False


# Global settings instance
settings = SettingsManager()
