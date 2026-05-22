#!/usr/bin/env python3
"""Step 06 — Burn captions into an mp4 (X-layer).

Contract:
    in:  clip mp4 + srt (or transcript JSON to derive a clip-relative srt)
    out: writes captioned mp4 at --out; prints out path to stdout.

If --transcript is given instead of --srt, this script slices the segments
overlapping [clip_start, clip_end] out of the full-video transcript and
writes a clip-relative .srt before invoking ffmpeg.

Decoupled: no imports from other steps. ffmpeg via FFMPEG_BIN env or PATH.

Usage (srt mode):
    python 06_caption.py clip.mp4 --srt clip.srt --out clip_captioned.mp4

Usage (slice from transcript):
    python 06_caption.py clip.mp4 --transcript source.transcript.json \
        --clip-start 124.3 --clip-end 187.6 --out clip_captioned.mp4
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


def _fmt_srt_ts(seconds: float) -> str:
    ms = max(0, int(round(seconds * 1000)))
    h, ms = ms // 3_600_000, ms % 3_600_000
    m, ms = ms // 60_000, ms % 60_000
    s, ms = ms // 1000, ms % 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _slice_srt(transcript_path: Path, clip_start: float, clip_end: float, out_srt: Path) -> None:
    """Write a clip-relative srt from full-video transcript segments."""
    t = json.loads(transcript_path.read_text())
    segments = t.get("segments", [])
    sliced = []
    for s in segments:
        ss, se = float(s["start"]), float(s["end"])
        if se <= clip_start or ss >= clip_end:
            continue
        sliced.append({
            "start": max(0.0, ss - clip_start),
            "end":   min(clip_end - clip_start, se - clip_start),
            "text":  s["text"],
        })
    lines = []
    for i, s in enumerate(sliced, 1):
        lines.append(str(i))
        lines.append(f"{_fmt_srt_ts(s['start'])} --> {_fmt_srt_ts(s['end'])}")
        lines.append(s["text"].replace("\r", "").replace("\n", " "))
        lines.append("")
    out_srt.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Step 06 — caption burn-in")
    ap.add_argument("clip",        help="input clip mp4")
    ap.add_argument("--out",       required=True, help="output mp4 path")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--srt",        help="srt file (already aligned to clip)")
    src.add_argument("--transcript", help="full-video transcript JSON; pair with --clip-start/--clip-end")
    ap.add_argument("--clip-start", type=float, help="(transcript mode) clip start seconds in source")
    ap.add_argument("--clip-end",   type=float, help="(transcript mode) clip end seconds in source")
    ap.add_argument(
        "--style",
        default="Fontname=Helvetica,Fontsize=22,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,BorderStyle=1,Alignment=2,MarginV=40",
        help="libass force_style — see http://www.tcax.org/docs/ass-specs.htm",
    )
    args = ap.parse_args()

    clip = Path(args.clip).expanduser().resolve()
    out  = Path(args.out).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    if args.transcript:
        if args.clip_start is None or args.clip_end is None:
            print("ERROR: --clip-start and --clip-end required with --transcript", file=sys.stderr)
            return 2
        srt_path = out.with_suffix(".derived.srt")
        _slice_srt(Path(args.transcript).expanduser().resolve(), args.clip_start, args.clip_end, srt_path)
    else:
        srt_path = Path(args.srt).expanduser().resolve()
        if not srt_path.exists():
            print(f"ERROR: srt not found: {srt_path}", file=sys.stderr)
            return 2

    vf = f"subtitles={srt_path}:force_style='{args.style}'"
    cmd = [
        _ffmpeg_bin(), "-y", "-loglevel", "error",
        "-i", str(clip),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "copy",
        str(out),
    ]
    print(f"[caption] burning {srt_path.name} into {clip.name}", file=sys.stderr)
    subprocess.run(cmd, check=True)
    print(str(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
