#!/usr/bin/env bash
# Setup for The Watcher video-review agent.
# Installs the runtime deps the vendored `watch` skill needs: yt-dlp + ffmpeg.
# Safe to run repeatedly. Runs automatically via the SessionStart hook.
set -uo pipefail

echo "[the-watcher] checking runtime deps..."

# yt-dlp (video download + captions)
if ! python3 -m yt_dlp --version >/dev/null 2>&1; then
  echo "[the-watcher] installing yt-dlp..."
  pip3 install --quiet --user yt-dlp 2>/dev/null || pip3 install --quiet yt-dlp
fi
python3 -m yt_dlp --version >/dev/null 2>&1 \
  && echo "[the-watcher] yt-dlp OK ($(python3 -m yt_dlp --version))" \
  || echo "[the-watcher] WARN: yt-dlp not available"

# ffmpeg (frame extraction)
if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "[the-watcher] installing ffmpeg..."
  if command -v apt-get >/dev/null 2>&1; then
    apt-get update -qq >/dev/null 2>&1
    apt-get install -y --no-install-recommends ffmpeg >/dev/null 2>&1
  elif command -v brew >/dev/null 2>&1; then
    brew install ffmpeg >/dev/null 2>&1
  fi
fi
command -v ffmpeg >/dev/null 2>&1 \
  && echo "[the-watcher] ffmpeg OK" \
  || echo "[the-watcher] WARN: ffmpeg missing — install it manually (apt-get install ffmpeg / brew install ffmpeg)"

# Whisper key reminder (only needed when a video has no captions)
if [ -z "${GROQ_API_KEY:-}" ] && [ -z "${OPENAI_API_KEY:-}" ] && [ ! -f "$HOME/.config/watch/.env" ]; then
  echo "[the-watcher] NOTE: no Whisper key found. Frames + captions still work;"
  echo "               add GROQ_API_KEY or OPENAI_API_KEY to ~/.config/watch/.env to transcribe caption-less videos."
fi

echo "[the-watcher] setup done."
