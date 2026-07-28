# ABIX Frontend

## Setup

```bash
npm install
npm start
```

## Tech Stack

- Electron
- React
- react-three-fiber (Three.js)

## Development

The frontend connects to the ABIX agent via WebSocket on port 8765.

States:
- `idle` — slow ambient motion
- `listening` — amber facets react to waveform
- `thinking` — tighter, faster amber pulse
- `speaking` — amber motion synced to TTS amplitude
- `confirming` — shifts to red for Tier-3 prompts
