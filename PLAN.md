# ReadIn AI - Implementation Plan

## Overview
A real-time AI assistant for live conversations. Listens to questions and instantly drafts responses to help you answer confidently - whether in TV interviews, expert panels, research questionnaires, or team meetings.

**Key Focus: Real-time help only** - No transcript storage, no search, just instant AI-drafted responses that you can rephrase in your own voice.

## Use Cases
- TV/media interviews requiring expert input
- Expert panels and Q&A sessions
- Research questionnaires
- Team meetings (Teams/Zoom)
- Podcasts and webinars

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         ReadIn AI                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐  │
│  │   Process    │───▶│   Audio      │───▶│   Whisper        │  │
│  │   Monitor    │    │   Capture    │    │   (Real-time)    │  │
│  │  (psutil)    │    │  (loopback)  │    │   Speech-to-Text │  │
│  └──────────────┘    └──────────────┘    └────────┬─────────┘  │
│         │                                          │            │
│         │ Triggers popup              Question/Statement        │
│         │                                          │            │
│         ▼                                          ▼            │
│  ┌──────────────────────────────────┐  ┌──────────────────┐    │
│  │      Floating Overlay UI         │◀─│   Claude API     │    │
│  │  - Question/statement heard      │  │  (Instant Draft) │    │
│  │  - AI-drafted response           │  └──────────────────┘    │
│  │  - Ready to rephrase & use       │                           │
│  └──────────────────────────────────┘                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Technology Stack

| Component | Technology | Reason |
|-----------|------------|--------|
| Language | Python 3.10+ | Best AI/audio ecosystem |
| UI Framework | PyQt6 | Native floating windows, modern look |
| Audio Capture | sounddevice + WASAPI | Windows system audio loopback |
| Transcription | OpenAI Whisper (faster-whisper) | Fast, accurate, local |
| AI Responses | Claude API (Anthropic) | High-quality drafted responses |
| Process Monitor | psutil | Cross-platform process detection |

## Project Structure

```
readin-ai/
├── main.py                 # Application entry point
├── requirements.txt        # Dependencies
├── config.py              # Configuration (API keys, settings)
├── PLAN.md                # This file
├── README.md              # User documentation
├── src/
│   ├── __init__.py
│   ├── process_monitor.py  # Detects Teams/Zoom launch
│   ├── audio_capture.py    # System audio loopback capture
│   ├── transcriber.py      # Real-time speech-to-text
│   ├── ai_assistant.py     # Claude API for instant responses
│   └── ui/
│       ├── __init__.py
│       └── overlay.py      # Floating overlay (question + response)
└── assets/
    └── icon.png           # App icon
```

## Implementation Steps

### Step 1: Project Setup
- Create project directory structure
- Create requirements.txt with dependencies
- Create config.py for API key management

### Step 2: Process Monitor (`src/process_monitor.py`)
- Monitor for Teams (`Teams.exe`, `ms-teams.exe`) and Zoom (`Zoom.exe`) processes
- Emit signal when meeting app launches
- Run as background thread with minimal CPU usage

### Step 3: Audio Capture (`src/audio_capture.py`)
- Capture system audio using WASAPI loopback (Windows)
- Buffer audio in chunks for real-time processing
- Handle audio device selection

### Step 4: Real-Time Speech-to-Text (`src/transcriber.py`)
- Use `faster-whisper` for optimized local transcription
- Process audio in small chunks (~3 seconds) for speed
- Output text immediately (no storage, ephemeral only)
- Voice activity detection to know when someone finishes speaking

### Step 5: Claude AI Integration (`src/ai_assistant.py`)
- Connect to Claude API (claude-sonnet-4-20250514 for speed)
- When speech segment detected:
  - Send to Claude with prompt: "Someone asked: [text]. Draft a response."
  - Stream response for fastest display
- Keep only recent context (last 2-3 exchanges) in memory
- Discard after session ends (no storage)

### Step 6: Floating Overlay UI (`src/ui/overlay.py`)
- Frameless, always-on-top floating window
- Semi-transparent, dark theme
- Two sections only:
  - **"They asked:"** - Shows what was just heard
  - **"Suggested answer:"** - AI-drafted response (highlighted)
- Draggable
- Close/minimize buttons
- Copy response button for quick use

### Step 7: Main Application (`main.py`)
- Initialize all components
- Wire up signals: audio → transcription → AI → display
- Handle graceful shutdown
- System tray for background running

## Key Features

1. **Auto-Launch Detection**: Overlay appears when Teams/Zoom starts
2. **Manual Mode**: Start listening anytime for interviews/panels
3. **Instant Listening**: Hears questions in real-time
4. **Immediate Responses**: AI drafts answer within seconds
5. **Ephemeral**: Nothing stored - real-time help only
6. **Minimal UI**: Just shows question + suggested answer
7. **Copy & Rephrase**: Use AI suggestion as inspiration

## Dependencies (requirements.txt)

```
anthropic>=0.18.0      # Claude API
faster-whisper>=0.10.0 # Optimized Whisper (local, fast)
sounddevice>=0.4.6     # Audio capture
numpy>=1.24.0          # Audio processing
PyQt6>=6.6.0           # UI framework
psutil>=5.9.0          # Process monitoring
python-dotenv>=1.0.0   # Config management
```

## Configuration

```python
# config.py
ANTHROPIC_API_KEY = "your-key-here"  # Or from .env file
WHISPER_MODEL = "base.en"  # Options: tiny.en (fastest), base.en (balanced), small.en (accurate)
RESPONSE_MODEL = "claude-sonnet-4-20250514"  # Fast responses
```

## Getting Started

1. **Install dependencies:**
   ```bash
   cd readin-ai
   pip install -r requirements.txt
   ```

2. **Set your API key:**
   Create a `.env` file:
   ```
   ANTHROPIC_API_KEY=your-api-key-here
   ```

3. **Run the application:**
   ```bash
   python main.py
   ```

4. **Usage:**
   - The app runs in the system tray
   - Auto-launches overlay when Teams/Zoom starts
   - Or right-click tray icon → "Start Listening" for interviews/panels
   - Double-click tray icon to show overlay

## Notes

- **Privacy**: System audio capture hears all participants. Intended for personal assistance only.
- **API Costs**: Claude API charges per token. Each response costs ~$0.001-0.01 depending on length.
- **Hardware**: Whisper "base.en" model runs well on most machines. Uses ~1GB RAM.
- **Latency Goal**: < 3 seconds from end of question to response displayed.
- **Your Voice**: AI suggestions are starting points - always rephrase in your own style.
