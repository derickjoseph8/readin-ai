"""First Run Setup Wizard for ReadIn AI."""

import sys
import os
from pathlib import Path
from typing import Optional
from PyQt6.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QHBoxLayout, QLabel,
    QCheckBox, QPushButton, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPalette, QColor, QPixmap

from src.ui.audio_setup_dialog import AudioSetupDialog
from src.audio_capture import AudioCapture


class WelcomePage(QWizardPage):
    """Welcome page of the setup wizard."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Welcome to ReadIn AI")
        self.setSubTitle("Your AI-powered meeting assistant")

        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        # Welcome message
        welcome_label = QLabel(
            "ReadIn AI helps you sound brilliant in every meeting by providing "
            "real-time AI-powered talking points.\n\n"
            "This quick setup will:\n"
            "• Configure your audio settings\n"
            "• Set up convenient shortcuts\n"
            "• Get you ready to use the app\n\n"
            "Click Next to continue."
        )
        welcome_label.setWordWrap(True)
        welcome_label.setStyleSheet("font-size: 13px;")
        layout.addWidget(welcome_label)

        layout.addStretch()


class AudioSetupPage(QWizardPage):
    """Audio configuration page."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Audio Setup")
        self.setSubTitle("Select which audio source to capture")
        self._device_index = None

        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Explanation
        info_label = QLabel(
            "To capture what others say in meetings, select a loopback device "
            "(like Stereo Mix or VB-Cable Output).\n\n"
            "If you only see microphones, you'll need to enable Stereo Mix in "
            "Windows Sound Settings, or install VB-Cable (free)."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Device info frame
        self.device_frame = QFrame()
        self.device_frame.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border: 1px solid #444;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        device_layout = QVBoxLayout(self.device_frame)

        self.device_label = QLabel("No device selected")
        self.device_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        device_layout.addWidget(self.device_label)

        self.device_type_label = QLabel("")
        self.device_type_label.setStyleSheet("color: #888;")
        device_layout.addWidget(self.device_type_label)

        layout.addWidget(self.device_frame)

        # Configure button
        self.configure_btn = QPushButton("Configure Audio Device...")
        self.configure_btn.setStyleSheet("""
            QPushButton {
                background-color: #22c55e;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #16a34a;
            }
        """)
        self.configure_btn.clicked.connect(self._configure_audio)
        layout.addWidget(self.configure_btn)

        layout.addStretch()

        # Auto-select recommended device
        self._auto_select_device()

    def _auto_select_device(self):
        """Auto-select the recommended device."""
        recommended = AudioCapture.get_recommended_device()
        if recommended is not None:
            self._device_index = recommended
            self._update_device_display()

    def _configure_audio(self):
        """Open audio configuration dialog."""
        device_index = AudioSetupDialog.get_audio_device(self)
        if device_index is not None:
            self._device_index = device_index
            self._update_device_display()

    def _update_device_display(self):
        """Update the device display."""
        if self._device_index is None:
            self.device_label.setText("No device selected")
            self.device_type_label.setText("")
            return

        devices = AudioCapture.get_available_devices()
        for device in devices:
            if device['index'] == self._device_index:
                self.device_label.setText(device['name'])
                if device['is_loopback']:
                    self.device_type_label.setText("✓ Loopback device - Will capture meeting audio")
                    self.device_type_label.setStyleSheet("color: #22c55e;")
                else:
                    self.device_type_label.setText("⚠ Microphone - Will capture your voice only")
                    self.device_type_label.setStyleSheet("color: #f59e0b;")
                break

    def get_device_index(self) -> Optional[int]:
        """Get the selected device index."""
        return self._device_index


class ShortcutsPage(QWizardPage):
    """Shortcuts and startup configuration page."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Convenience Settings")
        self.setSubTitle("Make ReadIn AI easy to access")

        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Startup option
        self.startup_check = QCheckBox("Start ReadIn AI when Windows starts")
        self.startup_check.setChecked(True)
        self.startup_check.setStyleSheet("font-size: 13px;")
        layout.addWidget(self.startup_check)

        startup_hint = QLabel(
            "Recommended: The app runs quietly in the system tray and "
            "automatically activates when you join a meeting."
        )
        startup_hint.setWordWrap(True)
        startup_hint.setStyleSheet("color: #888; margin-left: 24px; font-size: 11px;")
        layout.addWidget(startup_hint)

        layout.addSpacing(16)

        # Desktop shortcut
        self.shortcut_check = QCheckBox("Create desktop shortcut")
        self.shortcut_check.setChecked(True)
        self.shortcut_check.setStyleSheet("font-size: 13px;")
        layout.addWidget(self.shortcut_check)

        layout.addSpacing(24)

        # Keyboard shortcuts info
        shortcuts_frame = QFrame()
        shortcuts_frame.setStyleSheet("""
            QFrame {
                background-color: #1e3a5f;
                border: 1px solid #3b82f6;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        shortcuts_layout = QVBoxLayout(shortcuts_frame)

        shortcuts_title = QLabel("Keyboard Shortcuts")
        shortcuts_title.setStyleSheet("font-weight: bold; color: #60a5fa;")
        shortcuts_layout.addWidget(shortcuts_title)

        shortcuts_text = QLabel(
            "Ctrl+Shift+R - Start/Stop listening\n"
            "Ctrl+Shift+H - Show/Hide overlay\n"
            "Ctrl+Shift+C - Clear conversation context"
        )
        shortcuts_text.setStyleSheet("color: #93c5fd; font-family: monospace;")
        shortcuts_layout.addWidget(shortcuts_text)

        layout.addWidget(shortcuts_frame)

        layout.addStretch()

    def should_add_to_startup(self) -> bool:
        """Check if user wants to add to startup."""
        return self.startup_check.isChecked()

    def should_create_shortcut(self) -> bool:
        """Check if user wants desktop shortcut."""
        return self.shortcut_check.isChecked()


class CompletePage(QWizardPage):
    """Setup complete page."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Setup Complete!")
        self.setSubTitle("You're ready to use ReadIn AI")

        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        # Success message
        success_label = QLabel(
            "ReadIn AI is now configured and ready to use!\n\n"
            "How it works:\n"
            "1. Start or join a meeting (Teams, Zoom, Google Meet, etc.)\n"
            "2. ReadIn AI automatically detects the meeting\n"
            "3. An overlay appears with AI-powered talking points\n"
            "4. Glance at the suggestions and speak naturally\n\n"
            "The app runs in the system tray - look for the ReadIn AI icon."
        )
        success_label.setWordWrap(True)
        success_label.setStyleSheet("font-size: 13px;")
        layout.addWidget(success_label)

        # Tip
        tip_frame = QFrame()
        tip_frame.setStyleSheet("""
            QFrame {
                background-color: #1a3a1a;
                border: 1px solid #22c55e;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        tip_layout = QVBoxLayout(tip_frame)

        tip_title = QLabel("💡 Tip")
        tip_title.setStyleSheet("font-weight: bold; color: #22c55e;")
        tip_layout.addWidget(tip_title)

        tip_text = QLabel(
            "For browser-based meetings (Google Meet, Webex in browser), "
            "right-click the tray icon and select 'Start Listening' manually."
        )
        tip_text.setWordWrap(True)
        tip_text.setStyleSheet("color: #86efac;")
        tip_layout.addWidget(tip_text)

        layout.addWidget(tip_frame)

        layout.addStretch()


class FirstRunWizard(QWizard):
    """First run setup wizard."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ReadIn AI Setup")
        self.setFixedSize(550, 450)
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)

        # Apply dark theme
        self._apply_dark_theme()

        # Add pages
        self.welcome_page = WelcomePage()
        self.audio_page = AudioSetupPage()
        self.shortcuts_page = ShortcutsPage()
        self.complete_page = CompletePage()

        self.addPage(self.welcome_page)
        self.addPage(self.audio_page)
        self.addPage(self.shortcuts_page)
        self.addPage(self.complete_page)

        # Connect finish signal
        self.finished.connect(self._on_finished)

    def _apply_dark_theme(self):
        """Apply dark theme."""
        self.setStyleSheet("""
            QWizard {
                background-color: #1e1e1e;
            }
            QWizardPage {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
            }
            QCheckBox {
                color: #ffffff;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QPushButton {
                background-color: #3d3d3d;
                color: #ffffff;
                border: 1px solid #555;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
        """)

    def _on_finished(self, result):
        """Handle wizard completion."""
        if result == QWizard.DialogCode.Accepted:
            self._apply_settings()

    def _apply_settings(self):
        """Apply the configured settings."""
        # Add to startup if requested
        if self.shortcuts_page.should_add_to_startup():
            self._add_to_startup()

        # Create desktop shortcut if requested
        if self.shortcuts_page.should_create_shortcut():
            self._create_desktop_shortcut()

    def _add_to_startup(self):
        """Add app to system startup (cross-platform)."""
        exe_path = sys.executable

        if sys.platform == 'win32':
            # Windows: Registry
            try:
                import winreg
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Run",
                    0, winreg.KEY_SET_VALUE
                )
                winreg.SetValueEx(key, "ReadInAI", 0, winreg.REG_SZ, exe_path)
                winreg.CloseKey(key)
                print("Added to Windows startup")
            except Exception as e:
                print(f"Failed to add to Windows startup: {e}")

        elif sys.platform == 'darwin':
            # macOS: Launch Agent
            try:
                launch_agents_dir = Path.home() / "Library" / "LaunchAgents"
                launch_agents_dir.mkdir(parents=True, exist_ok=True)

                plist_path = launch_agents_dir / "com.brider.readin-ai.plist"
                plist_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.brider.readin-ai</string>
    <key>ProgramArguments</key>
    <array>
        <string>{exe_path}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
'''
                plist_path.write_text(plist_content)
                print(f"Added to macOS startup: {plist_path}")
            except Exception as e:
                print(f"Failed to add to macOS startup: {e}")

        elif sys.platform.startswith('linux'):
            # Linux: XDG Autostart
            try:
                autostart_dir = Path.home() / ".config" / "autostart"
                autostart_dir.mkdir(parents=True, exist_ok=True)

                desktop_path = autostart_dir / "readin-ai.desktop"
                desktop_content = f'''[Desktop Entry]
Type=Application
Name=ReadIn AI
Comment=AI Meeting Assistant
Exec={exe_path}
Icon=readin-ai
Terminal=false
Categories=Utility;
X-GNOME-Autostart-enabled=true
'''
                desktop_path.write_text(desktop_content)
                print(f"Added to Linux autostart: {desktop_path}")
            except Exception as e:
                print(f"Failed to add to Linux autostart: {e}")

    def _create_desktop_shortcut(self):
        """Create desktop shortcut (cross-platform)."""
        exe_path = sys.executable
        desktop = Path.home() / "Desktop"

        # Ensure desktop exists
        if not desktop.exists():
            print(f"Desktop directory not found: {desktop}")
            return

        if sys.platform == 'win32':
            shortcut_path = desktop / "ReadIn AI.lnk"

            # Method 1: Try using win32com (pywin32)
            try:
                from win32com.client import Dispatch

                shell = Dispatch('WScript.Shell')
                shortcut = shell.CreateShortCut(str(shortcut_path))
                shortcut.Targetpath = exe_path
                shortcut.WorkingDirectory = os.path.dirname(exe_path)
                shortcut.IconLocation = exe_path
                shortcut.Description = "ReadIn AI - AI Meeting Assistant"
                shortcut.save()
                print(f"Created desktop shortcut: {shortcut_path}")
                return
            except ImportError:
                pass
            except Exception as e:
                print(f"win32com shortcut failed: {e}")

            # Method 2: Use PowerShell
            try:
                import subprocess

                shortcut_path_str = str(shortcut_path).replace("'", "''")
                exe_path_str = exe_path.replace("'", "''")
                work_dir_str = os.path.dirname(exe_path).replace("'", "''")

                ps_script = f'''
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut('{shortcut_path_str}')
$Shortcut.TargetPath = '{exe_path_str}'
$Shortcut.WorkingDirectory = '{work_dir_str}'
$Shortcut.Description = 'ReadIn AI - AI Meeting Assistant'
$Shortcut.Save()
'''
                result = subprocess.run(
                    ['powershell', '-NoProfile', '-Command', ps_script],
                    capture_output=True,
                    text=True
                )

                if result.returncode == 0:
                    print(f"Created desktop shortcut via PowerShell: {shortcut_path}")
                else:
                    print(f"PowerShell shortcut failed: {result.stderr}")
            except Exception as e:
                print(f"Failed to create Windows shortcut: {e}")

        elif sys.platform == 'darwin':
            # macOS: Create an alias or app bundle
            try:
                import subprocess

                # Create a simple shell script wrapper
                app_path = desktop / "ReadIn AI.command"
                app_content = f'''#!/bin/bash
cd "{os.path.dirname(exe_path)}"
"{exe_path}" &
'''
                app_path.write_text(app_content)
                os.chmod(app_path, 0o755)
                print(f"Created macOS shortcut: {app_path}")
            except Exception as e:
                print(f"Failed to create macOS shortcut: {e}")

        elif sys.platform.startswith('linux'):
            # Linux: .desktop file
            try:
                desktop_path = desktop / "ReadIn AI.desktop"
                desktop_content = f'''[Desktop Entry]
Type=Application
Name=ReadIn AI
Comment=AI Meeting Assistant
Exec={exe_path}
Icon=readin-ai
Terminal=false
Categories=Utility;
'''
                desktop_path.write_text(desktop_content)
                os.chmod(desktop_path, 0o755)
                print(f"Created Linux desktop shortcut: {desktop_path}")
            except Exception as e:
                print(f"Failed to create Linux shortcut: {e}")

    def get_audio_device(self) -> Optional[int]:
        """Get the selected audio device index."""
        return self.audio_page.get_device_index()

    @staticmethod
    def run_wizard(parent=None) -> tuple:
        """Run the wizard and return (accepted, device_index).

        Returns:
            Tuple of (was_accepted, selected_device_index)
        """
        wizard = FirstRunWizard(parent)
        result = wizard.exec()
        accepted = result == QWizard.DialogCode.Accepted
        device_index = wizard.get_audio_device() if accepted else None
        return accepted, device_index
