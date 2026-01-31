"""Auto-update checker for ReadIn AI."""

import threading
import webbrowser
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass
from packaging import version

import httpx

from config import APP_VERSION, UPDATE_CHECK_URL, GITHUB_RELEASES_URL


@dataclass
class UpdateInfo:
    """Information about an available update."""
    version: str
    download_url: str
    changelog: str
    is_required: bool = False
    release_date: Optional[str] = None
    size_mb: Optional[float] = None


class UpdateChecker:
    """Checks for application updates."""

    def __init__(
        self,
        current_version: str = APP_VERSION,
        check_url: str = UPDATE_CHECK_URL,
        on_update_available: Optional[Callable[[UpdateInfo], None]] = None,
        on_error: Optional[Callable[[str], None]] = None
    ):
        """Initialize the update checker.

        Args:
            current_version: Current application version
            check_url: URL to check for updates
            on_update_available: Callback when update is found
            on_error: Callback when error occurs
        """
        self.current_version = current_version
        self.check_url = check_url
        self.on_update_available = on_update_available
        self.on_error = on_error

        self._latest_update: Optional[UpdateInfo] = None
        self._checking = False

    def check_for_updates(self, background: bool = True) -> Optional[UpdateInfo]:
        """Check for available updates.

        Args:
            background: If True, check in a background thread

        Returns:
            UpdateInfo if update available (only when background=False)
        """
        if self._checking:
            return None

        if background:
            thread = threading.Thread(target=self._check, daemon=True)
            thread.start()
            return None
        else:
            return self._check()

    def _check(self) -> Optional[UpdateInfo]:
        """Perform the update check."""
        self._checking = True

        try:
            # Try the API endpoint first
            update_info = self._check_api()
            if update_info:
                self._latest_update = update_info
                if self.on_update_available:
                    self.on_update_available(update_info)
                return update_info

            # Fall back to GitHub releases
            update_info = self._check_github()
            if update_info:
                self._latest_update = update_info
                if self.on_update_available:
                    self.on_update_available(update_info)
                return update_info

        except Exception as e:
            if self.on_error:
                self.on_error(str(e))
        finally:
            self._checking = False

        return None

    def _check_api(self) -> Optional[UpdateInfo]:
        """Check for updates via API endpoint."""
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(self.check_url)

                if response.status_code != 200:
                    return None

                data = response.json()

                latest_version = data.get('version', '')
                if not latest_version:
                    return None

                # Compare versions
                if not self._is_newer_version(latest_version):
                    return None

                return UpdateInfo(
                    version=latest_version,
                    download_url=data.get('download_url', GITHUB_RELEASES_URL),
                    changelog=data.get('changelog', ''),
                    is_required=data.get('required', False),
                    release_date=data.get('release_date'),
                    size_mb=data.get('size_mb')
                )

        except Exception:
            return None

    def _check_github(self) -> Optional[UpdateInfo]:
        """Check for updates via GitHub releases API."""
        try:
            # Extract owner/repo from releases URL
            # Expected format: https://github.com/owner/repo/releases
            parts = GITHUB_RELEASES_URL.replace('https://github.com/', '').split('/')
            if len(parts) < 2:
                return None

            owner, repo = parts[0], parts[1]
            api_url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"

            with httpx.Client(timeout=10.0) as client:
                response = client.get(api_url)

                if response.status_code != 200:
                    return None

                data = response.json()

                tag_name = data.get('tag_name', '')
                # Remove 'v' prefix if present
                latest_version = tag_name.lstrip('v')

                if not latest_version:
                    return None

                # Compare versions
                if not self._is_newer_version(latest_version):
                    return None

                # Get download URL for the appropriate asset
                download_url = data.get('html_url', GITHUB_RELEASES_URL)
                assets = data.get('assets', [])

                # Look for platform-specific installer
                import sys
                if sys.platform == 'win32':
                    for asset in assets:
                        if asset['name'].endswith('.exe'):
                            download_url = asset['browser_download_url']
                            break
                elif sys.platform == 'darwin':
                    for asset in assets:
                        if asset['name'].endswith('.dmg'):
                            download_url = asset['browser_download_url']
                            break

                return UpdateInfo(
                    version=latest_version,
                    download_url=download_url,
                    changelog=data.get('body', ''),
                    is_required=False,
                    release_date=data.get('published_at', '')[:10] if data.get('published_at') else None
                )

        except Exception:
            return None

    def _is_newer_version(self, latest: str) -> bool:
        """Check if the latest version is newer than current.

        Args:
            latest: Latest version string

        Returns:
            True if latest is newer than current
        """
        try:
            return version.parse(latest) > version.parse(self.current_version)
        except Exception:
            # Fall back to simple string comparison
            return latest > self.current_version

    def get_latest_update(self) -> Optional[UpdateInfo]:
        """Get the latest update info from the last check."""
        return self._latest_update

    def is_update_available(self) -> bool:
        """Check if an update is available (from last check)."""
        return self._latest_update is not None

    def open_download_page(self):
        """Open the download page in the default browser."""
        if self._latest_update and self._latest_update.download_url:
            webbrowser.open(self._latest_update.download_url)
        else:
            webbrowser.open(GITHUB_RELEASES_URL)

    def get_update_message(self) -> str:
        """Get a formatted update message for display."""
        if not self._latest_update:
            return "No updates available."

        update = self._latest_update
        message = f"ReadIn AI {update.version} is available!\n"
        message += f"You're currently using version {self.current_version}.\n"

        if update.release_date:
            message += f"\nReleased: {update.release_date}"

        if update.changelog:
            # Truncate long changelogs
            changelog = update.changelog
            if len(changelog) > 500:
                changelog = changelog[:500] + "..."
            message += f"\n\nWhat's new:\n{changelog}"

        return message


# Convenience function for quick update check
def check_for_update() -> Optional[UpdateInfo]:
    """Quick synchronous check for updates.

    Returns:
        UpdateInfo if update available, None otherwise
    """
    checker = UpdateChecker()
    return checker.check_for_updates(background=False)
