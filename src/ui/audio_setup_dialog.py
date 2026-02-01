"""Audio Setup Dialog for first-run configuration."""

import subprocess
import os
from typing import Optional, List, Dict, Any
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QRadioButton, QButtonGroup, QFrame, QScrollArea, QWidget,
    QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPalette, QColor

from src.audio_capture import AudioCapture


class AudioSetupDialog(QDialog):
    """Dialog for selecting audio input device on first run."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected_device = None
        self._devices = []
        self._apply_dark_theme()
        self.setup_ui()

    def _apply_dark_theme(self):
        """Apply dark theme using QPalette."""
        self.setAutoFillBackground(True)
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#1e1e1e"))
        palette.setColor(QPalette.ColorRole.WindowText, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.Base, QColor("#2d2d2d"))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#3d3d3d"))
        palette.setColor(QPalette.ColorRole.Text, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.Button, QColor("#3d3d3d"))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.Highlight, QColor("#22c55e"))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
        self.setPalette(palette)

    def setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Audio Setup - ReadIn AI")
        self.setFixedWidth(520)
        self.setMinimumHeight(450)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Header
        header = QLabel("Audio Input Setup")
        header.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header.setStyleSheet("color: #ffffff; background: transparent;")
        layout.addWidget(header)

        # Description
        desc = QLabel(
            "Select the audio source ReadIn AI should listen to.\n\n"
            "To capture meeting audio (what others say), select a loopback device "
            "like 'Stereo Mix' or 'CABLE Output'."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #aaaaaa; font-size: 12px; background: transparent;")
        layout.addWidget(desc)

        # Device list container
        device_frame = QFrame()
        device_frame.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border: 1px solid #444444;
                border-radius: 8px;
            }
        """)
        device_layout = QVBoxLayout(device_frame)
        device_layout.setContentsMargins(12, 12, 12, 12)
        device_layout.setSpacing(8)

        # Load devices
        self.button_group = QButtonGroup(self)
        self.button_group.buttonClicked.connect(self._on_device_selected)
        self._devices = AudioCapture.get_available_devices()

        # Sort: loopback first, then default, then others
        def sort_key(d):
            if d['is_loopback']:
                return (0, d['name'])
            if d['is_default']:
                return (1, d['name'])
            return (2, d['name'])

        self._devices.sort(key=sort_key)

        has_loopback = any(d['is_loopback'] for d in self._devices)

        for i, device in enumerate(self._devices):
            radio = QRadioButton()

            # Build label with badges
            name = device['name']
            if len(name) > 45:
                name = name[:42] + "..."

            badges = []
            if device['is_loopback']:
                badges.append("RECOMMENDED")
            if device['is_default']:
                badges.append("DEFAULT")

            label = name
            if badges:
                label += f"  [{', '.join(badges)}]"
            radio.setText(label)

            # Style based on type
            if device['is_loopback']:
                radio.setStyleSheet("""
                    QRadioButton {
                        color: #22c55e;
                        font-weight: bold;
                        padding: 8px;
                        background-color: #1a3a1a;
                        border-radius: 6px;
                    }
                    QRadioButton::indicator {
                        width: 16px;
                        height: 16px;
                    }
                """)
            else:
                radio.setStyleSheet("""
                    QRadioButton {
                        color: #cccccc;
                        padding: 8px;
                    }
                    QRadioButton::indicator {
                        width: 16px;
                        height: 16px;
                    }
                """)

            radio.setProperty("device_index", device['index'])
            self.button_group.addButton(radio, i)
            device_layout.addWidget(radio)

            # Auto-select first loopback device, or first device
            if device['is_loopback'] and self._selected_device is None:
                radio.setChecked(True)
                self._selected_device = device['index']

        # If no loopback, select first device
        if self._selected_device is None and self._devices:
            first_btn = self.button_group.button(0)
            if first_btn:
                first_btn.setChecked(True)
                self._selected_device = self._devices[0]['index']

        device_layout.addStretch()
        layout.addWidget(device_frame, 1)

        # Warning if no loopback devices
        if not has_loopback:
            warning_frame = QFrame()
            warning_frame.setStyleSheet("""
                QFrame {
                    background-color: #3d2a00;
                    border: 1px solid #f59e0b;
                    border-radius: 6px;
                    padding: 8px;
                }
            """)
            warning_layout = QVBoxLayout(warning_frame)
            warning_layout.setContentsMargins(12, 8, 12, 8)

            warning_text = QLabel(
                "No loopback devices found! Only microphones are available.\n"
                "To capture meeting audio, you need to enable Stereo Mix or install VB-Cable."
            )
            warning_text.setWordWrap(True)
            warning_text.setStyleSheet("color: #fbbf24; font-size: 11px; background: transparent;")
            warning_layout.addWidget(warning_text)

            btn_row = QHBoxLayout()

            open_sound_btn = QPushButton("Open Sound Settings")
            open_sound_btn.setStyleSheet("""
                QPushButton {
                    background-color: #f59e0b;
                    color: #000000;
                    border: none;
                    padding: 6px 12px;
                    border-radius: 4px;
                    font-weight: bold;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #d97706;
                }
            """)
            open_sound_btn.clicked.connect(self._open_sound_settings)
            btn_row.addWidget(open_sound_btn)

            btn_row.addStretch()
            warning_layout.addLayout(btn_row)

            layout.addWidget(warning_frame)

        # Continue button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.continue_btn = QPushButton("Continue")
        self.continue_btn.setStyleSheet("""
            QPushButton {
                background-color: #22c55e;
                color: #ffffff;
                border: none;
                padding: 12px 32px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #16a34a;
            }
        """)
        self.continue_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.continue_btn)

        layout.addLayout(btn_layout)

    def _on_device_selected(self, button):
        """Handle device selection."""
        self._selected_device = button.property("device_index")

    def _open_sound_settings(self):
        """Open Windows Sound settings."""
        try:
            # Open the Recording devices tab in Sound settings
            subprocess.Popen(['control', 'mmsys.cpl', ',1'], shell=True)
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error",
                f"Could not open Sound settings: {e}\n\n"
                "Please open Sound settings manually:\n"
                "1. Right-click the speaker icon in taskbar\n"
                "2. Click 'Sound settings'\n"
                "3. Click 'More sound settings'\n"
                "4. Go to 'Recording' tab\n"
                "5. Right-click and enable 'Stereo Mix'"
            )

    def get_selected_device(self) -> Optional[int]:
        """Get the selected device index."""
        return self._selected_device

    @staticmethod
    def get_audio_device(parent=None) -> Optional[int]:
        """Show dialog and return selected device index.

        Returns:
            Device index or None if cancelled
        """
        dialog = AudioSetupDialog(parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.get_selected_device()
        return None
