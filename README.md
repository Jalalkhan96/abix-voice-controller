# ABIX — Voice-Controlled AI Desktop Agent

ABIX is a local-first, voice-controlled AI agent for your desktop. Say "Hi ABIX," then talk: open a file, search for a document, launch an app, run a terminal command, or ask what's going on.

## Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- A working microphone
- Linux (X11 recommended for window management)

### 1. Start Docker services

```bash
cd docker
docker-compose up -d
```

### 2. Install Python dependencies

```bash
pip install -r backend/requirements.txt
pip install -r agent/requirements.txt
```

### 3. Run ABIX

```bash
python -m agent.main
```

### 4. Grant permissions

ABIX needs access to your microphone and (optionally) camera:

```bash
# Check microphone access
arecord -l

# For hand tracking, ensure your user is in the video group
sudo usermod -aG video $USER
```

## Architecture

```
┌─────────────────────────────────────────────┐
│  Host (Native)                              │
│  ┌─────────┐  ┌──────────┐  ┌───────────┐  │
│  │ Wake    │  │ Audio    │  │ Hand      │  │
│  │ Word    │  │ Capture  │  │ Tracking  │  │
│  └────┬────┘  └────┬─────┘  └─────┬─────┘  │
│       │            │              │         │
│  ┌────┴────────────┴──────────────┴──────┐  │
│  │           ABIX Agent (Python)         │  │
│  └────────────────┬──────────────────────┘  │
│                   │ WebSocket/HTTP           │
├───────────────────┼─────────────────────────┤
│  Docker Services  │                         │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐      │
│  │  STT    │ │  TTS    │ │  NLU    │      │
│  │(Whisper)│ │ (Piper) │ │ (Rules) │      │
│  └─────────┘ └─────────┘ └─────────┘      │
└─────────────────────────────────────────────┘
```

## Voice Commands

| Command | Action | Tier |
|---------|--------|------|
| "Hi ABIX" | Wake word activation | — |
| "Open Firefox" | Launch application | 2 |
| "Open my resume" | Open file with default app | 1 |
| "Search for the budget spreadsheet" | Search files | 1 |
| "Write 'meeting at 5pm' to notes.txt" | Write to file | 2 |
| "Close this window" | Close active window | 2 |
| "Delete the file test.txt" | Delete file | 3 (confirm) |
| "Run git status" | Execute CLI command | 3 (confirm) |
| "Play music" / "Pause" | Media control | 2 |
| "Turn on hand tracking" | Enable hand tracking | 2 |
| "What's on my screen?" | Screen info | 1 |

## Permission Tiers

- **Tier 1 (Safe):** Read-only operations — auto-approved
- **Tier 2 (Write):** Modifications — auto-approved, logged
- **Tier 3 (Destructive):** Destructive actions — requires spoken confirmation

## Configuration

Edit `config/settings.yaml` to customize:
- Wake word phrase
- Service URLs
- UI settings
- Hand tracking parameters

Edit `config/whitelist.yaml` to manage:
- Pre-approved commands (skip confirmation)
- Blocked commands (always rejected)

## Hand Tracking (Opt-in)

When enabled, ABIX tracks your hand via webcam and translates it to mouse control:
- **Index finger:** Cursor movement
- **Pinch gesture:** Click
- **Two-finger swipe:** Scroll

Enable with: "Hi ABIX, turn on hand tracking"

## Development

### Run tests
```bash
pytest tests/
```

### Start with logging
```bash
python -m agent.main --log-level debug
```

## Project Structure

```
abix/
├── agent/              # Host-native process (mic, cam, mouse)
├── backend/            # FastAPI server + action modules
├── docker/             # STT, TTS, NLU services
├── frontend/           # Electron + React + Three.js UI
├── config/             # Settings and whitelist
├── tests/              # Unit tests
└── models/             # Downloaded AI models
```

## License

MIT
