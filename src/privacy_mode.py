"""Privacy Mode Handler for ReadIn AI.

Provides comprehensive privacy protection by:
- Managing excluded apps list
- Auto-detecting sensitive apps (banking, medical, password managers)
- Temporarily pausing monitoring with reason tracking
- Maintaining pause history for audit/review
"""

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Dict, List, Optional, Set
from enum import Enum

import psutil

from settings_manager import settings, SettingsManager

logger = logging.getLogger(__name__)


class PauseReason(Enum):
    """Reasons for pausing monitoring."""
    SENSITIVE_APP_DETECTED = "sensitive_app_detected"
    MANUAL_PAUSE = "manual_pause"
    EXCLUDED_APP_ACTIVE = "excluded_app_active"
    PRIVACY_HOTKEY = "privacy_hotkey"
    SCHEDULED_PAUSE = "scheduled_pause"


@dataclass
class PauseEvent:
    """Represents a single pause event for history tracking."""
    timestamp: datetime
    reason: PauseReason
    app_name: Optional[str] = None
    duration_seconds: Optional[float] = None
    category: Optional[str] = None
    ended_at: Optional[datetime] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "reason": self.reason.value,
            "app_name": self.app_name,
            "duration_seconds": self.duration_seconds,
            "category": self.category,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "PauseEvent":
        """Create from dictionary."""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            reason=PauseReason(data["reason"]),
            app_name=data.get("app_name"),
            duration_seconds=data.get("duration_seconds"),
            category=data.get("category"),
            ended_at=datetime.fromisoformat(data["ended_at"]) if data.get("ended_at") else None,
        )


class PrivacyModeHandler:
    """Handles Privacy Mode functionality for ReadIn AI.

    Features:
    - Excluded apps list management
    - Auto-pause for sensitive apps (banking, medical, password managers)
    - Default exclusion list for common sensitive apps
    - Temporary pause with reason tracking
    - Pause history for audit purposes
    """

    # Default sensitive apps to auto-detect (extends settings categories)
    DEFAULT_SENSITIVE_PATTERNS = [
        # Banking keywords in process names
        "bank", "chase", "wells", "citi", "capital",
        # Trading
        "trade", "fidelity", "schwab", "robinhood", "coinbase",
        # Password managers
        "1password", "lastpass", "bitwarden", "dashlane", "keepass", "keeper",
        # Medical
        "health", "medical", "mychart", "teladoc",
        # Security/VPN
        "vpn", "nord", "express", "proton", "tunnel",
        # Crypto
        "wallet", "metamask", "ledger", "exodus", "trezor",
    ]

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._pause_history: List[PauseEvent] = []
        self._max_history_size = 100
        self._current_pause: Optional[PauseEvent] = None
        self._detected_sensitive_apps: Set[str] = set()
        self._auto_detect_enabled = True
        self._callbacks: List[Callable[[bool, Optional[str]], None]] = []
        self._monitor_thread: Optional[threading.Thread] = None
        self._monitoring = False
        self._check_interval = 2.0  # seconds

        # Load pause history from settings if available
        self._load_history()

        self._initialized = True

    def _load_history(self):
        """Load pause history from settings."""
        try:
            history_data = settings.get("_privacy_pause_history", [])
            self._pause_history = [
                PauseEvent.from_dict(event) for event in history_data
            ]
        except Exception as e:
            logger.warning(f"Could not load pause history: {e}")
            self._pause_history = []

    def _save_history(self):
        """Save pause history to settings."""
        try:
            history_data = [event.to_dict() for event in self._pause_history[-self._max_history_size:]]
            settings.set("_privacy_pause_history", history_data)
        except Exception as e:
            logger.warning(f"Could not save pause history: {e}")

    @property
    def is_enabled(self) -> bool:
        """Check if Privacy Mode is enabled."""
        return settings.get("privacy_mode_enabled", True)

    @property
    def is_paused(self) -> bool:
        """Check if monitoring is currently paused."""
        return self._current_pause is not None

    @property
    def current_pause_reason(self) -> Optional[PauseReason]:
        """Get the reason for current pause."""
        return self._current_pause.reason if self._current_pause else None

    @property
    def current_pause_app(self) -> Optional[str]:
        """Get the app that caused current pause."""
        return self._current_pause.app_name if self._current_pause else None

    def get_excluded_apps(self) -> List[str]:
        """Get the list of excluded apps.

        Returns:
            List of app names that are excluded from monitoring.
        """
        return settings.get_excluded_apps()

    def add_excluded_app(self, app_name: str) -> bool:
        """Add an app to the excluded list.

        Args:
            app_name: Name of the app to exclude

        Returns:
            True if added successfully, False if already exists
        """
        result = settings.add_excluded_app(app_name)
        if result:
            logger.info(f"Added '{app_name}' to excluded apps list")
        return result

    def remove_excluded_app(self, app_name: str) -> bool:
        """Remove an app from the excluded list.

        Args:
            app_name: Name of the app to remove

        Returns:
            True if removed, False if not found
        """
        result = settings.remove_excluded_app(app_name)
        if result:
            logger.info(f"Removed '{app_name}' from excluded apps list")
        return result

    def is_app_excluded(self, app_name: str) -> bool:
        """Check if an app is in the excluded list.

        Args:
            app_name: Name of the app to check

        Returns:
            True if excluded, False otherwise
        """
        return settings.is_app_excluded(app_name)

    def add_sensitive_category(self, category_key: str) -> int:
        """Add all apps from a sensitive category to exclusions.

        Args:
            category_key: Key from SENSITIVE_APP_CATEGORIES

        Returns:
            Number of apps added
        """
        return settings.add_sensitive_category(category_key)

    def remove_sensitive_category(self, category_key: str) -> int:
        """Remove all apps from a sensitive category from exclusions.

        Args:
            category_key: Key from SENSITIVE_APP_CATEGORIES

        Returns:
            Number of apps removed
        """
        return settings.remove_sensitive_category(category_key)

    def get_sensitive_categories(self) -> Dict:
        """Get all available sensitive app categories.

        Returns:
            Dictionary of category data
        """
        return SettingsManager.SENSITIVE_APP_CATEGORIES

    def pause_monitoring(self, reason: PauseReason, app_name: Optional[str] = None,
                        category: Optional[str] = None) -> bool:
        """Temporarily pause monitoring.

        Args:
            reason: Why monitoring is being paused
            app_name: Optional name of app that triggered pause
            category: Optional category of the sensitive app

        Returns:
            True if paused, False if already paused
        """
        if self._current_pause is not None:
            return False

        self._current_pause = PauseEvent(
            timestamp=datetime.now(),
            reason=reason,
            app_name=app_name,
            category=category,
        )

        logger.info(f"Privacy Mode: Paused monitoring - {reason.value}"
                   f"{f' (app: {app_name})' if app_name else ''}")

        # Notify callbacks
        self._notify_callbacks(True, app_name)

        return True

    def resume_monitoring(self) -> bool:
        """Resume monitoring after pause.

        Returns:
            True if resumed, False if not paused
        """
        if self._current_pause is None:
            return False

        # Complete the pause event
        self._current_pause.ended_at = datetime.now()
        self._current_pause.duration_seconds = (
            self._current_pause.ended_at - self._current_pause.timestamp
        ).total_seconds()

        # Add to history
        self._pause_history.append(self._current_pause)

        # Trim history if needed
        if len(self._pause_history) > self._max_history_size:
            self._pause_history = self._pause_history[-self._max_history_size:]

        # Save history
        self._save_history()

        logger.info(f"Privacy Mode: Resumed monitoring after "
                   f"{self._current_pause.duration_seconds:.1f}s pause")

        app_name = self._current_pause.app_name
        self._current_pause = None

        # Notify callbacks
        self._notify_callbacks(False, app_name)

        return True

    def get_pause_history(self, limit: int = 50) -> List[PauseEvent]:
        """Get the pause history.

        Args:
            limit: Maximum number of events to return

        Returns:
            List of pause events, most recent first
        """
        return list(reversed(self._pause_history[-limit:]))

    def clear_pause_history(self):
        """Clear all pause history."""
        self._pause_history = []
        self._save_history()
        logger.info("Privacy Mode: Cleared pause history")

    def detect_sensitive_apps(self) -> List[Dict]:
        """Scan running processes for sensitive apps.

        Returns:
            List of detected sensitive apps with details
        """
        detected = []
        excluded_apps = [app.lower() for app in self.get_excluded_apps()]

        for proc in psutil.process_iter(['name', 'pid']):
            try:
                proc_name = proc.info['name']
                if not proc_name:
                    continue

                proc_name_lower = proc_name.lower()

                # Check if already excluded
                if proc_name_lower in excluded_apps:
                    continue

                # Check against default patterns
                for pattern in self.DEFAULT_SENSITIVE_PATTERNS:
                    if pattern in proc_name_lower:
                        detected.append({
                            "name": proc_name,
                            "pid": proc.info['pid'],
                            "pattern_matched": pattern,
                            "category": self._categorize_pattern(pattern),
                        })
                        break

                # Check against category apps
                for cat_key, cat_data in SettingsManager.SENSITIVE_APP_CATEGORIES.items():
                    cat_apps_lower = [app.lower() for app in cat_data["apps"]]
                    if proc_name_lower in cat_apps_lower:
                        detected.append({
                            "name": proc_name,
                            "pid": proc.info['pid'],
                            "category": cat_data["name"],
                            "category_key": cat_key,
                        })
                        break

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return detected

    def _categorize_pattern(self, pattern: str) -> str:
        """Get category name for a pattern match."""
        categories = {
            ("bank", "chase", "wells", "citi", "capital"): "Banking",
            ("trade", "fidelity", "schwab", "robinhood"): "Trading",
            ("1password", "lastpass", "bitwarden", "dashlane", "keepass", "keeper"): "Password Manager",
            ("health", "medical", "mychart", "teladoc"): "Medical",
            ("vpn", "nord", "express", "proton", "tunnel"): "VPN/Security",
            ("wallet", "metamask", "ledger", "exodus", "trezor", "coinbase"): "Crypto",
        }

        for patterns, category in categories.items():
            if pattern in patterns:
                return category
        return "Sensitive"

    def auto_exclude_detected(self) -> int:
        """Auto-add detected sensitive apps to exclusion list.

        Returns:
            Number of apps added
        """
        detected = self.detect_sensitive_apps()
        added = 0

        for app in detected:
            if self.add_excluded_app(app["name"]):
                added += 1
                logger.info(f"Auto-excluded sensitive app: {app['name']} ({app.get('category', 'Unknown')})")

        return added

    def should_skip_app(self, app_name: str, process_name: Optional[str] = None) -> bool:
        """Check if an app should be skipped for monitoring.

        This is the main method that process_monitor should call.

        Args:
            app_name: Friendly app name
            process_name: Optional process executable name

        Returns:
            True if app should be skipped, False otherwise
        """
        if not self.is_enabled:
            return False

        # Check excluded apps list
        excluded = [app.lower() for app in self.get_excluded_apps()]

        if app_name.lower() in excluded:
            return True

        if process_name and process_name.lower() in excluded:
            return True

        return False

    def check_and_pause_for_sensitive(self) -> Optional[str]:
        """Check for sensitive apps and pause if found.

        Returns:
            Name of sensitive app if paused, None otherwise
        """
        if not self.is_enabled or not self._auto_detect_enabled:
            return None

        detected = self.detect_sensitive_apps()

        if detected and not self.is_paused:
            # Pause for the first detected sensitive app
            app = detected[0]
            self.pause_monitoring(
                reason=PauseReason.SENSITIVE_APP_DETECTED,
                app_name=app["name"],
                category=app.get("category"),
            )
            return app["name"]

        return None

    def register_callback(self, callback: Callable[[bool, Optional[str]], None]):
        """Register a callback for pause/resume events.

        Callback signature: callback(is_paused: bool, app_name: Optional[str])

        Args:
            callback: Function to call on pause/resume
        """
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def unregister_callback(self, callback: Callable):
        """Unregister a callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def _notify_callbacks(self, is_paused: bool, app_name: Optional[str]):
        """Notify all registered callbacks."""
        for callback in self._callbacks:
            try:
                callback(is_paused, app_name)
            except Exception as e:
                logger.warning(f"Privacy callback error: {e}")

    def start_background_monitor(self):
        """Start background monitoring for sensitive apps.

        This runs in a separate thread and auto-pauses/resumes
        based on detected sensitive apps.
        """
        if self._monitoring:
            return

        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._background_monitor_loop,
            daemon=True,
            name="PrivacyMonitor"
        )
        self._monitor_thread.start()
        logger.info("Privacy Mode: Started background monitoring")

    def stop_background_monitor(self):
        """Stop background monitoring."""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5.0)
            self._monitor_thread = None
        logger.info("Privacy Mode: Stopped background monitoring")

    def _background_monitor_loop(self):
        """Background thread loop for monitoring sensitive apps."""
        import time

        while self._monitoring:
            try:
                if self.is_enabled and self._auto_detect_enabled:
                    detected = self.detect_sensitive_apps()

                    if detected:
                        # Sensitive app detected
                        if not self.is_paused:
                            app = detected[0]
                            self.pause_monitoring(
                                reason=PauseReason.SENSITIVE_APP_DETECTED,
                                app_name=app["name"],
                                category=app.get("category"),
                            )
                        self._detected_sensitive_apps = {d["name"] for d in detected}
                    else:
                        # No sensitive apps
                        if (self.is_paused and
                            self.current_pause_reason == PauseReason.SENSITIVE_APP_DETECTED):
                            self.resume_monitoring()
                        self._detected_sensitive_apps = set()

            except Exception as e:
                logger.warning(f"Privacy monitor error: {e}")

            time.sleep(self._check_interval)

    def set_auto_detect(self, enabled: bool):
        """Enable or disable auto-detection of sensitive apps.

        Args:
            enabled: Whether to enable auto-detection
        """
        self._auto_detect_enabled = enabled
        logger.info(f"Privacy Mode: Auto-detect {'enabled' if enabled else 'disabled'}")

    def is_auto_detect_enabled(self) -> bool:
        """Check if auto-detection is enabled."""
        return self._auto_detect_enabled

    def get_status(self) -> Dict:
        """Get current privacy mode status.

        Returns:
            Dictionary with current status information
        """
        return {
            "enabled": self.is_enabled,
            "paused": self.is_paused,
            "pause_reason": self.current_pause_reason.value if self.current_pause_reason else None,
            "pause_app": self.current_pause_app,
            "auto_detect": self._auto_detect_enabled,
            "excluded_count": len(self.get_excluded_apps()),
            "detected_sensitive": list(self._detected_sensitive_apps),
            "history_count": len(self._pause_history),
        }


# Global singleton instance
privacy_handler = PrivacyModeHandler()


def get_privacy_handler() -> PrivacyModeHandler:
    """Get the global privacy handler instance."""
    return privacy_handler
