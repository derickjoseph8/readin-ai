#!/usr/bin/env python3
"""
Cross-platform test script for ReadIn AI.
Run this on macOS or Linux to verify the application works.
"""

import sys
import os

def main():
    print("=" * 60)
    print("ReadIn AI - Platform Compatibility Test")
    print("=" * 60)
    print(f"\nPlatform: {sys.platform}")
    print(f"Python: {sys.version}")
    print()

    errors = []

    # Test 1: Config
    print("[1/8] Testing config...")
    try:
        from config import IS_WINDOWS, IS_MACOS, IS_LINUX, MONITORED_PROCESSES
        platform_name = "Windows" if IS_WINDOWS else "macOS" if IS_MACOS else "Linux"
        print(f"      Detected platform: {platform_name}")
        print(f"      Monitored processes: {len(MONITORED_PROCESSES)}")
    except Exception as e:
        errors.append(f"Config: {e}")
        print(f"      FAILED: {e}")

    # Test 2: Audio capture module
    print("[2/8] Testing audio capture...")
    try:
        from src.audio_capture import AudioCapture
        devices = AudioCapture.get_available_devices()
        print(f"      Found {len(devices)} audio devices")

        loopback_devices = [d for d in devices if d['is_loopback']]
        if loopback_devices:
            print(f"      Loopback devices: {[d['name'] for d in loopback_devices]}")
        else:
            print("      WARNING: No loopback device found")
            if IS_MACOS:
                print("      Tip: Install BlackHole (brew install blackhole-2ch)")
            elif IS_LINUX:
                print("      Tip: Select PulseAudio monitor device")
    except ImportError as e:
        if 'sounddevice' in str(e):
            errors.append("sounddevice not installed. Run: pip install sounddevice")
            print(f"      FAILED: sounddevice not installed")
            print(f"      Fix: pip install sounddevice")
        else:
            errors.append(f"Audio: {e}")
            print(f"      FAILED: {e}")
    except Exception as e:
        errors.append(f"Audio: {e}")
        print(f"      FAILED: {e}")

    # Test 3: Transcriber
    print("[3/8] Testing transcriber...")
    try:
        from src.transcriber import Transcriber
        print("      Transcriber module OK")
    except ImportError as e:
        if 'faster_whisper' in str(e):
            errors.append("faster-whisper not installed")
            print(f"      FAILED: faster-whisper not installed")
            print(f"      Fix: pip install faster-whisper")
        else:
            errors.append(f"Transcriber: {e}")
            print(f"      FAILED: {e}")
    except Exception as e:
        errors.append(f"Transcriber: {e}")
        print(f"      FAILED: {e}")

    # Test 4: Process monitor
    print("[4/8] Testing process monitor...")
    try:
        from src.process_monitor import ProcessMonitor
        import psutil

        # Quick test - list running processes
        running_count = len(list(psutil.process_iter(['name'])))
        print(f"      Process monitor OK ({running_count} processes running)")
    except Exception as e:
        errors.append(f"Process monitor: {e}")
        print(f"      FAILED: {e}")

    # Test 5: Browser bridge
    print("[5/8] Testing browser bridge...")
    try:
        from src.browser_bridge import BrowserBridge, WEBSOCKETS_AVAILABLE
        if WEBSOCKETS_AVAILABLE:
            bridge = BrowserBridge()
            print("      Browser bridge OK")
        else:
            print("      WARNING: websockets not installed")
            print("      Fix: pip install websockets")
    except Exception as e:
        errors.append(f"Browser bridge: {e}")
        print(f"      FAILED: {e}")

    # Test 6: Hotkey manager
    print("[6/8] Testing hotkey manager...")
    try:
        from src.hotkey_manager import HotkeyManager
        hm = HotkeyManager()

        # Test macOS-specific shortcut
        if IS_MACOS:
            formatted = hm.format_shortcut('cmd+shift+r', display=True)
            print(f"      macOS shortcut display: {formatted}")
        else:
            formatted = hm.format_shortcut('ctrl+shift+r', display=True)
            print(f"      Shortcut display: {formatted}")
    except Exception as e:
        errors.append(f"Hotkey manager: {e}")
        print(f"      FAILED: {e}")

    # Test 7: PyQt6 UI
    print("[7/8] Testing PyQt6...")
    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import QCoreApplication

        # Don't create app if one exists
        app = QCoreApplication.instance()
        if app is None:
            app = QApplication([])
        print("      PyQt6 OK")
    except Exception as e:
        errors.append(f"PyQt6: {e}")
        print(f"      FAILED: {e}")

    # Test 8: First run wizard (shortcut creation)
    print("[8/8] Testing first run wizard...")
    try:
        from src.ui.first_run_wizard import FirstRunWizard
        from pathlib import Path

        desktop = Path.home() / "Desktop"
        print(f"      Desktop path: {desktop}")
        print(f"      Desktop exists: {desktop.exists()}")

        if IS_MACOS:
            launch_agents = Path.home() / "Library" / "LaunchAgents"
            print(f"      LaunchAgents dir: {launch_agents.exists()}")
        elif IS_LINUX:
            autostart = Path.home() / ".config" / "autostart"
            print(f"      Autostart dir exists: {autostart.exists()}")
    except Exception as e:
        errors.append(f"First run wizard: {e}")
        print(f"      FAILED: {e}")

    # Summary
    print("\n" + "=" * 60)
    if errors:
        print(f"FAILED - {len(errors)} error(s):")
        for err in errors:
            print(f"  - {err}")
        print("\nFix the errors above and run this test again.")
        return 1
    else:
        print("ALL TESTS PASSED!")
        print("\nThe application is ready to run on this platform.")
        print("\nTo start the app:")
        print("  python main.py")
        return 0


if __name__ == "__main__":
    sys.exit(main())
