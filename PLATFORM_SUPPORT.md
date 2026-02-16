# ReadIn AI - Platform Support Guide

## Desktop Application

### Windows
- **Audio Capture**: Uses PyAudio with WASAPI
- **Loopback**: Stereo Mix, WASAPI Loopback, or VB-Cable
- **Auto-start**: Windows Registry
- **Shortcuts**: .lnk files via PowerShell/pywin32
- **Meeting Detection**: Native process monitoring

### macOS
- **Audio Capture**: Uses sounddevice with CoreAudio
- **Loopback**: Install [BlackHole](https://existential.audio/blackhole/) (free) for system audio capture
- **Auto-start**: LaunchAgent plist in ~/Library/LaunchAgents
- **Shortcuts**: .command scripts on Desktop
- **Meeting Detection**: Native process monitoring

**macOS Setup:**
1. Install BlackHole: `brew install blackhole-2ch`
2. Go to System Preferences > Sound > Input > Select "BlackHole 2ch"
3. Create Multi-Output Device in Audio MIDI Setup to hear audio while capturing

### Linux
- **Audio Capture**: Uses sounddevice with PulseAudio/PipeWire
- **Loopback**: PulseAudio Monitor of output device
- **Auto-start**: XDG autostart .desktop file in ~/.config/autostart
- **Shortcuts**: .desktop files on Desktop
- **Meeting Detection**: Native process monitoring

**Linux Setup:**
1. Install dependencies: `sudo apt install python3-pyaudio portaudio19-dev`
2. For PulseAudio loopback: `pactl load-module module-loopback`
3. Or select "Monitor of [output device]" as input

---

## Browser Extensions

### Chrome / Chromium-based (Brave, Opera, Vivaldi)
**Location**: `extension/`
- Full tabCapture API support
- Offscreen document for audio processing
- Best experience, recommended

### Microsoft Edge
**Location**: `extension-edge/`
- Identical to Chrome (Chromium-based)
- Load from edge://extensions

### Firefox
**Location**: `extension-firefox/`
- Uses getDisplayMedia API (requires user to share tab)
- User must check "Share audio" when selecting tab
- Manifest V2 format

### Safari
**Status**: Not currently supported

**Why:**
1. Safari extensions require Xcode and macOS to build
2. Requires Apple Developer Program membership ($99/year)
3. Must be distributed through Mac App Store or signed
4. Safari Web Extensions use different packaging (.appex bundles)
5. Safari doesn't support the tabCapture API

**Alternative for Safari users:**
- Use the desktop app with BlackHole for system audio capture
- The desktop app works excellently on macOS and captures all system audio
- This actually provides a better experience than a browser extension

**Future Safari Support:**
If there's demand, we can create a Safari extension. Requirements:
1. macOS development machine with Xcode
2. Apple Developer Program membership
3. App Store submission and review process

---

## Installation Requirements

### All Platforms
```
Python 3.10+
PyQt6
anthropic
faster-whisper
numpy
httpx
websockets
```

### Windows
```
pip install pyaudio
```

### macOS
```
brew install portaudio
pip install sounddevice
# For system audio:
brew install blackhole-2ch
```

### Linux
```
sudo apt install python3-pyaudio portaudio19-dev pulseaudio
pip install sounddevice
```

---

## Browser Extension Installation

### Chrome/Edge
1. Go to `chrome://extensions` or `edge://extensions`
2. Enable "Developer mode"
3. Click "Load unpacked"
4. Select the `extension/` or `extension-edge/` folder

### Firefox
1. Go to `about:debugging#/runtime/this-firefox`
2. Click "Load Temporary Add-on"
3. Select `extension-firefox/manifest.json`

---

## Recommended Setup by Platform

### Windows Users
1. Install desktop app
2. Enable Stereo Mix or install VB-Cable
3. Optionally install Chrome extension for easier meeting capture

### macOS Users
1. Install desktop app
2. Install BlackHole for system audio
3. Desktop app is recommended over browser extension

### Linux Users
1. Install desktop app
2. Configure PulseAudio monitor
3. Chrome extension available as alternative

---

## Troubleshooting

### No audio being captured
- **Windows**: Enable Stereo Mix in Sound Settings, or install VB-Cable
- **macOS**: Install BlackHole and set as audio input
- **Linux**: Select PulseAudio monitor device

### Browser extension not connecting
- Ensure desktop app is running (WebSocket server on port 8765)
- Check that no firewall is blocking localhost connections

### Extension shows "Desktop App Not Running"
- Start the ReadIn AI desktop application first
- The app must be running for the extension to connect
