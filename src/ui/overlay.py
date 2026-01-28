"""Floating overlay UI optimized for reading while speaking naturally."""

import sys

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QApplication, QSizeGrip,
    QScrollArea
)
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QClipboard, QCursor

from config import OVERLAY_WIDTH, OVERLAY_HEIGHT, OVERLAY_OPACITY, IS_WINDOWS


class OverlayWindow(QWidget):
    """Floating overlay optimized for glancing while speaking."""

    # Signals for thread-safe UI updates
    update_heard_signal = pyqtSignal(str)
    update_response_signal = pyqtSignal(str)
    append_response_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._drag_position: QPoint = QPoint()
        self._current_response = ""
        self._large_mode = False
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Initialize the UI components."""
        # Window flags for floating overlay
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowOpacity(OVERLAY_OPACITY)
        self.setMinimumSize(OVERLAY_WIDTH, OVERLAY_HEIGHT)
        self.resize(OVERLAY_WIDTH, OVERLAY_HEIGHT)

        # Main container with dark theme
        self.container = QFrame(self)
        self.container.setObjectName("container")
        self.container.setStyleSheet("""
            #container {
                background-color: #1e1e2e;
                border: 1px solid #45475a;
                border-radius: 12px;
            }
        """)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.container)

        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(16, 12, 16, 12)
        container_layout.setSpacing(8)

        # Header with title and controls
        header = QHBoxLayout()

        title = QLabel("ReadIn AI")
        title.setStyleSheet("color: #89b4fa; font-weight: bold; font-size: 13px;")
        header.addWidget(title)

        header.addStretch()

        # Font size toggle button
        self.size_btn = QPushButton("A+")
        self.size_btn.setFixedSize(28, 24)
        self.size_btn.setToolTip("Toggle large text mode")
        self.size_btn.setStyleSheet("""
            QPushButton {
                background-color: #45475a;
                color: #cdd6f4;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #585b70;
            }
        """)
        self.size_btn.clicked.connect(self._toggle_size)
        header.addWidget(self.size_btn)

        # Minimize button
        min_btn = QPushButton("-")
        min_btn.setFixedSize(24, 24)
        min_btn.setStyleSheet("""
            QPushButton {
                background-color: #45475a;
                color: #cdd6f4;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #585b70;
            }
        """)
        min_btn.clicked.connect(self.showMinimized)
        header.addWidget(min_btn)

        # Close button
        close_btn = QPushButton("x")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #f38ba8;
                color: #1e1e2e;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #eba0ac;
            }
        """)
        close_btn.clicked.connect(self.hide)
        header.addWidget(close_btn)

        container_layout.addLayout(header)

        # "They asked:" section (compact)
        heard_header = QLabel("THEY ASKED:")
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

        # "Your answer:" section (prominent, large, readable)
        response_header = QLabel("YOUR ANSWER:")
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
            self.size_btn.setText("A-")
            self.resize(520, 380)
        else:
            self.size_btn.setText("A+")
            self.resize(OVERLAY_WIDTH, OVERLAY_HEIGHT)

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
        # Truncate if too long to keep focus on the answer
        if len(text) > 150:
            text = text[:147] + "..."
        self.heard_label.setText(text)

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
