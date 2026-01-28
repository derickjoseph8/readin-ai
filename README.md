# ReadIn AI

Your real-time AI assistant for live conversations. Listens to questions and instantly shows talking points you can glance at and rephrase in your own voice - looking natural, not reading a script.

## Use Cases

- **TV/Media Interviews** - Glance at key points while answering naturally
- **Expert Panels** - Quick facts when put on the spot
- **Research Questionnaires** - Structured talking points
- **Team Meetings** - Contribute thoughtfully
- **Podcasts & Webinars** - Never caught off guard

## How It Works

```
┌─────────────────────────────────────┐
│ THEY ASKED:                         │
│ "What's your view on AI regulation?"│
├─────────────────────────────────────┤
│ YOUR ANSWER:                        │
│ • Balance innovation with safety    │
│ • Industry self-regulation first    │
│ • Government oversight for risks    │
├─────────────────────────────────────┤
│ Glance & rephrase in your own words │
└─────────────────────────────────────┘
```

**You glance → You rephrase → You sound natural**

The AI gives you bullet points, not scripts. You turn them into your own words while speaking.

## Features

- **Talking Points** - Bullet points, not paragraphs
- **Quick Glance** - Scan in 2 seconds
- **Your Voice** - Rephrase naturally
- **A+ Button** - Toggle larger text
- **Resizable** - Drag corner to resize
- **Draggable** - Position anywhere on screen

## Supported Video Conferencing Tools

**Auto-detected (starts listening automatically):**
- Microsoft Teams
- Zoom
- Cisco Webex
- Skype
- Discord
- Slack
- GoToMeeting
- BlueJeans
- RingCentral
- Amazon Chime
- And more...

**Manual start (right-click tray > Start Listening):**
- Google Meet (browser-based)
- Any browser-based meeting
- Phone/conference calls
- In-person interviews with laptop nearby

## Requirements

- Python 3.10+
- Windows, macOS, or Linux
- Anthropic API key

## Installation

```bash
cd readin-ai
pip install -r requirements.txt
```

Or double-click `install.bat`

## Setup

1. Copy `.env.example` to `.env`
2. Add your `ANTHROPIC_API_KEY`

## Usage

```bash
python main.py
```

Or double-click `run.bat`

**Controls:**
- Right-click tray icon to access menu
- **Start Listening** - Click to begin (required for Google Meet/browser meetings)
- **Auto-detection** - Automatically starts when Teams, Zoom, Webex, or other desktop apps launch
- **A+** button toggles large text mode
- Drag the window to reposition
- Drag corner to resize

## Configuration

| Setting | Default | Options |
|---------|---------|---------|
| `WHISPER_MODEL` | `base.en` | `tiny.en` (fast), `base.en` (balanced), `small.en` (accurate) |
| `RESPONSE_MODEL` | `claude-sonnet-4-20250514` | Any Claude model |

## Tips for Looking Natural

1. **Position the overlay** where you can glance without obvious head movement
2. **Don't read verbatim** - the points are prompts, not scripts
3. **Pause naturally** - a brief glance looks like thinking
4. **Add your personality** - AI gives facts, you add style
5. **Use A+ mode** for easier reading from distance

## Privacy

- Whisper runs **locally** - audio never leaves your machine
- Only transcribed text goes to Claude API
- Nothing stored - fully ephemeral

## Troubleshooting

**No audio (Windows)?** Enable "Stereo Mix" in Windows Sound settings, or use a virtual audio cable

**No audio (macOS)?** Install BlackHole or similar virtual audio driver to capture system audio

**No audio (Linux)?** Select PulseAudio monitor device as input

**Model download?** First run downloads ~150MB Whisper model

**API errors?** Check your ANTHROPIC_API_KEY in .env

**Browser meetings not detected?** Google Meet and other browser-based meetings require manual start - right-click the tray icon and select "Start Listening"

## License

MIT
