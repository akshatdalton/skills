#!/usr/bin/env bash
# setup.sh — verify (and where possible install) the decode-x-content media pipeline.
# Idempotent. Prints resolved binary paths and exits 0 only when everything is READY.
#
# The pipeline deliberately avoids Homebrew ffmpeg (broken on this machine — missing
# libx265.215.dylib) and uses imageio-ffmpeg's bundled static ffmpeg instead.
set -uo pipefail
ok=1
echo "decode-x-content :: environment check"

PY="$(command -v python3 || true)"; [ -z "$PY" ] && { echo "  python3: MISSING"; ok=0; } || echo "  python3: $PY ($($PY --version 2>&1))"

# yt-dlp — downloads X native video (needs Chrome cookies for auth; see fetch_media.sh)
if ! command -v yt-dlp >/dev/null 2>&1; then
  echo "  yt-dlp: missing -> installing"; python3 -m pip install -q yt-dlp || ok=0
fi
echo "  yt-dlp: $(command -v yt-dlp || echo MISSING) $(yt-dlp --version 2>/dev/null)"

# imageio-ffmpeg — static ffmpeg 7.x (replacement for broken brew ffmpeg)
if ! python3 -c "import imageio_ffmpeg" 2>/dev/null; then
  echo "  imageio-ffmpeg: missing -> installing"; python3 -m pip install -q imageio-ffmpeg || ok=0
fi
FFMPEG="$(python3 -c 'import imageio_ffmpeg as i; print(i.get_ffmpeg_exe())' 2>/dev/null || echo MISSING)"
echo "  ffmpeg (static): $FFMPEG"

# whisper.cpp (Meetily build, Metal) + large-v3-turbo model — transcription (L2)
WCLI="${WHISPER_CLI:-$HOME/opensource/meetily/backend/whisper.cpp/build/bin/whisper-cli}"
WMODEL="${WHISPER_MODEL:-$HOME/Library/Application Support/meetily-rec/models/ggml-large-v3-turbo.bin}"
[ -x "$WCLI" ]  && echo "  whisper-cli: $WCLI" || { echo "  whisper-cli: MISSING ($WCLI) — build meetily whisper.cpp with cmake -DGGML_METAL=ON"; ok=0; }
[ -f "$WMODEL" ] && echo "  whisper model: $WMODEL" || { echo "  whisper model: MISSING ($WMODEL)"; ok=0; }

# Chrome cookies — yt-dlp reads these so X serves the video (else 'Bad guest token')
CK="$HOME/Library/Application Support/Google/Chrome/Default/Cookies"
[ -f "$CK" ] && echo "  chrome cookies: present" || echo "  chrome cookies: not at default path (pass --cookies-from-browser target if needed)"

[ "$ok" = 1 ] && { echo "READY"; exit 0; } || { echo "NOT READY — fix the MISSING items above"; exit 1; }
