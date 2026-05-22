#!/usr/bin/env python3
"""Step 07 — Extract preview frames from a clip for Claude vision review.

Contract:
    in:  clip mp4 + comma-separated timestamps (seconds)
    out: writes <out_dir>/<clip_stem>_t<sec>.jpg per timestamp
         prints JSON array of frame paths to stdout

Decoupled: no imports from other steps. ffmpeg via FFMPEG_BIN env or PATH.

Usage:
    python 07_extract_frames.py clip.mp4 --times 0,5,15 --out-dir review/
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def _ffmpeg_bin() -> str:
    candidate = os.environ.get("FFMPEG_BIN", "/Applications/meetily.app/Contents/MacOS/ffmpeg")
    if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
        return candidate
    return "ffmpeg"


def main() -> int:
    ap = argparse.ArgumentParser(description="Step 07 — extract preview frames")
    ap.add_argument("clip",      help="clip mp4 path")
    ap.add_argument("--times",   default="0,5,15", help="comma-separated seconds (default: 0,5,15)")
    ap.add_argument("--out-dir", default=None,     help="output directory (default: same dir as clip)")
    args = ap.parse_args()

    clip = Path(args.clip).expanduser().resolve()
    if not clip.exists():
        print(f"ERROR: clip not found: {clip}", file=sys.stderr)
        return 2

    out_dir = Path(args.out_dir).expanduser().resolve() if args.out_dir else clip.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    times = [float(t.strip()) for t in args.times.split(",") if t.strip()]
    paths = []
    for t in times:
        out_path = out_dir / f"{clip.stem}_t{t:g}.jpg"
        cmd = [
            _ffmpeg_bin(), "-y", "-loglevel", "error",
            "-ss", f"{t:.3f}",
            "-i", str(clip),
            "-frames:v", "1",
            "-q:v", "3",
            str(out_path),
        ]
        try:
            subprocess.run(cmd, check=True)
            paths.append(str(out_path))
        except subprocess.CalledProcessError as e:
            print(f"WARN: frame at t={t} failed: {e}", file=sys.stderr)

    print(f"[frames] {len(paths)}/{len(times)} extracted", file=sys.stderr)
    print(json.dumps(paths))
    return 0


if __name__ == "__main__":
    sys.exit(main())
