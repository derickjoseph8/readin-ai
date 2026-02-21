"""Audio Setup Dialog for first-run configuration (cross-platform)."""

import subprocess
import os
import sys
import threading
import time
import webbrowser
from typing import Optional, List, Dict, Any
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QRadioButton, QButtonGroup, QFrame, QScrollArea, QWidget,
    QMessageBox, QProgressBar
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QMetaObject, Q_ARG, Qt as QtCore, pyqtSlot
from PyQt6.QtGui import QFont, QPalette, QColor

import numpy as np

from src.audio_capture import AudioCapture
from src.drivers.driver_installer import VirtualAudioInstaller
from config import IS_WINDOWS, IS_MACOS, IS_LINUX


class AudioSetupDialog(QDialog):
    """Dialog for selecting audio input device on first run."""

    audio_level_updated = pyqtSignal(float)
    # Signal for thread-safe testing state changes
    testing_state_changed = pyqtSignal(bool)
    # Signal for thread-safe test cleanup
    test_cleanup_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected_device = None
        self._devices = []
        self._testing = False
        self._test_thread = None
        self._audio_levels = []
        self._apply_dark_theme()
        self.setup_ui()

        # Connect signals for thread-safe UI updates
        self.audio_level_updated.connect(self._update_audio_level_display)
        self.testing_state_changed.connect(self._on_testing_state_changed)
        self.test_cleanup_requested.connect(self._cleanup_test_thread)

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
        self.setFixedWidth(460)
        self.setMinimumHeight(350)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        # Header
        header = QLabel("Audio Input Setup")
        header.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        header.setStyleSheet("color: #ffffff; background: transparent;")
        layout.addWidget(header)

        # Description - platform specific
        if IS_WINDOWS:
            desc_text = (
                "Select the audio source ReadIn AI should listen to.\n\n"
                "To capture meeting audio (what others say), select a loopback device "
                "like 'Stereo Mix' or 'CABLE Output'."
            )
        elif IS_MACOS:
            desc_text = (
                "Select the audio source ReadIn AI should listen to.\n\n"
                "To capture meeting audio, install BlackHole (free) and select it. "
                "Run: brew install blackhole-2ch"
            )
        else:  # Linux
            desc_text = (
                "Select the audio source ReadIn AI should listen to.\n\n"
                "To capture meeting audio, select a 'Monitor' device from PulseAudio "
                "(e.g., 'Monitor of Built-in Audio')."
            )

        desc = QLabel(desc_text)
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #aaaaaa; font-size: 11px; background: transparent;")
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
                        padding: 6px;
                        background-color: #1a3a1a;
                        border-radius: 6px;
                    }
                    QRadioButton::indicator {
                        width: 14px;
                        height: 14px;
                    }
                """)
            else:
                radio.setStyleSheet("""
                    QRadioButton {
                        color: #cccccc;
                        padding: 6px;
                    }
                    QRadioButton::indicator {
                        width: 14px;
                        height: 14px;
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

        # Audio test section
        test_frame = QFrame()
        test_frame.setStyleSheet("""
            QFrame {
                background-color: #2a2a2a;
                border: 1px solid #444444;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        test_layout = QVBoxLayout(test_frame)
        test_layout.setContentsMargins(12, 8, 12, 8)

        test_label = QLabel("Test Selected Device:")
        test_label.setStyleSheet("color: #ffffff; font-weight: bold; background: transparent;")
        test_layout.addWidget(test_label)

        test_desc = QLabel(
            "Click 'Test' and speak or play audio from your meeting app.\n"
            "The level bar should move if the correct device is selected."
        )
        test_desc.setWordWrap(True)
        test_desc.setStyleSheet("color: #888888; font-size: 11px; background: transparent;")
        test_layout.addWidget(test_desc)

        # Audio level indicator
        self.audio_level_bar = QProgressBar()
        self.audio_level_bar.setMinimum(0)
        self.audio_level_bar.setMaximum(100)
        self.audio_level_bar.setValue(0)
        self.audio_level_bar.setTextVisible(False)
        self.audio_level_bar.setFixedHeight(16)
        self.audio_level_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #444444;
                border-radius: 4px;
                background-color: #1e1e1e;
            }
            QProgressBar::chunk {
                background-color: #22c55e;
                border-radius: 3px;
            }
        """)
        test_layout.addWidget(self.audio_level_bar)

        # Test button row
        test_btn_row = QHBoxLayout()
        self.test_btn = QPushButton("Test Device")
        self.test_btn.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                color: #ffffff;
                border: 1px solid #555555;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
            QPushButton:pressed {
                background-color: #2d2d2d;
            }
        """)
        self.test_btn.clicked.connect(self._toggle_test)
        test_btn_row.addWidget(self.test_btn)
        test_btn_row.addStretch()

        self.test_status = QLabel("")
        self.test_status.setStyleSheet("color: #888888; font-size: 11px; background: transparent;")
        test_btn_row.addWidget(self.test_status)

        test_layout.addLayout(test_btn_row)
        layout.addWidget(test_frame)

        # Store reference to device frame for refreshing
        self._device_frame = device_frame
        self._main_layout = layout

        # Warning/Install section if no loopback devices
        self._warning_frame = None
        if not has_loopback:
            self._create_install_section(layout)

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
        # Stop any ongoing test when device changes
        if self._testing:
            self._stop_test()

    def _toggle_test(self):
        """Toggle audio device test."""
        if self._testing:
            self._stop_test()
        else:
            self._start_test()

    def _start_test(self):
        """Start testing the selected audio device."""
        if self._selected_device is None:
            QMessageBox.warning(self, "No Device", "Please select an audio device first.")
            return

        # Use signal for thread-safe state change
        self._set_testing_state(True)
        self.test_btn.setText("Stop Test")
        self.test_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc2626;
                color: #ffffff;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #b91c1c;
            }
        """)
        self.test_status.setText("Listening... speak or play audio")
        self.test_status.setStyleSheet("color: #22c55e; font-size: 11px; background: transparent;")

        # Start test thread
        self._test_thread = threading.Thread(target=self._test_audio_loop, daemon=True)
        self._test_thread.start()

    def _stop_test(self):
        """Stop the audio test with proper thread cleanup."""
        # Use signal for thread-safe state change
        self._set_testing_state(False)
        self.test_btn.setText("Test Device")
        self.test_btn.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                color: #ffffff;
                border: 1px solid #555555;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
        """)
        self.test_status.setText("")
        self.audio_level_bar.setValue(0)

        # Request cleanup of test thread
        self.test_cleanup_requested.emit()

    def _set_testing_state(self, testing: bool):
        """Thread-safe method to set testing state."""
        self._testing = testing
        self.testing_state_changed.emit(testing)

    def _on_testing_state_changed(self, testing: bool):
        """Handle testing state change in main thread."""
        # This runs in the main thread, safe for UI updates
        pass  # UI updates are done in _start_test and _stop_test

    def _cleanup_test_thread(self):
        """Properly cleanup the test thread."""
        if self._test_thread is not None:
            # Wait briefly for thread to finish
            if self._test_thread.is_alive():
                self._test_thread.join(timeout=0.5)
            self._test_thread = None

    def _is_testing(self) -> bool:
        """Thread-safe method to check testing state."""
        return self._testing

    def _test_audio_loop(self):
        """Audio test loop running in background thread (cross-platform)."""
        try:
            if IS_WINDOWS:
                self._test_audio_windows()
            else:
                self._test_audio_sounddevice()
        except Exception as e:
            print(f"Audio test error: {e}")
            # Use signal for thread-safe state change
            self._set_testing_state(False)

    def _test_audio_windows(self):
        """Test audio on Windows using PyAudio."""
        import pyaudio

        try:
            pa = pyaudio.PyAudio()

            # Get device info
            device_info = pa.get_device_info_by_index(self._selected_device)
            channels = min(int(device_info['maxInputChannels']), 2)
            sample_rate = int(device_info.get('defaultSampleRate', 16000))

            # Try device's native sample rate first
            try:
                stream = pa.open(
                    format=pyaudio.paInt16,
                    channels=channels,
                    rate=sample_rate,
                    input=True,
                    input_device_index=self._selected_device,
                    frames_per_buffer=1024,
                )
            except Exception:
                # Fall back to 16kHz
                stream = pa.open(
                    format=pyaudio.paInt16,
                    channels=channels,
                    rate=16000,
                    input=True,
                    input_device_index=self._selected_device,
                    frames_per_buffer=1024,
                )

            while self._is_testing():
                try:
                    data = stream.read(1024, exception_on_overflow=False)
                    audio = np.frombuffer(data, dtype=np.int16).astype(np.float32)

                    # Calculate RMS level
                    rms = np.sqrt(np.mean(audio ** 2))
                    # Normalize to 0-100 scale
                    level = min(100, int(rms / 200))

                    # Emit signal to update UI (thread-safe via Qt signals)
                    self.audio_level_updated.emit(level)

                except Exception:
                    break

            stream.stop_stream()
            stream.close()
            pa.terminate()

        except Exception as e:
            print(f"Windows audio test error: {e}")
            # Use signal for thread-safe state change
            self._set_testing_state(False)

    def _test_audio_sounddevice(self):
        """Test audio on macOS/Linux using sounddevice."""
        import sounddevice as sd

        try:
            # Get device info
            device_info = sd.query_devices(self._selected_device)
            channels = min(int(device_info['max_input_channels']), 2)
            sample_rate = int(device_info.get('default_samplerate', 16000))

            # Audio callback to process data
            audio_data = []

            def callback(indata, frames, time_info, status):
                if self._testing:
                    audio_data.append(indata.copy())

            # Try device's native sample rate first
            try:
                stream = sd.InputStream(
                    device=self._selected_device,
                    channels=channels,
                    samplerate=sample_rate,
                    dtype=np.float32,
                    callback=callback,
                    blocksize=1024,
                )
            except Exception:
                # Fall back to 16kHz
                stream = sd.InputStream(
                    device=self._selected_device,
                    channels=channels,
                    samplerate=16000,
                    dtype=np.float32,
                    callback=callback,
                    blocksize=1024,
                )

            stream.start()

            while self._is_testing():
                time.sleep(0.05)  # 50ms update interval

                if audio_data:
                    # Get latest audio data
                    latest = audio_data[-1]
                    audio_data.clear()

                    # Convert to mono if stereo
                    if latest.ndim > 1:
                        audio = latest.mean(axis=1)
                    else:
                        audio = latest.flatten()

                    # Calculate RMS level
                    rms = np.sqrt(np.mean(audio ** 2))
                    # Normalize to 0-100 scale (float32 is -1 to 1)
                    level = min(100, int(rms * 500))

                    # Emit signal to update UI
                    self.audio_level_updated.emit(level)

            stream.stop()
            stream.close()

        except Exception as e:
            print(f"sounddevice audio test error: {e}")
            # Use signal for thread-safe state change
            self._set_testing_state(False)

    @pyqtSlot(float)
    def _update_audio_level_display(self, level: float):
        """Update the audio level bar (called from main thread via signal)."""
        self.audio_level_bar.setValue(int(level))

    def _invoke_ui_update(self, method_name: str, *args):
        """Thread-safe UI update using QMetaObject.invokeMethod.

        This provides an alternative to signals for cross-thread calls,
        ensuring UI updates happen on the main thread.

        Args:
            method_name: Name of the method to invoke
            *args: Arguments to pass to the method
        """
        QMetaObject.invokeMethod(
            self,
            method_name,
            QtCore.ConnectionType.QueuedConnection
        )

    def _open_sound_settings(self):
        """Open Windows Sound settings."""
        if not IS_WINDOWS:
            return

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

    def _open_vbcable_download(self):
        """Open VB-Cable download page."""
        webbrowser.open("https://vb-audio.com/Cable/")

    def _install_blackhole(self):
        """Install BlackHole via Homebrew on macOS."""
        if not IS_MACOS:
            return

        try:
            # Try to run brew install in Terminal
            script = '''
            tell application "Terminal"
                activate
                do script "brew install blackhole-2ch && echo 'BlackHole installed! Please restart ReadIn AI.' && read"
            end tell
            '''
            subprocess.Popen(['osascript', '-e', script])
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error",
                f"Could not run Homebrew: {e}\n\n"
                "Please install manually:\n"
                "1. Open Terminal\n"
                "2. Run: brew install blackhole-2ch\n"
                "3. Restart ReadIn AI"
            )

    def _open_blackhole_download(self):
        """Open BlackHole download page."""
        webbrowser.open("https://existential.audio/blackhole/")

    def _open_pavucontrol(self):
        """Open PulseAudio Volume Control on Linux."""
        if not IS_LINUX:
            return

        try:
            subprocess.Popen(['pavucontrol'])
        except FileNotFoundError:
            QMessageBox.warning(
                self,
                "PulseAudio Control Not Found",
                "pavucontrol is not installed.\n\n"
                "Install it with:\n"
                "  Ubuntu/Debian: sudo apt install pavucontrol\n"
                "  Fedora: sudo dnf install pavucontrol\n"
                "  Arch: sudo pacman -S pavucontrol"
            )
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error",
                f"Could not open PulseAudio Control: {e}"
            )

    def _create_install_section(self, layout):
        """Create compact install section for virtual audio driver."""
        self._warning_frame = QFrame()
        self._warning_frame.setStyleSheet("""
            QFrame {
                background-color: #2a3a2a;
                border: 1px solid #22c55e;
                border-radius: 6px;
            }
        """)
        warning_layout = QVBoxLayout(self._warning_frame)
        warning_layout.setContentsMargins(12, 8, 12, 8)
        warning_layout.setSpacing(6)

        # Compact message with install button
        driver_name = VirtualAudioInstaller.get_driver_name()

        header_row = QHBoxLayout()
        warning_title = QLabel(f"Install {driver_name} for meeting audio capture")
        warning_title.setStyleSheet("color: #22c55e; font-weight: bold; font-size: 11px; background: transparent;")
        header_row.addWidget(warning_title)
        header_row.addStretch()
        warning_layout.addLayout(header_row)

        # Button row
        btn_row = QHBoxLayout()

        self._install_btn = QPushButton(VirtualAudioInstaller.get_install_button_text())
        self._install_btn.setStyleSheet("""
            QPushButton {
                background-color: #22c55e;
                color: #ffffff;
                border: none;
                padding: 6px 16px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #16a34a;
            }
            QPushButton:disabled {
                background-color: #4a4a4a;
                color: #888888;
            }
        """)
        self._install_btn.clicked.connect(self._install_virtual_audio)
        btn_row.addWidget(self._install_btn)

        self._refresh_btn = QPushButton("Refresh")
        self._refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                color: #ffffff;
                border: 1px solid #555555;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
        """)
        self._refresh_btn.clicked.connect(self._refresh_devices)
        btn_row.addWidget(self._refresh_btn)

        btn_row.addStretch()

        # Install status label
        self._install_status = QLabel("")
        self._install_status.setStyleSheet("color: #888888; font-size: 10px; background: transparent;")
        btn_row.addWidget(self._install_status)

        warning_layout.addLayout(btn_row)
        layout.addWidget(self._warning_frame)

    def _install_virtual_audio(self):
        """Install virtual audio driver."""
        self._install_btn.setEnabled(False)
        self._install_btn.setText("Installing...")
        self._install_status.setText("")
        self._install_status.setStyleSheet("color: #888888; font-size: 10px; background: transparent;")

        # Run installation in background thread
        def install_thread():
            def progress_callback(msg):
                # Update status from main thread
                QTimer.singleShot(0, lambda: self._install_status.setText(msg))

            result = VirtualAudioInstaller.install(progress_callback)

            # Update UI from main thread
            QTimer.singleShot(0, lambda: self._on_install_complete(result))

        thread = threading.Thread(target=install_thread, daemon=True)
        thread.start()

    def _on_install_complete(self, result):
        """Handle installation completion."""
        self._install_btn.setEnabled(True)
        self._install_btn.setText(VirtualAudioInstaller.get_install_button_text())

        if result.success:
            self._install_status.setText(result.message)
            self._install_status.setStyleSheet("color: #22c55e; font-size: 10px; background: transparent;")

            if result.needs_restart:
                # Refresh devices after a short delay
                QTimer.singleShot(1000, self._refresh_devices)
        else:
            self._install_status.setText(result.message)
            self._install_status.setStyleSheet("color: #f59e0b; font-size: 10px; background: transparent;")

    def _refresh_devices(self):
        """Refresh the device list."""
        # Stop any ongoing test
        if self._testing:
            self._stop_test()

        # Clear existing device buttons
        for btn in self.button_group.buttons():
            self.button_group.removeButton(btn)
            btn.deleteLater()

        # Clear device frame layout
        device_layout = self._device_frame.layout()
        while device_layout.count():
            item = device_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Reload devices
        self._devices = AudioCapture.get_available_devices()
        self._selected_device = None

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

            if device['is_loopback']:
                radio.setStyleSheet("""
                    QRadioButton {
                        color: #22c55e;
                        font-weight: bold;
                        padding: 6px;
                        background-color: #1a3a1a;
                        border-radius: 6px;
                    }
                    QRadioButton::indicator {
                        width: 14px;
                        height: 14px;
                    }
                """)
            else:
                radio.setStyleSheet("""
                    QRadioButton {
                        color: #cccccc;
                        padding: 6px;
                    }
                    QRadioButton::indicator {
                        width: 14px;
                        height: 14px;
                    }
                """)

            radio.setProperty("device_index", device['index'])
            self.button_group.addButton(radio, i)
            device_layout.addWidget(radio)

            if device['is_loopback'] and self._selected_device is None:
                radio.setChecked(True)
                self._selected_device = device['index']

        if self._selected_device is None and self._devices:
            first_btn = self.button_group.button(0)
            if first_btn:
                first_btn.setChecked(True)
                self._selected_device = self._devices[0]['index']

        device_layout.addStretch()

        # Update warning frame visibility
        if has_loopback and self._warning_frame:
            self._warning_frame.hide()
            self._install_status.setText("Virtual audio detected!")
            self._install_status.setStyleSheet("color: #22c55e; font-size: 10px; background: transparent;")

    def get_selected_device(self) -> Optional[int]:
        """Get the selected device index."""
        return self._selected_device

    def closeEvent(self, event):
        """Handle dialog close - stop any ongoing test."""
        self._stop_test()
        super().closeEvent(event)

    def reject(self):
        """Handle dialog rejection (cancel/escape)."""
        self._stop_test()
        super().reject()

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
