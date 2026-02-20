"""Floating overlay UI optimized for reading while speaking naturally."""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QApplication, QSizeGrip,
    QScrollArea
)
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QClipboard, QCursor

from config import OVERLAY_WIDTH, OVERLAY_HEIGHT, OVERLAY_OPACITY, IS_WINDOWS

# Import theme support
try:
    from ui.themes import get_overlay_stylesheet, THEMES
    from settings_manager import SettingsManager
    THEMES_AVAILABLE = True
except ImportError:
    THEMES_AVAILABLE = False


class OverlayWindow(QWidget):
    """Floating overlay optimized for glancing while speaking."""

    # Signals for thread-safe UI updates
    update_heard_signal = pyqtSignal(str)
    update_response_signal = pyqtSignal(str)
    append_response_signal = pyqtSignal(str)
    export_requested = pyqtSignal()
    settings_requested = pyqtSignal()
    logout_requested = pyqtSignal()
    listen_toggled = pyqtSignal(bool)  # True = start, False = stop

    def __init__(self):
        super().__init__()
        self._drag_position: QPoint = QPoint()
        self._current_response = ""
        self._current_heard = ""
        self._large_mode = False
        self._hidden_from_capture = False
        self._settings = SettingsManager() if THEMES_AVAILABLE else None
        self._setup_ui()
        self._connect_signals()
        self._load_position()
        # Only enable screen capture protection if setting is enabled
        if self._settings and self._settings.get("hide_from_screen_capture", False):
            self._setup_screen_capture_protection()

    def _setup_ui(self):
        """Initialize the UI components."""
        # Window flags for floating overlay
        always_on_top = self._settings.get("always_on_top", True) if self._settings else True
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint

        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(OVERLAY_WIDTH, OVERLAY_HEIGHT)
        self.resize(OVERLAY_WIDTH, OVERLAY_HEIGHT)

        # Get opacity from settings (used for container background)
        self._opacity = (self._settings.get("overlay_opacity", 0.92)) if self._settings else OVERLAY_OPACITY

        # Main container - apply theme with opacity
        self.container = QFrame(self)
        self.container.setObjectName("container")
        self.container.setAutoFillBackground(True)
        self._apply_theme()

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.container)

        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(16, 12, 16, 12)
        container_layout.setSpacing(8)

        # Header with title and controls
        header = QHBoxLayout()

        self.title_label = QLabel("ReadIn AI")
        self._apply_title_style()
        header.addWidget(self.title_label)

        header.addStretch()

        # Start/Stop Listening button - 44px height minimum for accessibility
        self.listen_btn = QPushButton("▶ Start")
        self.listen_btn.setFixedSize(80, 44)
        self.listen_btn.setToolTip("Start/Stop Listening")
        self._is_listening = False
        self._update_listen_btn_style()
        self.listen_btn.clicked.connect(self._on_listen_clicked)
        header.addWidget(self.listen_btn)

        # Font size toggle button - 44x44 minimum for accessibility
        self.size_btn = QPushButton("A+ Text")
        self.size_btn.setFixedSize(60, 44)
        self.size_btn.setToolTip("Toggle large text mode")
        self.size_btn.setStyleSheet("""
            QPushButton {
                background-color: #333333;
                color: #ffffff;
                border: 1px solid #444444;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #d4af37;
                color: #000000;
                border-color: #d4af37;
            }
        """)
        self.size_btn.clicked.connect(self._toggle_size)
        header.addWidget(self.size_btn)

        # Settings button - 44x44 minimum for accessibility
        self.settings_btn = QPushButton("⚙ Settings")
        self.settings_btn.setFixedSize(80, 44)
        self.settings_btn.setToolTip("Settings")
        self.settings_btn.setStyleSheet("""
            QPushButton {
                background-color: #333333;
                color: #ffffff;
                border: 1px solid #444444;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #d4af37;
                color: #000000;
                border-color: #d4af37;
            }
        """)
        self.settings_btn.clicked.connect(self.settings_requested.emit)
        header.addWidget(self.settings_btn)

        # Logout button - 44x44 minimum for accessibility
        self.logout_btn = QPushButton("⏻ Logout")
        self.logout_btn.setFixedSize(80, 44)
        self.logout_btn.setToolTip("Logout")
        self.logout_btn.setStyleSheet("""
            QPushButton {
                background-color: #333333;
                color: #ffffff;
                border: 1px solid #444444;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #f59e0b;
                color: #000000;
                border-color: #f59e0b;
            }
        """)
        self.logout_btn.clicked.connect(self.logout_requested.emit)
        header.addWidget(self.logout_btn)

        # Minimize button - 44x44 minimum for accessibility
        self.min_btn = QPushButton("— Min")
        self.min_btn.setFixedSize(60, 44)
        self.min_btn.setToolTip("Minimize window")
        self.min_btn.setStyleSheet("""
            QPushButton {
                background-color: #333333;
                color: #ffffff;
                border: 1px solid #444444;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #d4af37;
                color: #000000;
                border-color: #d4af37;
            }
        """)
        self.min_btn.clicked.connect(self.showMinimized)
        header.addWidget(self.min_btn)

        # Close button - 44x44 minimum for accessibility
        self.close_btn = QPushButton("✕ Close")
        self.close_btn.setFixedSize(70, 44)
        self.close_btn.setToolTip("Close overlay")
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc2626;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #ef4444;
            }
        """)
        self.close_btn.clicked.connect(self.hide)
        header.addWidget(self.close_btn)

        container_layout.addLayout(header)

        # "They asked:" section (compact) with color-blind accessible text labels
        heard_header = QLabel("THEY ASKED: (Question)")
        heard_header.setStyleSheet("color: #a6adc8; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        container_layout.addWidget(heard_header)

        self.heard_label = QLabel("Listening...")
        self.heard_label.setWordWrap(True)
        self.heard_label.setStyleSheet("""
            color: #bac2de;
            font-size: 12px;
            background-color: #313244;
            padding: 8px 10px;
            border-radius: 6px;
        """)
        self.heard_label.setMaximumHeight(55)
        container_layout.addWidget(self.heard_label)

        # "Your answer:" section (prominent, large, readable) with color-blind accessible text labels
        response_header = QLabel("YOUR ANSWER: (AI Response)")
        response_header.setStyleSheet("color: #a6e3a1; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        container_layout.addWidget(response_header)

        # Scrollable response area for longer answers
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: #313244;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #585b70;
                border-radius: 4px;
                min-height: 20px;
            }
        """)

        self.response_label = QLabel("Waiting for question...")
        self.response_label.setWordWrap(True)
        self.response_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._apply_response_style(large=False)

        scroll_area.setWidget(self.response_label)
        container_layout.addWidget(scroll_area, 1)

        # Bottom bar with hint
        bottom_bar = QHBoxLayout()

        hint_label = QLabel("Glance & rephrase naturally - works with any meeting app")
        hint_label.setStyleSheet("color: #6c7086; font-size: 10px; font-style: italic;")
        bottom_bar.addWidget(hint_label)

        bottom_bar.addStretch()

        # Size grip for resizing
        size_grip = QSizeGrip(self)
        size_grip.setStyleSheet("background: transparent;")
        bottom_bar.addWidget(size_grip)

        container_layout.addLayout(bottom_bar)

        # Set normal cursor (prevent busy/loading cursor)
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

        # Position in bottom-right of screen
        self._position_window()

    def _apply_response_style(self, large: bool):
        """Apply styling to response label based on size mode."""
        if large:
            self.response_label.setStyleSheet("""
                QLabel {
                    color: #a6e3a1;
                    font-size: 18px;
                    font-weight: 500;
                    line-height: 1.5;
                    background-color: #313244;
                    padding: 12px 14px;
                    border-radius: 8px;
                    border-left: 3px solid #a6e3a1;
                }
            """)
        else:
            self.response_label.setStyleSheet("""
                QLabel {
                    color: #a6e3a1;
                    font-size: 14px;
                    font-weight: 500;
                    line-height: 1.4;
                    background-color: #313244;
                    padding: 10px 12px;
                    border-radius: 8px;
                    border-left: 3px solid #a6e3a1;
                }
            """)

    def _toggle_size(self):
        """Toggle between normal and large text mode."""
        self._large_mode = not self._large_mode
        self._apply_response_style(self._large_mode)

        if self._large_mode:
            self.size_btn.setText("A- Text")
            self.resize(520, 380)
        else:
            self.size_btn.setText("A+ Text")
            self.resize(OVERLAY_WIDTH, OVERLAY_HEIGHT)

    def _update_listen_btn_style(self):
        """Update listen button style based on state."""
        if self._is_listening:
            self.listen_btn.setText("■ Stop")
            self.listen_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ef4444;
                    color: #ffffff;
                    border: none;
                    border-radius: 4px;
                    font-weight: bold;
                    font-size: 10px;
                }
                QPushButton:hover {
                    background-color: #dc2626;
                }
            """)
        else:
            self.listen_btn.setText("▶ Start")
            self.listen_btn.setStyleSheet("""
                QPushButton {
                    background-color: #22c55e;
                    color: #ffffff;
                    border: none;
                    border-radius: 4px;
                    font-weight: bold;
                    font-size: 10px;
                }
                QPushButton:hover {
                    background-color: #16a34a;
                }
            """)

    def _on_listen_clicked(self):
        """Handle listen button click."""
        self._is_listening = not self._is_listening
        self._update_listen_btn_style()
        self.listen_toggled.emit(self._is_listening)

    def set_listening_state(self, is_listening: bool):
        """Set the listening state from external source."""
        self._is_listening = is_listening
        self._update_listen_btn_style()

    def _connect_signals(self):
        """Connect signals for thread-safe updates."""
        self.update_heard_signal.connect(self._update_heard)
        self.update_response_signal.connect(self._update_response)
        self.append_response_signal.connect(self._append_response)

    def _position_window(self):
        """Position window in bottom-right corner."""
        screen = QApplication.primaryScreen()
        if screen:
            geometry = screen.availableGeometry()
            x = geometry.width() - OVERLAY_WIDTH - 20
            y = geometry.height() - OVERLAY_HEIGHT - 20
            self.move(x, y)

    def _update_heard(self, text: str):
        """Update the 'They asked' label."""
        self._current_heard = text
        # Truncate if too long to keep focus on the answer
        display_text = text
        if len(display_text) > 150:
            display_text = display_text[:147] + "..."
        self.heard_label.setText(display_text)

    def _update_response(self, text: str):
        """Update the response label (full replacement)."""
        self._current_response = text
        self.response_label.setText(text)

    def _append_response(self, text: str):
        """Append to response (for streaming)."""
        self._current_response += text
        self.response_label.setText(self._current_response)

    def set_heard_text(self, text: str):
        """Thread-safe method to update heard text."""
        self.update_heard_signal.emit(text)
        self._current_response = ""
        self.update_response_signal.emit("Thinking...")

    def set_response_text(self, text: str):
        """Thread-safe method to set response text."""
        self.update_response_signal.emit(text)

    def append_response_text(self, text: str):
        """Thread-safe method to append to response (streaming)."""
        self.append_response_signal.emit(text)

    def _force_on_top(self):
        """Force window above all others including meeting apps (cross-platform)."""
        try:
            if IS_WINDOWS:
                # Use Windows API for guaranteed topmost
                import ctypes
                hwnd = int(self.winId())
                HWND_TOPMOST = -1
                SWP_NOMOVE = 0x0002
                SWP_NOSIZE = 0x0001
                SWP_SHOWWINDOW = 0x0040
                ctypes.windll.user32.SetWindowPos(
                    hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                    SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW
                )
            else:
                # Qt approach for macOS and Linux
                self.raise_()
                self.activateWindow()
        except Exception as e:
            print(f"force_on_top error: {e}")

    def showEvent(self, event):
        """When shown, force to top and start keep-alive timer."""
        super().showEvent(event)
        self._force_on_top()
        # Apply screen capture protection if setting is enabled
        if self._settings and self._settings.get("hide_from_screen_capture", False):
            self._setup_screen_capture_protection()
        # Periodically re-raise above other always-on-top windows
        if not hasattr(self, '_top_timer'):
            self._top_timer = QTimer(self)
            self._top_timer.timeout.connect(self._force_on_top)
            self._top_timer.start(3000)  # Every 3 seconds

    def reset(self):
        """Reset to initial state."""
        self.update_heard_signal.emit("Listening...")
        self.update_response_signal.emit("Waiting for question...")
        self._current_response = ""

    def show_usage_warning(self, remaining: int):
        """Show warning when running low on daily responses."""
        if remaining == 0:
            warning = "Daily limit reached!"
        else:
            warning = f"{remaining} responses left today"
        # Could show a toast/notification here
        print(f"Usage warning: {warning}")

    # Dragging support
    def mousePressEvent(self, event):
        """Handle mouse press for dragging."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging."""
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()

    def moveEvent(self, event):
        """Save position when window is moved."""
        super().moveEvent(event)
        self._save_position()

    def resizeEvent(self, event):
        """Save size when window is resized."""
        super().resizeEvent(event)
        self._save_position()

    def _load_position(self):
        """Load saved window position from settings with multi-monitor validation."""
        if not self._settings or not self._settings.get("remember_position", True):
            self._position_window()
            return

        pos = self._settings.get("overlay_position")
        if pos:
            x = pos.get("x", 0)
            y = pos.get("y", 0)
            width = pos.get("width", OVERLAY_WIDTH)
            height = pos.get("height", OVERLAY_HEIGHT)

            # Validate position against all available screens
            if self._validate_position(x, y, width, height):
                self.move(x, y)
                if width and height:
                    self.resize(width, height)
            else:
                # Position is off-screen, reset to default
                self._position_window()
        else:
            self._position_window()

    def _validate_position(self, x: int, y: int, width: int, height: int) -> bool:
        """Validate that the position is visible on at least one monitor.

        Uses QApplication.screens() to detect all monitors and ensures
        the overlay stays visible by clamping to available screen geometry.

        Returns:
            True if position is valid, False if overlay would be off-screen
        """
        screens = QApplication.screens()
        if not screens:
            return False

        # Build combined geometry of all screens
        for screen in screens:
            geometry = screen.availableGeometry()
            # Check if overlay center point is within this screen
            center_x = x + width // 2
            center_y = y + height // 2

            if geometry.contains(center_x, center_y):
                return True

            # Also check if at least 100 pixels of the overlay is visible
            overlay_rect_left = max(x, geometry.left())
            overlay_rect_right = min(x + width, geometry.right())
            overlay_rect_top = max(y, geometry.top())
            overlay_rect_bottom = min(y + height, geometry.bottom())

            visible_width = overlay_rect_right - overlay_rect_left
            visible_height = overlay_rect_bottom - overlay_rect_top

            if visible_width >= 100 and visible_height >= 100:
                return True

        return False

    def _clamp_position_to_screen(self, x: int, y: int) -> tuple:
        """Clamp position to ensure overlay stays visible on available screens.

        Returns:
            Tuple of (clamped_x, clamped_y) that keeps overlay visible
        """
        screens = QApplication.screens()
        if not screens:
            return (x, y)

        width = self.width()
        height = self.height()

        # Find the closest screen to the requested position
        best_screen = screens[0]
        best_distance = float('inf')

        for screen in screens:
            geometry = screen.availableGeometry()
            center_x = geometry.center().x()
            center_y = geometry.center().y()
            distance = ((x - center_x) ** 2 + (y - center_y) ** 2) ** 0.5

            if distance < best_distance:
                best_distance = distance
                best_screen = screen

        # Clamp to the best screen's geometry
        geometry = best_screen.availableGeometry()
        clamped_x = max(geometry.left(), min(x, geometry.right() - width))
        clamped_y = max(geometry.top(), min(y, geometry.bottom() - height))

        return (clamped_x, clamped_y)

    def _setup_screen_capture_protection(self):
        """
        Make overlay invisible during screen sharing/recording.
        Uses Windows SetWindowDisplayAffinity API with WDA_EXCLUDEFROMCAPTURE.
        The overlay remains visible to you but won't appear in screen shares.
        """
        if not IS_WINDOWS:
            return

        # Check if setting is enabled (default: False for visibility)
        hide_from_capture = False
        if self._settings:
            hide_from_capture = self._settings.get("hide_from_screen_capture", False)

        if not hide_from_capture:
            # User disabled this feature - make sure capture is allowed
            self.set_screen_capture_visibility(visible=True)
            return

        try:
            import ctypes

            # WDA_EXCLUDEFROMCAPTURE = 0x00000011 (Windows 10 2004+)
            # This excludes the window from screen capture while keeping it visible locally
            WDA_EXCLUDEFROMCAPTURE = 0x00000011

            hwnd = int(self.winId())
            result = ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)

            if result:
                self._hidden_from_capture = True
                print("Screen capture protection enabled - overlay hidden from screen sharing")
            else:
                # Fallback: try WDA_MONITOR (0x01) for older Windows versions
                WDA_MONITOR = 0x00000001
                result = ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, WDA_MONITOR)
                if result:
                    self._hidden_from_capture = True
                    print("Screen capture protection enabled (legacy mode)")
                else:
                    print("Warning: Could not enable screen capture protection")
        except Exception as e:
            print(f"Screen capture protection setup error: {e}")

    def set_screen_capture_visibility(self, visible: bool):
        """
        Toggle whether overlay is visible during screen sharing.

        Args:
            visible: If True, overlay WILL be visible in screen shares.
                    If False (default), overlay is hidden from screen shares.
        """
        if not IS_WINDOWS:
            return

        try:
            import ctypes

            hwnd = int(self.winId())

            if visible:
                # WDA_NONE = 0 - Allow capture
                result = ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, 0)
            else:
                # WDA_EXCLUDEFROMCAPTURE = 0x11 - Exclude from capture
                result = ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, 0x00000011)

            if result:
                self._hidden_from_capture = not visible
                status = "visible to" if visible else "hidden from"
                print(f"Overlay is now {status} screen sharing")
        except Exception as e:
            print(f"Error toggling screen capture visibility: {e}")

    def _save_position(self):
        """Save current window position to settings."""
        if not self._settings or not self._settings.get("remember_position", True):
            return

        self._settings.set("overlay_position", {
            "x": self.x(),
            "y": self.y(),
            "width": self.width(),
            "height": self.height()
        })

    def _apply_theme(self):
        """Apply the current theme to the overlay."""
        opacity = getattr(self, '_opacity', 0.95)
        opacity_hex = format(int(opacity * 255), '02x')

        if THEMES_AVAILABLE and self._settings:
            theme_id = self._settings.get("theme", "dark_gold")
            theme = THEMES.get(theme_id, THEMES["dark_gold"])
            bg_color = theme["background"]
            border_color = theme["border"]
        else:
            bg_color = "#1e1e2e"
            border_color = "#45475a"

        # Convert hex to rgba for opacity support
        bg_r = int(bg_color[1:3], 16)
        bg_g = int(bg_color[3:5], 16)
        bg_b = int(bg_color[5:7], 16)

        self.container.setStyleSheet(f"""
            #container {{
                background-color: rgba({bg_r}, {bg_g}, {bg_b}, {opacity});
                border: 1px solid {border_color};
                border-radius: 12px;
            }}
        """)

        # Update title color
        if hasattr(self, 'title_label'):
            self._apply_title_style()

    def _apply_title_style(self):
        """Apply theme-aware title styling."""
        if THEMES_AVAILABLE and self._settings and hasattr(self, 'title_label'):
            theme_id = self._settings.get("theme", "dark_gold")
            theme = THEMES.get(theme_id, THEMES["dark_gold"])
            self.title_label.setStyleSheet(f"color: {theme['accent']}; font-weight: bold; font-size: 13px;")
        elif hasattr(self, 'title_label'):
            self.title_label.setStyleSheet("color: #89b4fa; font-weight: bold; font-size: 13px;")

    def set_theme(self, theme_id: str):
        """Change the overlay theme."""
        if self._settings:
            self._settings.set("theme", theme_id)
        self._apply_theme()

    def connect_to_settings_window(self, settings_window):
        """Connect overlay to settings window signals for immediate updates.

        Args:
            settings_window: SettingsWindow instance to connect to
        """
        # Connect theme changes for immediate application
        settings_window.theme_changed.connect(self.set_theme)

        # Connect individual setting changes
        settings_window.setting_changed.connect(self._on_setting_changed)

    def _on_setting_changed(self, key: str, value):
        """Handle individual setting changes from settings window.

        Args:
            key: The setting key that changed
            value: The new value
        """
        if key == "opacity":
            self.set_opacity(value)
        elif key == "always_on_top":
            self._update_always_on_top(value)
        elif key == "hide_from_screen_capture":
            self.set_screen_capture_visibility(not value)

    def _update_always_on_top(self, enabled: bool):
        """Update the always-on-top window flag.

        Args:
            enabled: Whether to enable always-on-top
        """
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if enabled:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()  # Required to apply new window flags

    def set_opacity(self, opacity: float):
        """Set overlay opacity (0.0-1.0 or 0-100)."""
        # Normalize to 0-1 range
        if opacity > 1:
            opacity = opacity / 100
        self._opacity = opacity
        self._apply_theme()
        if self._settings:
            self._settings.set("overlay_opacity", opacity)

    def get_conversation_data(self) -> dict:
        """Get current conversation data for export."""
        return {
            "heard": self._current_heard,
            "response": self._current_response
        }

    def clear_context(self):
        """Clear the current conversation context."""
        self.reset()

    def hideEvent(self, event):
        """Handle hide event - save position."""
        super().hideEvent(event)
        self._save_position()

    def closeEvent(self, event):
        """Handle close event - hide instead of close."""
        event.ignore()
        self.hide()
