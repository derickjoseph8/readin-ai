"""Meeting Type Selection Dialog."""

from typing import Optional, Tuple
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QRadioButton, QButtonGroup, QLineEdit, QFrame, QWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from meeting_session import MeetingSession


class MeetingTypeDialog(QDialog):
    """Dialog for selecting meeting type before starting a session."""

    def __init__(self, parent=None, detected_app: Optional[str] = None):
        super().__init__(parent)
        self.detected_app = detected_app
        self._selected_type = "general"
        self._title = None
        self.setup_ui()

    def setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Start Meeting")
        self.setFixedWidth(400)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)

        # Dark theme
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1a1a;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
            }
            QRadioButton {
                color: #ffffff;
                padding: 8px;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
            }
            QRadioButton::indicator:checked {
                background-color: #fbbf24;
                border: 2px solid #fbbf24;
                border-radius: 9px;
            }
            QRadioButton::indicator:unchecked {
                background-color: #2d2d2d;
                border: 2px solid #4a4a4a;
                border-radius: 9px;
            }
            QLineEdit {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #4a4a4a;
                border-radius: 6px;
                padding: 8px 12px;
            }
            QLineEdit:focus {
                border-color: #fbbf24;
            }
            QPushButton {
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton#startBtn {
                background-color: #fbbf24;
                color: #1a1a1a;
                border: none;
            }
            QPushButton#startBtn:hover {
                background-color: #f59e0b;
            }
            QPushButton#cancelBtn {
                background-color: transparent;
                color: #999999;
                border: 1px solid #4a4a4a;
            }
            QPushButton#cancelBtn:hover {
                background-color: #2d2d2d;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Header
        header = QLabel("What type of meeting is this?")
        header.setFont(QFont("", 14, QFont.Weight.Bold))
        layout.addWidget(header)

        # Detected app info
        if self.detected_app:
            app_label = QLabel(f"Detected: {self.detected_app}")
            app_label.setStyleSheet("color: #fbbf24; font-size: 12px;")
            layout.addWidget(app_label)

        # Meeting types
        self.button_group = QButtonGroup(self)
        types_layout = QVBoxLayout()
        types_layout.setSpacing(4)

        for type_id, type_name in MeetingSession.MEETING_TYPES:
            radio = QRadioButton(type_name)
            radio.setProperty("type_id", type_id)
            self.button_group.addButton(radio)
            types_layout.addWidget(radio)

            if type_id == "general":
                radio.setChecked(True)

        layout.addLayout(types_layout)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #4a4a4a;")
        layout.addWidget(separator)

        # Meeting title (optional)
        title_label = QLabel("Meeting title (optional)")
        title_label.setStyleSheet("color: #999999; font-size: 12px;")
        layout.addWidget(title_label)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("e.g., Interview with Acme Corp")
        layout.addWidget(self.title_input)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        start_btn = QPushButton("Start Meeting")
        start_btn.setObjectName("startBtn")
        start_btn.clicked.connect(self.accept)
        btn_layout.addWidget(start_btn)

        layout.addLayout(btn_layout)

    def get_selection(self) -> Tuple[str, Optional[str]]:
        """Get the selected meeting type and title.

        Returns:
            Tuple of (meeting_type, title)
        """
        selected = self.button_group.checkedButton()
        if selected:
            self._selected_type = selected.property("type_id")

        title = self.title_input.text().strip()
        self._title = title if title else None

        return (self._selected_type, self._title)

    @staticmethod
    def get_meeting_type(parent=None, detected_app: Optional[str] = None) -> Optional[Tuple[str, Optional[str]]]:
        """Show dialog and return selected meeting type.

        Args:
            parent: Parent widget
            detected_app: Detected meeting application name

        Returns:
            Tuple of (meeting_type, title) or None if cancelled
        """
        dialog = MeetingTypeDialog(parent, detected_app)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.get_selection()
        return None


class QuickMeetingBar(QWidget):
    """Compact meeting type selector bar for overlay."""

    def __init__(self, parent=None, on_type_selected=None):
        super().__init__(parent)
        self.on_type_selected = on_type_selected
        self._current_type = "general"
        self.setup_ui()

    def setup_ui(self):
        """Set up the compact bar UI."""
        self.setStyleSheet("""
            QWidget {
                background-color: #2d2d2d;
                border-radius: 6px;
            }
            QPushButton {
                background-color: transparent;
                color: #999999;
                border: none;
                padding: 6px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                color: #ffffff;
                background-color: #3d3d3d;
            }
            QPushButton:checked, QPushButton[selected="true"] {
                color: #fbbf24;
                background-color: #3d3d3d;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setSpacing(2)
        layout.setContentsMargins(4, 4, 4, 4)

        # Quick type buttons (abbreviated)
        quick_types = [
            ("general", "General"),
            ("interview", "Interview"),
            ("manager", "1:1"),
            ("client", "Client"),
            ("sales", "Sales"),
        ]

        self.type_buttons = {}
        for type_id, label in quick_types:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setProperty("type_id", type_id)
            btn.clicked.connect(lambda checked, t=type_id: self._on_type_clicked(t))
            layout.addWidget(btn)
            self.type_buttons[type_id] = btn

            if type_id == "general":
                btn.setChecked(True)

    def _on_type_clicked(self, type_id: str):
        """Handle type button click."""
        self._current_type = type_id

        # Update button states
        for tid, btn in self.type_buttons.items():
            btn.setChecked(tid == type_id)

        if self.on_type_selected:
            self.on_type_selected(type_id)

    def get_current_type(self) -> str:
        """Get currently selected meeting type."""
        return self._current_type

    def set_current_type(self, type_id: str):
        """Set the current meeting type."""
        self._current_type = type_id
        for tid, btn in self.type_buttons.items():
            btn.setChecked(tid == type_id)
