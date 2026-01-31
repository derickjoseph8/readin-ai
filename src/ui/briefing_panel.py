"""Pre-Meeting Briefing Panel."""

from typing import Optional, Dict, Any, List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QTextEdit, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


class BriefingPanel(QWidget):
    """Panel displaying pre-meeting briefing information."""

    dismissed = pyqtSignal()
    start_meeting = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._briefing_data: Optional[Dict] = None
        self.setup_ui()

    def setup_ui(self):
        """Set up the panel UI."""
        self.setStyleSheet("""
            QWidget {
                background-color: #1a1a1a;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QFrame#section {
                background-color: #2d2d2d;
                border-radius: 8px;
                padding: 12px;
            }
            QLabel#sectionTitle {
                color: #fbbf24;
                font-weight: bold;
                font-size: 13px;
            }
            QLabel#bullet {
                color: #999999;
            }
            QPushButton#startBtn {
                background-color: #fbbf24;
                color: #1a1a1a;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton#startBtn:hover {
                background-color: #f59e0b;
            }
            QPushButton#dismissBtn {
                background-color: transparent;
                color: #999999;
                border: 1px solid #4a4a4a;
                padding: 12px 24px;
                border-radius: 6px;
            }
            QPushButton#dismissBtn:hover {
                background-color: #2d2d2d;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        # Header
        header_layout = QHBoxLayout()
        header = QLabel("Pre-Meeting Briefing")
        header.setFont(QFont("", 16, QFont.Weight.Bold))
        header_layout.addWidget(header)
        header_layout.addStretch()

        # Close button
        close_btn = QPushButton("×")
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #999999;
                border: none;
                font-size: 20px;
            }
            QPushButton:hover {
                color: #ffffff;
            }
        """)
        close_btn.clicked.connect(self.dismissed.emit)
        header_layout.addWidget(close_btn)

        layout.addLayout(header_layout)

        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setSpacing(12)
        self.content_layout.setContentsMargins(0, 0, 0, 0)

        scroll.setWidget(self.content_widget)
        layout.addWidget(scroll, 1)

        # Loading placeholder
        self.loading_label = QLabel("Generating briefing...")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.setStyleSheet("color: #999999; padding: 40px;")
        self.content_layout.addWidget(self.loading_label)

        # Action buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        dismiss_btn = QPushButton("Dismiss")
        dismiss_btn.setObjectName("dismissBtn")
        dismiss_btn.clicked.connect(self.dismissed.emit)
        btn_layout.addWidget(dismiss_btn)

        start_btn = QPushButton("Start Meeting")
        start_btn.setObjectName("startBtn")
        start_btn.clicked.connect(self.start_meeting.emit)
        btn_layout.addWidget(start_btn)

        layout.addLayout(btn_layout)

    def set_briefing(self, briefing: Dict[str, Any]):
        """Set briefing data and update display."""
        self._briefing_data = briefing

        # Clear existing content
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not briefing:
            error_label = QLabel("Could not generate briefing")
            error_label.setStyleSheet("color: #ef4444; padding: 20px;")
            self.content_layout.addWidget(error_label)
            return

        # Summary section
        if briefing.get("summary"):
            self._add_section("Summary", [briefing["summary"]])

        # Participant insights
        participants = briefing.get("participant_insights", [])
        if participants:
            participant_items = []
            for p in participants:
                name = p.get("name", "Unknown")
                insight = p.get("key_insight", "")
                topics = p.get("suggested_topics", [])

                text = f"<b>{name}</b>: {insight}"
                if topics:
                    text += f"<br><span style='color: #999999; font-size: 11px;'>Topics: {', '.join(topics[:3])}</span>"
                participant_items.append(text)

            self._add_section("Participants", participant_items, is_html=True)

        # Talking points
        talking_points = briefing.get("talking_points", [])
        if talking_points:
            self._add_section("Talking Points", talking_points)

        # Follow-up items
        follow_ups = briefing.get("follow_up_items", [])
        if follow_ups:
            self._add_section("Follow Up On", follow_ups)

        # Questions to ask
        questions = briefing.get("questions_to_ask", [])
        if questions:
            self._add_section("Questions to Consider", questions)

        # Topics to avoid
        avoid = briefing.get("topics_to_avoid", [])
        if avoid:
            self._add_section("Topics to Avoid", avoid, warning=True)

        # Preparation tips
        tips = briefing.get("preparation_tips", [])
        if tips:
            self._add_section("Preparation Tips", tips)

        # Add stretch at end
        self.content_layout.addStretch()

    def _add_section(self, title: str, items: List[str], is_html: bool = False, warning: bool = False):
        """Add a section to the briefing panel."""
        section = QFrame()
        section.setObjectName("section")
        section_layout = QVBoxLayout(section)
        section_layout.setSpacing(8)
        section_layout.setContentsMargins(12, 12, 12, 12)

        # Title
        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")
        if warning:
            title_label.setStyleSheet("color: #f59e0b; font-weight: bold;")
        section_layout.addWidget(title_label)

        # Items
        for item in items:
            item_layout = QHBoxLayout()
            item_layout.setSpacing(8)

            bullet = QLabel("•")
            bullet.setObjectName("bullet")
            bullet.setFixedWidth(12)
            bullet.setAlignment(Qt.AlignmentFlag.AlignTop)
            item_layout.addWidget(bullet)

            text_label = QLabel(item)
            text_label.setWordWrap(True)
            text_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            if is_html:
                text_label.setTextFormat(Qt.TextFormat.RichText)
            item_layout.addWidget(text_label, 1)

            section_layout.addLayout(item_layout)

        self.content_layout.addWidget(section)

    def show_loading(self):
        """Show loading state."""
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.loading_label = QLabel("Generating briefing...")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.setStyleSheet("color: #999999; padding: 40px;")
        self.content_layout.addWidget(self.loading_label)


class SummaryPanel(QWidget):
    """Panel displaying post-meeting summary."""

    dismissed = pyqtSignal()
    export_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._summary_data: Optional[Dict] = None
        self.setup_ui()

    def setup_ui(self):
        """Set up the panel UI."""
        self.setStyleSheet("""
            QWidget {
                background-color: #1a1a1a;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QFrame#section {
                background-color: #2d2d2d;
                border-radius: 8px;
            }
            QLabel#sectionTitle {
                color: #10b981;
                font-weight: bold;
            }
            QTextEdit {
                background-color: #2d2d2d;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 12px;
            }
            QPushButton#exportBtn {
                background-color: #10b981;
                color: #ffffff;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton#exportBtn:hover {
                background-color: #059669;
            }
            QPushButton#dismissBtn {
                background-color: transparent;
                color: #999999;
                border: 1px solid #4a4a4a;
                padding: 10px 20px;
                border-radius: 6px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        # Header
        header_layout = QHBoxLayout()
        header = QLabel("Meeting Summary")
        header.setFont(QFont("", 16, QFont.Weight.Bold))
        header_layout.addWidget(header)
        header_layout.addStretch()

        close_btn = QPushButton("×")
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #999999;
                border: none;
                font-size: 20px;
            }
            QPushButton:hover { color: #ffffff; }
        """)
        close_btn.clicked.connect(self.dismissed.emit)
        header_layout.addWidget(close_btn)
        layout.addLayout(header_layout)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setSpacing(12)
        self.content_layout.setContentsMargins(0, 0, 0, 0)

        scroll.setWidget(self.content_widget)
        layout.addWidget(scroll, 1)

        # Buttons
        btn_layout = QHBoxLayout()
        dismiss_btn = QPushButton("Dismiss")
        dismiss_btn.setObjectName("dismissBtn")
        dismiss_btn.clicked.connect(self.dismissed.emit)
        btn_layout.addWidget(dismiss_btn)

        export_btn = QPushButton("Export Summary")
        export_btn.setObjectName("exportBtn")
        export_btn.clicked.connect(self.export_clicked.emit)
        btn_layout.addWidget(export_btn)

        layout.addLayout(btn_layout)

    def set_summary(self, summary: Dict[str, Any]):
        """Set summary data and update display."""
        self._summary_data = summary

        # Clear existing
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not summary:
            error = QLabel("No summary available")
            error.setStyleSheet("color: #999999; padding: 20px;")
            self.content_layout.addWidget(error)
            return

        # Summary text
        if summary.get("summary_text"):
            text_edit = QTextEdit()
            text_edit.setReadOnly(True)
            text_edit.setPlainText(summary["summary_text"])
            text_edit.setMaximumHeight(150)
            self.content_layout.addWidget(text_edit)

        # Key points
        key_points = summary.get("key_points", [])
        if key_points:
            self._add_list_section("Key Points", key_points, "#10b981")

        # Action items
        action_items = summary.get("action_items", [])
        if action_items:
            items = []
            for a in action_items:
                if isinstance(a, dict):
                    text = f"{a.get('assignee', 'Someone')}: {a.get('description', '')}"
                    if a.get('due_date'):
                        text += f" (Due: {a['due_date']})"
                else:
                    text = str(a)
                items.append(text)
            self._add_list_section("Action Items", items, "#3b82f6")

        # Commitments
        commitments = summary.get("commitments", [])
        if commitments:
            items = []
            for c in commitments:
                if isinstance(c, dict):
                    text = c.get('description', '')
                    if c.get('due_date'):
                        text += f" (Due: {c['due_date']})"
                else:
                    text = str(c)
                items.append(text)
            self._add_list_section("Your Commitments", items, "#f59e0b")

        self.content_layout.addStretch()

    def _add_list_section(self, title: str, items: List[str], color: str):
        """Add a list section."""
        section = QFrame()
        section.setObjectName("section")
        section_layout = QVBoxLayout(section)
        section_layout.setContentsMargins(12, 12, 12, 12)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {color}; font-weight: bold;")
        section_layout.addWidget(title_label)

        for item in items:
            item_label = QLabel(f"• {item}")
            item_label.setWordWrap(True)
            section_layout.addWidget(item_label)

        self.content_layout.addWidget(section)
