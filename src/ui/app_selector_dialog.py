"""Meeting App Selector Dialog for when multiple apps are detected."""

from typing import Optional, List
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QRadioButton, QButtonGroup
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPalette, QColor


class AppSelectorDialog(QDialog):
    """Dialog for selecting which meeting app to use."""

    def __init__(self, apps: List[str], parent=None):
        super().__init__(parent)
        self._apps = apps
        self._selected_app = apps[0] if apps else None
        self._apply_dark_theme()
        self.setup_ui()

    def _apply_dark_theme(self):
        """Apply dark theme."""
        self.setAutoFillBackground(True)
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#1e1e1e"))
        palette.setColor(QPalette.ColorRole.WindowText, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.Base, QColor("#2d2d2d"))
        palette.setColor(QPalette.ColorRole.Text, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.Button, QColor("#3d3d3d"))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor("#ffffff"))
        self.setPalette(palette)

    def setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Select Meeting App")
        self.setFixedWidth(350)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Header
        header = QLabel("Multiple Meeting Apps Detected")
        header.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        header.setStyleSheet("color: #ffffff; background: transparent;")
        layout.addWidget(header)

        # Description
        desc = QLabel("Select which meeting app you want ReadIn AI to assist with:")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #aaaaaa; font-size: 12px; background: transparent;")
        layout.addWidget(desc)

        # App buttons
        self.button_group = QButtonGroup(self)

        for i, app in enumerate(self._apps):
            radio = QRadioButton(app)
            radio.setStyleSheet("""
                QRadioButton {
                    color: #ffffff;
                    padding: 10px;
                    font-size: 13px;
                }
                QRadioButton::indicator {
                    width: 18px;
                    height: 18px;
                }
            """)
            radio.setProperty("app_name", app)
            self.button_group.addButton(radio, i)
            layout.addWidget(radio)

            if i == 0:
                radio.setChecked(True)

        self.button_group.buttonClicked.connect(self._on_app_selected)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        select_btn = QPushButton("Start Listening")
        select_btn.setStyleSheet("""
            QPushButton {
                background-color: #22c55e;
                color: #ffffff;
                border: none;
                padding: 10px 24px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #16a34a;
            }
        """)
        select_btn.clicked.connect(self.accept)
        btn_layout.addWidget(select_btn)

        layout.addLayout(btn_layout)

    def _on_app_selected(self, button):
        """Handle app selection."""
        self._selected_app = button.property("app_name")

    def get_selected_app(self) -> Optional[str]:
        """Get the selected app name."""
        return self._selected_app

    @staticmethod
    def select_app(apps: List[str], parent=None) -> Optional[str]:
        """Show dialog and return selected app.

        Returns:
            App name or None if cancelled
        """
        dialog = AppSelectorDialog(apps, parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.get_selected_app()
        return None
