"""Process monitor for detecting Teams/Zoom launches."""

import threading
import time
from typing import Callable, Optional

import psutil

from config import MONITORED_PROCESSES, PROCESS_CHECK_INTERVAL


class ProcessMonitor(threading.Thread):
    """Monitors for Teams/Zoom process launches and notifies via callback."""

    def __init__(self, on_meeting_detected: Callable[[str], None],
                 on_meeting_ended: Callable[[], None]):
        super().__init__(daemon=True)
        self.on_meeting_detected = on_meeting_detected
        self.on_meeting_ended = on_meeting_ended
        self._running = False
        self._active_meeting_process: Optional[str] = None

    def _find_meeting_process(self) -> Optional[str]:
        """Check if any monitored process is running."""
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
        while self._running:
            meeting_process = self._find_meeting_process()

            if meeting_process and not self._active_meeting_process:
                # Meeting app just started
                self._active_meeting_process = meeting_process
                self.on_meeting_detected(meeting_process)
            elif not meeting_process and self._active_meeting_process:
                # Meeting app closed
                self._active_meeting_process = None
                self.on_meeting_ended()

            time.sleep(PROCESS_CHECK_INTERVAL)

    def stop(self):
        """Stop the monitoring loop."""
        self._running = False

    def is_meeting_active(self) -> bool:
        """Check if a meeting process is currently active."""
        return self._active_meeting_process is not None

    def get_active_process(self) -> Optional[str]:
        """Get the name of the currently active meeting process."""
        return self._active_meeting_process
