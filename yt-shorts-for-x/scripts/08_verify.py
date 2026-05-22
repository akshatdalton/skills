#!/usr/bin/env python3
"""Step 08 — Automated jitter scan + strategic frame extraction for Claude's vision gate.

This is the AUTOMATED layer of the verify step. It does NOT make the final
pass/reject call — that's Claude's job, after looking at the frames this
script extracts. Claude writes <clip>.verify_result.json with status PASS or
REJECT, and 09_upload.py refuses to upload anything without status=PASS.

What this script does per captioned clip:
  1. Read scene boundaries from <pre_caption_clip>.scenes.json (sidecar
     emitted by 05_clip.py). Used to know where natural motion is expected.
  2. Compute optical flow magnitude per 0.5s window across the whole clip.
  3. Flag windows whose mean flow exceeds a threshold AND are not near a
     known scene cut (cuts have legitimate high flow).
  4. Extract strategic review frames:
       * t = 0.5s  (opening)
       * t = duration / 2  (mid)
       * t = duration - 0.5s  (closing)
       * t = cut ± 0.3s  (each scene boundary)
       * t = window_mid  (each flagged window)
  5. Write a verify-summary JSON describing scores + flagged windows +
     frame paths. Claude reads this + the frames to decide PASS / REJECT.

Decoupled: no imports from other steps. ffmpeg via FFMPEG_BIN env or PATH.

Usage:
    python 08_verify.py <captioned_clip.mp4> \\
        [--scenes-from <pre_caption_clip>.scenes.json] \\
        [--flow-threshold 8.0] \\
        [--window 0.5]
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Optional


def _ffmpeg_bin() -> str:
    candidate = os.environ.get("FFMPEG_BIN", "/Applications/meetily.app/Contents/MacOS/ffmpeg")
    if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
        return candidate
    return "ffmpeg"


def _video_meta(path: str) -> dict:
    import cv2
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise RuntimeError(f"could not open {path}")
    meta = {
        "fps":          cap.get(cv2.CAP_PROP_FPS) or 30.0,
        "frame_count":  int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        "width":        int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height":       int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
    }
    meta["duration_s"] = meta["frame_count"] / meta["fps"] if meta["fps"] else 0.0
    cap.release()
    return meta


def _flow_per_window(video_path: str, window_s: float) -> List[dict]:
    """Farneback optical flow on downsampled frames, averaged per window.

    Returns list of {start_s, end_s, flow_mean, flow_max}.
    """
    import cv2
    import numpy as np

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frames_per_window = max(1, int(round(window_s * fps)))

    prev_gray = None
    current = []
    windows = []
    fi = 0
    win_start_fi = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            # Downsample (half each dim) for speed
            h, w = frame.shape[:2]
            small = cv2.resize(frame, (w // 2, h // 2))
            gray  = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            if prev_gray is not None:
                flow = cv2.calcOpticalFlowFarneback(
                    prev_gray, gray, None,
                    pyr_scale=0.5, levels=3, winsize=15,
                    iterations=3, poly_n=5, poly_sigma=1.2, flags=0,
                )
                mag = float(np.sqrt(flow[..., 0] ** 2 + flow[..., 1] ** 2).mean())
                current.append(mag)
            prev_gray = gray
            fi += 1
            if len(current) >= frames_per_window:
                windows.append({
                    "start_s":   round(win_start_fi / fps, 3),
                    "end_s":     round(fi / fps, 3),
                    "flow_mean": round(float(np.mean(current)), 3),
                    "flow_max":  round(float(np.max(current)), 3),
                })
                current = []
                win_start_fi = fi
        # Tail window if any
        if current:
            windows.append({
                "start_s":   round(win_start_fi / fps, 3),
                "end_s":     round(fi / fps, 3),
                "flow_mean": round(float(np.mean(current)), 3),
                "flow_max":  round(float(np.max(current)), 3),
            })
    finally:
        cap.release()
    return windows


def _near_scene_cut(t: float, scenes: List[dict], window: float = 0.5) -> bool:
    """Return True if t is within `window` seconds of any scene boundary."""
    for sc in scenes:
        if abs(t - sc["start_s"]) <= window or abs(t - sc["end_s"]) <= window:
            return True
    return False


def _parse_srt(path: Path) -> List[dict]:
    """Parse an SRT file into [{start_s, end_s, text}, ...]."""
    if not path.exists():
        return []
    content = path.read_text(encoding="utf-8-sig").strip()
    segments = []
    ts_re = re.compile(r"(\d{2}):(\d{2}):(\d{2}),(\d{3})")
    for block in re.split(r"\n\s*\n", content):
        lines = [l for l in block.splitlines() if l.strip()]
        if not lines:
            continue
        if "-->" not in lines[0] and len(lines) > 1 and "-->" in lines[1]:
            lines = lines[1:]
        if not lines or "-->" not in lines[0]:
            continue
        a, b = (p.strip() for p in lines[0].split("-->", 1))
        def to_s(s):
            m = ts_re.fullmatch(s)
            if not m:
                return 0.0
            h, mn, sc, ms = map(int, m.groups())
            return h * 3600 + mn * 60 + sc + ms / 1000.0
        segments.append({
            "start_s": to_s(a),
            "end_s":   to_s(b),
            "text":    " ".join(lines[1:]).strip(),
        })
    return segments


def _transcript_at(t: float, segments: List[dict]) -> Optional[str]:
    """Return the SRT line active at time t, or None."""
    for seg in segments:
        if seg["start_s"] <= t <= seg["end_s"]:
            return seg["text"]
    # If between segments, return the nearest one within 0.5s
    nearest = min(
        segments,
        key=lambda seg: min(abs(t - seg["start_s"]), abs(t - seg["end_s"])),
        default=None,
    )
    if nearest and (abs(t - nearest["start_s"]) <= 0.5 or abs(t - nearest["end_s"]) <= 0.5):
        return nearest["text"]
    return None


def _extract_frame(video_path: str, t: float, out_path: str) -> bool:
    cmd = [
        _ffmpeg_bin(), "-y", "-loglevel", "error",
        "-ss", f"{max(0.0, t):.3f}",
        "-i", video_path,
        "-frames:v", "1",
        "-q:v", "3",
        out_path,
    ]
    try:
        subprocess.run(cmd, check=True)
        return os.path.exists(out_path)
    except subprocess.CalledProcessError:
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description="Step 08 — automated jitter scan + frame extraction")
    ap.add_argument("clip",                help="captioned clip mp4 (from step 07)")
    ap.add_argument("--scenes-from",       default=None,
                    help="path to <pre_caption>.scenes.json (default: auto-discover next to source)")
    ap.add_argument("--srt",               default=None,
                    help="path to clip-relative SRT (default: auto-discover <clip>.derived.srt)")
    ap.add_argument("--flow-threshold",    type=float, default=8.0,
                    help="mean flow above this in a window flags it as suspect (default 8.0)")
    ap.add_argument("--window",            type=float, default=0.5,
                    help="window size in seconds (default 0.5)")
    ap.add_argument("--out-dir",           default=None,
                    help="directory for review frames (default: <clip_dir>/verify_frames/<clip_stem>/)")
    args = ap.parse_args()

    clip = Path(args.clip).expanduser().resolve()
    if not clip.exists():
        print(f"ERROR: clip not found: {clip}", file=sys.stderr); return 2

    # Discover scenes sidecar if not given
    scenes_path: Optional[Path] = None
    if args.scenes_from:
        scenes_path = Path(args.scenes_from).expanduser().resolve()
    else:
        # Conventional: source pre-caption clip lives at <run_dir>/clips/<same_stem>.mp4
        # with a .scenes.json sidecar
        candidate = clip.parent.parent / "clips" / (clip.stem + ".scenes.json")
        if candidate.exists():
            scenes_path = candidate

    scenes: List[dict] = []
    if scenes_path and scenes_path.exists():
        sidecar = json.loads(scenes_path.read_text())
        scenes  = sidecar.get("scenes", [])
        print(f"[verify] loaded {len(scenes)} scene boundaries from {scenes_path.name}", file=sys.stderr)
    else:
        print("[verify] no scenes sidecar found — flagged windows won't exclude scene-cut motion", file=sys.stderr)

    # Locate the clip-relative SRT for transcript context on each frame.
    srt_path: Optional[Path] = None
    if args.srt:
        srt_path = Path(args.srt).expanduser().resolve()
    else:
        # 06_caption.py writes <out>.derived.srt next to the captioned clip.
        candidate = clip.with_suffix(".derived.srt")
        if candidate.exists():
            srt_path = candidate
    srt_segments: List[dict] = []
    if srt_path and srt_path.exists():
        srt_segments = _parse_srt(srt_path)
        print(f"[verify] loaded {len(srt_segments)} SRT segments from {srt_path.name}", file=sys.stderr)
    else:
        print("[verify] no SRT found — frames won't carry transcript context", file=sys.stderr)

    meta = _video_meta(str(clip))
    print(f"[verify] clip duration {meta['duration_s']:.1f}s @ {meta['fps']:.2f}fps", file=sys.stderr)

    print(f"[verify] computing optical flow per {args.window}s window…", file=sys.stderr)
    windows = _flow_per_window(str(clip), args.window)

    # Flag windows that exceed threshold AND aren't near a known scene cut
    flagged = []
    for w in windows:
        mid_t = (w["start_s"] + w["end_s"]) / 2
        if w["flow_mean"] > args.flow_threshold and not _near_scene_cut(mid_t, scenes):
            flagged.append(w)

    # Build sampling timestamps for review frames
    duration = meta["duration_s"]
    timestamps: List[tuple] = [
        ("opening", 0.5),
        ("mid",     round(duration / 2, 2)),
        ("closing", round(max(0.5, duration - 0.5), 2)),
    ]
    for i, sc in enumerate(scenes):
        if sc["start_s"] > 0.3:
            timestamps.append((f"cut{i}_before", round(sc["start_s"] - 0.3, 3)))
        if sc["start_s"] < duration - 0.3:
            timestamps.append((f"cut{i}_after",  round(sc["start_s"] + 0.3, 3)))
    for j, w in enumerate(flagged):
        mid = round((w["start_s"] + w["end_s"]) / 2, 3)
        timestamps.append((f"flag{j}_mid", mid))

    # Dedup timestamps (within 0.2s)
    seen = set()
    deduped = []
    for label, t in timestamps:
        key = round(t / 0.2)
        if key in seen:
            continue
        seen.add(key)
        deduped.append((label, t))

    # Output directory
    out_dir = (Path(args.out_dir).expanduser().resolve()
               if args.out_dir
               else clip.parent / "verify_frames" / clip.stem)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[verify] extracting {len(deduped)} review frames…", file=sys.stderr)
    frames = []
    for label, t in deduped:
        fname = f"{clip.stem}__{label}__t{t:g}.jpg"
        fpath = out_dir / fname
        if _extract_frame(str(clip), t, str(fpath)):
            transcript_line = _transcript_at(t, srt_segments) if srt_segments else None
            frames.append({
                "label":           label,
                "t_seconds":       t,
                "path":            str(fpath),
                "transcript_at_t": transcript_line,
            })

    # Summary JSON
    summary = {
        "clip":            str(clip),
        "meta":            meta,
        "scenes_source":   str(scenes_path) if scenes_path else None,
        "scenes":          scenes,
        "params": {
            "flow_threshold": args.flow_threshold,
            "window_s":       args.window,
        },
        "windows":         windows,
        "flagged_windows": flagged,
        "review_frames":   frames,
        "auto_summary": {
            "n_windows":         len(windows),
            "n_flagged":         len(flagged),
            "max_flow_mean":     max((w["flow_mean"] for w in windows), default=0.0),
            "needs_human_check": True,  # Claude is the gate
        },
    }
    out_summary = clip.with_suffix(".verify.json")
    out_summary.write_text(json.dumps(summary, indent=2))

    print(f"[verify] {len(flagged)} flagged window(s), max mean flow = {summary['auto_summary']['max_flow_mean']:.2f}", file=sys.stderr)
    print(f"[verify] summary: {out_summary}", file=sys.stderr)
    print(json.dumps({
        "verify_summary":    str(out_summary),
        "review_frames":     [f["path"] for f in frames],
        "flagged_windows":   flagged,
        "max_flow_mean":     summary["auto_summary"]["max_flow_mean"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
