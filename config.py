"""Configuration for Meeting Read-In AI Tool."""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Platform detection
IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")

# API Configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Backend API Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "https://www.getreadin.us")

# Whisper Configuration
# Options: tiny.en (fastest), base.en (balanced), small.en (accurate)
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base.en")

# Claude Configuration
RESPONSE_MODEL = "claude-sonnet-4-20250514"  # Fast responses

# Audio Configuration
AUDIO_SAMPLE_RATE = 16000  # Whisper expects 16kHz
AUDIO_CHUNK_DURATION = 3.0  # Seconds per chunk for transcription

# Process Monitor Configuration - Platform specific
# Comprehensive list of video conferencing applications
if IS_WINDOWS:
    MONITORED_PROCESSES = [
        # Microsoft Teams
        "Teams.exe",
        "ms-teams.exe",
        "msteams.exe",
        # Zoom
        "Zoom.exe",
        "zoom.exe",
        # Cisco Webex
        "webex.exe",
        "CiscoWebexStart.exe",
        "atmgr.exe",
        "webexmta.exe",
        # Skype
        "Skype.exe",
        "SkypeApp.exe",
        "SkypeHost.exe",
        # Discord
        "Discord.exe",
        # Slack
        "slack.exe",
        # GoToMeeting
        "g2mstart.exe",
        "g2mlauncher.exe",
        "GoToMeeting.exe",
        # BlueJeans
        "BlueJeans.exe",
        # RingCentral
        "RingCentral.exe",
        "RingCentralMeetings.exe",
        # Amazon Chime
        "Amazon Chime.exe",
        # Google Meet (desktop app)
        "Google Meet.exe",
        # Jitsi Meet
        "Jitsi Meet.exe",
        # Signal
        "Signal.exe",
        # Whereby
        "Whereby.exe",
        # Loom
        "Loom.exe",
        # Livestorm
        "Livestorm.exe",
        # Hopin
        "Hopin.exe",
        # StreamYard
        "StreamYard.exe",
    ]
elif IS_MACOS:
    MONITORED_PROCESSES = [
        # Microsoft Teams
        "Microsoft Teams",
        "Microsoft Teams (work or school)",
        "Microsoft Teams classic",
        # Zoom
        "zoom.us",
        "Zoom",
        # Cisco Webex
        "Cisco Webex Meetings",
        "Webex",
        "webex",
        # Skype
        "Skype",
        "Skype for Business",
        # Discord
        "Discord",
        # Slack
        "Slack",
        # GoToMeeting
        "GoToMeeting",
        "GoTo Meeting",
        # BlueJeans
        "BlueJeans",
        # RingCentral
        "RingCentral",
        "RingCentral Meetings",
        # Amazon Chime
        "Amazon Chime",
        # Google Meet (PWA)
        "Google Meet",
        # Jitsi Meet
        "Jitsi Meet",
        # FaceTime
        "FaceTime",
        # Signal
        "Signal",
        # Whereby
        "Whereby",
        # Loom
        "Loom",
    ]
else:  # Linux
    MONITORED_PROCESSES = [
        # Microsoft Teams
        "teams",
        "Teams",
        "microsoft teams",
        # Zoom
        "zoom",
        "Zoom",
        "ZoomLauncher",
        # Cisco Webex
        "webex",
        "CiscoWebex",
        # Skype
        "skype",
        "skypeforlinux",
        # Discord
        "discord",
        "Discord",
        # Slack
        "slack",
        "Slack",
        # Jitsi Meet
        "jitsi-meet",
        "Jitsi Meet",
        # Signal
        "signal-desktop",
        "Signal",
        # Element (Matrix)
        "element-desktop",
        "Element",
        # Zoom PWA
        "zoom-client",
    ]

PROCESS_CHECK_INTERVAL = 2.0  # Seconds between process checks

# UI Configuration
OVERLAY_WIDTH = 450
OVERLAY_HEIGHT = 300
OVERLAY_OPACITY = 0.92

# Version info
APP_VERSION = "1.4.7"
APP_NAME = "ReadIn AI"
UPDATE_CHECK_URL = "https://www.getreadin.us/api/v1/version"
GITHUB_RELEASES_URL = "https://github.com/derickjoseph8/readin-ai/releases"

# Default keyboard shortcuts
DEFAULT_SHORTCUTS = {
    "toggle_listen": "ctrl+shift+r",
    "show_hide": "ctrl+shift+h",
    "clear_context": "ctrl+shift+c",
}

# AI Configuration defaults
DEFAULT_CONTEXT_WINDOW = 3
MAX_CONTEXT_WINDOW = 10
MIN_CONTEXT_WINDOW = 1

# Export configuration
EXPORT_FORMATS = ["txt", "md", "json"]
DEFAULT_EXPORT_FORMAT = "md"
