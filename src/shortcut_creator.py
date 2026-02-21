"""Desktop shortcut creator for ReadIn AI."""

import os
import sys
from pathlib import Path

IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")


def get_executable_path() -> Path:
    """Get the path to the current executable."""
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller bundle
        return Path(sys.executable)
    else:
        # Running as script
        return Path(__file__).parent.parent / "main.py"


def get_icon_path() -> Path:
    """Get the path to the application icon."""
    if getattr(sys, 'frozen', False):
        base_path = Path(sys._MEIPASS) if hasattr(sys, '_MEIPASS') else Path(sys.executable).parent
    else:
        base_path = Path(__file__).parent.parent

    if IS_WINDOWS:
        return base_path / "assets" / "icon.ico"
    else:
        return base_path / "assets" / "icon.png"


def create_desktop_shortcut() -> tuple[bool, str]:
    """Create a desktop shortcut for ReadIn AI.

    Returns:
        Tuple of (success, message)
    """
    if IS_WINDOWS:
        return _create_windows_shortcut()
    elif IS_MACOS:
        return _create_macos_shortcut()
    elif IS_LINUX:
        return _create_linux_shortcut()
    else:
        return False, "Unsupported platform"


def _create_windows_shortcut() -> tuple[bool, str]:
    """Create Windows desktop shortcut using PowerShell."""
    try:
        import subprocess

        desktop = Path(os.environ.get('USERPROFILE', '')) / 'Desktop'
        if not desktop.exists():
            desktop = Path.home() / 'Desktop'

        shortcut_path = desktop / "ReadIn AI.lnk"
        exe_path = get_executable_path()
        icon_path = get_icon_path()

        # Use PowerShell to create shortcut
        ps_script = f'''
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
$Shortcut.TargetPath = "{exe_path}"
$Shortcut.WorkingDirectory = "{exe_path.parent}"
$Shortcut.IconLocation = "{icon_path}"
$Shortcut.Description = "ReadIn AI - Real-time AI Meeting Assistant"
$Shortcut.Save()
'''

        result = subprocess.run(
            ['powershell', '-ExecutionPolicy', 'Bypass', '-Command', ps_script],
            capture_output=True,
            timeout=10
        )

        if result.returncode == 0 and shortcut_path.exists():
            return True, f"Desktop shortcut created at {shortcut_path}"
        else:
            error = result.stderr.decode() if result.stderr else "Unknown error"
            return False, f"Failed to create shortcut: {error}"

    except Exception as e:
        return False, f"Failed to create shortcut: {e}"


def _create_macos_shortcut() -> tuple[bool, str]:
    """Create macOS alias/symlink on Desktop."""
    try:
        desktop = Path.home() / "Desktop"
        exe_path = get_executable_path()

        # For .app bundles, link to the .app
        if exe_path.suffix == '.app' or '.app' in str(exe_path):
            app_path = exe_path
            # Find the .app bundle
            for parent in exe_path.parents:
                if parent.suffix == '.app':
                    app_path = parent
                    break
            link_path = desktop / "ReadIn AI.app"
        else:
            app_path = exe_path
            link_path = desktop / "ReadIn AI"

        # Remove existing link
        if link_path.exists() or link_path.is_symlink():
            link_path.unlink()

        # Create symlink
        link_path.symlink_to(app_path)

        return True, f"Desktop shortcut created at {link_path}"

    except Exception as e:
        return False, f"Failed to create shortcut: {e}"


def _create_linux_shortcut() -> tuple[bool, str]:
    """Create Linux .desktop file."""
    try:
        desktop = Path.home() / "Desktop"
        desktop.mkdir(exist_ok=True)

        exe_path = get_executable_path()
        icon_path = get_icon_path()

        desktop_entry = f"""[Desktop Entry]
Type=Application
Name=ReadIn AI
Comment=Real-time AI Meeting Assistant
Exec={exe_path}
Icon={icon_path}
Terminal=false
Categories=Utility;Office;
StartupNotify=true
"""

        desktop_file = desktop / "readin-ai.desktop"
        desktop_file.write_text(desktop_entry)

        # Make executable
        desktop_file.chmod(0o755)

        # Also add to applications menu
        applications_dir = Path.home() / ".local" / "share" / "applications"
        applications_dir.mkdir(parents=True, exist_ok=True)
        (applications_dir / "readin-ai.desktop").write_text(desktop_entry)

        return True, f"Desktop shortcut created at {desktop_file}"

    except Exception as e:
        return False, f"Failed to create shortcut: {e}"


def shortcut_exists() -> bool:
    """Check if desktop shortcut already exists."""
    desktop = Path.home() / "Desktop"

    if IS_WINDOWS:
        return (desktop / "ReadIn AI.lnk").exists()
    elif IS_MACOS:
        return (desktop / "ReadIn AI.app").exists() or (desktop / "ReadIn AI").exists()
    elif IS_LINUX:
        return (desktop / "readin-ai.desktop").exists()

    return False
