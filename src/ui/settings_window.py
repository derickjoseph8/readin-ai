"""
Settings Window UI

Provides a tabbed settings dialog with the following tabs:
- Audio: Device selection, input settings
- AI: Custom prompts, model selection, context window
- Appearance: Themes, opacity, font size
- Shortcuts: Global hotkey configuration
- Advanced: Export, updates, debug options
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QComboBox, QSlider, QPushButton, QLineEdit,
    QTextEdit, QSpinBox, QCheckBox, QGroupBox, QFormLayout,
    QMessageBox, QFileDialog, QListWidget, QListWidgetItem,
    QInputDialog, QFrame, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeySequence, QFont

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from settings_manager import SettingsManager
from ai_personas import AI_PERSONAS

# Get presets and languages from the class
PROMPT_PRESETS = SettingsManager.PROMPT_PRESETS
SUPPORTED_LANGUAGES = SettingsManager.SUPPORTED_LANGUAGES
from ui.themes import THEMES, generate_stylesheet
from audio_capture import AudioCapture


class ShortcutEdit(QLineEdit):
    """Custom widget for capturing keyboard shortcuts."""

    shortcut_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setPlaceholderText("Click and press shortcut...")

    def keyPressEvent(self, event):
        modifiers = event.modifiers()
        key = event.key()

        # Ignore standalone modifier keys
        if key in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
            return

        # Build shortcut string
        parts = []
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            parts.append("ctrl")
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            parts.append("shift")
        if modifiers & Qt.KeyboardModifier.AltModifier:
            parts.append("alt")

        # Get key name
        key_name = QKeySequence(key).toString().lower()
        if key_name:
            parts.append(key_name)

        shortcut = "+".join(parts)
        self.setText(shortcut)
        self.shortcut_changed.emit(shortcut)


class SettingsWindow(QDialog):
    """Main settings dialog with tabbed interface."""

    settings_changed = pyqtSignal()
    # Signal emitted when theme changes for immediate application
    theme_changed = pyqtSignal(str)
    # Signal emitted when shortcuts change for immediate registration
    shortcuts_changed = pyqtSignal(dict)
    # Signal emitted when specific settings change
    setting_changed = pyqtSignal(str, object)  # key, value

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = SettingsManager()
        self._original_theme = self.settings.get("theme", "dark_gold")
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        """Initialize the UI components."""
        self.setWindowTitle("ReadIn AI Settings")
        self.setMinimumSize(600, 500)

        # Apply theme
        theme = self.settings.get("theme", "dark_gold")
        self.setStyleSheet(generate_stylesheet(theme))

        layout = QVBoxLayout(self)

        # Create tab widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Add tabs
        self.tabs.addTab(self.create_audio_tab(), "Audio")
        self.tabs.addTab(self.create_ai_tab(), "AI")
        self.tabs.addTab(self.create_translation_tab(), "Translation")
        self.tabs.addTab(self.create_appearance_tab(), "Appearance")
        self.tabs.addTab(self.create_shortcuts_tab(), "Shortcuts")
        self.tabs.addTab(self.create_diarization_tab(), "Speakers")
        self.tabs.addTab(self.create_voice_commands_tab(), "Voice Commands")
        self.tabs.addTab(self.create_voice_feedback_tab(), "Voice Output")
        self.tabs.addTab(self.create_privacy_tab(), "Privacy")
        self.tabs.addTab(self.create_offline_tab(), "Offline")
        self.tabs.addTab(self.create_advanced_tab(), "Advanced")

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.apply_btn = QPushButton("Apply")
        self.apply_btn.clicked.connect(self.apply_settings)
        button_layout.addWidget(self.apply_btn)

        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.accept_settings)
        button_layout.addWidget(self.ok_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

    def create_audio_tab(self) -> QWidget:
        """Create the Audio settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Device selection group
        device_group = QGroupBox("Audio Device")
        device_layout = QFormLayout(device_group)

        self.device_combo = QComboBox()
        self.refresh_devices_btn = QPushButton("Refresh")
        self.refresh_devices_btn.clicked.connect(self.refresh_audio_devices)

        device_row = QHBoxLayout()
        device_row.addWidget(self.device_combo, 1)
        device_row.addWidget(self.refresh_devices_btn)
        device_layout.addRow("Input Device:", device_row)

        # Audio setup wizard button
        self.setup_wizard_btn = QPushButton("Run Audio Setup Wizard")
        self.setup_wizard_btn.setToolTip(
            "Opens the guided audio setup dialog to help select\n"
            "the correct device for capturing meeting audio."
        )
        self.setup_wizard_btn.clicked.connect(self.run_audio_setup_wizard)
        device_layout.addRow("", self.setup_wizard_btn)

        layout.addWidget(device_group)

        # Audio settings group
        audio_group = QGroupBox("Audio Settings")
        audio_layout = QFormLayout(audio_group)

        self.sample_rate_combo = QComboBox()
        self.sample_rate_combo.addItems(["16000", "22050", "44100", "48000"])
        audio_layout.addRow("Sample Rate:", self.sample_rate_combo)

        self.channels_combo = QComboBox()
        self.channels_combo.addItems(["1 (Mono)", "2 (Stereo)"])
        audio_layout.addRow("Channels:", self.channels_combo)

        layout.addWidget(audio_group)

        # Help text
        help_label = QLabel(
            "Tip: To capture what others say in meetings, select a loopback device\n"
            "(Stereo Mix, CABLE Output, etc.) instead of your microphone.\n"
            "Use the Audio Setup Wizard if you're not sure which device to use."
        )
        help_label.setWordWrap(True)
        help_label.setStyleSheet("color: #888888; font-size: 11px;")
        layout.addWidget(help_label)

        layout.addStretch()

        # Populate devices
        self.refresh_audio_devices()

        return widget

    def run_audio_setup_wizard(self):
        """Run the audio setup wizard dialog."""
        from ui.audio_setup_dialog import AudioSetupDialog
        device_index = AudioSetupDialog.get_audio_device(self)
        if device_index is not None:
            # Update the combo box to match
            for i in range(self.device_combo.count()):
                if self.device_combo.itemData(i) == device_index:
                    self.device_combo.setCurrentIndex(i)
                    break
            # Also save immediately
            self.settings.set("audio_device", device_index)
            QMessageBox.information(
                self,
                "Audio Setup Complete",
                "Audio device configured. The new device will be used for capturing."
            )

    def create_ai_tab(self) -> QWidget:
        """Create the AI settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Model settings
        model_group = QGroupBox("Model Settings")
        model_layout = QFormLayout(model_group)

        self.model_combo = QComboBox()
        self.model_combo.addItems([
            "claude-sonnet-4-20250514",
            "claude-3-haiku-20240307",
            "claude-3-opus-20240229"
        ])
        model_layout.addRow("AI Model:", self.model_combo)

        self.context_spin = QSpinBox()
        self.context_spin.setRange(1, 10)
        self.context_spin.setValue(3)
        model_layout.addRow("Context Window:", self.context_spin)

        layout.addWidget(model_group)

        # AI Persona settings
        persona_group = QGroupBox("AI Persona")
        persona_layout = QVBoxLayout(persona_group)

        # Persona description
        persona_desc = QLabel(
            "Select a persona to customize how the AI responds. "
            "Each persona has a different tone and style."
        )
        persona_desc.setWordWrap(True)
        persona_desc.setStyleSheet("color: #888888; font-size: 11px; margin-bottom: 5px;")
        persona_layout.addWidget(persona_desc)

        # Persona selection dropdown
        persona_select_layout = QHBoxLayout()
        persona_select_layout.addWidget(QLabel("Persona:"))
        self.persona_combo = QComboBox()
        for key, data in AI_PERSONAS.items():
            self.persona_combo.addItem(f"{data['name']} - {data['description']}", key)
        self.persona_combo.currentIndexChanged.connect(self.on_persona_changed)
        persona_select_layout.addWidget(self.persona_combo, 1)
        persona_layout.addLayout(persona_select_layout)

        # Custom persona prompt editor (shown only when "custom" is selected)
        self.custom_persona_label = QLabel("Custom Persona Prompt:")
        self.custom_persona_label.setStyleSheet("margin-top: 10px;")
        persona_layout.addWidget(self.custom_persona_label)

        self.custom_persona_edit = QTextEdit()
        self.custom_persona_edit.setPlaceholderText(
            "Enter your custom persona prompt...\n\n"
            "Example: You are a friendly mentor who explains things with patience and uses analogies."
        )
        self.custom_persona_edit.setMaximumHeight(100)
        persona_layout.addWidget(self.custom_persona_edit)

        # Initially hide custom prompt editor
        self.custom_persona_label.setVisible(False)
        self.custom_persona_edit.setVisible(False)

        layout.addWidget(persona_group)

        # Prompt settings
        prompt_group = QGroupBox("System Prompt")
        prompt_layout = QVBoxLayout(prompt_group)

        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("Preset:"))
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(list(PROMPT_PRESETS.keys()))
        self.preset_combo.currentTextChanged.connect(self.on_preset_changed)
        preset_layout.addWidget(self.preset_combo, 1)
        prompt_layout.addLayout(preset_layout)

        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText("Enter custom system prompt...")
        self.prompt_edit.setMaximumHeight(150)
        prompt_layout.addWidget(self.prompt_edit)

        layout.addWidget(prompt_group)

        # Language settings
        lang_group = QGroupBox("Language")
        lang_layout = QFormLayout(lang_group)

        self.language_combo = QComboBox()
        # SUPPORTED_LANGUAGES is a list of (code, name) tuples
        for code, name in SUPPORTED_LANGUAGES:
            self.language_combo.addItem(name, code)
        lang_layout.addRow("Transcription Language:", self.language_combo)

        layout.addWidget(lang_group)
        layout.addStretch()

        return widget

    def on_persona_changed(self, index: int):
        """Handle persona selection change."""
        persona_key = self.persona_combo.itemData(index)
        # Show/hide custom prompt editor based on selection
        is_custom = persona_key == "custom"
        self.custom_persona_label.setVisible(is_custom)
        self.custom_persona_edit.setVisible(is_custom)

    def create_translation_tab(self) -> QWidget:
        """Create the Translation settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Enable/disable Translation
        self.translation_check = QCheckBox("Enable Real-Time Translation")
        self.translation_check.setToolTip(
            "Translate transcribed text to your preferred language in real-time.\n"
            "Uses Claude Haiku for fast, accurate translations."
        )
        self.translation_check.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(self.translation_check)

        # Description
        desc_label = QLabel(
            "Real-time translation helps you understand conversations in languages "
            "you're not fluent in. The original text will be shown alongside the "
            "translation if desired."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #888888; font-size: 11px; margin-bottom: 10px;")
        layout.addWidget(desc_label)

        # Target language selection
        lang_group = QGroupBox("Translation Settings")
        lang_layout = QFormLayout(lang_group)

        self.translation_lang_combo = QComboBox()
        # Add supported translation languages
        for code, name, native in SettingsManager.TRANSLATION_LANGUAGES:
            display_name = f"{name} ({native})" if native != name else name
            self.translation_lang_combo.addItem(display_name, code)

        lang_layout.addRow("Translate To:", self.translation_lang_combo)

        # Show original text option
        self.show_original_check = QCheckBox("Show original text alongside translation")
        self.show_original_check.setChecked(True)
        self.show_original_check.setToolTip(
            "When enabled, the original transcribed text will be shown\n"
            "below the translated text for reference."
        )
        lang_layout.addRow("", self.show_original_check)

        layout.addWidget(lang_group)

        # Info about translation
        info_group = QGroupBox("How It Works")
        info_layout = QVBoxLayout(info_group)

        info_text = QLabel(
            "1. Audio is transcribed in its original language\n"
            "2. The transcription is sent to Claude Haiku for translation\n"
            "3. Both original and translated text appear in the overlay\n\n"
            "Translation adds a small latency (~200-500ms) to responses.\n"
            "For best results, ensure the transcription language is set correctly."
        )
        info_text.setWordWrap(True)
        info_text.setStyleSheet("color: #aaaaaa; font-size: 11px;")
        info_layout.addWidget(info_text)

        layout.addWidget(info_group)

        # Supported languages hint
        hint_label = QLabel(
            "Tip: Supports 28 languages including English, Spanish, French, German, "
            "Chinese, Japanese, Korean, Arabic, Hindi, and more."
        )
        hint_label.setWordWrap(True)
        hint_label.setStyleSheet("color: #666666; font-size: 10px;")
        layout.addWidget(hint_label)

        layout.addStretch()

        return widget

    def create_appearance_tab(self) -> QWidget:
        """Create the Appearance settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Theme settings
        theme_group = QGroupBox("Theme")
        theme_layout = QFormLayout(theme_group)

        self.theme_combo = QComboBox()
        for theme_id, theme_data in THEMES.items():
            self.theme_combo.addItem(theme_data["name"], theme_id)
        self.theme_combo.currentIndexChanged.connect(self.preview_theme)
        theme_layout.addRow("Color Theme:", self.theme_combo)

        layout.addWidget(theme_group)

        # Overlay settings
        overlay_group = QGroupBox("Overlay")
        overlay_layout = QFormLayout(overlay_group)

        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(50, 100)
        self.opacity_slider.setValue(90)
        self.opacity_label = QLabel("90%")
        self.opacity_slider.valueChanged.connect(
            lambda v: self.opacity_label.setText(f"{v}%")
        )

        opacity_row = QHBoxLayout()
        opacity_row.addWidget(self.opacity_slider, 1)
        opacity_row.addWidget(self.opacity_label)
        overlay_layout.addRow("Opacity:", opacity_row)

        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(10, 24)
        self.font_size_spin.setValue(14)
        overlay_layout.addRow("Font Size:", self.font_size_spin)

        self.always_on_top_check = QCheckBox("Keep overlay on top")
        self.always_on_top_check.setChecked(True)
        overlay_layout.addRow("", self.always_on_top_check)

        self.remember_position_check = QCheckBox("Remember window position")
        self.remember_position_check.setChecked(True)
        overlay_layout.addRow("", self.remember_position_check)

        self.hide_from_capture_check = QCheckBox("Hide overlay during screen sharing")
        self.hide_from_capture_check.setChecked(False)
        self.hide_from_capture_check.setToolTip(
            "When enabled, the overlay will be invisible to others during screen sharing.\n"
            "You can still see it, but it won't appear in recordings or shared screens.\n"
            "(Windows 10 version 2004 or later required)"
        )
        overlay_layout.addRow("", self.hide_from_capture_check)

        layout.addWidget(overlay_group)
        layout.addStretch()

        return widget

    def create_shortcuts_tab(self) -> QWidget:
        """Create the Shortcuts settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        shortcuts_group = QGroupBox("Global Hotkeys")
        shortcuts_layout = QFormLayout(shortcuts_group)

        self.shortcut_toggle = ShortcutEdit()
        shortcuts_layout.addRow("Toggle Listening:", self.shortcut_toggle)

        self.shortcut_show_hide = ShortcutEdit()
        shortcuts_layout.addRow("Show/Hide Overlay:", self.shortcut_show_hide)

        self.shortcut_clear = ShortcutEdit()
        shortcuts_layout.addRow("Clear Context:", self.shortcut_clear)

        self.enable_shortcuts_check = QCheckBox("Enable global hotkeys")
        self.enable_shortcuts_check.setChecked(True)
        shortcuts_layout.addRow("", self.enable_shortcuts_check)

        layout.addWidget(shortcuts_group)

        # Reset button
        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self.reset_shortcuts)
        layout.addWidget(reset_btn)

        layout.addStretch()

        return widget

    def create_diarization_tab(self) -> QWidget:
        """Create the Speaker Diarization settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Enable/disable diarization
        self.diarization_check = QCheckBox("Enable Speaker Diarization")
        self.diarization_check.setToolTip(
            "Identify different speakers in your meetings.\n"
            "Requires a HuggingFace API token."
        )
        self.diarization_check.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(self.diarization_check)

        # Description
        desc_label = QLabel(
            "Speaker diarization identifies who is speaking in your meetings. "
            "This allows you to see which participant said what, and you can assign "
            "custom names to speakers (e.g., rename 'SPEAKER_00' to 'John')."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #888888; font-size: 11px; margin-bottom: 10px;")
        layout.addWidget(desc_label)

        # API Token group
        token_group = QGroupBox("HuggingFace API Token")
        token_layout = QVBoxLayout(token_group)

        # Installation notice with install button
        install_frame = QFrame()
        install_frame.setStyleSheet(
            "background-color: #3d3000; border-radius: 6px; padding: 4px;"
        )
        install_frame_layout = QVBoxLayout(install_frame)
        install_frame_layout.setContentsMargins(10, 10, 10, 10)

        install_notice = QLabel(
            "⚠️ OPTIONAL INSTALL REQUIRED\n"
            "Speaker diarization requires additional components (~2GB)."
        )
        install_notice.setStyleSheet("color: #ffa500; font-size: 11px; font-weight: bold;")
        install_notice.setWordWrap(True)
        install_frame_layout.addWidget(install_notice)

        self.install_diarization_btn = QPushButton("📦 Install Speaker Diarization")
        self.install_diarization_btn.setStyleSheet(
            "QPushButton { background-color: #d4a000; color: #1a1a1a; font-weight: bold; "
            "padding: 8px 16px; border-radius: 4px; } "
            "QPushButton:hover { background-color: #e6b000; }"
        )
        self.install_diarization_btn.clicked.connect(self._run_diarization_installer)
        install_frame_layout.addWidget(self.install_diarization_btn)

        token_layout.addWidget(install_frame)

        token_desc = QLabel(
            "After installing, you'll also need a HuggingFace token:\n"
            "1. Create an account at huggingface.co\n"
            "2. Go to Settings > Access Tokens > New token\n"
            "3. Accept the license at huggingface.co/pyannote/speaker-diarization-3.1"
        )
        token_desc.setStyleSheet("color: #aaaaaa; font-size: 11px;")
        token_desc.setWordWrap(True)
        token_layout.addWidget(token_desc)

        token_input_layout = QHBoxLayout()
        token_input_layout.addWidget(QLabel("Token:"))
        self.hf_token_input = QLineEdit()
        self.hf_token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.hf_token_input.setPlaceholderText("hf_...")
        token_input_layout.addWidget(self.hf_token_input, 1)

        self.show_token_btn = QPushButton("Show")
        self.show_token_btn.setCheckable(True)
        self.show_token_btn.clicked.connect(self._toggle_token_visibility)
        token_input_layout.addWidget(self.show_token_btn)

        token_layout.addLayout(token_input_layout)

        # Token status
        self.token_status_label = QLabel("")
        self.token_status_label.setStyleSheet("font-size: 11px;")
        token_layout.addWidget(self.token_status_label)

        layout.addWidget(token_group)

        # Speaker settings group
        speaker_group = QGroupBox("Speaker Detection Settings")
        speaker_layout = QFormLayout(speaker_group)

        self.min_speakers_spin = QSpinBox()
        self.min_speakers_spin.setRange(1, 20)
        self.min_speakers_spin.setValue(1)
        self.min_speakers_spin.setToolTip("Minimum number of speakers expected")
        speaker_layout.addRow("Min Speakers:", self.min_speakers_spin)

        self.max_speakers_spin = QSpinBox()
        self.max_speakers_spin.setRange(1, 20)
        self.max_speakers_spin.setValue(10)
        self.max_speakers_spin.setToolTip("Maximum number of speakers expected")
        speaker_layout.addRow("Max Speakers:", self.max_speakers_spin)

        self.diarization_interval_spin = QSpinBox()
        self.diarization_interval_spin.setRange(10, 120)
        self.diarization_interval_spin.setValue(30)
        self.diarization_interval_spin.setSuffix(" seconds")
        self.diarization_interval_spin.setToolTip(
            "How often to update speaker identification.\n"
            "Lower values = more responsive but higher CPU usage."
        )
        speaker_layout.addRow("Update Interval:", self.diarization_interval_spin)

        layout.addWidget(speaker_group)

        # Manage speakers button
        manage_speakers_layout = QHBoxLayout()
        manage_speakers_layout.addStretch()

        self.manage_speakers_btn = QPushButton("Manage Speaker Names...")
        self.manage_speakers_btn.setToolTip("Rename detected speakers for the current session")
        self.manage_speakers_btn.clicked.connect(self._open_speaker_manager)
        manage_speakers_layout.addWidget(self.manage_speakers_btn)

        layout.addLayout(manage_speakers_layout)

        # Help text
        help_label = QLabel(
            "Note: Speaker diarization requires significant CPU resources. "
            "For best results, ensure your system meets the requirements and "
            "consider using a GPU if available."
        )
        help_label.setWordWrap(True)
        help_label.setStyleSheet("color: #666666; font-size: 10px;")
        layout.addWidget(help_label)

        layout.addStretch()

        return widget

    def _toggle_token_visibility(self):
        """Toggle HuggingFace token visibility."""
        if self.show_token_btn.isChecked():
            self.hf_token_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_token_btn.setText("Hide")
        else:
            self.hf_token_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_token_btn.setText("Show")

    def _run_diarization_installer(self):
        """Run the speaker diarization installer script."""
        import subprocess
        import sys
        from pathlib import Path

        # Find the installer script
        if sys.platform == "win32":
            script_name = "install_speaker_diarization.bat"
        else:
            script_name = "install_speaker_diarization.sh"

        # Look for script in app directory
        app_dir = Path(__file__).parent.parent.parent
        script_path = app_dir / script_name

        if not script_path.exists():
            # Try current working directory
            script_path = Path.cwd() / script_name

        if not script_path.exists():
            QMessageBox.warning(
                self,
                "Installer Not Found",
                f"Could not find {script_name}.\n\n"
                "You can manually install by running:\n"
                "pip install pyannote.audio torch\n\n"
                "Or download the installer from the ReadIn AI website."
            )
            return

        try:
            if sys.platform == "win32":
                # Open in a new command prompt window
                subprocess.Popen(
                    ["cmd", "/c", "start", "cmd", "/k", str(script_path)],
                    shell=True
                )
            else:
                # Make script executable and run in terminal
                script_path.chmod(0o755)
                if sys.platform == "darwin":
                    # macOS - open in Terminal
                    subprocess.Popen([
                        "osascript", "-e",
                        f'tell app "Terminal" to do script "{script_path}"'
                    ])
                else:
                    # Linux - try common terminals
                    for terminal in ["gnome-terminal", "xterm", "konsole"]:
                        try:
                            subprocess.Popen([terminal, "-e", str(script_path)])
                            break
                        except FileNotFoundError:
                            continue

            QMessageBox.information(
                self,
                "Installer Started",
                "The installer has been launched in a new window.\n\n"
                "Please follow the instructions there.\n"
                "After installation completes, restart ReadIn AI."
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to launch installer: {e}\n\n"
                "You can manually install by running:\n"
                "pip install pyannote.audio torch"
            )

    def _open_speaker_manager(self):
        """Open the speaker manager dialog."""
        try:
            from ui.speaker_manager_dialog import SpeakerManagerDialog

            # Get current speaker data from settings
            speaker_mapping = self.settings.get("speaker_mapping", {})

            # Create sample speakers if none exist (for demo purposes)
            speakers = []
            for speaker_id, name in speaker_mapping.items():
                speakers.append({
                    "id": speaker_id,
                    "name": name,
                    "message_count": 0,
                    "percentage": 0.0
                })

            if not speakers:
                QMessageBox.information(
                    self,
                    "No Speakers Detected",
                    "No speakers have been detected yet.\n\n"
                    "Start a meeting with speaker diarization enabled, "
                    "and speakers will appear here as they are identified."
                )
                return

            result = SpeakerManagerDialog.edit_speakers(
                speakers=speakers,
                speaker_mapping=speaker_mapping,
                parent=self
            )

            if result is not None:
                self.settings.set("speaker_mapping", result)
                QMessageBox.information(
                    self,
                    "Speakers Updated",
                    "Speaker names have been updated."
                )

        except ImportError as e:
            QMessageBox.warning(
                self,
                "Error",
                f"Could not open speaker manager: {e}"
            )

    def create_voice_commands_tab(self) -> QWidget:
        """Create the Voice Commands settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Check if voice commands are available
        try:
            from voice_commands import is_voice_commands_available
            voice_commands_available = is_voice_commands_available()
        except ImportError:
            voice_commands_available = False

        # Enable/disable Voice Commands
        self.voice_commands_check = QCheckBox("Enable Voice Commands")
        self.voice_commands_check.setToolTip(
            "Control ReadIn AI with your voice using wake words.\n"
            "Say 'Hey ReadIn' followed by a command."
        )
        self.voice_commands_check.setStyleSheet("font-weight: bold; font-size: 13px;")
        self.voice_commands_check.setEnabled(voice_commands_available)
        layout.addWidget(self.voice_commands_check)

        # Availability warning
        if not voice_commands_available:
            warning_label = QLabel(
                "Voice commands are not available. Please install speech_recognition:\n"
                "pip install SpeechRecognition pyaudio"
            )
            warning_label.setWordWrap(True)
            warning_label.setStyleSheet("color: #f9e2af; font-size: 11px; margin-bottom: 10px;")
            layout.addWidget(warning_label)

        # Description
        desc_label = QLabel(
            "Voice commands allow you to control ReadIn AI hands-free. "
            "Say the wake word ('Hey ReadIn' or 'ReadIn') followed by a command "
            "like 'summarize', 'repeat', or 'action items'."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #888888; font-size: 11px; margin-bottom: 10px;")
        layout.addWidget(desc_label)

        # Wake Word Settings
        wake_word_group = QGroupBox("Wake Word Settings")
        wake_word_layout = QFormLayout(wake_word_group)

        # Wake word info
        wake_words_label = QLabel(
            "Supported wake words: 'Hey ReadIn', 'ReadIn', 'OK ReadIn', 'Hi ReadIn'"
        )
        wake_words_label.setStyleSheet("color: #aaaaaa; font-size: 11px;")
        wake_word_layout.addRow("", wake_words_label)

        # Microphone selection for voice commands
        self.voice_cmd_device_combo = QComboBox()
        self.voice_cmd_device_combo.setEnabled(voice_commands_available)
        self._refresh_voice_command_devices()
        wake_word_layout.addRow("Microphone:", self.voice_cmd_device_combo)

        # Refresh button
        refresh_voice_btn = QPushButton("Refresh Devices")
        refresh_voice_btn.setEnabled(voice_commands_available)
        refresh_voice_btn.clicked.connect(self._refresh_voice_command_devices)
        wake_word_layout.addRow("", refresh_voice_btn)

        layout.addWidget(wake_word_group)

        # Available Commands
        commands_group = QGroupBox("Available Voice Commands")
        commands_layout = QVBoxLayout(commands_group)

        commands_text = QLabel(
            "After saying the wake word, you can use these commands:\n\n"
            "  - 'Summarize' / 'Summary' - Summarize recent conversation\n"
            "  - 'Repeat' / 'Say again' - Repeat the last AI response\n"
            "  - 'Action items' / 'Tasks' - List action items from the meeting\n"
            "  - 'What did they say' - Repeat the last transcription\n"
            "  - 'Stop listening' / 'Pause' - Stop audio capture\n"
            "  - 'Start listening' / 'Resume' - Start audio capture\n"
            "  - 'Clear' / 'Reset' - Clear conversation context"
        )
        commands_text.setWordWrap(True)
        commands_text.setStyleSheet("color: #aaaaaa; font-size: 11px;")
        commands_layout.addWidget(commands_text)

        layout.addWidget(commands_group)

        # TTS Feedback for voice commands
        feedback_group = QGroupBox("Voice Command Feedback")
        feedback_layout = QFormLayout(feedback_group)

        self.voice_cmd_tts_check = QCheckBox("Speak command confirmations")
        self.voice_cmd_tts_check.setToolTip(
            "When enabled, ReadIn AI will speak a confirmation\n"
            "after recognizing a voice command (e.g., 'Generating summary')."
        )
        self.voice_cmd_tts_check.setEnabled(voice_commands_available)
        feedback_layout.addRow("", self.voice_cmd_tts_check)

        layout.addWidget(feedback_group)

        # Test voice commands button
        test_layout = QHBoxLayout()
        self.voice_cmd_test_btn = QPushButton("Test Voice Commands")
        self.voice_cmd_test_btn.setToolTip("Test if your microphone can hear voice commands")
        self.voice_cmd_test_btn.setEnabled(voice_commands_available)
        self.voice_cmd_test_btn.clicked.connect(self._test_voice_commands)
        test_layout.addWidget(self.voice_cmd_test_btn)
        test_layout.addStretch()
        layout.addLayout(test_layout)

        # Tips
        tips_group = QGroupBox("Tips")
        tips_layout = QVBoxLayout(tips_group)
        tips_text = QLabel(
            "- Speak clearly and at a normal pace\n"
            "- Wait for a brief pause after the wake word\n"
            "- Use a headset microphone for best results\n"
            "- Voice commands work alongside keyboard shortcuts\n"
            "- Commands are processed using Google's speech recognition"
        )
        tips_text.setWordWrap(True)
        tips_text.setStyleSheet("color: #aaaaaa; font-size: 11px;")
        tips_layout.addWidget(tips_text)
        layout.addWidget(tips_group)

        layout.addStretch()

        return widget

    def _refresh_voice_command_devices(self):
        """Refresh the list of microphone devices for voice commands."""
        self.voice_cmd_device_combo.clear()
        self.voice_cmd_device_combo.addItem("Default Microphone", None)

        try:
            from voice_commands import VoiceCommandHandler
            devices = VoiceCommandHandler.list_microphones()
            for device in devices:
                self.voice_cmd_device_combo.addItem(
                    device.get('name', f"Device {device['index']}"),
                    device['index']
                )
        except ImportError:
            pass
        except Exception as e:
            import logging
            logging.warning(f"Failed to list voice command devices: {e}")

    def _test_voice_commands(self):
        """Test voice command recognition."""
        try:
            from voice_commands import is_voice_commands_available, VoiceCommandHandler

            if not is_voice_commands_available():
                QMessageBox.warning(
                    self,
                    "Voice Commands Unavailable",
                    "Voice commands are not available.\n"
                    "Please install speech_recognition: pip install SpeechRecognition pyaudio"
                )
                return

            # Get selected device
            device_index = self.voice_cmd_device_combo.currentData()

            # Show listening dialog
            QMessageBox.information(
                self,
                "Voice Test",
                "After clicking OK, speak into your microphone.\n"
                "Say 'Hey ReadIn' followed by a command like 'summarize'.\n\n"
                "The test will listen for 5 seconds."
            )

            # Create a simple test
            import speech_recognition as sr
            recognizer = sr.Recognizer()

            try:
                with sr.Microphone(device_index=device_index) as source:
                    recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    audio = recognizer.listen(source, timeout=5.0, phrase_time_limit=5.0)
                    text = recognizer.recognize_google(audio)

                    # Check if wake word was detected
                    text_lower = text.lower()
                    wake_words = ["hey readin", "hey read in", "readin", "read in", "ok readin", "hi readin"]
                    wake_word_found = any(w in text_lower for w in wake_words)

                    if wake_word_found:
                        QMessageBox.information(
                            self,
                            "Voice Test Successful",
                            f"Heard: '{text}'\n\n"
                            "Wake word detected! Voice commands are working correctly."
                        )
                    else:
                        QMessageBox.information(
                            self,
                            "Voice Test Result",
                            f"Heard: '{text}'\n\n"
                            "No wake word detected. Try saying 'Hey ReadIn' clearly."
                        )

            except sr.WaitTimeoutError:
                QMessageBox.warning(
                    self,
                    "Voice Test",
                    "No speech detected within 5 seconds.\n"
                    "Please ensure your microphone is working and speak clearly."
                )
            except sr.UnknownValueError:
                QMessageBox.warning(
                    self,
                    "Voice Test",
                    "Could not understand the audio.\n"
                    "Please speak more clearly and reduce background noise."
                )
            except sr.RequestError as e:
                QMessageBox.warning(
                    self,
                    "Voice Test Error",
                    f"Speech recognition service error:\n{e}\n\n"
                    "Please check your internet connection."
                )

        except ImportError:
            QMessageBox.warning(
                self,
                "Voice Commands Unavailable",
                "Voice commands are not available.\n"
                "Please install speech_recognition: pip install SpeechRecognition pyaudio"
            )
        except Exception as e:
            QMessageBox.warning(
                self,
                "Voice Test Error",
                f"Error testing voice commands: {e}"
            )

    def create_voice_feedback_tab(self) -> QWidget:
        """Create the Voice Feedback settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Check if voice feedback is available
        try:
            from services.voice_feedback import is_voice_feedback_available
            voice_available = is_voice_feedback_available()
        except ImportError:
            voice_available = False

        # Enable/disable Voice Feedback
        self.voice_feedback_check = QCheckBox("Enable Voice Feedback")
        self.voice_feedback_check.setToolTip(
            "Speak AI responses aloud using text-to-speech.\n"
            "Requires pyttsx3 package to be installed."
        )
        self.voice_feedback_check.setStyleSheet("font-weight: bold; font-size: 13px;")
        self.voice_feedback_check.setEnabled(voice_available)
        layout.addWidget(self.voice_feedback_check)

        # Availability warning
        if not voice_available:
            warning_label = QLabel(
                "Voice feedback is not available. Please install pyttsx3:\n"
                "pip install pyttsx3"
            )
            warning_label.setWordWrap(True)
            warning_label.setStyleSheet("color: #f9e2af; font-size: 11px; margin-bottom: 10px;")
            layout.addWidget(warning_label)

        # Description
        desc_label = QLabel(
            "Voice feedback reads AI responses aloud using your system's "
            "text-to-speech engine. This can help you stay focused on the "
            "conversation while receiving guidance."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #888888; font-size: 11px; margin-bottom: 10px;")
        layout.addWidget(desc_label)

        # Voice Settings Group
        voice_group = QGroupBox("Voice Settings")
        voice_layout = QFormLayout(voice_group)

        # Speech rate slider
        rate_layout = QHBoxLayout()
        self.voice_rate_slider = QSlider(Qt.Orientation.Horizontal)
        self.voice_rate_slider.setRange(50, 300)
        self.voice_rate_slider.setValue(150)
        self.voice_rate_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.voice_rate_slider.setTickInterval(50)
        self.voice_rate_slider.setEnabled(voice_available)
        self.voice_rate_label = QLabel("150 wpm")
        self.voice_rate_label.setMinimumWidth(60)
        self.voice_rate_slider.valueChanged.connect(
            lambda v: self.voice_rate_label.setText(f"{v} wpm")
        )
        rate_layout.addWidget(self.voice_rate_slider, 1)
        rate_layout.addWidget(self.voice_rate_label)
        voice_layout.addRow("Speech Rate:", rate_layout)

        # Volume slider
        volume_layout = QHBoxLayout()
        self.voice_volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.voice_volume_slider.setRange(0, 100)
        self.voice_volume_slider.setValue(80)
        self.voice_volume_slider.setEnabled(voice_available)
        self.voice_volume_label = QLabel("80%")
        self.voice_volume_label.setMinimumWidth(60)
        self.voice_volume_slider.valueChanged.connect(
            lambda v: self.voice_volume_label.setText(f"{v}%")
        )
        volume_layout.addWidget(self.voice_volume_slider, 1)
        volume_layout.addWidget(self.voice_volume_label)
        voice_layout.addRow("Volume:", volume_layout)

        layout.addWidget(voice_group)

        # Test button
        test_layout = QHBoxLayout()
        self.voice_test_btn = QPushButton("Test Voice")
        self.voice_test_btn.setToolTip("Play a test message to preview voice settings")
        self.voice_test_btn.setEnabled(voice_available)
        self.voice_test_btn.clicked.connect(self._test_voice_feedback)
        test_layout.addWidget(self.voice_test_btn)
        test_layout.addStretch()
        layout.addLayout(test_layout)

        # Tips
        tips_group = QGroupBox("Tips")
        tips_layout = QVBoxLayout(tips_group)
        tips_text = QLabel(
            "- Adjust speech rate to match your listening preference\n"
            "- Lower rates are easier to understand but take longer\n"
            "- Voice feedback works best with shorter AI responses\n"
            "- Use headphones to avoid feedback during meetings"
        )
        tips_text.setWordWrap(True)
        tips_text.setStyleSheet("color: #aaaaaa; font-size: 11px;")
        tips_layout.addWidget(tips_text)
        layout.addWidget(tips_group)

        layout.addStretch()

        return widget

    def _test_voice_feedback(self):
        """Test voice feedback with current settings."""
        try:
            from services.voice_feedback import VoiceFeedback

            # Create temporary voice feedback instance with current settings
            rate = self.voice_rate_slider.value()
            volume = self.voice_volume_slider.value() / 100.0

            test_voice = VoiceFeedback(rate=rate, volume=volume)
            test_voice.set_enabled(True)

            if test_voice.start():
                test_voice.speak("This is a test of the voice feedback feature. How does this sound?")
                # Schedule cleanup after a delay
                import threading
                def cleanup():
                    import time
                    time.sleep(8)  # Wait for speech to complete
                    test_voice.stop()
                threading.Thread(target=cleanup, daemon=True).start()
            else:
                QMessageBox.warning(
                    self,
                    "Voice Test Failed",
                    "Could not start the voice feedback engine.\n"
                    "Please ensure pyttsx3 is properly installed."
                )
        except ImportError:
            QMessageBox.warning(
                self,
                "Voice Test Failed",
                "Voice feedback is not available.\n"
                "Please install pyttsx3: pip install pyttsx3"
            )
        except Exception as e:
            QMessageBox.warning(
                self,
                "Voice Test Failed",
                f"Error testing voice feedback: {e}"
            )

    def create_privacy_tab(self) -> QWidget:
        """Create the Privacy Mode settings tab."""
        widget = QWidget()

        # Use scroll area for the tab content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)

        # Enable/disable Privacy Mode
        self.privacy_mode_check = QCheckBox("Enable Privacy Mode")
        self.privacy_mode_check.setToolTip(
            "When enabled, ReadIn AI will not monitor or transcribe\n"
            "audio from apps in your excluded list."
        )
        self.privacy_mode_check.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(self.privacy_mode_check)

        # Description
        desc_label = QLabel(
            "Privacy Mode lets you exclude sensitive apps from being monitored. "
            "When an excluded app is running, ReadIn AI will skip it during process detection."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #888888; font-size: 11px; margin-bottom: 10px;")
        layout.addWidget(desc_label)

        # Auto-Detection Group
        auto_detect_group = QGroupBox("Auto-Detection")
        auto_detect_layout = QVBoxLayout(auto_detect_group)

        self.auto_detect_check = QCheckBox("Auto-detect sensitive apps")
        self.auto_detect_check.setToolTip(
            "Automatically detect and pause monitoring when sensitive apps\n"
            "(banking, password managers, medical, etc.) are running."
        )
        auto_detect_layout.addWidget(self.auto_detect_check)

        # Scan button
        scan_layout = QHBoxLayout()
        self.scan_sensitive_btn = QPushButton("Scan for Sensitive Apps")
        self.scan_sensitive_btn.setToolTip("Scan running processes for sensitive applications")
        self.scan_sensitive_btn.clicked.connect(self._scan_sensitive_apps)
        scan_layout.addWidget(self.scan_sensitive_btn)

        self.auto_exclude_btn = QPushButton("Auto-Exclude Detected")
        self.auto_exclude_btn.setToolTip("Automatically add all detected sensitive apps to exclusion list")
        self.auto_exclude_btn.clicked.connect(self._auto_exclude_detected)
        scan_layout.addWidget(self.auto_exclude_btn)
        scan_layout.addStretch()

        auto_detect_layout.addLayout(scan_layout)

        # Detected apps label
        self.detected_apps_label = QLabel("No scan performed yet.")
        self.detected_apps_label.setWordWrap(True)
        self.detected_apps_label.setStyleSheet("color: #a6adc8; font-size: 11px;")
        auto_detect_layout.addWidget(self.detected_apps_label)

        layout.addWidget(auto_detect_group)

        # Sensitive Categories Group
        categories_group = QGroupBox("Quick Add Sensitive Categories")
        categories_layout = QVBoxLayout(categories_group)

        categories_desc = QLabel("Add all apps from a category to your exclusion list:")
        categories_desc.setStyleSheet("color: #aaaaaa; font-size: 11px;")
        categories_layout.addWidget(categories_desc)

        # Category checkboxes
        self.category_checkboxes = {}
        for cat_key, cat_data in SettingsManager.SENSITIVE_APP_CATEGORIES.items():
            cat_layout = QHBoxLayout()

            checkbox = QCheckBox(cat_data["name"])
            checkbox.setToolTip(cat_data["description"])
            checkbox.setProperty("category_key", cat_key)
            checkbox.stateChanged.connect(self._on_category_toggled)
            self.category_checkboxes[cat_key] = checkbox
            cat_layout.addWidget(checkbox)

            # Show count label
            count_label = QLabel("")
            count_label.setStyleSheet("color: #666666; font-size: 10px;")
            count_label.setProperty("category_key", cat_key)
            cat_layout.addWidget(count_label)
            cat_layout.addStretch()

            categories_layout.addLayout(cat_layout)

        layout.addWidget(categories_group)

        # Custom Excluded Apps Group
        apps_group = QGroupBox("Excluded Apps")
        apps_layout = QVBoxLayout(apps_group)

        # List of excluded apps
        self.excluded_apps_list = QListWidget()
        self.excluded_apps_list.setMinimumHeight(100)
        self.excluded_apps_list.setMaximumHeight(150)
        self.excluded_apps_list.setToolTip("Apps that will not be monitored by ReadIn AI")
        apps_layout.addWidget(self.excluded_apps_list)

        # Add/Remove buttons
        btn_layout = QHBoxLayout()

        self.add_app_btn = QPushButton("Add App")
        self.add_app_btn.clicked.connect(self._add_excluded_app)
        btn_layout.addWidget(self.add_app_btn)

        self.add_running_btn = QPushButton("Add from Running Apps")
        self.add_running_btn.clicked.connect(self._add_running_app)
        self.add_running_btn.setToolTip("Select from currently running applications")
        btn_layout.addWidget(self.add_running_btn)

        self.remove_app_btn = QPushButton("Remove Selected")
        self.remove_app_btn.clicked.connect(self._remove_excluded_app)
        btn_layout.addWidget(self.remove_app_btn)

        apps_layout.addLayout(btn_layout)

        # Clear all button
        clear_btn_layout = QHBoxLayout()
        clear_btn_layout.addStretch()
        self.clear_apps_btn = QPushButton("Clear All")
        self.clear_apps_btn.clicked.connect(self._clear_all_excluded_apps)
        self.clear_apps_btn.setStyleSheet("color: #ff6b6b;")
        clear_btn_layout.addWidget(self.clear_apps_btn)
        apps_layout.addLayout(clear_btn_layout)

        layout.addWidget(apps_group)

        # Pause History Group
        history_group = QGroupBox("Pause History")
        history_layout = QVBoxLayout(history_group)

        history_desc = QLabel(
            "View when monitoring was paused due to sensitive apps or manual actions."
        )
        history_desc.setWordWrap(True)
        history_desc.setStyleSheet("color: #aaaaaa; font-size: 11px;")
        history_layout.addWidget(history_desc)

        # History buttons
        history_btn_layout = QHBoxLayout()

        self.view_history_btn = QPushButton("View Pause History")
        self.view_history_btn.setToolTip("View the history of monitoring pauses")
        self.view_history_btn.clicked.connect(self._view_pause_history)
        history_btn_layout.addWidget(self.view_history_btn)

        self.clear_history_btn = QPushButton("Clear History")
        self.clear_history_btn.setToolTip("Clear all pause history")
        self.clear_history_btn.clicked.connect(self._clear_pause_history)
        self.clear_history_btn.setStyleSheet("color: #f9e2af;")
        history_btn_layout.addWidget(self.clear_history_btn)

        history_btn_layout.addStretch()
        history_layout.addLayout(history_btn_layout)

        # History count label
        self.history_count_label = QLabel("0 pause events recorded")
        self.history_count_label.setStyleSheet("color: #6c7086; font-size: 11px;")
        history_layout.addWidget(self.history_count_label)

        layout.addWidget(history_group)

        # Help text
        help_label = QLabel(
            "Tip: App names should match the process name or friendly name. "
            "For example: 'Discord', 'discord.exe', 'Microsoft Teams', etc."
        )
        help_label.setWordWrap(True)
        help_label.setStyleSheet("color: #666666; font-size: 10px;")
        layout.addWidget(help_label)

        layout.addStretch()

        scroll.setWidget(scroll_content)

        # Main layout for widget
        main_layout = QVBoxLayout(widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

        return widget

    def _scan_sensitive_apps(self):
        """Scan for sensitive apps running on the system."""
        try:
            from privacy_mode import get_privacy_handler
            handler = get_privacy_handler()
            detected = handler.detect_sensitive_apps()

            if detected:
                app_list = []
                for app in detected[:10]:  # Limit display
                    category = app.get("category", "Unknown")
                    app_list.append(f"  - {app['name']} ({category})")

                more = len(detected) - 10 if len(detected) > 10 else 0
                text = f"Found {len(detected)} sensitive app(s):\n" + "\n".join(app_list)
                if more > 0:
                    text += f"\n  ... and {more} more"

                self.detected_apps_label.setText(text)
                self.detected_apps_label.setStyleSheet("color: #f9e2af; font-size: 11px;")
            else:
                self.detected_apps_label.setText("No sensitive apps detected.")
                self.detected_apps_label.setStyleSheet("color: #a6e3a1; font-size: 11px;")

        except Exception as e:
            self.detected_apps_label.setText(f"Scan failed: {e}")
            self.detected_apps_label.setStyleSheet("color: #ef4444; font-size: 11px;")

    def _auto_exclude_detected(self):
        """Auto-exclude all detected sensitive apps."""
        try:
            from privacy_mode import get_privacy_handler
            handler = get_privacy_handler()
            added = handler.auto_exclude_detected()

            if added > 0:
                self._refresh_excluded_apps_list()
                QMessageBox.information(
                    self,
                    "Apps Excluded",
                    f"Added {added} sensitive app(s) to the exclusion list."
                )
            else:
                QMessageBox.information(
                    self,
                    "No Apps Added",
                    "No new sensitive apps were detected to add.\n"
                    "Try scanning first or all detected apps are already excluded."
                )

        except Exception as e:
            QMessageBox.warning(
                self,
                "Error",
                f"Could not auto-exclude apps: {e}"
            )

    def _view_pause_history(self):
        """View the pause history dialog."""
        try:
            from privacy_mode import get_privacy_handler
            handler = get_privacy_handler()
            history = handler.get_pause_history(limit=50)

            if not history:
                QMessageBox.information(
                    self,
                    "Pause History",
                    "No pause events have been recorded yet.\n\n"
                    "Pause events are recorded when:\n"
                    "- A sensitive app is auto-detected\n"
                    "- Monitoring is manually paused\n"
                    "- An excluded app becomes active"
                )
                return

            # Create history dialog
            dialog = QDialog(self)
            dialog.setWindowTitle("Privacy Mode - Pause History")
            dialog.setMinimumSize(500, 400)
            dialog_layout = QVBoxLayout(dialog)

            # Description
            desc = QLabel(f"Showing {len(history)} most recent pause events:")
            desc.setStyleSheet("font-weight: bold; margin-bottom: 10px;")
            dialog_layout.addWidget(desc)

            # History list
            history_list = QListWidget()
            history_list.setAlternatingRowColors(True)

            for event in history:
                # Format the event
                timestamp = event.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                reason = event.reason.value.replace("_", " ").title()
                duration = f"{event.duration_seconds:.1f}s" if event.duration_seconds else "ongoing"
                app = event.app_name or "N/A"
                category = event.category or ""

                text = f"{timestamp} - {reason}"
                if app != "N/A":
                    text += f"\n    App: {app}"
                    if category:
                        text += f" ({category})"
                text += f"\n    Duration: {duration}"

                item = QListWidgetItem(text)
                history_list.addItem(item)

            dialog_layout.addWidget(history_list)

            # Close button
            close_btn = QPushButton("Close")
            close_btn.clicked.connect(dialog.accept)
            dialog_layout.addWidget(close_btn)

            dialog.exec()

        except Exception as e:
            QMessageBox.warning(
                self,
                "Error",
                f"Could not load pause history: {e}"
            )

    def _clear_pause_history(self):
        """Clear all pause history."""
        reply = QMessageBox.question(
            self,
            "Clear Pause History",
            "Are you sure you want to clear all pause history?\n"
            "This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                from privacy_mode import get_privacy_handler
                handler = get_privacy_handler()
                handler.clear_pause_history()
                self._update_history_count()
                QMessageBox.information(
                    self,
                    "History Cleared",
                    "Pause history has been cleared."
                )
            except Exception as e:
                QMessageBox.warning(
                    self,
                    "Error",
                    f"Could not clear history: {e}"
                )

    def _update_history_count(self):
        """Update the history count label."""
        try:
            from privacy_mode import get_privacy_handler
            handler = get_privacy_handler()
            history = handler.get_pause_history()
            count = len(history)
            self.history_count_label.setText(f"{count} pause event(s) recorded")
        except Exception:
            self.history_count_label.setText("Unable to load history")

    def _on_category_toggled(self, state):
        """Handle category checkbox toggle."""
        checkbox = self.sender()
        if not checkbox:
            return

        cat_key = checkbox.property("category_key")
        if state == Qt.CheckState.Checked.value:
            # Add all apps from category
            added = self.settings.add_sensitive_category(cat_key)
            if added > 0:
                self._refresh_excluded_apps_list()
        else:
            # Remove all apps from category
            removed = self.settings.remove_sensitive_category(cat_key)
            if removed > 0:
                self._refresh_excluded_apps_list()

    def _add_excluded_app(self):
        """Add a custom app to the excluded list."""
        app_name, ok = QInputDialog.getText(
            self,
            "Add Excluded App",
            "Enter the app name or process name to exclude:\n"
            "(e.g., 'Discord', 'discord.exe', 'Microsoft Teams')",
        )

        if ok and app_name.strip():
            app_name = app_name.strip()
            if self.settings.add_excluded_app(app_name):
                self._refresh_excluded_apps_list()
            else:
                QMessageBox.information(
                    self,
                    "Already Excluded",
                    f"'{app_name}' is already in the exclusion list."
                )

    def _add_running_app(self):
        """Show dialog to add from currently running apps."""
        try:
            import psutil
            running_apps = []
            seen_names = set()

            for proc in psutil.process_iter(['name']):
                try:
                    name = proc.info['name']
                    if name and name not in seen_names and not name.startswith('_'):
                        # Filter out system processes
                        if not name.lower() in ['system', 'idle', 'registry', 'smss.exe',
                                                 'csrss.exe', 'wininit.exe', 'services.exe',
                                                 'lsass.exe', 'svchost.exe', 'fontdrvhost.exe',
                                                 'dwm.exe', 'spoolsv.exe', 'sihost.exe',
                                                 'taskhostw.exe', 'ctfmon.exe', 'runtimebroker.exe',
                                                 'searchhost.exe', 'startmenuexperiencehost.exe']:
                            running_apps.append(name)
                            seen_names.add(name)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            running_apps.sort(key=lambda x: x.lower())

            if not running_apps:
                QMessageBox.information(
                    self,
                    "No Apps Found",
                    "No running applications were found."
                )
                return

            app_name, ok = QInputDialog.getItem(
                self,
                "Add Running App",
                "Select an app to exclude from monitoring:",
                running_apps,
                0,
                False
            )

            if ok and app_name:
                if self.settings.add_excluded_app(app_name):
                    self._refresh_excluded_apps_list()
                else:
                    QMessageBox.information(
                        self,
                        "Already Excluded",
                        f"'{app_name}' is already in the exclusion list."
                    )

        except ImportError:
            QMessageBox.warning(
                self,
                "psutil Required",
                "The psutil package is required for this feature."
            )

    def _remove_excluded_app(self):
        """Remove the selected app from the excluded list."""
        current_item = self.excluded_apps_list.currentItem()
        if current_item:
            app_name = current_item.text()
            self.settings.remove_excluded_app(app_name)
            self._refresh_excluded_apps_list()

    def _clear_all_excluded_apps(self):
        """Clear all excluded apps."""
        if self.excluded_apps_list.count() == 0:
            return

        reply = QMessageBox.question(
            self,
            "Clear All Excluded Apps",
            "Are you sure you want to remove all apps from the exclusion list?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.settings.set("excluded_apps", [])
            self._refresh_excluded_apps_list()
            # Uncheck all category checkboxes
            for checkbox in self.category_checkboxes.values():
                checkbox.blockSignals(True)
                checkbox.setChecked(False)
                checkbox.blockSignals(False)

    def _refresh_excluded_apps_list(self):
        """Refresh the excluded apps list widget."""
        self.excluded_apps_list.clear()
        excluded_apps = self.settings.get_excluded_apps()

        for app in sorted(excluded_apps, key=lambda x: x.lower()):
            item = QListWidgetItem(app)
            self.excluded_apps_list.addItem(item)

        # Update category checkbox states
        self._update_category_states()

    def _update_category_states(self):
        """Update category checkboxes based on current exclusions."""
        for cat_key, checkbox in self.category_checkboxes.items():
            excluded_count, total_count = self.settings.get_category_status(cat_key)

            # Block signals to prevent triggering stateChanged
            checkbox.blockSignals(True)

            if excluded_count == total_count:
                checkbox.setChecked(True)
            elif excluded_count > 0:
                checkbox.setTristate(True)
                checkbox.setCheckState(Qt.CheckState.PartiallyChecked)
            else:
                checkbox.setTristate(False)
                checkbox.setChecked(False)

            checkbox.blockSignals(False)

    def create_offline_tab(self) -> QWidget:
        """Create the Offline Mode settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Enable/disable Offline Mode
        self.offline_mode_check = QCheckBox("Enable Offline Mode")
        self.offline_mode_check.setToolTip(
            "Store meetings and conversations locally for offline access.\n"
            "Data will sync automatically when back online."
        )
        self.offline_mode_check.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(self.offline_mode_check)

        # Description
        desc_label = QLabel(
            "Offline Mode allows ReadIn AI to work without an internet connection. "
            "Your meetings, transcripts, and action items are stored locally and "
            "synced when you're back online. Local transcription works offline by default."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #888888; font-size: 11px; margin-bottom: 10px;")
        layout.addWidget(desc_label)

        # Sync Settings Group
        sync_group = QGroupBox("Sync Settings")
        sync_layout = QFormLayout(sync_group)

        # Sync interval
        self.sync_interval_spin = QSpinBox()
        self.sync_interval_spin.setRange(1, 60)
        self.sync_interval_spin.setValue(1)
        self.sync_interval_spin.setSuffix(" minutes")
        self.sync_interval_spin.setToolTip(
            "How often to sync data with the server when online.\n"
            "Lower values = more frequent syncs but higher network usage."
        )
        sync_layout.addRow("Sync Interval:", self.sync_interval_spin)

        # Auto sync options
        self.auto_sync_startup_check = QCheckBox("Sync on startup")
        self.auto_sync_startup_check.setToolTip("Automatically sync when the app starts")
        sync_layout.addRow("", self.auto_sync_startup_check)

        self.sync_on_meeting_end_check = QCheckBox("Sync when meeting ends")
        self.sync_on_meeting_end_check.setToolTip("Automatically sync data after each meeting")
        sync_layout.addRow("", self.sync_on_meeting_end_check)

        layout.addWidget(sync_group)

        # Storage Settings Group
        storage_group = QGroupBox("Storage Settings")
        storage_layout = QFormLayout(storage_group)

        # Max storage
        self.max_storage_spin = QSpinBox()
        self.max_storage_spin.setRange(100, 2000)
        self.max_storage_spin.setValue(500)
        self.max_storage_spin.setSuffix(" MB")
        self.max_storage_spin.setToolTip(
            "Maximum disk space for offline storage.\n"
            "Older synced data will be removed when limit is reached."
        )
        storage_layout.addRow("Max Storage:", self.max_storage_spin)

        # Storage usage display
        self.storage_usage_label = QLabel("Calculating...")
        self.storage_usage_label.setStyleSheet("color: #a6adc8; font-size: 11px;")
        storage_layout.addRow("Current Usage:", self.storage_usage_label)

        layout.addWidget(storage_group)

        # Sync Status Group
        status_group = QGroupBox("Sync Status")
        status_layout = QFormLayout(status_group)

        # Status labels
        self.sync_status_label = QLabel("Unknown")
        self.sync_status_label.setStyleSheet("color: #a6adc8;")
        status_layout.addRow("Status:", self.sync_status_label)

        self.pending_syncs_label = QLabel("0 items")
        self.pending_syncs_label.setStyleSheet("color: #a6adc8;")
        status_layout.addRow("Pending:", self.pending_syncs_label)

        self.last_sync_label = QLabel("Never")
        self.last_sync_label.setStyleSheet("color: #a6adc8;")
        status_layout.addRow("Last Sync:", self.last_sync_label)

        # Sync now button
        sync_btn_layout = QHBoxLayout()
        self.sync_now_btn = QPushButton("Sync Now")
        self.sync_now_btn.setToolTip("Manually trigger a sync")
        self.sync_now_btn.clicked.connect(self._on_sync_now_clicked)
        sync_btn_layout.addWidget(self.sync_now_btn)

        self.clear_offline_btn = QPushButton("Clear Offline Data")
        self.clear_offline_btn.setToolTip("Remove all locally stored data (synced data only)")
        self.clear_offline_btn.setStyleSheet("color: #f9e2af;")
        self.clear_offline_btn.clicked.connect(self._on_clear_offline_clicked)
        sync_btn_layout.addWidget(self.clear_offline_btn)

        sync_btn_layout.addStretch()
        status_layout.addRow("", sync_btn_layout)

        layout.addWidget(status_group)

        # Help text
        help_label = QLabel(
            "Note: Local transcription already works offline. This feature stores "
            "meetings and conversations locally so they can be synced later."
        )
        help_label.setWordWrap(True)
        help_label.setStyleSheet("color: #666666; font-size: 10px;")
        layout.addWidget(help_label)

        layout.addStretch()

        # Update storage usage
        self._update_storage_usage()

        return widget

    def _on_sync_now_clicked(self):
        """Handle sync now button click."""
        try:
            from services.sync_manager import get_sync_manager
            sync_manager = get_sync_manager()
            if sync_manager.sync_now():
                QMessageBox.information(
                    self,
                    "Sync Started",
                    "Sync has been initiated. Check the sync status for progress."
                )
            else:
                QMessageBox.warning(
                    self,
                    "Sync Not Available",
                    "Cannot sync at this time. Either a sync is already in progress "
                    "or offline mode is not properly configured."
                )
        except Exception as e:
            QMessageBox.warning(
                self,
                "Sync Error",
                f"Could not start sync: {e}"
            )

    def _on_clear_offline_clicked(self):
        """Handle clear offline data button click."""
        reply = QMessageBox.question(
            self,
            "Clear Offline Data",
            "This will remove all locally stored data that has already been synced.\n"
            "Pending (unsynced) data will be preserved.\n\n"
            "Are you sure you want to continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                from services.offline_storage import get_offline_storage
                storage = get_offline_storage()
                storage.cleanup_old_data(days=0)  # Remove all synced data
                self._update_storage_usage()
                QMessageBox.information(
                    self,
                    "Data Cleared",
                    "Synced offline data has been removed."
                )
            except Exception as e:
                QMessageBox.warning(
                    self,
                    "Error",
                    f"Could not clear offline data: {e}"
                )

    def _update_storage_usage(self):
        """Update storage usage display."""
        try:
            from services.offline_storage import get_offline_storage
            storage = get_offline_storage()
            status = storage.get_status()

            usage_mb = status.get("storage_size_mb", 0)
            max_mb = self.max_storage_spin.value()
            percentage = int((usage_mb / max_mb) * 100) if max_mb > 0 else 0

            self.storage_usage_label.setText(
                f"{usage_mb:.1f} MB / {max_mb} MB ({percentage}%)"
            )

            # Update pending count
            pending = status.get("pending_syncs", 0)
            self.pending_syncs_label.setText(f"{pending} items")

            # Color code based on usage
            if percentage >= 90:
                self.storage_usage_label.setStyleSheet("color: #ef4444;")
            elif percentage >= 70:
                self.storage_usage_label.setStyleSheet("color: #f9e2af;")
            else:
                self.storage_usage_label.setStyleSheet("color: #a6e3a1;")

        except Exception as e:
            self.storage_usage_label.setText("Unable to calculate")
            self.storage_usage_label.setStyleSheet("color: #6c7086;")

    def _update_sync_status(self):
        """Update sync status display."""
        try:
            from services.sync_manager import get_sync_manager
            sync_manager = get_sync_manager()
            status = sync_manager.get_status()

            # Update status label
            if status.get("is_syncing"):
                self.sync_status_label.setText("Syncing...")
                self.sync_status_label.setStyleSheet("color: #f59e0b;")
            elif status.get("is_online"):
                self.sync_status_label.setText("Online")
                self.sync_status_label.setStyleSheet("color: #a6e3a1;")
            else:
                self.sync_status_label.setText("Offline")
                self.sync_status_label.setStyleSheet("color: #ef4444;")

            # Update last sync
            last_sync = status.get("last_sync")
            if last_sync:
                from datetime import datetime
                try:
                    dt = datetime.fromisoformat(last_sync)
                    self.last_sync_label.setText(dt.strftime("%Y-%m-%d %H:%M"))
                except (ValueError, TypeError):
                    self.last_sync_label.setText("Unknown")
            else:
                self.last_sync_label.setText("Never")

        except Exception:
            self.sync_status_label.setText("Unknown")
            self.sync_status_label.setStyleSheet("color: #6c7086;")

    def create_advanced_tab(self) -> QWidget:
        """Create the Advanced settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Export settings
        export_group = QGroupBox("Data Export")
        export_layout = QVBoxLayout(export_group)

        export_btn_layout = QHBoxLayout()

        self.export_txt_btn = QPushButton("Export as TXT")
        self.export_txt_btn.clicked.connect(lambda: self.export_conversations("txt"))
        export_btn_layout.addWidget(self.export_txt_btn)

        self.export_md_btn = QPushButton("Export as Markdown")
        self.export_md_btn.clicked.connect(lambda: self.export_conversations("md"))
        export_btn_layout.addWidget(self.export_md_btn)

        self.export_json_btn = QPushButton("Export as JSON")
        self.export_json_btn.clicked.connect(lambda: self.export_conversations("json"))
        export_btn_layout.addWidget(self.export_json_btn)

        export_layout.addLayout(export_btn_layout)
        layout.addWidget(export_group)

        # Startup settings
        startup_group = QGroupBox("Startup")
        startup_layout = QFormLayout(startup_group)

        self.auto_start_check = QCheckBox("Start ReadIn AI when Windows starts")
        self.auto_start_check.setChecked(self._is_in_startup())
        self.auto_start_check.stateChanged.connect(self._toggle_startup)
        startup_layout.addRow("", self.auto_start_check)

        layout.addWidget(startup_group)

        # Updates
        update_group = QGroupBox("Updates")
        update_layout = QFormLayout(update_group)

        self.auto_update_check = QCheckBox("Check for updates on startup")
        self.auto_update_check.setChecked(True)
        update_layout.addRow("", self.auto_update_check)

        self.check_updates_btn = QPushButton("Check Now")
        self.check_updates_btn.clicked.connect(self.check_for_updates)
        update_layout.addRow("Manual Check:", self.check_updates_btn)

        layout.addWidget(update_group)

        # Debug
        debug_group = QGroupBox("Debug")
        debug_layout = QFormLayout(debug_group)

        self.debug_mode_check = QCheckBox("Enable debug logging")
        debug_layout.addRow("", self.debug_mode_check)

        self.reset_all_btn = QPushButton("Reset All Settings")
        self.reset_all_btn.clicked.connect(self.reset_all_settings)
        debug_layout.addRow("", self.reset_all_btn)

        layout.addWidget(debug_group)
        layout.addStretch()

        return widget

    def refresh_audio_devices(self):
        """Refresh the list of available audio devices."""
        self.device_combo.clear()

        try:
            devices = AudioCapture.get_available_devices()

            # Sort: loopback first, then default, then others
            def sort_key(d):
                if d['is_loopback']:
                    return (0, d['name'])
                if d['is_default']:
                    return (1, d['name'])
                return (2, d['name'])

            devices.sort(key=sort_key)

            for device in devices:
                # Build display name with indicators
                name = device['name']
                badges = []
                if device['is_loopback']:
                    badges.append("LOOPBACK")
                if device['is_default']:
                    badges.append("DEFAULT")

                display_name = f"{name} ({device['channels']} ch)"
                if badges:
                    display_name += f" [{', '.join(badges)}]"

                self.device_combo.addItem(display_name, device['index'])
        except Exception as e:
            self.device_combo.addItem("Default Device", -1)

    def on_preset_changed(self, preset_name: str):
        """Handle preset selection change."""
        if preset_name in PROMPT_PRESETS:
            preset_data = PROMPT_PRESETS[preset_name]
            self.prompt_edit.setPlainText(preset_data.get("prompt", ""))

    def preview_theme(self, index: int):
        """Preview the selected theme and emit signal for immediate application."""
        theme_id = self.theme_combo.itemData(index)
        if theme_id:
            self.setStyleSheet(generate_stylesheet(theme_id))
            # Emit signal for immediate theme application to overlay
            self.theme_changed.emit(theme_id)
            self.setting_changed.emit("theme", theme_id)

    def reset_shortcuts(self):
        """Reset shortcuts to defaults."""
        from config import DEFAULT_SHORTCUTS
        self.shortcut_toggle.setText(DEFAULT_SHORTCUTS.get("toggle_listen", "ctrl+shift+r"))
        self.shortcut_show_hide.setText(DEFAULT_SHORTCUTS.get("show_hide", "ctrl+shift+h"))
        self.shortcut_clear.setText(DEFAULT_SHORTCUTS.get("clear_context", "ctrl+shift+c"))

    def export_conversations(self, format: str):
        """Export conversations in the specified format."""
        file_filter = {
            "txt": "Text Files (*.txt)",
            "md": "Markdown Files (*.md)",
            "json": "JSON Files (*.json)"
        }

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Conversations",
            f"readin_export.{format}",
            file_filter.get(format, "All Files (*)")
        )

        if file_path:
            # Signal to main app to perform export
            self.settings.set("export_path", file_path)
            self.settings.set("export_format", format)
            QMessageBox.information(
                self,
                "Export",
                f"Export path saved. Click Apply to export to:\n{file_path}"
            )

    def check_for_updates(self):
        """Check for application updates."""
        try:
            from src.update_checker import UpdateChecker
            import webbrowser
            checker = UpdateChecker()
            update_info = checker.check_for_updates(background=False)

            if update_info:
                # Create a custom message box with Download button
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Update Available")
                msg_box.setText(f"Version {update_info.version} is available!")
                msg_box.setInformativeText(
                    f"{update_info.changelog or 'New improvements and bug fixes.'}\n\n"
                    "Click 'Download' to get the latest version."
                )
                msg_box.setIcon(QMessageBox.Icon.Information)

                download_btn = msg_box.addButton("Download", QMessageBox.ButtonRole.AcceptRole)
                msg_box.addButton("Later", QMessageBox.ButtonRole.RejectRole)

                msg_box.exec()

                if msg_box.clickedButton() == download_btn:
                    # Open the download page
                    download_url = update_info.download_url or "https://www.getreadin.us/download"
                    webbrowser.open(download_url)
            else:
                QMessageBox.information(
                    self,
                    "Up to Date",
                    "You're running the latest version."
                )
        except Exception as e:
            QMessageBox.warning(
                self,
                "Update Check Failed",
                f"Could not check for updates:\n{str(e)}"
            )

    def reset_all_settings(self):
        """Reset all settings to defaults."""
        reply = QMessageBox.question(
            self,
            "Reset Settings",
            "Are you sure you want to reset all settings to defaults?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.settings.reset_to_defaults()
            self.load_settings()
            QMessageBox.information(
                self,
                "Settings Reset",
                "All settings have been reset to defaults."
            )

    def load_settings(self):
        """Load current settings into UI."""
        # Audio
        device_index = self.settings.get("audio_device", -1)
        for i in range(self.device_combo.count()):
            if self.device_combo.itemData(i) == device_index:
                self.device_combo.setCurrentIndex(i)
                break

        self.sample_rate_combo.setCurrentText(
            str(self.settings.get("sample_rate", 16000))
        )

        # AI
        self.model_combo.setCurrentText(
            self.settings.get("model", "claude-sonnet-4-20250514")
        )
        self.context_spin.setValue(self.settings.get("context_size", 3))
        self.prompt_edit.setPlainText(self.settings.get("system_prompt", ""))

        # AI Persona
        ai_persona = self.settings.get("ai_persona", "professional")
        for i in range(self.persona_combo.count()):
            if self.persona_combo.itemData(i) == ai_persona:
                self.persona_combo.setCurrentIndex(i)
                break
        custom_persona_prompt = self.settings.get("custom_persona_prompt", "")
        self.custom_persona_edit.setPlainText(custom_persona_prompt)
        # Show/hide custom prompt editor
        is_custom = ai_persona == "custom"
        self.custom_persona_label.setVisible(is_custom)
        self.custom_persona_edit.setVisible(is_custom)

        # Translation
        self.translation_check.setChecked(
            self.settings.get("translation_enabled", False)
        )
        translation_lang = self.settings.get("translation_target_language", "en")
        for i in range(self.translation_lang_combo.count()):
            if self.translation_lang_combo.itemData(i) == translation_lang:
                self.translation_lang_combo.setCurrentIndex(i)
                break
        self.show_original_check.setChecked(
            self.settings.get("translation_show_original", True)
        )

        lang = self.settings.get("language", "en")
        for i in range(self.language_combo.count()):
            if self.language_combo.itemData(i) == lang:
                self.language_combo.setCurrentIndex(i)
                break

        # Appearance
        theme = self.settings.get("theme", "dark_gold")
        for i in range(self.theme_combo.count()):
            if self.theme_combo.itemData(i) == theme:
                self.theme_combo.setCurrentIndex(i)
                break

        self.opacity_slider.setValue(self.settings.get("opacity", 90))
        self.font_size_spin.setValue(self.settings.get("font_size", 14))
        self.always_on_top_check.setChecked(
            self.settings.get("always_on_top", True)
        )
        self.remember_position_check.setChecked(
            self.settings.get("remember_position", True)
        )
        self.hide_from_capture_check.setChecked(
            self.settings.get("hide_from_screen_capture", False)
        )

        # Shortcuts
        shortcuts = self.settings.get("shortcuts", {})
        self.shortcut_toggle.setText(shortcuts.get("toggle_listening", "ctrl+shift+r"))
        self.shortcut_show_hide.setText(shortcuts.get("show_hide_overlay", "ctrl+shift+h"))
        self.shortcut_clear.setText(shortcuts.get("clear_context", "ctrl+shift+c"))
        self.enable_shortcuts_check.setChecked(
            self.settings.get("shortcuts_enabled", True)
        )

        # Advanced
        self.auto_update_check.setChecked(
            self.settings.get("auto_update_check", True)
        )
        self.debug_mode_check.setChecked(
            self.settings.get("debug_mode", False)
        )

        # Privacy Mode
        self.privacy_mode_check.setChecked(
            self.settings.get("privacy_mode_enabled", True)
        )
        self._refresh_excluded_apps_list()

        # Auto-detect sensitive apps
        try:
            from privacy_mode import get_privacy_handler
            handler = get_privacy_handler()
            self.auto_detect_check.setChecked(handler.is_auto_detect_enabled())
            self._update_history_count()
        except Exception:
            self.auto_detect_check.setChecked(True)

        # Speaker Diarization
        self.diarization_check.setChecked(
            self.settings.get("diarization_enabled", False)
        )
        self.min_speakers_spin.setValue(
            self.settings.get("diarization_min_speakers", 1)
        )
        self.max_speakers_spin.setValue(
            self.settings.get("diarization_max_speakers", 10)
        )
        self.diarization_interval_spin.setValue(
            int(self.settings.get("diarization_interval", 30))
        )

        # Load HuggingFace token from environment or settings
        import os
        hf_token = os.getenv("HUGGINGFACE_TOKEN", "")
        if hf_token:
            self.hf_token_input.setText(hf_token)
            self.token_status_label.setText("Token loaded from environment")
            self.token_status_label.setStyleSheet("color: #a6e3a1; font-size: 11px;")
        else:
            self.token_status_label.setText("No token configured")
            self.token_status_label.setStyleSheet("color: #f9e2af; font-size: 11px;")

        # Voice Commands
        self.voice_commands_check.setChecked(
            self.settings.get("voice_commands_enabled", False)
        )
        # Load voice command microphone device
        voice_cmd_device = self.settings.get("voice_command_device_index")
        for i in range(self.voice_cmd_device_combo.count()):
            if self.voice_cmd_device_combo.itemData(i) == voice_cmd_device:
                self.voice_cmd_device_combo.setCurrentIndex(i)
                break
        self.voice_cmd_tts_check.setChecked(
            self.settings.get("voice_command_tts_feedback", False)
        )

        # Voice Feedback
        self.voice_feedback_check.setChecked(
            self.settings.get("voice_feedback_enabled", False)
        )
        voice_rate = self.settings.get("voice_feedback_rate", 150)
        self.voice_rate_slider.setValue(voice_rate)
        self.voice_rate_label.setText(f"{voice_rate} wpm")
        voice_volume = int(self.settings.get("voice_feedback_volume", 0.8) * 100)
        self.voice_volume_slider.setValue(voice_volume)
        self.voice_volume_label.setText(f"{voice_volume}%")

        # Offline Mode
        self.offline_mode_check.setChecked(
            self.settings.get("offline_mode_enabled", True)
        )
        self.sync_interval_spin.setValue(
            self.settings.get("sync_interval_minutes", 1)
        )
        self.max_storage_spin.setValue(
            self.settings.get("max_offline_storage_mb", 500)
        )
        self.auto_sync_startup_check.setChecked(
            self.settings.get("auto_sync_on_startup", True)
        )
        self.sync_on_meeting_end_check.setChecked(
            self.settings.get("sync_on_meeting_end", True)
        )
        self._update_storage_usage()
        self._update_sync_status()

    def apply_settings(self):
        """Apply current settings without closing, emitting signals for each change."""
        # Audio - validate device before saving
        device_data = self.device_combo.currentData()
        if self._validate_audio_device(device_data):
            old_device = self.settings.get("audio_device")
            self.settings.set("audio_device", device_data)
            if old_device != device_data:
                self.setting_changed.emit("audio_device", device_data)

        old_sample_rate = self.settings.get("sample_rate")
        new_sample_rate = int(self.sample_rate_combo.currentText())
        self.settings.set("sample_rate", new_sample_rate)
        if old_sample_rate != new_sample_rate:
            self.setting_changed.emit("sample_rate", new_sample_rate)

        # AI - emit signals for each change
        old_model = self.settings.get("model")
        new_model = self.model_combo.currentText()
        self.settings.set("model", new_model)
        if old_model != new_model:
            self.setting_changed.emit("model", new_model)

        old_context = self.settings.get("context_size")
        new_context = self.context_spin.value()
        self.settings.set("context_size", new_context)
        if old_context != new_context:
            self.setting_changed.emit("context_size", new_context)

        old_prompt = self.settings.get("system_prompt")
        new_prompt = self.prompt_edit.toPlainText()
        self.settings.set("system_prompt", new_prompt)
        if old_prompt != new_prompt:
            self.setting_changed.emit("system_prompt", new_prompt)

        # AI Persona settings
        old_persona = self.settings.get("ai_persona")
        new_persona = self.persona_combo.currentData()
        self.settings.set("ai_persona", new_persona)
        if old_persona != new_persona:
            self.setting_changed.emit("ai_persona", new_persona)

        old_custom_persona = self.settings.get("custom_persona_prompt")
        new_custom_persona = self.custom_persona_edit.toPlainText()
        self.settings.set("custom_persona_prompt", new_custom_persona)
        if old_custom_persona != new_custom_persona:
            self.setting_changed.emit("custom_persona_prompt", new_custom_persona)

        # Translation settings
        old_translation_enabled = self.settings.get("translation_enabled")
        new_translation_enabled = self.translation_check.isChecked()
        self.settings.set("translation_enabled", new_translation_enabled)
        if old_translation_enabled != new_translation_enabled:
            self.setting_changed.emit("translation_enabled", new_translation_enabled)

        old_translation_lang = self.settings.get("translation_target_language")
        new_translation_lang = self.translation_lang_combo.currentData()
        self.settings.set("translation_target_language", new_translation_lang)
        if old_translation_lang != new_translation_lang:
            self.setting_changed.emit("translation_target_language", new_translation_lang)

        old_show_original = self.settings.get("translation_show_original")
        new_show_original = self.show_original_check.isChecked()
        self.settings.set("translation_show_original", new_show_original)
        if old_show_original != new_show_original:
            self.setting_changed.emit("translation_show_original", new_show_original)

        old_language = self.settings.get("language")
        new_language = self.language_combo.currentData()
        self.settings.set("language", new_language)
        if old_language != new_language:
            self.setting_changed.emit("language", new_language)

        # Appearance - emit signals for immediate application
        new_theme = self.theme_combo.currentData()
        self.settings.set("theme", new_theme)

        old_opacity = self.settings.get("opacity")
        new_opacity = self.opacity_slider.value()
        self.settings.set("opacity", new_opacity)
        if old_opacity != new_opacity:
            self.setting_changed.emit("opacity", new_opacity)

        old_font_size = self.settings.get("font_size")
        new_font_size = self.font_size_spin.value()
        self.settings.set("font_size", new_font_size)
        if old_font_size != new_font_size:
            self.setting_changed.emit("font_size", new_font_size)

        old_always_on_top = self.settings.get("always_on_top")
        new_always_on_top = self.always_on_top_check.isChecked()
        self.settings.set("always_on_top", new_always_on_top)
        if old_always_on_top != new_always_on_top:
            self.setting_changed.emit("always_on_top", new_always_on_top)

        old_remember_position = self.settings.get("remember_position")
        new_remember_position = self.remember_position_check.isChecked()
        self.settings.set("remember_position", new_remember_position)
        if old_remember_position != new_remember_position:
            self.setting_changed.emit("remember_position", new_remember_position)

        old_hide_from_capture = self.settings.get("hide_from_screen_capture")
        new_hide_from_capture = self.hide_from_capture_check.isChecked()
        self.settings.set("hide_from_screen_capture", new_hide_from_capture)
        if old_hide_from_capture != new_hide_from_capture:
            self.setting_changed.emit("hide_from_screen_capture", new_hide_from_capture)

        # Emit theme change for immediate application
        if new_theme != self._original_theme:
            self.theme_changed.emit(new_theme)
            self._original_theme = new_theme

        # Shortcuts - immediate registration
        shortcuts = {
            "toggle_listening": self.shortcut_toggle.text(),
            "show_hide_overlay": self.shortcut_show_hide.text(),
            "clear_context": self.shortcut_clear.text()
        }
        self.settings.set("shortcuts", shortcuts)
        self.settings.set("shortcuts_enabled", self.enable_shortcuts_check.isChecked())

        # Emit signal for immediate shortcut registration
        if self.enable_shortcuts_check.isChecked():
            self.shortcuts_changed.emit(shortcuts)

        # Advanced - emit signals for each change
        old_auto_update = self.settings.get("auto_update_check")
        new_auto_update = self.auto_update_check.isChecked()
        self.settings.set("auto_update_check", new_auto_update)
        if old_auto_update != new_auto_update:
            self.setting_changed.emit("auto_update_check", new_auto_update)

        old_debug_mode = self.settings.get("debug_mode")
        new_debug_mode = self.debug_mode_check.isChecked()
        self.settings.set("debug_mode", new_debug_mode)
        if old_debug_mode != new_debug_mode:
            self.setting_changed.emit("debug_mode", new_debug_mode)

        # Privacy Mode - emit signals for changes
        old_privacy_mode = self.settings.get("privacy_mode_enabled")
        new_privacy_mode = self.privacy_mode_check.isChecked()
        self.settings.set("privacy_mode_enabled", new_privacy_mode)
        if old_privacy_mode != new_privacy_mode:
            self.setting_changed.emit("privacy_mode_enabled", new_privacy_mode)

        # Auto-detect sensitive apps setting
        try:
            from privacy_mode import get_privacy_handler
            handler = get_privacy_handler()
            handler.set_auto_detect(self.auto_detect_check.isChecked())
        except Exception:
            pass

        # Note: excluded_apps are saved immediately when modified through the UI

        # Speaker Diarization - emit signals for changes
        old_diarization = self.settings.get("diarization_enabled")
        new_diarization = self.diarization_check.isChecked()
        self.settings.set("diarization_enabled", new_diarization)
        if old_diarization != new_diarization:
            self.setting_changed.emit("diarization_enabled", new_diarization)

        self.settings.set("diarization_min_speakers", self.min_speakers_spin.value())
        self.settings.set("diarization_max_speakers", self.max_speakers_spin.value())
        self.settings.set("diarization_interval", float(self.diarization_interval_spin.value()))

        # Save HuggingFace token to environment if provided
        hf_token = self.hf_token_input.text().strip()
        if hf_token:
            import os
            os.environ["HUGGINGFACE_TOKEN"] = hf_token
            self.token_status_label.setText("Token saved to session")
            self.token_status_label.setStyleSheet("color: #a6e3a1; font-size: 11px;")

        # Voice Commands - emit signals for changes
        old_voice_commands_enabled = self.settings.get("voice_commands_enabled")
        new_voice_commands_enabled = self.voice_commands_check.isChecked()
        self.settings.set("voice_commands_enabled", new_voice_commands_enabled)
        if old_voice_commands_enabled != new_voice_commands_enabled:
            self.setting_changed.emit("voice_commands_enabled", new_voice_commands_enabled)

        old_voice_cmd_device = self.settings.get("voice_command_device_index")
        new_voice_cmd_device = self.voice_cmd_device_combo.currentData()
        self.settings.set("voice_command_device_index", new_voice_cmd_device)
        if old_voice_cmd_device != new_voice_cmd_device:
            self.setting_changed.emit("voice_command_device_index", new_voice_cmd_device)

        old_voice_cmd_tts = self.settings.get("voice_command_tts_feedback")
        new_voice_cmd_tts = self.voice_cmd_tts_check.isChecked()
        self.settings.set("voice_command_tts_feedback", new_voice_cmd_tts)
        if old_voice_cmd_tts != new_voice_cmd_tts:
            self.setting_changed.emit("voice_command_tts_feedback", new_voice_cmd_tts)

        # Voice Feedback - emit signals for changes
        old_voice_feedback_enabled = self.settings.get("voice_feedback_enabled")
        new_voice_feedback_enabled = self.voice_feedback_check.isChecked()
        self.settings.set("voice_feedback_enabled", new_voice_feedback_enabled)
        if old_voice_feedback_enabled != new_voice_feedback_enabled:
            self.setting_changed.emit("voice_feedback_enabled", new_voice_feedback_enabled)

        old_voice_rate = self.settings.get("voice_feedback_rate")
        new_voice_rate = self.voice_rate_slider.value()
        self.settings.set("voice_feedback_rate", new_voice_rate)
        if old_voice_rate != new_voice_rate:
            self.setting_changed.emit("voice_feedback_rate", new_voice_rate)

        old_voice_volume = self.settings.get("voice_feedback_volume")
        new_voice_volume = self.voice_volume_slider.value() / 100.0
        self.settings.set("voice_feedback_volume", new_voice_volume)
        if old_voice_volume != new_voice_volume:
            self.setting_changed.emit("voice_feedback_volume", new_voice_volume)

        # Offline Mode - emit signals for changes
        old_offline_mode = self.settings.get("offline_mode_enabled")
        new_offline_mode = self.offline_mode_check.isChecked()
        self.settings.set("offline_mode_enabled", new_offline_mode)
        if old_offline_mode != new_offline_mode:
            self.setting_changed.emit("offline_mode_enabled", new_offline_mode)

        old_sync_interval = self.settings.get("sync_interval_minutes")
        new_sync_interval = self.sync_interval_spin.value()
        self.settings.set("sync_interval_minutes", new_sync_interval)
        if old_sync_interval != new_sync_interval:
            self.setting_changed.emit("sync_interval_minutes", new_sync_interval)
            # Update sync manager if available
            try:
                from services.sync_manager import get_sync_manager
                sync_manager = get_sync_manager()
                sync_manager.set_sync_interval(new_sync_interval * 60)  # Convert to seconds
            except Exception:
                pass

        old_max_storage = self.settings.get("max_offline_storage_mb")
        new_max_storage = self.max_storage_spin.value()
        self.settings.set("max_offline_storage_mb", new_max_storage)
        if old_max_storage != new_max_storage:
            self.setting_changed.emit("max_offline_storage_mb", new_max_storage)

        self.settings.set("auto_sync_on_startup", self.auto_sync_startup_check.isChecked())
        self.settings.set("sync_on_meeting_end", self.sync_on_meeting_end_check.isChecked())

        # Update storage display
        self._update_storage_usage()

        self.settings_changed.emit()

    def _validate_audio_device(self, device_index) -> bool:
        """Validate that the audio device index is valid before saving.

        Args:
            device_index: The device index to validate

        Returns:
            True if device is valid, False otherwise
        """
        if device_index is None or device_index == -1:
            return True  # Default device is always valid

        try:
            devices = AudioCapture.get_available_devices()
            valid_indices = [d['index'] for d in devices]
            return device_index in valid_indices
        except Exception:
            return False

    def accept_settings(self):
        """Apply settings and close dialog."""
        self.apply_settings()
        self.accept()

    def _is_in_startup(self) -> bool:
        """Check if the app is set to start with Windows."""
        if sys.platform != 'win32':
            return False
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_READ
            )
            try:
                winreg.QueryValueEx(key, "ReadInAI")
                return True
            except WindowsError:
                return False
            finally:
                winreg.CloseKey(key)
        except Exception:
            return False

    def _toggle_startup(self, state):
        """Toggle auto-start with Windows."""
        if sys.platform != 'win32':
            QMessageBox.information(
                self,
                "Not Supported",
                "Auto-start is only supported on Windows."
            )
            return

        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE
            )

            if state:  # Enable auto-start
                # Get the path to the current executable
                exe_path = sys.executable
                if getattr(sys, 'frozen', False):
                    # Running as compiled exe
                    exe_path = sys.executable
                else:
                    # Running as script - use pythonw to avoid console
                    import os
                    main_script = os.path.join(
                        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                        "main.py"
                    )
                    exe_path = f'"{sys.executable}" "{main_script}"'

                winreg.SetValueEx(key, "ReadInAI", 0, winreg.REG_SZ, exe_path)
                QMessageBox.information(
                    self,
                    "Auto-Start Enabled",
                    "ReadIn AI will now start automatically when Windows starts."
                )
            else:  # Disable auto-start
                try:
                    winreg.DeleteValue(key, "ReadInAI")
                    QMessageBox.information(
                        self,
                        "Auto-Start Disabled",
                        "ReadIn AI will no longer start automatically."
                    )
                except WindowsError:
                    pass  # Value doesn't exist

            winreg.CloseKey(key)

        except Exception as e:
            QMessageBox.warning(
                self,
                "Error",
                f"Could not modify startup settings: {e}"
            )
            # Revert checkbox state
            self.auto_start_check.setChecked(self._is_in_startup())
