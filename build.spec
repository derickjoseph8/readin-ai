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

# Include src directory structure
if (PROJECT_ROOT / 'src').exists():
    datas.append(('src', 'src'))

# Hidden imports - all modules that PyInstaller might miss
hidden_imports = [
    # Qt
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.sip',

    # Core
    'numpy',
    'numpy.core._methods',
    'numpy.lib.format',

    # Audio processing (high-quality resampling)
    'scipy',
    'scipy.signal',
    'scipy.signal.signaltools',

    # AI and Transcription
    'faster_whisper',
    'faster_whisper.tokenizer',
    'faster_whisper.audio',
    'faster_whisper.vad',
    'ctranslate2',
    'anthropic',
    'anthropic._streaming',

    # HTTP
    'httpx',
    'httpx._transports',
    'httpx._transports.default',
    'httpcore',
    'h11',
    'certifi',
    'idna',
    'sniffio',
    'anyio',
    'anyio._backends',
    'anyio._backends._asyncio',

    # System
    'psutil',
    'psutil._psutil_common',

    # Keyboard/Input
    'pynput',
    'pynput.keyboard',
    'pynput.mouse',

    # Environment
    'dotenv',
    'python-dotenv',

    # Websockets (for browser extension bridge)
    'websockets',
    'websockets.server',
    'websockets.client',

    # JSON/Data
    'json',
    'datetime',
    'collections',
    'queue',
    'threading',

    # Encoding
    'encodings',
    'encodings.utf_8',
    'encodings.ascii',
    'encodings.latin_1',
]

if IS_WINDOWS:
    hidden_imports.extend([
        'pyaudio',
        'ctypes',
        'ctypes.wintypes',
        'win32api',
        'win32con',
        'win32gui',
        'pywintypes',
        'psutil._pswindows',
        'pynput.keyboard._win32',
        'pynput.mouse._win32',
    ])
elif IS_MACOS:
    hidden_imports.extend([
        'sounddevice',
        'psutil._psosx',
        'pynput.keyboard._darwin',
        'pynput.mouse._darwin',
        'AppKit',
        'Foundation',
        'objc',
    ])
else:  # Linux
    hidden_imports.extend([
        'sounddevice',
        'psutil._pslinux',
        'pynput.keyboard._xorg',
        'pynput.mouse._xorg',
        'Xlib',
    ])

# Icon path
icon_path = None
if IS_WINDOWS and (PROJECT_ROOT / 'assets' / 'icon.ico').exists():
    icon_path = str(PROJECT_ROOT / 'assets' / 'icon.ico')
elif IS_MACOS and (PROJECT_ROOT / 'assets' / 'icon.icns').exists():
    icon_path = str(PROJECT_ROOT / 'assets' / 'icon.icns')
elif (PROJECT_ROOT / 'assets' / 'icon.png').exists():
    icon_path = str(PROJECT_ROOT / 'assets' / 'icon.png')

# Collect data files from packages that need them
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

# Collect faster_whisper data (tokenizers, etc.)
try:
    datas += collect_data_files('faster_whisper')
except Exception:
    pass

# Collect ctranslate2 libraries
try:
    datas += collect_data_files('ctranslate2')
    binaries = collect_dynamic_libs('ctranslate2')
except Exception:
    binaries = []

# Collect anthropic data
try:
    datas += collect_data_files('anthropic')
except Exception:
    pass

# Collect certifi certificates
try:
    datas += collect_data_files('certifi')
except Exception:
    pass

a = Analysis(
    ['main.py'],
    pathex=[str(PROJECT_ROOT), str(PROJECT_ROOT / 'src')],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary modules to reduce size
        'tkinter',
        'matplotlib',
        # 'scipy', - KEEP scipy for high-quality audio resampling
        'pandas',
        'PIL.ImageTk',
        'IPython',
        'jupyter',
        'notebook',
        'test',
        'tests',
        'unittest',
        'pytest',
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
    # Windows/Linux: Create single-file portable executable
    # Note: This is a PORTABLE app, NOT an installer. Run directly, no installation needed.
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name='ReadInAI-Portable',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        console=False,  # No console window
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=icon_path,
    )
