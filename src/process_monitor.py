"""Process monitor for detecting Teams/Zoom launches."""

import threading
import time
from typing import Callable, Optional, List, Set

import psutil

from config import MONITORED_PROCESSES, PROCESS_CHECK_INTERVAL

# Map process names to friendly app names (cross-platform)
PROCESS_TO_APP = {
    # Microsoft Teams - Windows
    "Teams.exe": "Microsoft Teams",
    "ms-teams.exe": "Microsoft Teams",
    "msteams.exe": "Microsoft Teams",
    # Microsoft Teams - macOS
    "Microsoft Teams": "Microsoft Teams",
    "Microsoft Teams (work or school)": "Microsoft Teams",
    "Microsoft Teams classic": "Microsoft Teams",
    # Microsoft Teams - Linux
    "teams": "Microsoft Teams",
    "Teams": "Microsoft Teams",
    "microsoft teams": "Microsoft Teams",

    # Zoom - Windows
    "Zoom.exe": "Zoom",
    "zoom.exe": "Zoom",
    # Zoom - macOS
    "zoom.us": "Zoom",
    "Zoom": "Zoom",
    # Zoom - Linux
    "zoom": "Zoom",
    "ZoomLauncher": "Zoom",
    "zoom-client": "Zoom",

    # Webex - Windows
    "webex.exe": "Cisco Webex",
    "CiscoWebexStart.exe": "Cisco Webex",
    "atmgr.exe": "Cisco Webex",
    "webexmta.exe": "Cisco Webex",
    # Webex - macOS/Linux
    "Cisco Webex Meetings": "Cisco Webex",
    "Webex": "Cisco Webex",
    "webex": "Cisco Webex",
    "CiscoWebex": "Cisco Webex",

    # Skype - Windows
    "Skype.exe": "Skype",
    "SkypeApp.exe": "Skype",
    "SkypeHost.exe": "Skype",
    # Skype - macOS/Linux
    "Skype": "Skype",
    "Skype for Business": "Skype",
    "skype": "Skype",
    "skypeforlinux": "Skype",

    # Discord - All platforms
    "Discord.exe": "Discord",
    "Discord": "Discord",
    "discord": "Discord",

    # Slack - All platforms
    "slack.exe": "Slack",
    "Slack": "Slack",
    "slack": "Slack",

    # GoToMeeting - Windows
    "g2mstart.exe": "GoToMeeting",
    "g2mlauncher.exe": "GoToMeeting",
    "GoToMeeting.exe": "GoToMeeting",
    # GoToMeeting - macOS
    "GoToMeeting": "GoToMeeting",
    "GoTo Meeting": "GoToMeeting",

    # BlueJeans - All platforms
    "BlueJeans.exe": "BlueJeans",
    "BlueJeans": "BlueJeans",

    # RingCentral - All platforms
    "RingCentral.exe": "RingCentral",
    "RingCentralMeetings.exe": "RingCentral",
    "RingCentral": "RingCentral",
    "RingCentral Meetings": "RingCentral",

    # Amazon Chime - All platforms
    "Amazon Chime.exe": "Amazon Chime",
    "Amazon Chime": "Amazon Chime",

    # Google Meet - All platforms
    "Google Meet.exe": "Google Meet",
    "Google Meet": "Google Meet",

    # Jitsi Meet - All platforms
    "Jitsi Meet.exe": "Jitsi Meet",
    "Jitsi Meet": "Jitsi Meet",
    "jitsi-meet": "Jitsi Meet",

    # FaceTime - macOS only
    "FaceTime": "FaceTime",

    # Signal - All platforms
    "Signal.exe": "Signal",
    "Signal": "Signal",
    "signal-desktop": "Signal",

    # Element (Matrix) - Linux
    "element-desktop": "Element",
    "Element": "Element",

    # Whereby
    "Whereby.exe": "Whereby",
    "Whereby": "Whereby",

    # Loom
    "Loom.exe": "Loom",
    "Loom": "Loom",
}


class ProcessMonitor(threading.Thread):
    """Monitors for Teams/Zoom process launches and notifies via callback."""

    def __init__(self, on_meeting_detected: Callable[[str], None],
                 on_meeting_ended: Callable[[], None],
                 on_multiple_detected: Callable[[List[str]], None] = None):
        super().__init__(daemon=True)
        self.on_meeting_detected = on_meeting_detected
        self.on_meeting_ended = on_meeting_ended
        self.on_multiple_detected = on_multiple_detected
        self._running = False
        self._active_meeting_process: Optional[str] = None
        self._detected_apps: Set[str] = set()

    def _find_all_meeting_processes(self) -> List[str]:
        """Find all running meeting processes and return unique app names."""
        found_apps = set()
        for proc in psutil.process_iter(['name']):
            try:
                proc_name = proc.info['name']
                if proc_name and proc_name in MONITORED_PROCESSES:
                    # Get friendly app name
                    app_name = PROCESS_TO_APP.get(proc_name, proc_name)
                    found_apps.add(app_name)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return list(found_apps)

    def _find_meeting_process(self) -> Optional[str]:
        """Check if any monitored process is running (returns first found)."""
        for proc in psutil.process_iter(['name']):
            try:
                proc_name = proc.info['name']
                if proc_name and proc_name in MONITORED_PROCESSES:
                    return proc_name
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return None

    def run(self):
        """Main monitoring loop."""
        self._running = True
        self._waiting_for_selection = False

        while self._running:
            # Find all running meeting apps
            running_apps = self._find_all_meeting_processes()

            if running_apps and not self._active_meeting_process and not self._waiting_for_selection:
                # Meeting app(s) detected
                self._detected_apps = set(running_apps)

                if len(running_apps) == 1:
                    # Only one app - use it directly
                    self._active_meeting_process = running_apps[0]
                    self.on_meeting_detected(running_apps[0])
                elif self.on_multiple_detected:
                    # Multiple apps - let user choose (only trigger once)
                    self._waiting_for_selection = True
                    self.on_multiple_detected(running_apps)
                else:
                    # No preference - just notify with all apps listed
                    apps_str = " & ".join(sorted(running_apps))
                    self._active_meeting_process = apps_str
                    self.on_meeting_detected(apps_str)

            elif not running_apps and self._active_meeting_process:
                # All meeting apps closed
                self._active_meeting_process = None
                self._detected_apps = set()
                self._waiting_for_selection = False
                self.on_meeting_ended()

            time.sleep(PROCESS_CHECK_INTERVAL)

    def stop(self):
        """Stop the monitoring loop."""
        self._running = False

    def set_active_process(self, app_name: str):
        """Manually set the active meeting process (used when user selects from multiple)."""
        self._active_meeting_process = app_name
        self._waiting_for_selection = False

    def get_running_apps(self) -> List[str]:
        """Get list of all currently running meeting apps."""
        return self._find_all_meeting_processes()

    def is_meeting_active(self) -> bool:
        """Check if a meeting process is currently active."""
        return self._active_meeting_process is not None

    def get_active_process(self) -> Optional[str]:
        """Get the name of the currently active meeting process."""
        return self._active_meeting_process
