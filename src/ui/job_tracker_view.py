"""Job Application Tracker View."""

from typing import Optional, Dict, Any, List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QLineEdit, QComboBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QDialog, QFormLayout,
    QTextEdit, QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


class AddJobDialog(QDialog):
    """Dialog for adding a new job application."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Add Job Application")
        self.setFixedWidth(400)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)

        self.setStyleSheet("""
            QDialog {
                background-color: #1a1a1a;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
            }
            QLineEdit, QTextEdit, QComboBox {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #4a4a4a;
                border-radius: 6px;
                padding: 8px;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
                border-color: #fbbf24;
            }
            QPushButton {
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton#saveBtn {
                background-color: #fbbf24;
                color: #1a1a1a;
                border: none;
            }
            QPushButton#saveBtn:hover {
                background-color: #f59e0b;
            }
            QPushButton#cancelBtn {
                background-color: transparent;
                color: #999999;
                border: 1px solid #4a4a4a;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Header
        header = QLabel("Add Job Application")
        header.setFont(QFont("", 14, QFont.Weight.Bold))
        layout.addWidget(header)

        # Form
        form = QFormLayout()
        form.setSpacing(12)

        self.company_input = QLineEdit()
        self.company_input.setPlaceholderText("e.g., Acme Corporation")
        form.addRow("Company:", self.company_input)

        self.position_input = QLineEdit()
        self.position_input.setPlaceholderText("e.g., Senior Software Engineer")
        form.addRow("Position:", self.position_input)

        self.status_combo = QComboBox()
        self.status_combo.addItems([
            "Applied",
            "Phone Screen",
            "Technical Interview",
            "On-site Interview",
            "Offer",
            "Rejected",
            "Withdrawn"
        ])
        form.addRow("Status:", self.status_combo)

        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Any notes about this application...")
        self.notes_input.setMaximumHeight(100)
        form.addRow("Notes:", self.notes_input)

        layout.addLayout(form)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save Application")
        save_btn.setObjectName("saveBtn")
        save_btn.clicked.connect(self._validate_and_accept)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _validate_and_accept(self):
        """Validate inputs and accept dialog."""
        if not self.company_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Company name is required.")
            return
        if not self.position_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Position is required.")
            return
        self.accept()

    def get_data(self) -> Dict[str, Any]:
        """Get the form data."""
        return {
            "company": self.company_input.text().strip(),
            "position": self.position_input.text().strip(),
            "status": self.status_combo.currentText().lower().replace(" ", "_"),
            "notes": self.notes_input.toPlainText().strip()
        }


class JobTrackerView(QWidget):
    """Widget for tracking job applications and interviews."""

    application_selected = pyqtSignal(dict)
    refresh_requested = pyqtSignal()

    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self.api = api_client
        self._applications: List[Dict] = []
        self.setup_ui()

    def setup_ui(self):
        """Set up the view UI."""
        self.setStyleSheet("""
            QWidget {
                background-color: #1a1a1a;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
            }
            QTableWidget {
                background-color: #2d2d2d;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                gridline-color: #3d3d3d;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QTableWidget::item:selected {
                background-color: #fbbf24;
                color: #1a1a1a;
            }
            QHeaderView::section {
                background-color: #3d3d3d;
                color: #ffffff;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
            QPushButton {
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton#addBtn {
                background-color: #fbbf24;
                color: #1a1a1a;
                border: none;
            }
            QPushButton#addBtn:hover {
                background-color: #f59e0b;
            }
            QPushButton#refreshBtn {
                background-color: transparent;
                color: #999999;
                border: 1px solid #4a4a4a;
            }
            QPushButton#refreshBtn:hover {
                background-color: #2d2d2d;
            }
            QFrame#statsFrame {
                background-color: #2d2d2d;
                border-radius: 8px;
                padding: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        # Header
        header_layout = QHBoxLayout()

        header = QLabel("Job Applications")
        header.setFont(QFont("", 18, QFont.Weight.Bold))
        header_layout.addWidget(header)

        header_layout.addStretch()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setObjectName("refreshBtn")
        refresh_btn.clicked.connect(self._refresh_applications)
        header_layout.addWidget(refresh_btn)

        add_btn = QPushButton("+ Add Application")
        add_btn.setObjectName("addBtn")
        add_btn.clicked.connect(self._show_add_dialog)
        header_layout.addWidget(add_btn)

        layout.addLayout(header_layout)

        # Stats row
        self.stats_frame = QFrame()
        self.stats_frame.setObjectName("statsFrame")
        stats_layout = QHBoxLayout(self.stats_frame)
        stats_layout.setSpacing(24)

        self.total_label = QLabel("Total: 0")
        self.total_label.setStyleSheet("font-size: 14px;")
        stats_layout.addWidget(self.total_label)

        self.active_label = QLabel("Active: 0")
        self.active_label.setStyleSheet("color: #10b981; font-size: 14px;")
        stats_layout.addWidget(self.active_label)

        self.interviews_label = QLabel("Interviews: 0")
        self.interviews_label.setStyleSheet("color: #3b82f6; font-size: 14px;")
        stats_layout.addWidget(self.interviews_label)

        self.offers_label = QLabel("Offers: 0")
        self.offers_label.setStyleSheet("color: #fbbf24; font-size: 14px;")
        stats_layout.addWidget(self.offers_label)

        stats_layout.addStretch()

        layout.addWidget(self.stats_frame)

        # Applications table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Company", "Position", "Status", "Interviews", "Last Updated"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.doubleClicked.connect(self._on_row_double_clicked)
        self.table.verticalHeader().setVisible(False)

        layout.addWidget(self.table, 1)

        # Empty state
        self.empty_label = QLabel("No job applications yet.\nClick '+ Add Application' to get started.")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: #999999; font-size: 14px; padding: 40px;")
        layout.addWidget(self.empty_label)

        # Initially hide table, show empty state
        self.table.hide()

    def _refresh_applications(self):
        """Refresh applications from API."""
        if not self.api.is_logged_in():
            return

        result = self.api.get_job_applications()
        if "error" not in result:
            self._applications = result.get("applications", [])
            self._update_display()

        self.refresh_requested.emit()

    def _update_display(self):
        """Update the display with current applications."""
        if not self._applications:
            self.table.hide()
            self.empty_label.show()
            self._update_stats()
            return

        self.empty_label.hide()
        self.table.show()

        self.table.setRowCount(len(self._applications))
        for row, app in enumerate(self._applications):
            self.table.setItem(row, 0, QTableWidgetItem(app.get("company", "")))
            self.table.setItem(row, 1, QTableWidgetItem(app.get("position", "")))

            status = app.get("status", "applied").replace("_", " ").title()
            status_item = QTableWidgetItem(status)
            self._style_status_item(status_item, app.get("status", ""))
            self.table.setItem(row, 2, status_item)

            interviews = app.get("interview_count", 0)
            self.table.setItem(row, 3, QTableWidgetItem(str(interviews)))

            updated = app.get("updated_at", "")
            if updated:
                # Format date nicely
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                    updated = dt.strftime("%b %d, %Y")
                except Exception:
                    pass
            self.table.setItem(row, 4, QTableWidgetItem(updated))

        self._update_stats()

    def _style_status_item(self, item: QTableWidgetItem, status: str):
        """Style a status table item based on status."""
        colors = {
            "applied": "#999999",
            "phone_screen": "#3b82f6",
            "technical_interview": "#8b5cf6",
            "on_site_interview": "#ec4899",
            "offer": "#10b981",
            "rejected": "#ef4444",
            "withdrawn": "#6b7280"
        }
        color = colors.get(status, "#999999")
        item.setForeground(Qt.GlobalColor.white)

    def _update_stats(self):
        """Update stats display."""
        total = len(self._applications)
        active = sum(1 for a in self._applications if a.get("status") not in ["rejected", "withdrawn", "offer"])
        interviews = sum(a.get("interview_count", 0) for a in self._applications)
        offers = sum(1 for a in self._applications if a.get("status") == "offer")

        self.total_label.setText(f"Total: {total}")
        self.active_label.setText(f"Active: {active}")
        self.interviews_label.setText(f"Interviews: {interviews}")
        self.offers_label.setText(f"Offers: {offers}")

    def _show_add_dialog(self):
        """Show dialog to add new application."""
        dialog = AddJobDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            self._create_application(data)

    def _create_application(self, data: Dict):
        """Create a new job application."""
        if not self.api.is_logged_in():
            QMessageBox.warning(self, "Error", "You must be logged in to add applications.")
            return

        result = self.api.create_job_application(
            company=data["company"],
            position=data["position"],
            status=data.get("status", "applied"),
            notes=data.get("notes")
        )

        if "error" in result:
            QMessageBox.warning(self, "Error", f"Failed to create application: {result['error']}")
        else:
            self._refresh_applications()

    def _on_row_double_clicked(self, index):
        """Handle row double-click to view details."""
        row = index.row()
        if row < len(self._applications):
            app = self._applications[row]
            self.application_selected.emit(app)

    def load_applications(self):
        """Load applications on view show."""
        self._refresh_applications()


class InterviewDetailsPanel(QWidget):
    """Panel showing interview details and improvement suggestions."""

    dismissed = pyqtSignal()

    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self.api = api_client
        self._application: Optional[Dict] = None
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
            QFrame#section {
                background-color: #2d2d2d;
                border-radius: 8px;
                padding: 12px;
            }
            QLabel#sectionTitle {
                color: #fbbf24;
                font-weight: bold;
            }
            QPushButton#closeBtn {
                background-color: transparent;
                color: #999999;
                border: none;
                font-size: 20px;
            }
            QPushButton#closeBtn:hover {
                color: #ffffff;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        # Header
        header_layout = QHBoxLayout()
        self.title_label = QLabel("Interview Details")
        self.title_label.setFont(QFont("", 16, QFont.Weight.Bold))
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()

        close_btn = QPushButton("x")
        close_btn.setObjectName("closeBtn")
        close_btn.setFixedSize(30, 30)
        close_btn.clicked.connect(self.dismissed.emit)
        header_layout.addWidget(close_btn)

        layout.addLayout(header_layout)

        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setSpacing(12)
        self.content_layout.setContentsMargins(0, 0, 0, 0)

        scroll.setWidget(self.content_widget)
        layout.addWidget(scroll, 1)

    def set_application(self, application: Dict):
        """Set the application to display."""
        self._application = application

        # Clear existing content
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not application:
            return

        # Title
        self.title_label.setText(f"{application.get('company', '')} - {application.get('position', '')}")

        # Status section
        self._add_info_section("Application Status", [
            f"Status: {application.get('status', 'applied').replace('_', ' ').title()}",
            f"Applied: {application.get('created_at', 'Unknown')[:10]}",
        ])

        # Interviews section
        interviews = application.get("interviews", [])
        if interviews:
            interview_items = []
            for i, interview in enumerate(interviews, 1):
                text = f"{i}. {interview.get('interview_type', 'Interview').replace('_', ' ').title()}"
                if interview.get("interviewer_name"):
                    text += f" with {interview['interviewer_name']}"
                if interview.get("performance_score"):
                    text += f" (Score: {interview['performance_score']}/10)"
                interview_items.append(text)
            self._add_info_section("Interviews", interview_items)

        # Improvement suggestions
        improvements = application.get("improvement_notes", [])
        if improvements:
            self._add_info_section("Areas for Improvement", improvements, color="#f59e0b")

        # Notes
        if application.get("notes"):
            self._add_info_section("Notes", [application["notes"]])

        self.content_layout.addStretch()

    def _add_info_section(self, title: str, items: List[str], color: str = "#fbbf24"):
        """Add an info section."""
        section = QFrame()
        section.setObjectName("section")
        section_layout = QVBoxLayout(section)
        section_layout.setContentsMargins(12, 12, 12, 12)

        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")
        title_label.setStyleSheet(f"color: {color}; font-weight: bold;")
        section_layout.addWidget(title_label)

        for item in items:
            item_label = QLabel(f"* {item}")
            item_label.setWordWrap(True)
            section_layout.addWidget(item_label)

        self.content_layout.addWidget(section)

    def load_improvement_suggestions(self):
        """Load ML improvement suggestions from API."""
        if not self._application or not self.api.is_logged_in():
            return

        app_id = self._application.get("id")
        if not app_id:
            return

        result = self.api.get_interview_improvement(app_id)
        if "error" not in result and result.get("suggestions"):
            suggestions = result["suggestions"]
            self._add_info_section("ML Improvement Suggestions", suggestions, color="#10b981")
