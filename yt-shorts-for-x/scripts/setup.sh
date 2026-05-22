#!/usr/bin/env bash
# One-time setup for yt-shorts-for-x.
# Creates a .venv in this directory and installs faster-whisper + opencv + yt-dlp.
# Re-runnable — uv is idempotent.

set -euo pipefail
cd "$(dirname "$0")"

echo "==> creating venv with uv (Python 3.11)..."
uv venv --python 3.11 .venv

echo "==> installing requirements..."
uv pip install --python .venv/bin/python -r requirements.txt

echo "==> verifying imports..."
.venv/bin/python -c "
import faster_whisper, cv2, yt_dlp, mediapipe, scenedetect
print(f'  faster-whisper: {faster_whisper.__version__}')
print(f'  opencv:         {cv2.__version__}')
print(f'  yt-dlp:         {yt_dlp.version.__version__}')
print(f'  mediapipe:      {mediapipe.__version__}')
print(f'  scenedetect:    {scenedetect.__version__}')
"

# MediaPipe Tasks API needs model files. Download once.
mkdir -p models
DETECTOR=models/blaze_face_short_range.tflite
LANDMARKER=models/face_landmarker.task
if [ ! -f "$DETECTOR" ]; then
  echo "==> downloading BlazeFace short-range model..."
  curl -sSL -o "$DETECTOR" "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite"
fi
if [ ! -f "$LANDMARKER" ]; then
  echo "==> downloading FaceLandmarker model (for active-speaker detection)..."
  curl -sSL -o "$LANDMARKER" "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
fi
echo "==> models:"
echo "    detector:   $(ls -la $DETECTOR | awk '{print $5, "bytes"}')"
echo "    landmarker: $(ls -la $LANDMARKER | awk '{print $5, "bytes"}')"

FFMPEG_BIN="${FFMPEG_BIN:-/Applications/meetily.app/Contents/MacOS/ffmpeg}"
if [ -x "$FFMPEG_BIN" ]; then
  echo "==> ffmpeg: $FFMPEG_BIN ($($FFMPEG_BIN -version 2>&1 | head -1))"
else
  echo "==> WARNING: ffmpeg not found at $FFMPEG_BIN — set FFMPEG_BIN env var or install."
fi

echo ""
echo "Done. Activate with: source $(pwd)/.venv/bin/activate"
echo "Or invoke scripts directly: $(pwd)/.venv/bin/python 01_download.py <url>"
