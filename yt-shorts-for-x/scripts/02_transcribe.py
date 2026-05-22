#!/usr/bin/env python3
"""Step 02 — Transcribe an mp4 to {duration, segments[start,end,text]}.

Contract:
    in:  local mp4 path
    out: writes <mp4_stem>.transcript.json next to the mp4
         writes <mp4_stem>.srt next to the mp4 (for caption burn-in)
         prints transcript json path to stdout

Decoupled: no imports from other steps. Caches by srt mtime.

Usage:
    python 02_transcribe.py <mp4> [--model base] [--language en] [--device auto]
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path


def _fmt_srt_ts(seconds: float) -> str:
    ms = max(0, int(round(seconds * 1000)))
    h, ms = ms // 3_600_000, ms % 3_600_000
    m, ms = ms // 60_000, ms % 60_000
    s, ms = ms // 1000, ms % 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _parse_srt_ts(value: str) -> float:
    m = re.fullmatch(r"(\d{2}):(\d{2}):(\d{2}),(\d{3})", value.strip())
    if not m:
        raise ValueError(f"bad srt ts: {value!r}")
    h, mn, s, ms = map(int, m.groups())
    return h * 3600 + mn * 60 + s + ms / 1000.0


def _load_srt(path: Path) -> dict:
    content = path.read_text(encoding="utf-8-sig").strip()
    segments = []
    for block in re.split(r"\n\s*\n", content):
        lines = [l for l in block.splitlines() if l.strip()]
        if not lines:
            continue
        if "-->" not in lines[0] and len(lines) > 1 and "-->" in lines[1]:
            lines = lines[1:]
        if not lines or "-->" not in lines[0]:
            continue
        a, b = (p.strip() for p in lines[0].split("-->", 1))
        segments.append({
            "start": _parse_srt_ts(a),
            "end":   _parse_srt_ts(b),
            "text":  "\n".join(lines[1:]).strip(),
        })
    return {"duration": segments[-1]["end"] if segments else 0.0, "segments": segments}


def _write_srt(path: Path, segments: list) -> None:
    lines = []
    for i, s in enumerate(segments, 1):
        lines.append(str(i))
        lines.append(f"{_fmt_srt_ts(s['start'])} --> {_fmt_srt_ts(s['end'])}")
        lines.append(s["text"].replace("\r", "").replace("\n", " "))
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _resolve_device(arg: str) -> str:
    if arg != "auto":
        return arg
    try:
        import torch
        return "cuda" if torch.cuda.is_available() else "cpu"
    except ImportError:
        return "cpu"


def main() -> int:
    ap = argparse.ArgumentParser(description="Step 02 — transcribe")
    ap.add_argument("mp4", help="local mp4 path")
    ap.add_argument("--model",    default="base",   help="whisper model (tiny/base/small/medium/large-v3)")
    ap.add_argument("--language", default=None,     help="ISO-639-1 e.g. 'en' (default: auto)")
    ap.add_argument("--device",   default="auto",   help="auto/cpu/cuda")
    args = ap.parse_args()

    mp4 = Path(args.mp4).expanduser().resolve()
    if not mp4.exists():
        print(f"ERROR: mp4 not found: {mp4}", file=sys.stderr)
        return 2

    srt_path  = mp4.with_suffix(".srt")
    json_path = mp4.with_suffix(".transcript.json")

    if srt_path.exists() and srt_path.stat().st_mtime >= mp4.stat().st_mtime and json_path.exists():
        print(f"[transcribe] cached: {srt_path}", file=sys.stderr)
        print(str(json_path))
        return 0

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("ERROR: faster-whisper not installed. Run scripts/setup.sh first.", file=sys.stderr)
        return 2

    device = _resolve_device(args.device)
    compute = "float16" if device == "cuda" else "int8"
    print(f"[transcribe] faster-whisper model={args.model} device={device}", file=sys.stderr)

    model = WhisperModel(args.model, device=device, compute_type=compute)
    seg_iter, info = model.transcribe(
        str(mp4),
        language=args.language,
        beam_size=5,
        vad_filter=True,
        condition_on_previous_text=False,
    )

    segments = [
        {"start": float(s.start), "end": float(s.end), "text": (s.text or "").strip()}
        for s in seg_iter
    ]
    duration = float(getattr(info, "duration", 0.0)) or (segments[-1]["end"] if segments else 0.0)

    transcript = {"duration": duration, "segments": segments}
    json_path.write_text(json.dumps(transcript, indent=2), encoding="utf-8")
    _write_srt(srt_path, segments)

    print(f"[transcribe] {len(segments)} segments, {duration:.0f}s", file=sys.stderr)
    print(str(json_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
