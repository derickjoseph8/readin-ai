"""Global keyboard shortcut manager for ReadIn AI."""

import threading
from typing import Callable, Dict, Optional, Set
from pynput import keyboard

from config import IS_WINDOWS, IS_MACOS


class HotkeyManager:
    """Manages global keyboard shortcuts across platforms."""

    # Mapping of modifier names to pynput keys
    MODIFIER_MAP = {
        'ctrl': keyboard.Key.ctrl_l,
        'control': keyboard.Key.ctrl_l,
        'shift': keyboard.Key.shift_l,
        'alt': keyboard.Key.alt_l,
        'cmd': keyboard.Key.cmd if IS_MACOS else keyboard.Key.ctrl_l,
        'command': keyboard.Key.cmd if IS_MACOS else keyboard.Key.ctrl_l,
        'win': keyboard.Key.cmd if IS_MACOS else keyboard.Key.ctrl_l,
    }

    def __init__(self):
        self._listener: Optional[keyboard.Listener] = None
        self._hotkeys: Dict[str, Callable] = {}  # normalized_shortcut -> callback
        self._pressed_keys: Set = set()
        self._running = False
        self._lock = threading.Lock()

    def _normalize_shortcut(self, shortcut: str) -> str:
        """Normalize a shortcut string to a consistent format.

        Example: 'Ctrl+Shift+R' -> 'ctrl+shift+r'
        """
        parts = shortcut.lower().replace(' ', '').split('+')
        # Sort modifiers alphabetically, keep the main key last
        modifiers = sorted([p for p in parts[:-1] if p in self.MODIFIER_MAP])
        key = parts[-1] if parts else ''
        return '+'.join(modifiers + [key])

    def _parse_shortcut(self, shortcut: str) -> tuple:
        """Parse a shortcut string into (modifiers_set, main_key).

        Returns:
            Tuple of (set of modifier keys, main key character or Key object)
        """
        parts = shortcut.lower().replace(' ', '').split('+')
        modifiers = set()
        main_key = None

        for part in parts:
            if part in self.MODIFIER_MAP:
                modifiers.add(self.MODIFIER_MAP[part])
            else:
                # It's the main key
                if len(part) == 1:
                    main_key = part
                else:
                    # Try to get a special key
                    try:
                        main_key = getattr(keyboard.Key, part)
                    except AttributeError:
                        main_key = part

        return modifiers, main_key

    def _get_pressed_modifiers(self) -> Set:
        """Get the set of currently pressed modifier keys."""
        modifiers = set()
        for key in self._pressed_keys:
            if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
                modifiers.add(keyboard.Key.ctrl_l)
            elif key in (keyboard.Key.shift_l, keyboard.Key.shift_r):
                modifiers.add(keyboard.Key.shift_l)
            elif key in (keyboard.Key.alt_l, keyboard.Key.alt_r):
                modifiers.add(keyboard.Key.alt_l)
            elif key in (keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r):
                modifiers.add(keyboard.Key.cmd)
        return modifiers

    def _on_press(self, key):
        """Handle key press events."""
        self._pressed_keys.add(key)

        # Check if any registered hotkey matches
        current_modifiers = self._get_pressed_modifiers()

        # Get the character for regular keys
        try:
            char = key.char.lower() if hasattr(key, 'char') and key.char else None
        except AttributeError:
            char = None

        with self._lock:
            for shortcut, callback in self._hotkeys.items():
                required_modifiers, main_key = self._parse_shortcut(shortcut)

                # Check if modifiers match
                if current_modifiers != required_modifiers:
                    continue

                # Check if main key matches
                key_matches = False
                if char is not None and main_key == char:
                    key_matches = True
                elif main_key == key:
                    key_matches = True

                if key_matches:
                    # Execute callback in a separate thread to avoid blocking
                    threading.Thread(target=callback, daemon=True).start()
                    break

    def _on_release(self, key):
        """Handle key release events."""
        self._pressed_keys.discard(key)

    def register(self, shortcut: str, callback: Callable) -> bool:
        """Register a global hotkey.

        Args:
            shortcut: Shortcut string like 'ctrl+shift+r'
            callback: Function to call when hotkey is pressed

        Returns:
            True if registration was successful
        """
        normalized = self._normalize_shortcut(shortcut)

        with self._lock:
            self._hotkeys[normalized] = callback

        return True

    def unregister(self, shortcut: str) -> bool:
        """Unregister a global hotkey.

        Args:
            shortcut: Shortcut string to unregister

        Returns:
            True if the hotkey was registered and is now removed
        """
        normalized = self._normalize_shortcut(shortcut)

        with self._lock:
            if normalized in self._hotkeys:
                del self._hotkeys[normalized]
                return True
        return False

    def unregister_all(self):
        """Unregister all hotkeys."""
        with self._lock:
            self._hotkeys.clear()

    def is_registered(self, shortcut: str) -> bool:
        """Check if a shortcut is registered."""
        normalized = self._normalize_shortcut(shortcut)
        with self._lock:
            return normalized in self._hotkeys

    def get_registered_shortcuts(self) -> list:
        """Get list of all registered shortcuts."""
        with self._lock:
            return list(self._hotkeys.keys())

    def start(self):
        """Start listening for global hotkeys."""
        if self._running:
            return

        self._running = True
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.start()

    def stop(self):
        """Stop listening for global hotkeys."""
        self._running = False
        if self._listener:
            self._listener.stop()
            self._listener = None
        self._pressed_keys.clear()

    def is_running(self) -> bool:
        """Check if the hotkey manager is active."""
        return self._running

    @staticmethod
    def format_shortcut(shortcut: str, display: bool = True) -> str:
        """Format a shortcut string for display.

        Args:
            shortcut: Shortcut string like 'ctrl+shift+r'
            display: If True, use platform-appropriate symbols

        Returns:
            Formatted string like 'Ctrl+Shift+R' or '⌃⇧R' on macOS
        """
        parts = shortcut.lower().replace(' ', '').split('+')

        if display and IS_MACOS:
            # Use macOS symbols
            symbol_map = {
                'ctrl': '⌃',
                'control': '⌃',
                'shift': '⇧',
                'alt': '⌥',
                'cmd': '⌘',
                'command': '⌘',
            }
            formatted = []
            for part in parts:
                if part in symbol_map:
                    formatted.append(symbol_map[part])
                else:
                    formatted.append(part.upper())
            return ''.join(formatted)
        else:
            # Use standard notation
            formatted = []
            for part in parts:
                if part in ('ctrl', 'control'):
                    formatted.append('Ctrl')
                elif part == 'shift':
                    formatted.append('Shift')
                elif part == 'alt':
                    formatted.append('Alt')
                elif part in ('cmd', 'command'):
                    formatted.append('Cmd' if IS_MACOS else 'Win')
                else:
                    formatted.append(part.upper())
            return '+'.join(formatted)

    @staticmethod
    def validate_shortcut(shortcut: str) -> tuple:
        """Validate a shortcut string.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not shortcut:
            return False, "Shortcut cannot be empty"

        parts = shortcut.lower().replace(' ', '').split('+')

        if len(parts) < 2:
            return False, "Shortcut must have at least one modifier and one key"

        # Check for valid modifiers
        valid_modifiers = {'ctrl', 'control', 'shift', 'alt', 'cmd', 'command', 'win'}
        modifiers_found = 0

        for part in parts[:-1]:  # All but the last part should be modifiers
            if part not in valid_modifiers:
                return False, f"Invalid modifier: {part}"
            modifiers_found += 1

        if modifiers_found == 0:
            return False, "Shortcut must have at least one modifier (Ctrl, Shift, Alt)"

        # Check the main key
        main_key = parts[-1]
        if not main_key:
            return False, "Shortcut must have a main key"

        # Valid if it's a single character or a known special key
        special_keys = {
            'space', 'enter', 'return', 'tab', 'escape', 'esc',
            'backspace', 'delete', 'home', 'end', 'pageup', 'pagedown',
            'up', 'down', 'left', 'right',
            'f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10', 'f11', 'f12',
        }

        if len(main_key) != 1 and main_key not in special_keys:
            return False, f"Invalid key: {main_key}"

        return True, ""


# Convenience function to check for shortcut conflicts
def check_shortcut_conflict(shortcut: str, existing_shortcuts: list) -> Optional[str]:
    """Check if a shortcut conflicts with existing shortcuts.

    Returns:
        The conflicting shortcut if found, None otherwise
    """
    manager = HotkeyManager()
    normalized = manager._normalize_shortcut(shortcut)

    for existing in existing_shortcuts:
        if manager._normalize_shortcut(existing) == normalized:
            return existing

    return None
