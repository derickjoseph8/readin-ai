"""ReadIn AI - Real-time AI Assistant for Live Conversations.

Commercial version with authentication and subscription management.
"""

import sys

# Enable line buffering for better logging (may not work on all platforms)
try:
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
except (AttributeError, OSError):
    pass  # Not supported on this platform

import webbrowser
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QMessageBox
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from config import ANTHROPIC_API_KEY
from src.process_monitor import ProcessMonitor
from src.audio_capture import AudioCapture
from src.transcriber import Transcriber
from src.ai_assistant import AIAssistant
from src.ui.overlay import OverlayWindow
from src.ui.login_window import LoginWindow
from src.ui.upgrade_prompt import UpgradePrompt
from src.api_client import api


class SignalBridge(QObject):
    """Bridges background threads to Qt main thread via signals."""
    meeting_detected = pyqtSignal(str)
    meeting_ended = pyqtSignal()
    transcription_ready = pyqtSignal(str)
    ai_response_ready = pyqtSignal(str, str)
    ai_chunk_ready = pyqtSignal(str)


class ReadInApp:
    """Main application controller."""

    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        self.signals = SignalBridge()
        self.signals.meeting_detected.connect(self._on_meeting_detected)
        self.signals.meeting_ended.connect(self._on_meeting_ended)
        self.signals.transcription_ready.connect(self._on_transcription)
        self.signals.ai_response_ready.connect(self._on_ai_response)
        self.signals.ai_chunk_ready.connect(self._on_streaming_chunk)

        # Components
        self.overlay = OverlayWindow()
        self.login_window = None
        self.ai_assistant = AIAssistant(
            on_response=lambda h, r: self.signals.ai_response_ready.emit(h, r),
            on_streaming_chunk=lambda c: self.signals.ai_chunk_ready.emit(c)
        )
        self.transcriber = Transcriber(
            on_transcription=lambda t: self.signals.transcription_ready.emit(t)
        )
        self.audio_capture = AudioCapture(on_audio_chunk=self.transcriber.process_audio)
        self.process_monitor = ProcessMonitor(
            on_meeting_detected=lambda name: self.signals.meeting_detected.emit(name),
            on_meeting_ended=lambda: self.signals.meeting_ended.emit()
        )

        self._listening = False
        self._user_status = None
        self._setup_tray()

    def _setup_tray(self):
        self.tray = QSystemTrayIcon(self.app)

        try:
            self.tray.setIcon(QIcon("assets/icon.png"))
        except Exception:
            from PyQt6.QtGui import QPixmap, QColor
            pixmap = QPixmap(32, 32)
            pixmap.fill(QColor("#89b4fa"))
            self.tray.setIcon(QIcon(pixmap))

        self._update_tray_menu()
        self.tray.setToolTip("ReadIn AI")
        self.tray.show()
        self.tray.activated.connect(self._on_tray_activated)

    def _update_tray_menu(self):
        """Update tray menu based on login state."""
        menu = QMenu()

        if api.is_logged_in():
            # Status
            self.status_action = QAction("Status: Ready", menu)
            self.status_action.setEnabled(False)
            menu.addAction(self.status_action)

            # Usage info
            if self._user_status:
                if self._user_status.get("subscription_status") == "trial":
                    remaining = self._user_status.get("daily_limit", 10) - self._user_status.get("daily_usage", 0)
                    days = self._user_status.get("trial_days_remaining", 0)
                    usage_text = f"Trial: {remaining}/10 left today ({days} days left)"
                else:
                    usage_text = "Plan: Premium (Unlimited)"
                usage_action = QAction(usage_text, menu)
                usage_action.setEnabled(False)
                menu.addAction(usage_action)

            menu.addSeparator()

            # Start/Stop listening - prominent action
            self.toggle_action = QAction("Start Listening", menu)
            self.toggle_action.setToolTip("Start listening for any meeting (works with all video conferencing tools)")
            self.toggle_action.triggered.connect(self._toggle_listening)
            menu.addAction(self.toggle_action)

            # Quick start hint for browser-based meetings
            browser_hint = QAction("Use for: Google Meet, Webex, any browser call", menu)
            browser_hint.setEnabled(False)
            menu.addAction(browser_hint)

            # Show overlay
            show_action = QAction("Show Overlay", menu)
            show_action.triggered.connect(self._show_overlay)
            menu.addAction(show_action)

            menu.addSeparator()

            # Account management
            if self._user_status and self._user_status.get("subscription_status") == "trial":
                upgrade_action = QAction("Upgrade to Premium", menu)
                upgrade_action.triggered.connect(self._open_upgrade)
                menu.addAction(upgrade_action)
            else:
                manage_action = QAction("Manage Subscription", menu)
                manage_action.triggered.connect(self._open_billing)
                menu.addAction(manage_action)

            # Logout
            logout_action = QAction("Logout", menu)
            logout_action.triggered.connect(self._logout)
            menu.addAction(logout_action)

        else:
            # Not logged in
            login_action = QAction("Login / Sign Up", menu)
            login_action.triggered.connect(self._show_login)
            menu.addAction(login_action)

        menu.addSeparator()

        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(self._quit)
        menu.addAction(quit_action)

        self.tray.setContextMenu(menu)

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            if api.is_logged_in():
                self._show_overlay()
            else:
                self._show_login()

    def _show_login(self):
        """Show login window."""
        if self.login_window is None:
            self.login_window = LoginWindow()
            self.login_window.login_successful.connect(self._on_login_success)
        self.login_window.show()
        self.login_window.raise_()
        self.login_window.activateWindow()

    def _on_login_success(self):
        """Called when user successfully logs in."""
        print("Login successful")
        self._refresh_user_status()
        self._update_tray_menu()
        self.tray.showMessage(
            "ReadIn AI",
            "Welcome! Auto-detects Teams, Zoom, Webex & more. For Google Meet or browser calls, right-click and select 'Start Listening'.",
            QSystemTrayIcon.MessageIcon.Information,
            5000
        )

    def _logout(self):
        """Logout user."""
        self._stop_listening()
        api.logout()
        self._user_status = None
        self._update_tray_menu()
        self.overlay.hide()

    def _refresh_user_status(self):
        """Refresh user subscription status from API."""
        if not api.is_logged_in():
            return

        status = api.get_status()
        if "error" not in status:
            self._user_status = status
            self._update_tray_menu()

            # Check if account is active
            if not status.get("is_active"):
                self.tray.showMessage(
                    "ReadIn AI",
                    "Your trial has expired. Upgrade to continue.",
                    QSystemTrayIcon.MessageIcon.Warning,
                    5000
                )

    def _show_overlay(self):
        if not api.is_logged_in():
            self._show_login()
            return

        self.overlay.show()
        self.overlay.raise_()
        self.overlay.activateWindow()

    def _toggle_listening(self):
        if not api.is_logged_in():
            self._show_login()
            return

        if self._listening:
            self._stop_listening()
        else:
            self._start_listening()

    def _start_listening(self):
        if self._listening:
            return

        # Check subscription status first
        self._refresh_user_status()
        if self._user_status and not self._user_status.get("is_active"):
            self._show_upgrade_prompt()
            return

        self._listening = True
        self.transcriber.start()
        self.audio_capture.start()
        self.overlay.reset()
        self._show_overlay()

        if hasattr(self, 'toggle_action'):
            self.toggle_action.setText("Stop Listening")
        if hasattr(self, 'status_action'):
            self.status_action.setText("Status: Listening...")
        print("Started listening for audio")

    def _stop_listening(self):
        if not self._listening:
            return

        self._listening = False
        self.audio_capture.stop()
        self.transcriber.stop()
        self.ai_assistant.clear_context()

        if hasattr(self, 'toggle_action'):
            self.toggle_action.setText("Start Listening")
        if hasattr(self, 'status_action'):
            self.status_action.setText("Status: Ready")
        print("Stopped listening")

    def _on_meeting_detected(self, process_name: str):
        if not api.is_logged_in():
            return

        print(f"Meeting app detected: {process_name}")
        if hasattr(self, 'status_action'):
            self.status_action.setText(f"Status: {process_name} detected")
        self.tray.showMessage(
            "ReadIn AI",
            f"{process_name} started. Ready to assist!",
            QSystemTrayIcon.MessageIcon.Information,
            3000
        )
        self._start_listening()

    def _on_meeting_ended(self):
        print("Meeting app closed")
        self._stop_listening()
        if hasattr(self, 'status_action'):
            self.status_action.setText("Status: Ready")
        self.overlay.hide()

    def _on_transcription(self, text: str):
        if not text.strip():
            return

        # Check if user can make request
        if not api.can_use():
            self._show_upgrade_prompt()
            return

        print(f"Heard: {text}")
        self.overlay.set_heard_text(text)
        self.ai_assistant.generate_response(text)

    def _on_streaming_chunk(self, chunk: str):
        self.overlay.append_response_text(chunk)

    def _on_ai_response(self, heard_text: str, response: str):
        print(f"Response: {response}")
        self.overlay.set_response_text(response)

        # Track usage
        result = api.increment_usage()
        if "error" not in result:
            # Update local status
            if self._user_status:
                self._user_status["daily_usage"] = result.get("count", 0)
            self._update_tray_menu()

            # Show remaining count for trial users
            remaining = result.get("remaining")
            if remaining is not None and remaining <= 3:
                self.overlay.show_usage_warning(remaining)

    def _show_upgrade_prompt(self):
        """Show upgrade dialog."""
        days = self._user_status.get("trial_days_remaining", 0) if self._user_status else 0
        dialog = UpgradePrompt(remaining_days=days)
        dialog.exec()

    def _open_upgrade(self):
        """Open Stripe checkout."""
        url = api.get_checkout_url()
        if url:
            webbrowser.open(url)

    def _open_billing(self):
        """Open Stripe billing portal."""
        url = api.get_billing_portal_url()
        if url:
            webbrowser.open(url)

    def _quit(self):
        self._stop_listening()
        self.process_monitor.stop()
        self.tray.hide()
        self.app.quit()

    def run(self):
        if not ANTHROPIC_API_KEY:
            print("WARNING: ANTHROPIC_API_KEY not set!")

        # Check login status and refresh
        if api.is_logged_in():
            print("User logged in, checking subscription...")
            self._refresh_user_status()
        else:
            print("User not logged in")
            # Show login after a short delay
            QTimer.singleShot(500, self._show_login)

        self.process_monitor.start()
        print("ReadIn AI started")

        return self.app.exec()


def main():
    app = ReadInApp()
    sys.exit(app.run())


if __name__ == "__main__":
    main()
