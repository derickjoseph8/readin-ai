"""Login/Register window for ReadIn AI."""

import webbrowser
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QStackedWidget, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from src.api_client import api


class LoginWindow(QWidget):
    """Login/Register window."""

    login_successful = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("ReadIn AI - Login")
        self.setFixedSize(400, 500)
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e2e;
                color: #cdd6f4;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLineEdit {
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
                color: #cdd6f4;
            }
            QLineEdit:focus {
                border: 1px solid #89b4fa;
            }
            QPushButton {
                background-color: #89b4fa;
                color: #1e1e2e;
                border: none;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #b4befe;
            }
            QPushButton:disabled {
                background-color: #45475a;
                color: #6c7086;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # Logo/Title
        title = QLabel("ReadIn AI")
        title.setStyleSheet("font-size: 28px; font-weight: bold; color: #89b4fa;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Your AI assistant for live conversations")
        subtitle.setStyleSheet("font-size: 12px; color: #a6adc8;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(20)

        # Stacked widget for login/register forms
        self.stack = QStackedWidget()
        self.stack.addWidget(self._create_login_form())
        self.stack.addWidget(self._create_register_form())
        layout.addWidget(self.stack)

        layout.addStretch()

    def _create_login_form(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        # Email
        self.login_email = QLineEdit()
        self.login_email.setPlaceholderText("Email")
        layout.addWidget(self.login_email)

        # Password
        self.login_password = QLineEdit()
        self.login_password.setPlaceholderText("Password")
        self.login_password.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.login_password)

        # Login button
        self.login_btn = QPushButton("Log In")
        self.login_btn.clicked.connect(self._do_login)
        layout.addWidget(self.login_btn)

        # Error label
        self.login_error = QLabel("")
        self.login_error.setStyleSheet("color: #f38ba8; font-size: 12px;")
        self.login_error.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.login_error)

        layout.addSpacing(10)

        # Switch to register
        switch_layout = QHBoxLayout()
        switch_label = QLabel("Don't have an account?")
        switch_label.setStyleSheet("color: #a6adc8; font-size: 12px;")
        switch_btn = QPushButton("Sign Up")
        switch_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #89b4fa;
                font-weight: bold;
                padding: 0;
            }
            QPushButton:hover {
                color: #b4befe;
            }
        """)
        switch_btn.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        switch_layout.addStretch()
        switch_layout.addWidget(switch_label)
        switch_layout.addWidget(switch_btn)
        switch_layout.addStretch()
        layout.addLayout(switch_layout)

        return widget

    def _create_register_form(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        # Name
        self.register_name = QLineEdit()
        self.register_name.setPlaceholderText("Full Name")
        layout.addWidget(self.register_name)

        # Email
        self.register_email = QLineEdit()
        self.register_email.setPlaceholderText("Email")
        layout.addWidget(self.register_email)

        # Password
        self.register_password = QLineEdit()
        self.register_password.setPlaceholderText("Password (min 8 characters)")
        self.register_password.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.register_password)

        # Register button
        self.register_btn = QPushButton("Start Free Trial")
        self.register_btn.clicked.connect(self._do_register)
        layout.addWidget(self.register_btn)

        # Trial info
        trial_info = QLabel("7-day free trial - No credit card required")
        trial_info.setStyleSheet("color: #a6e3a1; font-size: 11px;")
        trial_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(trial_info)

        # Error label
        self.register_error = QLabel("")
        self.register_error.setStyleSheet("color: #f38ba8; font-size: 12px;")
        self.register_error.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.register_error)

        layout.addSpacing(10)

        # Switch to login
        switch_layout = QHBoxLayout()
        switch_label = QLabel("Already have an account?")
        switch_label.setStyleSheet("color: #a6adc8; font-size: 12px;")
        switch_btn = QPushButton("Log In")
        switch_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #89b4fa;
                font-weight: bold;
                padding: 0;
            }
            QPushButton:hover {
                color: #b4befe;
            }
        """)
        switch_btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        switch_layout.addStretch()
        switch_layout.addWidget(switch_label)
        switch_layout.addWidget(switch_btn)
        switch_layout.addStretch()
        layout.addLayout(switch_layout)

        return widget

    def _do_login(self):
        email = self.login_email.text().strip()
        password = self.login_password.text()

        if not email or not password:
            self.login_error.setText("Please enter email and password")
            return

        self.login_btn.setEnabled(False)
        self.login_btn.setText("Logging in...")
        self.login_error.setText("")

        result = api.login(email, password)

        self.login_btn.setEnabled(True)
        self.login_btn.setText("Log In")

        if "access_token" in result:
            self.login_successful.emit()
            self.close()
        else:
            self.login_error.setText(result.get("message", "Login failed"))

    def _do_register(self):
        name = self.register_name.text().strip()
        email = self.register_email.text().strip()
        password = self.register_password.text()

        if not email or not password:
            self.register_error.setText("Please fill in all fields")
            return

        if len(password) < 8:
            self.register_error.setText("Password must be at least 8 characters")
            return

        self.register_btn.setEnabled(False)
        self.register_btn.setText("Creating account...")
        self.register_error.setText("")

        result = api.register(email, password, name if name else None)

        self.register_btn.setEnabled(True)
        self.register_btn.setText("Start Free Trial")

        if "access_token" in result:
            self.login_successful.emit()
            self.close()
        else:
            self.register_error.setText(result.get("message", "Registration failed"))
