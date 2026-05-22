#!/usr/bin/env python3
"""Step 04 — Drop overlapping highlights and keep top N.

Contract:
    in:  highlights JSON file with shape {"highlights": [{...,start_time,end_time,score}]}
         or a bare array.
    out: prints deduped + top-N JSON object {"highlights": [...]} to stdout.

A highlight is dropped if it overlaps > 50% with a higher-scored kept highlight.

Decoupled: pure interval math, no other-step imports.

Usage:
    python 04_dedupe.py <highlights.json> [--top N] [--overlap-frac 0.5]
"""
import argparse
import json
import sys
from pathlib import Path


def dedupe(highlights: list, overlap_frac: float = 0.5) -> list:
    ranked = sorted(highlights, key=lambda x: int(x.get("score", 0)), reverse=True)
    kept = []
    for h in ranked:
        hs, he = float(h["start_time"]), float(h["end_time"])
        hd = he - hs
        if hd <= 0:
            continue
        overlapping = False
        for k in kept:
            ks, ke = float(k["start_time"]), float(k["end_time"])
            overlap = max(0.0, min(he, ke) - max(hs, ks))
            if overlap > overlap_frac * hd:
                overlapping = True
                break
        if not overlapping:
            kept.append(h)
    return kept


def main() -> int:
    ap = argparse.ArgumentParser(description="Step 04 — dedupe + top-N")
    ap.add_argument("highlights",     help="highlights JSON path")
    ap.add_argument("--top",           type=int,   default=None, help="keep top N (default: keep all after dedupe)")
    ap.add_argument("--overlap-frac",  type=float, default=0.5,  help="overlap threshold (default: 0.5)")
    args = ap.parse_args()

    src = Path(args.highlights).expanduser().resolve()
    if not src.exists():
        print(f"ERROR: highlights not found: {src}", file=sys.stderr)
        return 2

    data = json.loads(src.read_text())
    highlights = data["highlights"] if isinstance(data, dict) and "highlights" in data else data
    if not isinstance(highlights, list):
        print("ERROR: expected list or {highlights: [...]}", file=sys.stderr)
        return 2

    kept = dedupe(highlights, overlap_frac=args.overlap_frac)
    if args.top is not None:
        kept = kept[:args.top]

    print(f"[dedupe] {len(highlights)} → {len(kept)} after dedupe + top-N", file=sys.stderr)
    print(json.dumps({"highlights": kept}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
