"""Process monitor for detecting Teams/Zoom launches."""

import threading
import time
from typing import Callable, Optional, List, Set

import psutil

from config import MONITORED_PROCESSES, PROCESS_CHECK_INTERVAL

# Map process names to friendly app names
PROCESS_TO_APP = {
    # Microsoft Teams
    "Teams.exe": "Microsoft Teams",
    "ms-teams.exe": "Microsoft Teams",
    "msteams.exe": "Microsoft Teams",
    "Microsoft Teams": "Microsoft Teams",
    "teams": "Microsoft Teams",
    # Zoom
    "Zoom.exe": "Zoom",
    "zoom.exe": "Zoom",
    "zoom.us": "Zoom",
    "zoom": "Zoom",
    "ZoomLauncher": "Zoom",
    # Webex
    "webex.exe": "Cisco Webex",
    "CiscoWebexStart.exe": "Cisco Webex",
    "Cisco Webex Meetings": "Cisco Webex",
    "webex": "Cisco Webex",
    # Google Meet (browser-based, detected by window title)
    "meet.google.com": "Google Meet",
    # Slack
    "slack.exe": "Slack",
    "Slack": "Slack",
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
