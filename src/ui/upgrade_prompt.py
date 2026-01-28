"""Upgrade prompt dialog for trial users who hit their limit."""

import webbrowser
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
)
from PyQt6.QtCore import Qt

from src.api_client import api


class UpgradePrompt(QDialog):
    """Dialog shown when trial user hits daily limit."""

    def __init__(self, parent=None, remaining_days: int = 0):
        super().__init__(parent)
        self.remaining_days = remaining_days
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("Upgrade to Premium")
        self.setFixedSize(380, 280)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e2e;
                color: #cdd6f4;
            }
            QLabel {
                color: #cdd6f4;
            }
            QPushButton {
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        # Icon/Emoji
        icon = QLabel("10")
        icon.setStyleSheet("font-size: 40px; color: #f9e2af;")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon)

        # Title
        title = QLabel("Daily Limit Reached")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #cdd6f4;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Message
        if self.remaining_days > 0:
            msg = f"You've used all 10 free responses for today.\n{self.remaining_days} days left in your trial."
        else:
            msg = "Your free trial has ended.\nUpgrade for unlimited responses."

        message = QLabel(msg)
        message.setStyleSheet("font-size: 13px; color: #a6adc8;")
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(message)

        layout.addSpacing(10)

        # Buttons
        btn_layout = QHBoxLayout()

        upgrade_btn = QPushButton("Upgrade - $10/month")
        upgrade_btn.setStyleSheet("""
            QPushButton {
                background-color: #a6e3a1;
                color: #1e1e2e;
            }
            QPushButton:hover {
                background-color: #94e2d5;
            }
        """)
        upgrade_btn.clicked.connect(self._open_checkout)
        btn_layout.addWidget(upgrade_btn)

        later_btn = QPushButton("Maybe Later")
        later_btn.setStyleSheet("""
            QPushButton {
                background-color: #45475a;
                color: #cdd6f4;
            }
            QPushButton:hover {
                background-color: #585b70;
            }
        """)
        later_btn.clicked.connect(self.close)
        btn_layout.addWidget(later_btn)

        layout.addLayout(btn_layout)

    def _open_checkout(self):
        """Open Stripe checkout in browser."""
        checkout_url = api.get_checkout_url()
        if checkout_url:
            webbrowser.open(checkout_url)
        self.close()
