"""
Sync Status Indicator Widget for ReadIn AI.

Displays the current synchronization status in the UI:
- Online/Offline indicator
- Pending sync count
- Last sync time
- Sync progress
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QToolTip, QFrame, QProgressBar, QMenu
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPoint
from PyQt6.QtGui import QCursor, QAction

from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class SyncStatusIndicator(QWidget):
    """
    Compact sync status indicator widget.

    Shows connectivity status, pending syncs, and allows manual sync trigger.
    """

    sync_requested = pyqtSignal()  # Emitted when user requests manual sync
    settings_requested = pyqtSignal()  # Emitted when user wants sync settings

    # Status colors
    COLOR_ONLINE = "#22c55e"      # Green
    COLOR_OFFLINE = "#ef4444"     # Red
    COLOR_SYNCING = "#f59e0b"     # Amber
    COLOR_PENDING = "#3b82f6"     # Blue
    COLOR_UNKNOWN = "#6b7280"     # Gray

    def __init__(self, parent=None):
        super().__init__(parent)

        self._is_online = True
        self._is_syncing = False
        self._pending_count = 0
        self._last_sync: Optional[datetime] = None
        self._sync_progress = 0
        self._error_message: Optional[str] = None

        self._setup_ui()
        self._setup_tooltip_timer()

    def _setup_ui(self):
        """Initialize the UI components."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)

        # Status indicator (colored dot)
        self.status_dot = QLabel()
        self.status_dot.setFixedSize(10, 10)
        self._update_status_dot()
        layout.addWidget(self.status_dot)

        # Status text
        self.status_label = QLabel("Online")
        self.status_label.setStyleSheet("font-size: 11px; color: #a6adc8;")
        layout.addWidget(self.status_label)

        # Pending count badge (only shown when pending > 0)
        self.pending_badge = QLabel("")
        self.pending_badge.setStyleSheet(f"""
            background-color: {self.COLOR_PENDING};
            color: white;
            font-size: 9px;
            font-weight: bold;
            padding: 1px 4px;
            border-radius: 6px;
            min-width: 12px;
        """)
        self.pending_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pending_badge.hide()
        layout.addWidget(self.pending_badge)

        # Sync button (refresh icon)
        self.sync_btn = QPushButton()
        self.sync_btn.setFixedSize(24, 24)
        self.sync_btn.setToolTip("Sync now")
        self.sync_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #45475a;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #313244;
                border-color: #585b70;
            }
            QPushButton:pressed {
                background-color: #45475a;
            }
            QPushButton:disabled {
                opacity: 0.5;
            }
        """)
        self.sync_btn.setText("\u21bb")  # Clockwise arrow
        self.sync_btn.clicked.connect(self._on_sync_clicked)
        layout.addWidget(self.sync_btn)

        # Context menu
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        # Click handler for status details
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def _setup_tooltip_timer(self):
        """Setup timer for tooltip updates."""
        self._tooltip_timer = QTimer(self)
        self._tooltip_timer.timeout.connect(self._update_tooltip)
        self._tooltip_timer.start(30000)  # Update every 30 seconds

    def _update_status_dot(self):
        """Update the status dot color."""
        if self._is_syncing:
            color = self.COLOR_SYNCING
        elif not self._is_online:
            color = self.COLOR_OFFLINE
        elif self._pending_count > 0:
            color = self.COLOR_PENDING
        else:
            color = self.COLOR_ONLINE

        self.status_dot.setStyleSheet(f"""
            background-color: {color};
            border-radius: 5px;
        """)

    def _update_tooltip(self):
        """Update the tooltip with current status details."""
        lines = []

        # Connectivity status
        status = "Online" if self._is_online else "Offline"
        lines.append(f"Status: {status}")

        # Sync status
        if self._is_syncing:
            lines.append(f"Syncing... ({self._sync_progress}%)")
        elif self._pending_count > 0:
            lines.append(f"Pending: {self._pending_count} item{'s' if self._pending_count != 1 else ''}")

        # Last sync time
        if self._last_sync:
            ago = self._format_time_ago(self._last_sync)
            lines.append(f"Last sync: {ago}")
        else:
            lines.append("Last sync: Never")

        # Error message if any
        if self._error_message and not self._is_online:
            lines.append(f"Error: {self._error_message}")

        self.setToolTip("\n".join(lines))

    def _format_time_ago(self, dt: datetime) -> str:
        """Format datetime as relative time."""
        now = datetime.now()
        diff = now - dt

        seconds = diff.total_seconds()
        if seconds < 60:
            return "Just now"
        elif seconds < 3600:
            mins = int(seconds / 60)
            return f"{mins} min{'s' if mins != 1 else ''} ago"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        else:
            days = int(seconds / 86400)
            return f"{days} day{'s' if days != 1 else ''} ago"

    def _on_sync_clicked(self):
        """Handle sync button click."""
        if not self._is_syncing:
            self.sync_requested.emit()

    def _show_context_menu(self, pos: QPoint):
        """Show context menu."""
        menu = QMenu(self)

        # Sync now action
        sync_action = QAction("Sync Now", self)
        sync_action.setEnabled(not self._is_syncing)
        sync_action.triggered.connect(self.sync_requested.emit)
        menu.addAction(sync_action)

        menu.addSeparator()

        # View pending items (future feature)
        pending_action = QAction(f"View Pending ({self._pending_count})", self)
        pending_action.setEnabled(self._pending_count > 0)
        menu.addAction(pending_action)

        menu.addSeparator()

        # Sync settings
        settings_action = QAction("Sync Settings...", self)
        settings_action.triggered.connect(self.settings_requested.emit)
        menu.addAction(settings_action)

        menu.exec(self.mapToGlobal(pos))

    # ==================== Public API ====================

    def set_online(self, is_online: bool):
        """Update online/offline status."""
        if self._is_online != is_online:
            self._is_online = is_online
            self.status_label.setText("Online" if is_online else "Offline")
            self._update_status_dot()
            self._update_tooltip()

            # Animate status change
            if not is_online:
                self.status_label.setStyleSheet("font-size: 11px; color: #ef4444;")
            else:
                self.status_label.setStyleSheet("font-size: 11px; color: #a6e3a1;")
                # Fade back to neutral after 2 seconds
                QTimer.singleShot(2000, lambda: self.status_label.setStyleSheet(
                    "font-size: 11px; color: #a6adc8;"
                ))

    def set_syncing(self, is_syncing: bool, progress: int = 0):
        """Update syncing status."""
        self._is_syncing = is_syncing
        self._sync_progress = progress

        if is_syncing:
            self.status_label.setText(f"Syncing... {progress}%")
            self.sync_btn.setEnabled(False)
            # Animate sync button
            self.sync_btn.setStyleSheet("""
                QPushButton {
                    background-color: #313244;
                    border: 1px solid #f59e0b;
                    border-radius: 4px;
                    font-size: 12px;
                    color: #f59e0b;
                }
            """)
        else:
            self.status_label.setText("Online" if self._is_online else "Offline")
            self.sync_btn.setEnabled(True)
            self.sync_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: 1px solid #45475a;
                    border-radius: 4px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #313244;
                    border-color: #585b70;
                }
            """)

        self._update_status_dot()
        self._update_tooltip()

    def set_pending_count(self, count: int):
        """Update pending sync count."""
        self._pending_count = count

        if count > 0:
            self.pending_badge.setText(str(count) if count < 100 else "99+")
            self.pending_badge.show()
        else:
            self.pending_badge.hide()

        self._update_status_dot()
        self._update_tooltip()

    def set_last_sync(self, dt: datetime):
        """Update last sync time."""
        self._last_sync = dt
        self._update_tooltip()

    def set_error(self, error: Optional[str]):
        """Set error message."""
        self._error_message = error
        self._update_tooltip()

    def update_from_status(self, status: dict):
        """Update all fields from a status dictionary.

        Args:
            status: Dict from SyncManager.get_status()
        """
        self.set_online(status.get("is_online", False))
        self.set_syncing(status.get("is_syncing", False))
        self.set_pending_count(status.get("pending_items", 0))
        self.set_error(status.get("last_error"))

        last_sync_str = status.get("last_sync")
        if last_sync_str:
            try:
                last_sync = datetime.fromisoformat(last_sync_str)
                self.set_last_sync(last_sync)
            except (ValueError, TypeError):
                pass


class SyncStatusBar(QFrame):
    """
    Full sync status bar with progress and details.

    Use this for more prominent sync status display.
    """

    sync_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Initialize the UI."""
        self.setStyleSheet("""
            QFrame {
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 6px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(6)

        # Top row: status indicator and text
        top_row = QHBoxLayout()

        self.indicator = SyncStatusIndicator()
        self.indicator.sync_requested.connect(self.sync_requested.emit)
        top_row.addWidget(self.indicator)

        top_row.addStretch()

        layout.addLayout(top_row)

        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #313244;
                border: none;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: #89b4fa;
                border-radius: 2px;
            }
        """)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        # Details label
        self.details_label = QLabel("")
        self.details_label.setStyleSheet("font-size: 10px; color: #6c7086;")
        self.details_label.hide()
        layout.addWidget(self.details_label)

    def set_syncing(self, is_syncing: bool, progress: int = 0, message: str = ""):
        """Update syncing status with progress."""
        self.indicator.set_syncing(is_syncing, progress)

        if is_syncing:
            self.progress_bar.setValue(progress)
            self.progress_bar.show()
            if message:
                self.details_label.setText(message)
                self.details_label.show()
        else:
            self.progress_bar.hide()
            self.details_label.hide()

    def update_from_status(self, status: dict):
        """Update from status dictionary."""
        self.indicator.update_from_status(status)

        progress_data = status.get("progress", {})
        if status.get("is_syncing"):
            total = progress_data.get("total", 0)
            synced = progress_data.get("synced", 0)
            if total > 0:
                progress = int((synced / total) * 100)
                self.set_syncing(True, progress, f"Syncing {synced}/{total} items...")
        else:
            self.set_syncing(False)
