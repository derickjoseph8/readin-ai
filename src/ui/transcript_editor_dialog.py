"""
Transcript Editor Dialog

PyQt6 dialog for viewing and editing meeting transcripts.
Allows users to correct transcription errors and save edits.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QTextEdit, QSplitter,
    QFrame, QMessageBox, QProgressBar, QWidget, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt6.QtGui import QFont, QColor

from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class TranscriptItem(QFrame):
    """Widget representing a single transcript entry."""

    edit_requested = pyqtSignal(int, str)  # transcript_id, current_text

    def __init__(
        self,
        transcript_id: int,
        speaker: str,
        text: str,
        timestamp: str,
        is_edited: bool = False,
        original_text: Optional[str] = None,
        parent=None
    ):
        super().__init__(parent)
        self.transcript_id = transcript_id
        self.speaker = speaker
        self.current_text = text
        self.original_text = original_text
        self.is_edited = is_edited
        self._setup_ui(speaker, text, timestamp, is_edited)

    def _setup_ui(self, speaker: str, text: str, timestamp: str, is_edited: bool):
        """Initialize the UI components."""
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setStyleSheet("""
            QFrame {
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 8px;
                padding: 8px;
                margin: 4px;
            }
            QFrame:hover {
                border-color: #89b4fa;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(6)

        # Header with speaker and timestamp
        header_layout = QHBoxLayout()

        # Speaker label with color coding
        speaker_label = QLabel(f"[{speaker}]")
        speaker_color = "#89b4fa" if speaker == "user" else "#a6e3a1"
        speaker_label.setStyleSheet(f"""
            color: {speaker_color};
            font-weight: bold;
            font-size: 11px;
        """)
        header_layout.addWidget(speaker_label)

        # Edit indicator
        if is_edited:
            edited_label = QLabel("(edited)")
            edited_label.setStyleSheet("color: #f9e2af; font-size: 10px; font-style: italic;")
            header_layout.addWidget(edited_label)

        header_layout.addStretch()

        # Timestamp
        timestamp_label = QLabel(timestamp)
        timestamp_label.setStyleSheet("color: #6c7086; font-size: 10px;")
        header_layout.addWidget(timestamp_label)

        layout.addLayout(header_layout)

        # Transcript text
        self.text_label = QLabel(text)
        self.text_label.setWordWrap(True)
        self.text_label.setStyleSheet("""
            color: #cdd6f4;
            font-size: 13px;
            line-height: 1.4;
            padding: 4px 0;
        """)
        layout.addWidget(self.text_label)

        # Show original text if edited
        if is_edited and self.original_text:
            original_label = QLabel(f"Original: {self.original_text[:100]}...")
            original_label.setWordWrap(True)
            original_label.setStyleSheet("""
                color: #6c7086;
                font-size: 11px;
                font-style: italic;
                padding: 4px 0;
            """)
            layout.addWidget(original_label)

        # Edit button
        edit_btn = QPushButton("Edit")
        edit_btn.setFixedWidth(60)
        edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #45475a;
                color: #cdd6f4;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #89b4fa;
                color: #1e1e2e;
            }
        """)
        edit_btn.clicked.connect(self._on_edit_clicked)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(edit_btn)
        layout.addLayout(btn_layout)

    def _on_edit_clicked(self):
        """Handle edit button click."""
        self.edit_requested.emit(self.transcript_id, self.current_text)

    def update_text(self, new_text: str):
        """Update the displayed text after editing."""
        self.current_text = new_text
        self.text_label.setText(new_text)
        self.is_edited = True


class TranscriptEditorDialog(QDialog):
    """Dialog for editing meeting transcripts."""

    transcript_updated = pyqtSignal(int, str)  # transcript_id, new_text

    def __init__(
        self,
        meeting_id: int,
        meeting_title: Optional[str] = None,
        api_client=None,
        parent=None
    ):
        super().__init__(parent)
        self.meeting_id = meeting_id
        self.meeting_title = meeting_title or f"Meeting {meeting_id}"
        self.api_client = api_client
        self.transcripts: List[Dict[str, Any]] = []
        self.transcript_items: Dict[int, TranscriptItem] = {}
        self.current_editing_id: Optional[int] = None
        self._setup_ui()
        self._load_transcripts()

    def _setup_ui(self):
        """Initialize the UI components."""
        self.setWindowTitle(f"Edit Transcripts - {self.meeting_title}")
        self.setMinimumSize(700, 500)
        self.resize(800, 600)
        self.setModal(True)

        # Apply dark theme
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e2e;
                color: #cdd6f4;
            }
            QLabel {
                color: #cdd6f4;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background: #313244;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #585b70;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #6c7086;
            }
            QTextEdit {
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 6px;
                padding: 8px;
                color: #cdd6f4;
                font-size: 13px;
            }
            QTextEdit:focus {
                border-color: #89b4fa;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header
        header_layout = QHBoxLayout()

        title_label = QLabel(f"Transcripts for: {self.meeting_title}")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #89b4fa;")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #45475a;
                color: #cdd6f4;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #585b70;
            }
        """)
        refresh_btn.clicked.connect(self._load_transcripts)
        header_layout.addWidget(refresh_btn)

        layout.addLayout(header_layout)

        # Main content splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #45475a;
                width: 2px;
            }
        """)

        # Left panel - Transcript list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 8, 0)

        list_header = QLabel("Transcript Entries")
        list_header.setStyleSheet("font-weight: bold; color: #a6adc8; font-size: 12px;")
        left_layout.addWidget(list_header)

        # Scroll area for transcript items
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.transcript_container = QWidget()
        self.transcript_layout = QVBoxLayout(self.transcript_container)
        self.transcript_layout.setContentsMargins(0, 0, 0, 0)
        self.transcript_layout.setSpacing(8)
        self.transcript_layout.addStretch()

        self.scroll_area.setWidget(self.transcript_container)
        left_layout.addWidget(self.scroll_area)

        # Loading indicator
        self.loading_label = QLabel("Loading transcripts...")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.setStyleSheet("color: #6c7086; font-style: italic;")
        left_layout.addWidget(self.loading_label)

        splitter.addWidget(left_panel)

        # Right panel - Editor
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(8, 0, 0, 0)

        editor_header = QLabel("Edit Transcript")
        editor_header.setStyleSheet("font-weight: bold; color: #a6adc8; font-size: 12px;")
        right_layout.addWidget(editor_header)

        # Editor text area
        self.editor = QTextEdit()
        self.editor.setPlaceholderText("Select a transcript entry to edit...")
        self.editor.setMinimumHeight(200)
        right_layout.addWidget(self.editor)

        # Editor buttons
        editor_btn_layout = QHBoxLayout()

        self.revert_btn = QPushButton("Revert to Original")
        self.revert_btn.setEnabled(False)
        self.revert_btn.setStyleSheet("""
            QPushButton {
                background-color: #45475a;
                color: #cdd6f4;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #f38ba8;
                color: #1e1e2e;
            }
            QPushButton:disabled {
                background-color: #313244;
                color: #6c7086;
            }
        """)
        self.revert_btn.clicked.connect(self._revert_to_original)
        editor_btn_layout.addWidget(self.revert_btn)

        editor_btn_layout.addStretch()

        self.save_btn = QPushButton("Save Changes")
        self.save_btn.setEnabled(False)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #89b4fa;
                color: #1e1e2e;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #b4befe;
            }
            QPushButton:disabled {
                background-color: #313244;
                color: #6c7086;
            }
        """)
        self.save_btn.clicked.connect(self._save_changes)
        editor_btn_layout.addWidget(self.save_btn)

        right_layout.addLayout(editor_btn_layout)

        # Info text
        info_label = QLabel(
            "Select a transcript entry from the list, edit the text, and save.\n"
            "Original transcriptions are preserved and can be reverted."
        )
        info_label.setStyleSheet("color: #6c7086; font-size: 11px;")
        info_label.setWordWrap(True)
        right_layout.addWidget(info_label)

        right_layout.addStretch()

        splitter.addWidget(right_panel)
        splitter.setSizes([400, 300])

        layout.addWidget(splitter)

        # Bottom buttons
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #45475a;
                color: #cdd6f4;
                border: none;
                border-radius: 4px;
                padding: 8px 24px;
            }
            QPushButton:hover {
                background-color: #585b70;
            }
        """)
        close_btn.clicked.connect(self.accept)
        bottom_layout.addWidget(close_btn)

        layout.addLayout(bottom_layout)

    def _load_transcripts(self):
        """Load transcripts from the API."""
        self.loading_label.show()
        self._clear_transcript_items()

        if not self.api_client:
            self.loading_label.setText("API client not available")
            return

        try:
            # Make API call to get transcripts
            result = self.api_client._request(
                "GET",
                f"/meetings/{self.meeting_id}/transcripts"
            )

            if "error" in result:
                self.loading_label.setText(f"Error: {result.get('message', 'Unknown error')}")
                return

            self.transcripts = result.get("transcripts", [])
            self._display_transcripts()
            self.loading_label.hide()

        except Exception as e:
            logger.error(f"Failed to load transcripts: {e}")
            self.loading_label.setText(f"Failed to load: {str(e)}")

    def _clear_transcript_items(self):
        """Clear all transcript items from the layout."""
        # Remove all widgets except the stretch
        while self.transcript_layout.count() > 1:
            item = self.transcript_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.transcript_items.clear()

    def _display_transcripts(self):
        """Display loaded transcripts."""
        self._clear_transcript_items()

        if not self.transcripts:
            no_data_label = QLabel("No transcripts found for this meeting.")
            no_data_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_data_label.setStyleSheet("color: #6c7086; font-style: italic; padding: 20px;")
            self.transcript_layout.insertWidget(0, no_data_label)
            return

        for i, transcript in enumerate(self.transcripts):
            # Format timestamp
            timestamp_str = transcript.get("timestamp", "")
            if timestamp_str:
                try:
                    dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                    timestamp_str = dt.strftime("%H:%M:%S")
                except (ValueError, AttributeError):
                    pass

            item = TranscriptItem(
                transcript_id=transcript.get("id", i),
                speaker=transcript.get("speaker", "unknown"),
                text=transcript.get("edited_text") or transcript.get("heard_text", ""),
                timestamp=timestamp_str,
                is_edited=transcript.get("is_edited", False),
                original_text=transcript.get("original_text"),
                parent=self
            )
            item.edit_requested.connect(self._on_edit_requested)

            self.transcript_items[transcript.get("id", i)] = item
            self.transcript_layout.insertWidget(i, item)

    def _on_edit_requested(self, transcript_id: int, current_text: str):
        """Handle request to edit a transcript."""
        self.current_editing_id = transcript_id
        self.editor.setText(current_text)
        self.save_btn.setEnabled(True)

        # Check if we can revert
        transcript = next(
            (t for t in self.transcripts if t.get("id") == transcript_id),
            None
        )
        if transcript and transcript.get("original_text"):
            self.revert_btn.setEnabled(True)
        else:
            self.revert_btn.setEnabled(False)

    def _save_changes(self):
        """Save the edited transcript."""
        if self.current_editing_id is None:
            return

        new_text = self.editor.toPlainText().strip()
        if not new_text:
            QMessageBox.warning(self, "Invalid Text", "Transcript text cannot be empty.")
            return

        if not self.api_client:
            QMessageBox.warning(self, "Error", "API client not available.")
            return

        try:
            # Make API call to update transcript
            result = self.api_client._request(
                "PATCH",
                f"/meetings/{self.meeting_id}/transcripts/{self.current_editing_id}",
                data={"edited_text": new_text}
            )

            if "error" in result:
                QMessageBox.warning(
                    self,
                    "Save Failed",
                    f"Failed to save: {result.get('message', 'Unknown error')}"
                )
                return

            # Update the UI
            if self.current_editing_id in self.transcript_items:
                self.transcript_items[self.current_editing_id].update_text(new_text)

            # Emit signal
            self.transcript_updated.emit(self.current_editing_id, new_text)

            # Show success message
            QMessageBox.information(self, "Saved", "Transcript updated successfully.")

            # Reset editor state
            self.current_editing_id = None
            self.editor.clear()
            self.save_btn.setEnabled(False)
            self.revert_btn.setEnabled(False)

            # Reload to show updated state
            self._load_transcripts()

        except Exception as e:
            logger.error(f"Failed to save transcript: {e}")
            QMessageBox.warning(self, "Error", f"Failed to save: {str(e)}")

    def _revert_to_original(self):
        """Revert the current transcript to its original text."""
        if self.current_editing_id is None:
            return

        transcript = next(
            (t for t in self.transcripts if t.get("id") == self.current_editing_id),
            None
        )

        if transcript and transcript.get("original_text"):
            self.editor.setText(transcript.get("original_text"))

    @staticmethod
    def edit_transcripts(
        meeting_id: int,
        meeting_title: Optional[str] = None,
        api_client=None,
        parent=None
    ) -> bool:
        """
        Show the transcript editor dialog.

        Args:
            meeting_id: ID of the meeting whose transcripts to edit.
            meeting_title: Title of the meeting for display.
            api_client: API client instance for making requests.
            parent: Parent widget.

        Returns:
            True if any changes were made, False otherwise.
        """
        dialog = TranscriptEditorDialog(
            meeting_id=meeting_id,
            meeting_title=meeting_title,
            api_client=api_client,
            parent=parent
        )

        result = dialog.exec()
        return result == QDialog.DialogCode.Accepted
