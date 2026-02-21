"""Cross-platform virtual audio driver installer."""

import os
import sys
import subprocess
import webbrowser
import tempfile
import urllib.request
from pathlib import Path
from typing import Optional, Tuple, List
from dataclasses import dataclass

# Platform detection
IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")


@dataclass
class InstallResult:
    """Result of driver installation."""
    success: bool
    message: str
    needs_restart: bool = False


class VirtualAudioInstaller:
    """Cross-platform virtual audio driver installer."""

    # VB-Cable download URL
    VBCABLE_URL = "https://download.vb-audio.com/Download_CABLE/VBCABLE_Driver_Pack43.zip"

    # Virtual audio device keywords for detection
    WINDOWS_KEYWORDS = ['cable output', 'stereo mix', 'vb-audio', 'virtual cable', 'voicemeeter']
    MACOS_KEYWORDS = ['blackhole', 'soundflower', 'loopback']
    LINUX_KEYWORDS = ['monitor of', 'pulse', 'pipewire']

    @classmethod
    def get_bundled_installer_path(cls) -> Optional[Path]:
        """Get path to bundled VB-Cable installer (Windows only)."""
        if not IS_WINDOWS:
            return None

        # Check various locations where installer might be bundled
        possible_paths = [
            Path(__file__).parent / "windows" / "VBCABLE_Setup_x64.exe",
            Path(sys.executable).parent / "drivers" / "windows" / "VBCABLE_Setup_x64.exe",
            Path(os.path.dirname(os.path.abspath(__file__))) / "windows" / "VBCABLE_Setup_x64.exe",
        ]

        # If running from PyInstaller bundle
        if getattr(sys, 'frozen', False):
            base_path = Path(sys._MEIPASS) if hasattr(sys, '_MEIPASS') else Path(sys.executable).parent
            possible_paths.insert(0, base_path / "drivers" / "windows" / "VBCABLE_Setup_x64.exe")

        for path in possible_paths:
            if path.exists():
                return path
        return None

    @classmethod
    def is_virtual_audio_installed(cls, devices: List[dict] = None) -> Tuple[bool, Optional[str]]:
        """Check if virtual audio driver is installed.

        Args:
            devices: List of audio devices from AudioCapture.get_available_devices()
                    If None, will attempt to detect system-wide.

        Returns:
            Tuple of (is_installed, device_name)
        """
        if devices:
            keywords = cls._get_platform_keywords()
            for device in devices:
                name_lower = device['name'].lower()
                for keyword in keywords:
                    if keyword in name_lower:
                        return True, device['name']
            return False, None

        # Fallback: system-level detection
        if IS_WINDOWS:
            return cls._check_windows_vbcable()
        elif IS_MACOS:
            return cls._check_macos_blackhole()
        else:
            return cls._check_linux_monitor()

    @classmethod
    def _get_platform_keywords(cls) -> List[str]:
        """Get keywords for detecting virtual audio on current platform."""
        if IS_WINDOWS:
            return cls.WINDOWS_KEYWORDS
        elif IS_MACOS:
            return cls.MACOS_KEYWORDS
        else:
            return cls.LINUX_KEYWORDS

    @classmethod
    def _check_windows_vbcable(cls) -> Tuple[bool, Optional[str]]:
        """Check if VB-Cable is installed on Windows."""
        try:
            import winreg
            # Check registry for VB-Cable
            try:
                key = winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"SOFTWARE\VB-Audio\VB-CABLE"
                )
                winreg.CloseKey(key)
                return True, "CABLE Output (VB-Audio Virtual Cable)"
            except WindowsError:
                pass

            # Check for driver file
            vbcable_paths = [
                Path(os.environ.get('WINDIR', 'C:\\Windows')) / "System32" / "vbcable.sys",
                Path(os.environ.get('WINDIR', 'C:\\Windows')) / "System32" / "drivers" / "vbcable.sys",
            ]
            for path in vbcable_paths:
                if path.exists():
                    return True, "CABLE Output (VB-Audio Virtual Cable)"

        except Exception:
            pass
        return False, None

    @classmethod
    def _check_macos_blackhole(cls) -> Tuple[bool, Optional[str]]:
        """Check if BlackHole is installed on macOS."""
        try:
            result = subprocess.run(
                ['brew', 'list', 'blackhole-2ch'],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                return True, "BlackHole 2ch"
        except Exception:
            pass

        # Check for kext
        blackhole_paths = [
            Path("/Library/Audio/Plug-Ins/HAL/BlackHole2ch.driver"),
            Path("/Library/Audio/Plug-Ins/HAL/BlackHole.driver"),
        ]
        for path in blackhole_paths:
            if path.exists():
                return True, "BlackHole 2ch"
        return False, None

    @classmethod
    def _check_linux_monitor(cls) -> Tuple[bool, Optional[str]]:
        """Check for PulseAudio/PipeWire monitor on Linux."""
        # Linux always has monitor devices if PulseAudio/PipeWire is running
        try:
            result = subprocess.run(
                ['pactl', 'info'],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                return True, "Monitor of Built-in Audio"
        except Exception:
            pass
        return False, None

    @classmethod
    def install(cls, progress_callback=None) -> InstallResult:
        """Install virtual audio driver for current platform.

        Args:
            progress_callback: Optional callback(message: str) for progress updates

        Returns:
            InstallResult with success status and message
        """
        if IS_WINDOWS:
            return cls._install_windows_vbcable(progress_callback)
        elif IS_MACOS:
            return cls._install_macos_blackhole(progress_callback)
        else:
            return cls._configure_linux_pulseaudio(progress_callback)

    @classmethod
    def _install_windows_vbcable(cls, progress_callback=None) -> InstallResult:
        """Install VB-Cable on Windows."""
        import ctypes

        def report(msg):
            if progress_callback:
                progress_callback(msg)

        # Check if already installed
        installed, _ = cls._check_windows_vbcable()
        if installed:
            return InstallResult(True, "VB-Cable is already installed.", needs_restart=False)

        # Check for bundled installer first
        bundled_path = cls.get_bundled_installer_path()

        if bundled_path and bundled_path.exists():
            report("Found bundled VB-Cable installer...")
            installer_path = bundled_path
        else:
            # Download VB-Cable
            report("Downloading VB-Cable driver...")
            try:
                temp_dir = tempfile.mkdtemp()
                zip_path = Path(temp_dir) / "vbcable.zip"

                urllib.request.urlretrieve(cls.VBCABLE_URL, zip_path)

                # Extract zip
                report("Extracting installer...")
                import zipfile
                with zipfile.ZipFile(zip_path, 'r') as zf:
                    zf.extractall(temp_dir)

                # Find installer
                installer_path = None
                for f in Path(temp_dir).rglob("*.exe"):
                    if "setup" in f.name.lower() and "x64" in f.name.lower():
                        installer_path = f
                        break
                    elif "setup" in f.name.lower():
                        installer_path = f

                if not installer_path:
                    return InstallResult(False, "Could not find VB-Cable installer in download.")

            except Exception as e:
                return InstallResult(False, f"Failed to download VB-Cable: {e}")

        # Check admin privileges
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        except Exception:
            is_admin = False

        report("Installing VB-Cable (requires admin)...")

        try:
            if is_admin:
                # Run installer silently
                result = subprocess.run(
                    [str(installer_path)],
                    timeout=60,
                    capture_output=True
                )
                if result.returncode == 0:
                    return InstallResult(
                        True,
                        "VB-Cable installed successfully! Select 'CABLE Output' as your audio device.",
                        needs_restart=True
                    )
                else:
                    return InstallResult(False, f"Installer returned error code: {result.returncode}")
            else:
                # Request elevation
                ctypes.windll.shell32.ShellExecuteW(
                    None,
                    "runas",
                    str(installer_path),
                    "",
                    None,
                    1  # SW_SHOWNORMAL
                )
                return InstallResult(
                    True,
                    "VB-Cable installer launched. Please complete the installation and click 'Refresh' to detect the new device.",
                    needs_restart=True
                )
        except Exception as e:
            return InstallResult(False, f"Failed to run installer: {e}")

    @classmethod
    def _install_macos_blackhole(cls, progress_callback=None) -> InstallResult:
        """Install BlackHole on macOS via Homebrew."""
        def report(msg):
            if progress_callback:
                progress_callback(msg)

        # Check if already installed
        installed, _ = cls._check_macos_blackhole()
        if installed:
            return InstallResult(True, "BlackHole is already installed.", needs_restart=False)

        # Check for Homebrew
        report("Checking for Homebrew...")
        try:
            result = subprocess.run(['brew', '--version'], capture_output=True, timeout=5)
            has_brew = result.returncode == 0
        except Exception:
            has_brew = False

        if has_brew:
            report("Installing BlackHole via Homebrew...")
            try:
                result = subprocess.run(
                    ['brew', 'install', 'blackhole-2ch'],
                    capture_output=True,
                    timeout=120
                )
                if result.returncode == 0:
                    return InstallResult(
                        True,
                        "BlackHole installed! You may need to configure Audio MIDI Setup.",
                        needs_restart=True
                    )
                else:
                    error = result.stderr.decode() if result.stderr else "Unknown error"
                    return InstallResult(False, f"Homebrew install failed: {error}")
            except subprocess.TimeoutExpired:
                return InstallResult(False, "Installation timed out. Please try manually: brew install blackhole-2ch")
            except Exception as e:
                return InstallResult(False, f"Failed to run Homebrew: {e}")
        else:
            # Open download page
            webbrowser.open("https://existential.audio/blackhole/")
            return InstallResult(
                False,
                "Homebrew not found. Opened BlackHole download page. Please install manually.",
                needs_restart=True
            )

    @classmethod
    def _configure_linux_pulseaudio(cls, progress_callback=None) -> InstallResult:
        """Configure PulseAudio monitor on Linux."""
        def report(msg):
            if progress_callback:
                progress_callback(msg)

        report("Checking PulseAudio/PipeWire...")

        # Check if PulseAudio is available
        try:
            result = subprocess.run(['pactl', 'info'], capture_output=True, timeout=5)
            if result.returncode == 0:
                return InstallResult(
                    True,
                    "PulseAudio monitor is available. Select 'Monitor of [device]' in the device list.",
                    needs_restart=False
                )
        except Exception:
            pass

        # Check for PipeWire
        try:
            result = subprocess.run(['pw-cli', 'info'], capture_output=True, timeout=5)
            if result.returncode == 0:
                return InstallResult(
                    True,
                    "PipeWire is available. Monitor devices should appear automatically.",
                    needs_restart=False
                )
        except Exception:
            pass

        return InstallResult(
            False,
            "PulseAudio/PipeWire not detected. Install with: sudo apt install pulseaudio",
            needs_restart=False
        )

    @classmethod
    def get_virtual_device_index(cls, devices: List[dict]) -> Optional[int]:
        """Find the index of virtual audio device.

        Args:
            devices: List of audio devices from AudioCapture.get_available_devices()

        Returns:
            Device index or None if not found
        """
        keywords = cls._get_platform_keywords()

        # Priority order for matching
        for keyword in keywords:
            for device in devices:
                if keyword in device['name'].lower():
                    return device['index']

        return None

    @classmethod
    def get_install_button_text(cls) -> str:
        """Get platform-specific install button text."""
        if IS_WINDOWS:
            return "Install VB-Cable"
        elif IS_MACOS:
            return "Install BlackHole"
        else:
            return "Configure Audio"

    @classmethod
    def get_driver_name(cls) -> str:
        """Get platform-specific driver name."""
        if IS_WINDOWS:
            return "VB-Cable"
        elif IS_MACOS:
            return "BlackHole"
        else:
            return "PulseAudio Monitor"
