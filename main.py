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

# Import new components
from src.settings_manager import SettingsManager
from src.hotkey_manager import HotkeyManager
from src.export_manager import ExportManager, ConversationRecorder
from src.update_checker import UpdateChecker
from src.ui.settings_window import SettingsWindow
from src.ui.themes import generate_stylesheet

# Import meeting intelligence components
from src.meeting_session import MeetingSession
from src.context_provider import ContextProvider
from src.ui.meeting_type_dialog import MeetingTypeDialog
from src.ui.briefing_panel import BriefingPanel, SummaryPanel


class SignalBridge(QObject):
    """Bridges background threads to Qt main thread via signals."""
    meeting_detected = pyqtSignal(str)
    meeting_ended = pyqtSignal()
    transcription_ready = pyqtSignal(str)
    ai_response_ready = pyqtSignal(str, str)
    ai_chunk_ready = pyqtSignal(str)
    briefing_ready = pyqtSignal(dict)
    summary_ready = pyqtSignal(dict)


class ReadInApp:
    """Main application controller."""

    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        # Initialize settings first
        self.settings = SettingsManager()

        # Note: Don't apply global stylesheet as it interferes with overlay rendering
        # Theme is applied to individual windows (settings, login, etc.)

        self.signals = SignalBridge()
        self.signals.meeting_detected.connect(self._on_meeting_detected)
        self.signals.meeting_ended.connect(self._on_meeting_ended)
        self.signals.transcription_ready.connect(self._on_transcription)
        self.signals.ai_response_ready.connect(self._on_ai_response)
        self.signals.ai_chunk_ready.connect(self._on_streaming_chunk)
        self.signals.briefing_ready.connect(self._on_briefing_ready)
        self.signals.summary_ready.connect(self._on_summary_ready)

        # Components
        self.overlay = OverlayWindow()
        self.overlay.settings_requested.connect(self._show_settings)
        self.overlay.logout_requested.connect(self._logout)
        self.login_window = None
        self.settings_window = None
        self.ai_assistant = AIAssistant(
            on_response=lambda h, r: self.signals.ai_response_ready.emit(h, r),
            on_streaming_chunk=lambda c: self.signals.ai_chunk_ready.emit(c)
        )

        # Initialize meeting session and context provider
        self.meeting_session = MeetingSession(api)
        self.context_provider = ContextProvider(api)
        self.ai_assistant.set_context_provider(self.context_provider)

        # Briefing and summary panels (created on demand)
        self.briefing_panel = None
        self.summary_panel = None
        self._current_meeting_app = None

        # Apply AI settings
        self._apply_ai_settings()

        self.transcriber = Transcriber(
            on_transcription=lambda t: self.signals.transcription_ready.emit(t)
        )

        # Apply transcription language
        language = self.settings.get("language", "en")
        self.transcriber.set_language(language)

        # Setup audio capture with device selection
        device_index = self.settings.get("audio_device", -1)
        self.audio_capture = AudioCapture(
            on_audio_chunk=self.transcriber.process_audio,
            device_index=device_index if device_index >= 0 else None
        )

        self.process_monitor = ProcessMonitor(
            on_meeting_detected=lambda name: self.signals.meeting_detected.emit(name),
            on_meeting_ended=lambda: self.signals.meeting_ended.emit()
        )

        # Initialize conversation recorder for export
        self.conversation_recorder = ConversationRecorder()

        # Initialize hotkey manager
        self.hotkey_manager = HotkeyManager()
        self._setup_hotkeys()

        # Initialize update checker
        self.update_checker = UpdateChecker()

        self._listening = False
        self._user_status = None
        self._setup_tray()

        # Listen for settings changes
        self.settings.on_change("theme", self._on_theme_changed)
        self.settings.on_change("transcription_language", self._on_language_changed)
        self.settings.on_change("audio_device_index", self._on_audio_device_changed)

    def _apply_ai_settings(self):
        """Apply AI-related settings."""
        model = self.settings.get("model", "claude-3-5-sonnet-20241022")
        self.ai_assistant.set_model(model)

        context_size = self.settings.get("context_size", 3)
        self.ai_assistant.set_context_size(context_size)

        system_prompt = self.settings.get("system_prompt")
        if system_prompt:
            self.ai_assistant.set_system_prompt(system_prompt)

    def _setup_hotkeys(self):
        """Setup global keyboard shortcuts."""
        if not self.settings.get("shortcuts_enabled", True):
            return

        shortcuts = self.settings.get("shortcuts", {})

        self.hotkey_manager.register(
            shortcuts.get("toggle_listening", "ctrl+shift+r"),
            self._toggle_listening
        )
        self.hotkey_manager.register(
            shortcuts.get("show_hide_overlay", "ctrl+shift+h"),
            self._toggle_overlay_visibility
        )
        self.hotkey_manager.register(
            shortcuts.get("clear_context", "ctrl+shift+c"),
            self._clear_context
        )

        self.hotkey_manager.start()

    def _toggle_overlay_visibility(self):
        """Toggle overlay visibility."""
        if self.overlay.isVisible():
            self.overlay.hide()
        else:
            self._show_overlay()

    def _clear_context(self):
        """Clear conversation context."""
        self.ai_assistant.clear_context()
        self.overlay.reset()
        print("Context cleared")

    def _on_theme_changed(self, key: str, theme: str, old_value):
        """Handle theme change."""
        # Apply theme to overlay only (not global app stylesheet)
        self.overlay.set_theme(theme)

    def _on_language_changed(self, key: str, language: str, old_value):
        """Handle language change."""
        self.transcriber.set_language(language)

    def _on_audio_device_changed(self, key: str, device_index, old_value):
        """Handle audio device change."""
        was_listening = self._listening
        if was_listening:
            self.audio_capture.stop()

        self.audio_capture.set_device(device_index if device_index and device_index >= 0 else None)

        if was_listening:
            self.audio_capture.start()

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

            # Request briefing
            briefing_action = QAction("Get Pre-Meeting Briefing", menu)
            briefing_action.triggered.connect(lambda: self._request_briefing())
            menu.addAction(briefing_action)

            menu.addSeparator()

            # Settings
            settings_action = QAction("Settings...", menu)
            settings_action.triggered.connect(self._show_settings)
            menu.addAction(settings_action)

            # Export conversations
            export_action = QAction("Export Conversations...", menu)
            export_action.triggered.connect(self._export_conversations)
            menu.addAction(export_action)

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

            # Settings available even when not logged in
            settings_action = QAction("Settings...", menu)
            settings_action.triggered.connect(self._show_settings)
            menu.addAction(settings_action)

        menu.addSeparator()

        # Check for updates
        update_action = QAction("Check for Updates", menu)
        update_action.triggered.connect(self._check_for_updates)
        menu.addAction(update_action)

        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(self._quit)
        menu.addAction(quit_action)

        self.tray.setContextMenu(menu)

    def _show_settings(self):
        """Show settings window."""
        if self.settings_window is None:
            self.settings_window = SettingsWindow()
            self.settings_window.settings_changed.connect(self._on_settings_changed)
        self.settings_window.show()
        self.settings_window.raise_()
        self.settings_window.activateWindow()

    def _on_settings_changed(self):
        """Handle settings changes from settings window."""
        # Re-apply AI settings
        self._apply_ai_settings()

        # Re-setup hotkeys
        self.hotkey_manager.stop()
        self._setup_hotkeys()

        print("Settings applied")

    def _export_conversations(self):
        """Export recorded conversations."""
        history = self.ai_assistant.get_conversation_history()
        if not history:
            QMessageBox.information(
                None,
                "Export",
                "No conversations to export."
            )
            return

        from PyQt6.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getSaveFileName(
            None,
            "Export Conversations",
            "readin_export.md",
            "Markdown Files (*.md);;Text Files (*.txt);;JSON Files (*.json)"
        )

        if file_path:
            try:
                exporter = ExportManager()
                format_type = "json" if file_path.endswith(".json") else "md" if file_path.endswith(".md") else "txt"
                exporter.export(history, file_path, format_type)
                QMessageBox.information(
                    None,
                    "Export Complete",
                    f"Conversations exported to:\n{file_path}"
                )
            except Exception as e:
                QMessageBox.warning(
                    None,
                    "Export Failed",
                    f"Failed to export: {str(e)}"
                )

    def _check_for_updates(self):
        """Check for application updates."""
        try:
            has_update, info = self.update_checker.check_for_updates()

            if has_update:
                result = QMessageBox.question(
                    None,
                    "Update Available",
                    f"Version {info['version']} is available!\n\n{info.get('description', '')}\n\nWould you like to download it?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if result == QMessageBox.StandardButton.Yes and info.get("download_url"):
                    webbrowser.open(info["download_url"])
            else:
                QMessageBox.information(
                    None,
                    "Up to Date",
                    "You're running the latest version."
                )
        except Exception as e:
            QMessageBox.warning(
                None,
                "Update Check Failed",
                f"Could not check for updates:\n{str(e)}"
            )

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

        # Refresh personalization context
        self.context_provider.refresh_context()

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

        # Clear context and reset session
        self.context_provider.clear_cache()
        self.meeting_session.reset()

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

    def _start_listening(self, meeting_app: str = None, skip_dialog: bool = False):
        if self._listening:
            return

        # Check subscription status first
        self._refresh_user_status()
        if self._user_status and not self._user_status.get("is_active"):
            self._show_upgrade_prompt()
            return

        # Show meeting type dialog if not skipped (e.g., for auto-detected meetings)
        meeting_type = "general"
        meeting_title = None

        if not skip_dialog:
            result = MeetingTypeDialog.get_meeting_type(
                detected_app=meeting_app or self._current_meeting_app
            )
            if result is None:
                # User cancelled
                return
            meeting_type, meeting_title = result

        # Start the meeting session
        self.meeting_session.start(
            meeting_type=meeting_type,
            title=meeting_title,
            meeting_app=meeting_app or self._current_meeting_app
        )

        # Set meeting type on AI assistant for context
        self.ai_assistant.set_meeting_type(meeting_type)

        # Refresh personalization context
        if api.is_logged_in():
            self.context_provider.refresh_context()

        self._listening = True
        self.transcriber.start()
        self.audio_capture.start()
        self.overlay.reset()
        self._show_overlay()

        if hasattr(self, 'toggle_action'):
            self.toggle_action.setText("Stop Listening")
        if hasattr(self, 'status_action'):
            self.status_action.setText("Status: Listening...")
        print(f"Started listening for audio (type: {meeting_type})")

    def _stop_listening(self):
        if not self._listening:
            return

        self._listening = False
        self.audio_capture.stop()
        self.transcriber.stop()
        self.ai_assistant.clear_context()

        # End the meeting session and get summary
        if self.meeting_session.is_active:
            import threading
            def end_meeting():
                summary = self.meeting_session.end()
                if summary:
                    self.signals.summary_ready.emit(summary)
            threading.Thread(target=end_meeting, daemon=True).start()

        if hasattr(self, 'toggle_action'):
            self.toggle_action.setText("Start Listening")
        if hasattr(self, 'status_action'):
            self.status_action.setText("Status: Ready")
        print("Stopped listening")

    def _on_meeting_detected(self, process_name: str):
        if not api.is_logged_in():
            return

        print(f"Meeting app detected: {process_name}")
        self._current_meeting_app = process_name
        if hasattr(self, 'status_action'):
            self.status_action.setText(f"Status: {process_name} detected")
        self.tray.showMessage(
            "ReadIn AI",
            f"{process_name} started. Ready to assist!",
            QSystemTrayIcon.MessageIcon.Information,
            3000
        )
        self._start_listening(meeting_app=process_name)

    def _on_meeting_ended(self):
        print("Meeting app closed")
        self._stop_listening()
        self._current_meeting_app = None
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

        # Save conversation to meeting session
        if self.meeting_session.is_active:
            self.meeting_session.add_conversation(
                heard_text=heard_text,
                response_text=response
            )

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

    def _on_briefing_ready(self, briefing: dict):
        """Handle pre-meeting briefing data."""
        if not briefing:
            return

        # Create or update briefing panel
        if self.briefing_panel is None:
            self.briefing_panel = BriefingPanel()
            self.briefing_panel.dismissed.connect(self._dismiss_briefing)
            self.briefing_panel.start_meeting.connect(self._start_from_briefing)

        self.briefing_panel.set_briefing(briefing)
        self.briefing_panel.setFixedSize(400, 500)
        self.briefing_panel.show()
        self.briefing_panel.raise_()

    def _on_summary_ready(self, summary: dict):
        """Handle post-meeting summary data."""
        if not summary:
            return

        # Create or update summary panel
        if self.summary_panel is None:
            self.summary_panel = SummaryPanel()
            self.summary_panel.dismissed.connect(self._dismiss_summary)
            self.summary_panel.export_clicked.connect(self._export_summary)

        self.summary_panel.set_summary(summary)
        self.summary_panel.setFixedSize(400, 500)
        self.summary_panel.show()
        self.summary_panel.raise_()

    def _dismiss_briefing(self):
        """Dismiss briefing panel."""
        if self.briefing_panel:
            self.briefing_panel.hide()

    def _start_from_briefing(self):
        """Start meeting from briefing panel."""
        if self.briefing_panel:
            self.briefing_panel.hide()
        self._start_listening(skip_dialog=True)

    def _dismiss_summary(self):
        """Dismiss summary panel."""
        if self.summary_panel:
            self.summary_panel.hide()

    def _export_summary(self):
        """Export meeting summary."""
        if not self.meeting_session:
            return

        from PyQt6.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getSaveFileName(
            None,
            "Export Meeting Summary",
            "meeting_summary.md",
            "Markdown Files (*.md);;Text Files (*.txt)"
        )

        if file_path:
            try:
                conversations = self.meeting_session.get_conversations()
                session_info = self.meeting_session.get_session_info()

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"# Meeting Summary\n\n")
                    f.write(f"**Type:** {session_info.get('meeting_type', 'General')}\n")
                    if session_info.get('title'):
                        f.write(f"**Title:** {session_info['title']}\n")
                    f.write(f"**Duration:** {session_info.get('duration_seconds', 0) // 60} minutes\n")
                    f.write(f"**Conversations:** {len(conversations)}\n\n")

                    f.write("## Conversation Log\n\n")
                    for i, conv in enumerate(conversations, 1):
                        f.write(f"### Exchange {i}\n")
                        f.write(f"**Heard:** {conv['heard_text']}\n\n")
                        f.write(f"**Response:** {conv['response_text']}\n\n")

                QMessageBox.information(
                    None,
                    "Export Complete",
                    f"Summary exported to:\n{file_path}"
                )
            except Exception as e:
                QMessageBox.warning(
                    None,
                    "Export Failed",
                    f"Failed to export: {str(e)}"
                )

        if self.summary_panel:
            self.summary_panel.hide()

    def _request_briefing(self, participant_names: list = None, meeting_context: str = None):
        """Request a pre-meeting briefing."""
        if not api.is_logged_in():
            return

        import threading
        def fetch_briefing():
            briefing = self.context_provider.get_briefing_context(
                participant_names=participant_names,
                meeting_context=meeting_context
            )
            if briefing:
                self.signals.briefing_ready.emit(briefing)

        threading.Thread(target=fetch_briefing, daemon=True).start()

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

        # End any active meeting session
        if self.meeting_session.is_active:
            self.meeting_session.end()

        self.process_monitor.stop()
        self.hotkey_manager.stop()
        self.tray.hide()
        self.app.quit()

    def run(self):
        if not ANTHROPIC_API_KEY:
            print("WARNING: ANTHROPIC_API_KEY not set!")

        # Check login status and refresh
        if api.is_logged_in():
            print("User logged in, checking subscription...")
            self._refresh_user_status()

            # Refresh personalization context
            self.context_provider.refresh_context()

            # Check for active meeting to resume
            if self.meeting_session.resume_active():
                print("Resumed active meeting session")
        else:
            print("User not logged in")
            # Show login after a short delay
            QTimer.singleShot(500, self._show_login)

        self.process_monitor.start()
        print("ReadIn AI started")

        # Check for updates on startup if enabled
        if self.settings.get("auto_update_check", True):
            QTimer.singleShot(3000, self._startup_update_check)

        return self.app.exec()

    def _startup_update_check(self):
        """Silent update check on startup."""
        try:
            has_update, info = self.update_checker.check_for_updates()
            if has_update:
                self.tray.showMessage(
                    "ReadIn AI Update",
                    f"Version {info['version']} is available! Click to download.",
                    QSystemTrayIcon.MessageIcon.Information,
                    5000
                )
        except Exception:
            pass  # Silently ignore startup update check failures


def main():
    app = ReadInApp()
    sys.exit(app.run())


if __name__ == "__main__":
    main()
