#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
MODELS_DIR="$ROOT_DIR/models"

mkdir -p "$MODELS_DIR/whisper" "$MODELS_DIR/tts" "$MODELS_DIR/llm"

echo "=== ABIX Model Downloader ==="
echo ""

# --- Whisper (faster-whisper downloads automatically on first use) ---
echo "[1/3] Whisper STT"
echo "  faster-whisper downloads the model on first run."
echo "  To pre-download, run inside the stt-service container:"
echo "    docker compose exec stt-service python -c \"from faster_whisper import WhisperModel; WhisperModel('base')\""
echo ""

# --- Piper TTS voice ---
echo "[2/3] Piper TTS voice"
PIPER_DIR="$MODELS_DIR/tts"
PIPER_VOICE="en_US-lessac-medium"
PIPER_ONNX="$PIPER_DIR/${PIPER_VOICE}.onnx"
PIPER_JSON="$PIPER_DIR/${PIPER_VOICE}.onnx.json"

if [ ! -f "$PIPER_ONNX" ]; then
    echo "  Downloading $PIPER_VOICE..."
    PIPER_BASE="https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium"
    curl -L -o "$PIPER_ONNX" "$PIPER_BASE/${PIPER_VOICE}.onnx" 2>/dev/null
    curl -L -o "$PIPER_JSON" "$PIPER_BASE/${PIPER_VOICE}.onnx.json" 2>/dev/null
    echo "  Done: $PIPER_ONNX"
else
    echo "  Already downloaded: $PIPER_ONNX"
fi
echo ""

# --- Local LLM (Ollama) ---
echo "[3/3] Local LLM via Ollama"
if command -v ollama &>/dev/null; then
    echo "  Pulling mistral model (lightweight, good for intent parsing)..."
    ollama pull mistral 2>/dev/null || echo "  Ollama pull failed — will use rule-based NLU fallback"
    echo "  Done"
else
    echo "  Ollama not installed. Install from https://ollama.ai"
    echo "  The rule-based NLU fast-path handles most commands without a local LLM."
fi

echo ""
echo "=== All models ready ==="
