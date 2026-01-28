# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for ReadIn AI (Cross-platform)."""

import sys
from pathlib import Path

block_cipher = None

# Get the project root
PROJECT_ROOT = Path(SPECPATH)

# Platform detection
IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")

# Data files to include
datas = [
    ('assets', 'assets'),
    ('config.py', '.'),
]

# Add .env only if it exists
if (PROJECT_ROOT / '.env').exists():
    datas.append(('.env', '.'))

# Hidden imports - platform specific
hidden_imports = [
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'numpy',
    'faster_whisper',
    'anthropic',
    'httpx',
    'psutil',
]

if IS_WINDOWS:
    hidden_imports.extend([
        'pyaudio',
        'ctypes',
        'ctypes.wintypes',
    ])
else:
    hidden_imports.append('sounddevice')

# Icon path
icon_path = None
if IS_WINDOWS and (PROJECT_ROOT / 'assets' / 'icon.ico').exists():
    icon_path = str(PROJECT_ROOT / 'assets' / 'icon.ico')
elif IS_MACOS and (PROJECT_ROOT / 'assets' / 'icon.icns').exists():
    icon_path = str(PROJECT_ROOT / 'assets' / 'icon.icns')
elif (PROJECT_ROOT / 'assets' / 'icon.png').exists():
    icon_path = str(PROJECT_ROOT / 'assets' / 'icon.png')

a = Analysis(
    ['main.py'],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'scipy',
        'pandas',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

if IS_MACOS:
    # macOS: Create .app bundle
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='ReadInAI',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=icon_path,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='ReadInAI',
    )
    app = BUNDLE(
        coll,
        name='ReadInAI.app',
        icon=icon_path,
        bundle_identifier='ai.readin.app',
        info_plist={
            'NSMicrophoneUsageDescription': 'ReadIn AI needs microphone access to transcribe meeting audio.',
            'NSHighResolutionCapable': True,
            'LSUIElement': True,  # Hide from Dock (system tray app)
        },
    )
else:
    # Windows/Linux: Create directory-based distribution
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='ReadInAI',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,  # No console window
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=icon_path,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='ReadInAI',
    )
