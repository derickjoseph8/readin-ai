"""
Speaker Manager Dialog

Allows users to rename detected speakers (e.g., "SPEAKER_00" to "John")
and view speaker statistics for the current meeting session.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QLineEdit, QGroupBox,
    QFormLayout, QProgressBar, QMessageBox, QHeaderView,
    QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class SpeakerManagerDialog(QDialog):
    """Dialog for managing speaker names and viewing speaker statistics."""

    # Signal emitted when a speaker is renamed
    speaker_renamed = pyqtSignal(str, str)  # speaker_id, new_name

    def __init__(
        self,
        speakers: List[Dict[str, Any]],
        speaker_mapping: Optional[Dict[str, str]] = None,
        parent=None
    ):
        """
        Initialize the speaker manager dialog.

        Args:
            speakers: List of speaker info dictionaries with id, name, message_count, etc.
            speaker_mapping: Current mapping of speaker IDs to custom names.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._speakers = speakers or []
        self._speaker_mapping = speaker_mapping or {}
        self._original_mapping = self._speaker_mapping.copy()
        self._init_ui()
        self._populate_table()

    def _init_ui(self):
        """Initialize the UI components."""
        self.setWindowTitle("Speaker Management")
        self.setMinimumSize(500, 400)
        self.setModal(True)

        # Apply dark theme
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e2e;
                color: #cdd6f4;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #45475a;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #89b4fa;
            }
            QTableWidget {
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 4px;
                gridline-color: #45475a;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QTableWidget::item:selected {
                background-color: #45475a;
            }
            QHeaderView::section {
                background-color: #45475a;
                color: #cdd6f4;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
            QLineEdit {
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 4px;
                padding: 6px 10px;
                color: #cdd6f4;
            }
            QLineEdit:focus {
                border-color: #89b4fa;
            }
            QPushButton {
                background-color: #45475a;
                color: #cdd6f4;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #585b70;
            }
            QPushButton:pressed {
                background-color: #313244;
            }
            QPushButton#applyBtn {
                background-color: #89b4fa;
                color: #1e1e2e;
            }
            QPushButton#applyBtn:hover {
                background-color: #b4befe;
            }
            QLabel {
                color: #cdd6f4;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        # Header
        header_label = QLabel("Rename speakers to identify participants in your meeting")
        header_label.setStyleSheet("color: #a6adc8; font-size: 12px;")
        layout.addWidget(header_label)

        # Speakers table
        speakers_group = QGroupBox("Detected Speakers")
        speakers_layout = QVBoxLayout(speakers_group)

        self.speakers_table = QTableWidget()
        self.speakers_table.setColumnCount(4)
        self.speakers_table.setHorizontalHeaderLabels([
            "ID", "Custom Name", "Messages", "Speaking %"
        ])
        self.speakers_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.speakers_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.speakers_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.speakers_table.verticalHeader().setVisible(False)
        self.speakers_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        speakers_layout.addWidget(self.speakers_table)

        # Rename section
        rename_layout = QHBoxLayout()

        rename_layout.addWidget(QLabel("New Name:"))

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter name for selected speaker...")
        self.name_input.returnPressed.connect(self._rename_selected)
        rename_layout.addWidget(self.name_input, 1)

        self.rename_btn = QPushButton("Rename")
        self.rename_btn.clicked.connect(self._rename_selected)
        rename_layout.addWidget(self.rename_btn)

        speakers_layout.addLayout(rename_layout)

        layout.addWidget(speakers_group)

        # Info label
        info_label = QLabel(
            "Tip: Click a speaker row, enter a name, and press Enter or click Rename.\n"
            "Names are saved with your meeting transcript."
        )
        info_label.setStyleSheet("color: #6c7086; font-size: 11px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.reset_btn = QPushButton("Reset Names")
        self.reset_btn.clicked.connect(self._reset_names)
        button_layout.addWidget(self.reset_btn)

        self.apply_btn = QPushButton("Apply")
        self.apply_btn.setObjectName("applyBtn")
        self.apply_btn.clicked.connect(self._apply_changes)
        button_layout.addWidget(self.apply_btn)

        self.close_btn = QPushButton("Cancel")
        self.close_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.close_btn)

        layout.addLayout(button_layout)

    def _populate_table(self):
        """Populate the speakers table with current data."""
        self.speakers_table.setRowCount(len(self._speakers))

        for row, speaker in enumerate(self._speakers):
            speaker_id = speaker.get("id", "UNKNOWN")
            custom_name = self._speaker_mapping.get(speaker_id, "")
            message_count = speaker.get("message_count", 0)
            percentage = speaker.get("percentage", 0.0)

            # ID column
            id_item = QTableWidgetItem(speaker_id)
            id_item.setData(Qt.ItemDataRole.UserRole, speaker_id)
            id_item.setForeground(QColor("#89b4fa"))
            self.speakers_table.setItem(row, 0, id_item)

            # Custom name column
            name_item = QTableWidgetItem(custom_name or "(Not set)")
            if not custom_name:
                name_item.setForeground(QColor("#6c7086"))
            self.speakers_table.setItem(row, 1, name_item)

            # Message count column
            count_item = QTableWidgetItem(str(message_count))
            count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.speakers_table.setItem(row, 2, count_item)

            # Speaking percentage column
            pct_item = QTableWidgetItem(f"{percentage:.1f}%")
            pct_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.speakers_table.setItem(row, 3, pct_item)

    def _rename_selected(self):
        """Rename the currently selected speaker."""
        selected_rows = self.speakers_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(
                self,
                "No Selection",
                "Please select a speaker to rename."
            )
            return

        row = selected_rows[0].row()
        speaker_id = self.speakers_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        new_name = self.name_input.text().strip()

        if not new_name:
            QMessageBox.warning(
                self,
                "Invalid Name",
                "Please enter a name for the speaker."
            )
            return

        # Update mapping
        self._speaker_mapping[speaker_id] = new_name

        # Update table display
        name_item = self.speakers_table.item(row, 1)
        name_item.setText(new_name)
        name_item.setForeground(QColor("#cdd6f4"))

        # Clear input
        self.name_input.clear()

        # Emit signal for immediate update
        self.speaker_renamed.emit(speaker_id, new_name)

        logger.info(f"Renamed speaker {speaker_id} to '{new_name}'")

    def _reset_names(self):
        """Reset all custom names."""
        reply = QMessageBox.question(
            self,
            "Reset Names",
            "Are you sure you want to reset all speaker names?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._speaker_mapping.clear()
            self._populate_table()

    def _apply_changes(self):
        """Apply changes and close dialog."""
        self.accept()

    def get_speaker_mapping(self) -> Dict[str, str]:
        """Get the current speaker name mapping."""
        return self._speaker_mapping.copy()

    @staticmethod
    def edit_speakers(
        speakers: List[Dict[str, Any]],
        speaker_mapping: Optional[Dict[str, str]] = None,
        parent=None
    ) -> Optional[Dict[str, str]]:
        """
        Show the speaker manager dialog and return updated mapping.

        Args:
            speakers: List of speaker info dictionaries.
            speaker_mapping: Current speaker name mapping.
            parent: Parent widget.

        Returns:
            Updated speaker mapping if accepted, None if cancelled.
        """
        dialog = SpeakerManagerDialog(speakers, speaker_mapping, parent)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.get_speaker_mapping()

        return None


class SpeakerLabelWidget(QLabel):
    """
    Compact widget for displaying a speaker label with click-to-rename.

    Used in the overlay or transcript display to show speaker attribution.
    """

    clicked = pyqtSignal(str)  # Emits speaker_id when clicked

    def __init__(
        self,
        speaker_id: str,
        speaker_name: Optional[str] = None,
        parent=None
    ):
        """
        Initialize the speaker label widget.

        Args:
            speaker_id: The speaker identifier.
            speaker_name: Custom display name (uses speaker_id if None).
            parent: Parent widget.
        """
        super().__init__(parent)
        self._speaker_id = speaker_id
        self._speaker_name = speaker_name or speaker_id
        self._update_display()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(f"Click to rename {speaker_id}")

    def _update_display(self):
        """Update the label display."""
        display_text = self._speaker_name
        if display_text.startswith("SPEAKER_"):
            # Format as short version: S0, S1, etc.
            try:
                num = int(display_text.split("_")[1])
                display_text = f"S{num}"
            except (IndexError, ValueError):
                pass

        self.setText(f"[{display_text}]")

        # Style based on whether it's a custom name
        if self._speaker_name != self._speaker_id:
            self.setStyleSheet("""
                QLabel {
                    color: #a6e3a1;
                    font-weight: bold;
                    font-size: 10px;
                    padding: 2px 4px;
                    background-color: rgba(166, 227, 161, 0.1);
                    border-radius: 3px;
                }
                QLabel:hover {
                    background-color: rgba(166, 227, 161, 0.2);
                }
            """)
        else:
            self.setStyleSheet("""
                QLabel {
                    color: #89b4fa;
                    font-weight: bold;
                    font-size: 10px;
                    padding: 2px 4px;
                    background-color: rgba(137, 180, 250, 0.1);
                    border-radius: 3px;
                }
                QLabel:hover {
                    background-color: rgba(137, 180, 250, 0.2);
                }
            """)

    def set_speaker_name(self, name: str):
        """Set the custom speaker name."""
        self._speaker_name = name
        self._update_display()

    def mousePressEvent(self, event):
        """Handle click to emit signal."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._speaker_id)
        super().mousePressEvent(event)

    @property
    def speaker_id(self) -> str:
        """Get the speaker ID."""
        return self._speaker_id

    @property
    def speaker_name(self) -> str:
        """Get the speaker name."""
        return self._speaker_name


class SpeakerColorManager:
    """Assigns consistent colors to speakers for visual distinction."""

    # Color palette for speakers (color-blind friendly)
    SPEAKER_COLORS = [
        "#89b4fa",  # Blue
        "#a6e3a1",  # Green
        "#f9e2af",  # Yellow
        "#cba6f7",  # Purple
        "#fab387",  # Orange
        "#f38ba8",  # Pink
        "#94e2d5",  # Teal
        "#eba0ac",  # Rose
    ]

    def __init__(self):
        """Initialize the color manager."""
        self._speaker_colors: Dict[str, str] = {}
        self._color_index = 0

    def get_color(self, speaker_id: str) -> str:
        """
        Get a consistent color for a speaker.

        Args:
            speaker_id: The speaker identifier.

        Returns:
            Hex color string.
        """
        if speaker_id not in self._speaker_colors:
            color = self.SPEAKER_COLORS[self._color_index % len(self.SPEAKER_COLORS)]
            self._speaker_colors[speaker_id] = color
            self._color_index += 1

        return self._speaker_colors[speaker_id]

    def reset(self):
        """Reset color assignments."""
        self._speaker_colors.clear()
        self._color_index = 0
