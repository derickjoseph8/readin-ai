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
    QMessageBox, QFileDialog, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeySequence

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from settings_manager import SettingsManager

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

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = SettingsManager()
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
        self.tabs.addTab(self.create_appearance_tab(), "Appearance")
        self.tabs.addTab(self.create_shortcuts_tab(), "Shortcuts")
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
        layout.addStretch()

        # Populate devices
        self.refresh_audio_devices()

        return widget

    def create_ai_tab(self) -> QWidget:
        """Create the AI settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Model settings
        model_group = QGroupBox("Model Settings")
        model_layout = QFormLayout(model_group)

        self.model_combo = QComboBox()
        self.model_combo.addItems([
            "claude-3-5-sonnet-20241022",
            "claude-3-haiku-20240307",
            "claude-3-opus-20240229"
        ])
        model_layout.addRow("AI Model:", self.model_combo)

        self.context_spin = QSpinBox()
        self.context_spin.setRange(1, 10)
        self.context_spin.setValue(3)
        model_layout.addRow("Context Window:", self.context_spin)

        layout.addWidget(model_group)

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
        self.hide_from_capture_check.setChecked(True)
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
            for device in devices:
                self.device_combo.addItem(
                    f"{device['name']} ({device['channels']} ch)",
                    device['index']
                )
        except Exception as e:
            self.device_combo.addItem("Default Device", -1)

    def on_preset_changed(self, preset_name: str):
        """Handle preset selection change."""
        if preset_name in PROMPT_PRESETS:
            preset_data = PROMPT_PRESETS[preset_name]
            self.prompt_edit.setPlainText(preset_data.get("prompt", ""))

    def preview_theme(self, index: int):
        """Preview the selected theme."""
        theme_id = self.theme_combo.itemData(index)
        if theme_id:
            self.setStyleSheet(generate_stylesheet(theme_id))

    def reset_shortcuts(self):
        """Reset shortcuts to defaults."""
        from config import DEFAULT_SHORTCUTS
        self.shortcut_toggle.setText(DEFAULT_SHORTCUTS["toggle_listening"])
        self.shortcut_show_hide.setText(DEFAULT_SHORTCUTS["show_hide_overlay"])
        self.shortcut_clear.setText(DEFAULT_SHORTCUTS["clear_context"])

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
            from update_checker import UpdateChecker
            checker = UpdateChecker()
            has_update, info = checker.check_for_updates()

            if has_update:
                QMessageBox.information(
                    self,
                    "Update Available",
                    f"Version {info['version']} is available!\n\n{info.get('description', '')}"
                )
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
            self.settings.get("model", "claude-3-5-sonnet-20241022")
        )
        self.context_spin.setValue(self.settings.get("context_size", 3))
        self.prompt_edit.setPlainText(self.settings.get("system_prompt", ""))

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
            self.settings.get("hide_from_screen_capture", True)
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

    def apply_settings(self):
        """Apply current settings without closing."""
        # Audio
        self.settings.set("audio_device", self.device_combo.currentData())
        self.settings.set("sample_rate", int(self.sample_rate_combo.currentText()))

        # AI
        self.settings.set("model", self.model_combo.currentText())
        self.settings.set("context_size", self.context_spin.value())
        self.settings.set("system_prompt", self.prompt_edit.toPlainText())
        self.settings.set("language", self.language_combo.currentData())

        # Appearance
        self.settings.set("theme", self.theme_combo.currentData())
        self.settings.set("opacity", self.opacity_slider.value())
        self.settings.set("font_size", self.font_size_spin.value())
        self.settings.set("always_on_top", self.always_on_top_check.isChecked())
        self.settings.set("remember_position", self.remember_position_check.isChecked())
        self.settings.set("hide_from_screen_capture", self.hide_from_capture_check.isChecked())

        # Shortcuts
        self.settings.set("shortcuts", {
            "toggle_listening": self.shortcut_toggle.text(),
            "show_hide_overlay": self.shortcut_show_hide.text(),
            "clear_context": self.shortcut_clear.text()
        })
        self.settings.set("shortcuts_enabled", self.enable_shortcuts_check.isChecked())

        # Advanced
        self.settings.set("auto_update_check", self.auto_update_check.isChecked())
        self.settings.set("debug_mode", self.debug_mode_check.isChecked())

        self.settings_changed.emit()

    def accept_settings(self):
        """Apply settings and close dialog."""
        self.apply_settings()
        self.accept()
