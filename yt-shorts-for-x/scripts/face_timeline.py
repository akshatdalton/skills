#!/usr/bin/env python3
"""Scan a video for CLEAN single-speaker windows croppable to 9:16.

A sampled instant is "clean" iff exactly ONE sufficiently-large, roughly-centered
face is detected -> excludes screenshare (0/tiny faces), split-screen (2 faces),
and multicam grids (3+ faces). Contiguous clean instants become windows.

Usage: face_timeline.py <mp4> [<mp4> ...]  --> writes face_timeline.json
"""
import sys, json, os
import cv2
from mediapipe import Image, ImageFormat
from mediapipe.tasks.python.core.base_options import BaseOptions
from mediapipe.tasks.python.vision import FaceDetector, FaceDetectorOptions, RunningMode

BLAZE = "/Users/akshat.v/.claude/skills/yt-shorts-for-x/scripts/models/blaze_face_short_range.tflite"
OUT = "/Users/akshat.v/.claude/skills/yt-shorts-for-x/output/run_2026-05-29/face_timeline.json"

STEP = 2.0          # sample every 2s
MIN_W = 0.13        # face must be >=13% of frame width (excludes tiny PiP / screenshare)
MAX_W = 0.78
CX_LO, CX_HI = 0.18, 0.82   # 05_clip pans to center, so position is forgiving; this only rejects edge-hugging faces
TINY = 0.055        # ignore detections narrower than this (background/PiP noise)
MIN_WIN = 30.0      # keep clean windows >= 30s

def analyze(path):
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    sw = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    dur = n / fps
    opts = FaceDetectorOptions(
        base_options=BaseOptions(model_asset_path=BLAZE),
        running_mode=RunningMode.IMAGE, min_detection_confidence=0.4)
    samples = []
    with FaceDetector.create_from_options(opts) as det:
        t = 0.0
        while t < dur:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(t * fps))
            ok, frame = cap.read()
            if not ok:
                break
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            res = det.detect(Image(image_format=ImageFormat.SRGB, data=rgb))
            faces = []
            for d in (res.detections or []):
                bb = d.bounding_box
                wfrac = bb.width / sw
                if wfrac < TINY:
                    continue
                cx = (bb.origin_x + bb.width / 2.0) / sw
                faces.append((wfrac, cx))
            faces.sort(reverse=True)
            big = faces[0] if faces else None
            clean = bool(big and len(faces) == 1 and MIN_W <= big[0] <= MAX_W and CX_LO <= big[1] <= CX_HI)
            samples.append({"t": round(t, 1), "n": len(faces),
                            "w": round(big[0], 3) if big else 0.0,
                            "cx": round(big[1], 3) if big else 0.0,
                            "clean": clean})
            t += STEP
    cap.release()
    # merge consecutive clean samples (bridge a single noisy sample)
    wins = []
    for s in samples:
        if not s["clean"]:
            continue
        if wins and s["t"] - wins[-1][1] <= STEP * 2.2:
            wins[-1][1] = s["t"]
        else:
            wins.append([s["t"], s["t"]])
    clean_windows = [{"start": round(a, 1), "end": round(b + STEP, 1), "dur": round(b + STEP - a, 1)}
                     for a, b in wins if (b + STEP - a) >= MIN_WIN]
    return {"path": path, "duration": round(dur, 1), "fps": round(fps, 2),
            "n_samples": len(samples), "clean_windows": clean_windows, "samples": samples}

if __name__ == "__main__":
    out = {}
    for p in sys.argv[1:]:
        r = analyze(p)
        key = os.path.basename(p)
        out[key] = r
        tot = sum(w["dur"] for w in r["clean_windows"])
        print(f"{key}: dur={r['duration']}s | {len(r['clean_windows'])} clean windows >= {MIN_WIN}s | total clean={tot:.0f}s", file=sys.stderr)
        for w in r["clean_windows"]:
            print(f"   {w['start']:.0f}-{w['end']:.0f}  ({w['dur']:.0f}s)", file=sys.stderr)
    json.dump(out, open(OUT, "w"), indent=2)
    print("WROTE " + OUT)
