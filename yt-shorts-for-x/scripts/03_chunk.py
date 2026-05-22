#!/usr/bin/env python3
"""Step 03 — Chunk a long transcript into overlapping windows.

Contract:
    in:  transcript json file path (the format produced by 02_transcribe.py)
    out: prints a JSON array of chunk-file paths to stdout.
         each chunk file is a transcript JSON with an extra `_offset` key.
         if duration < threshold, prints [<original_path>] and exits 0.

Decoupled: pure interval math, no LLM, no other-step imports.

Usage:
    python 03_chunk.py <transcript.json> [--chunk-seconds 1200] [--overlap 60] [--threshold 1800]
"""
import argparse
import json
import sys
from pathlib import Path


def chunk_transcript(transcript: dict, chunk_seconds: int, overlap: int) -> list:
    segments = transcript.get("segments", [])
    duration = transcript.get("duration", segments[-1]["end"] if segments else 0)
    chunks = []
    start = 0
    while start < duration:
        end = min(start + chunk_seconds, duration)
        seg_in_chunk = [s for s in segments if s["start"] >= start and s["end"] <= end + overlap]
        if seg_in_chunk:
            chunks.append({
                "duration": end - start,
                "segments": seg_in_chunk,
                "_offset":  start,
            })
        start += chunk_seconds - overlap
    return chunks


def main() -> int:
    ap = argparse.ArgumentParser(description="Step 03 — chunk long transcripts")
    ap.add_argument("transcript",     help="transcript JSON path")
    ap.add_argument("--chunk-seconds", type=int, default=1200, help="window size (default: 1200)")
    ap.add_argument("--overlap",       type=int, default=60,   help="overlap in seconds (default: 60)")
    ap.add_argument("--threshold",     type=int, default=1800, help="skip chunking below this (default: 1800)")
    args = ap.parse_args()

    src = Path(args.transcript).expanduser().resolve()
    if not src.exists():
        print(f"ERROR: transcript not found: {src}", file=sys.stderr)
        return 2

    transcript = json.loads(src.read_text())
    duration = transcript.get("duration", 0)

    if duration < args.threshold:
        print(f"[chunk] duration={duration:.0f}s < threshold={args.threshold}s — no chunking", file=sys.stderr)
        print(json.dumps([str(src)]))
        return 0

    chunks = chunk_transcript(transcript, args.chunk_seconds, args.overlap)
    print(f"[chunk] duration={duration:.0f}s → {len(chunks)} windows", file=sys.stderr)

    paths = []
    for i, c in enumerate(chunks):
        p = src.with_name(f"{src.stem}.chunk_{i:02d}.json")
        p.write_text(json.dumps(c, indent=2))
        paths.append(str(p))

    print(json.dumps(paths))
    return 0


if __name__ == "__main__":
    sys.exit(main())
