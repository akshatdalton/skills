#!/usr/bin/env python3
"""Step 05 — Cut a subclip and reframe to a target aspect ratio.

Scene-aware reframing (Level B from the design):
  1. ffmpeg cuts the [start, end] subclip from source (audio kept).
  2. PySceneDetect finds scene cuts inside the cut clip.
  3. MediaPipe FaceDetector runs on every frame; per-shot face positions are
     collected. Tracker state resets at every cut — we never chase a face
     across a scene boundary.
  4. Per shot, decide mode based on speaker movement variance:
       * stationary (std_x < deadband)  → lock crop on median face position
       * tracking   (std_x >= deadband) → smoothed + deadbanded chase
  5. Re-mux original audio.

A sidecar `<out>.scenes.json` is written with the detected scene boundaries
in clip-relative seconds, so 08_verify.py can sample frames near every cut.

Decoupled: no imports from other steps. ffmpeg via FFMPEG_BIN env or PATH.

Usage:
    python 05_clip.py <source.mp4> --start 124.3 --end 187.6 --out short_01.mp4 \\
        [--aspect 9:16] [--blackout-bottom 0.28] [--smoothing 0.06] [--deadband 24] \\
        [--scene-threshold 27.0] [--stationary-mode auto|on|off]
"""
import argparse
import json
import os
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def _ffmpeg_bin() -> str:
    candidate = os.environ.get("FFMPEG_BIN", "/Applications/meetily.app/Contents/MacOS/ffmpeg")
    if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
        return candidate
    return "ffmpeg"


def _ratio(aspect: str) -> float:
    try:
        w, h = aspect.split(":")
        return float(w) / float(h)
    except (ValueError, ZeroDivisionError):
        return 9.0 / 16.0


def _cut(src: str, start: float, end: float, out: str) -> None:
    cmd = [
        _ffmpeg_bin(), "-y", "-loglevel", "error",
        "-i", src,
        "-ss", f"{start:.3f}",
        "-to", f"{end:.3f}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        out,
    ]
    subprocess.run(cmd, check=True)


def _detect_scenes(video_path: str, threshold: float) -> List[Tuple[int, int]]:
    """Return list of (start_frame, end_frame) per shot."""
    from scenedetect import detect, ContentDetector
    scene_list = detect(video_path, ContentDetector(threshold=threshold))
    return [(s.get_frames(), e.get_frames()) for s, e in scene_list]


_FACE_MODEL_PATH       = str(Path(__file__).parent / "models" / "blaze_face_short_range.tflite")
_LANDMARKER_MODEL_PATH = str(Path(__file__).parent / "models" / "face_landmarker.task")

# Mouth landmark indices in MediaPipe's 468-point face mesh:
# 13 = upper-inner-lip midpoint, 14 = lower-inner-lip midpoint.
# Vertical distance = "mouth openness". Variance over a shot = "talking-ness".
_LIP_UPPER_IDX = 13
_LIP_LOWER_IDX = 14


def _detect_all_faces_per_frame(
    in_path: str, sw: int, sh: int,
    blackout_top: float, blackout_bottom: float,
    max_faces: int = 5,
    min_confidence: float = 0.65,
    min_area_frac: float = 0.04,
) -> List[List[dict]]:
    """Run FaceLandmarker on every frame, multi-face.

    Returns list-of-lists: per_frame[fi] = [{cx, cy, w, h, mouth_open}, ...]

    Defensive filtering:
      - min_face_detection_confidence raised to 0.65 (was 0.5)
      - face bbox must cover at least min_area_frac of the frame
        → kills background hallucinations (bookshelf/plant texture as 'face')
      - max_faces bumped to 5 for round-table panels

    Faces are NOT yet tracked across frames here — that happens in
    _per_shot_crop_centers using bbox-center proximity.
    """
    import cv2
    from mediapipe import Image, ImageFormat
    from mediapipe.tasks.python.core.base_options import BaseOptions
    from mediapipe.tasks.python.vision import (
        FaceLandmarker, FaceLandmarkerOptions, RunningMode,
    )

    if not os.path.exists(_LANDMARKER_MODEL_PATH):
        raise RuntimeError(
            f"FaceLandmarker model missing at {_LANDMARKER_MODEL_PATH}. "
            "Run scripts/setup.sh to download it."
        )

    cap = cv2.VideoCapture(in_path)
    if not cap.isOpened():
        raise RuntimeError(f"could not open {in_path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    top_y    = int(sh * blackout_top) if blackout_top > 0 else 0
    bottom_y = int(sh * (1.0 - blackout_bottom)) if blackout_bottom > 0 else sh

    frame_area = sw * sh
    min_face_area = int(min_area_frac * frame_area)

    options = FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=_LANDMARKER_MODEL_PATH),
        running_mode=RunningMode.VIDEO,
        num_faces=max_faces,
        min_face_detection_confidence=min_confidence,
    )

    per_frame: List[List[dict]] = []
    fi = 0
    rejected = 0
    with FaceLandmarker.create_from_options(options) as detector:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if top_y > 0:
                frame[:top_y, :] = 0
            if bottom_y < sh:
                frame[bottom_y:, :] = 0
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = Image(image_format=ImageFormat.SRGB, data=rgb)
            timestamp_ms = int(fi * 1000 / fps)
            result = detector.detect_for_video(mp_image, timestamp_ms)

            frame_faces = []
            for lm_list in (result.face_landmarks or []):
                if not lm_list:
                    continue
                xs = [lm.x for lm in lm_list]
                ys = [lm.y for lm in lm_list]
                x_min, x_max = int(min(xs) * sw), int(max(xs) * sw)
                y_min, y_max = int(min(ys) * sh), int(max(ys) * sh)
                bw = x_max - x_min
                bh = y_max - y_min
                # Defensive: reject tiny bboxes (background hallucinations)
                if bw * bh < min_face_area:
                    rejected += 1
                    continue
                cx = (x_min + x_max) // 2
                cy = (y_min + y_max) // 2
                upper_y = lm_list[_LIP_UPPER_IDX].y * sh
                lower_y = lm_list[_LIP_LOWER_IDX].y * sh
                mouth_open = abs(upper_y - lower_y) / max(1.0, bh)
                frame_faces.append({
                    "cx": cx, "cy": cy, "w": bw, "h": bh,
                    "mouth_open": float(mouth_open),
                })
            per_frame.append(frame_faces)
            fi += 1
    cap.release()
    if rejected:
        print(f"[clip]   defensive filter dropped {rejected} small-bbox face(s)", file=sys.stderr)
    return per_frame


def _build_tracks(per_frame: List[List[dict]], s_start: int, s_end: int,
                  max_link_dist: int = 100) -> List[dict]:
    """Link face detections across consecutive frames within [s_start, s_end)
    by bbox-center proximity. Returns list of tracks.

    Each track = {"frames": {fi: face_dict}, "mouth_var": float, "avg_area": float}
    """
    tracks: List[dict] = []
    for fi in range(s_start, s_end):
        if fi >= len(per_frame):
            break
        for face in per_frame[fi]:
            best_track = None
            best_dist = float("inf")
            for tr in tracks:
                if (fi - 1) not in tr["frames"]:
                    continue
                prev = tr["frames"][fi - 1]
                d = ((face["cx"] - prev["cx"]) ** 2 + (face["cy"] - prev["cy"]) ** 2) ** 0.5
                if d < best_dist and d < max_link_dist:
                    best_dist = d
                    best_track = tr
            if best_track is not None:
                best_track["frames"][fi] = face
            else:
                tracks.append({"frames": {fi: face}})

    # Summarize each track
    for tr in tracks:
        mouths = [f["mouth_open"] for f in tr["frames"].values()]
        areas  = [f["w"] * f["h"]   for f in tr["frames"].values()]
        if len(mouths) > 1:
            mean_m = sum(mouths) / len(mouths)
            tr["mouth_var"] = float(sum((m - mean_m) ** 2 for m in mouths) / (len(mouths) - 1)) ** 0.5
        else:
            tr["mouth_var"] = 0.0
        tr["avg_area"] = sum(areas) / len(areas) if areas else 0.0
    return tracks


def _pick_speaker(tracks: List[dict], min_track_frames: int = 5,
                  talking_threshold: float = 0.005) -> Optional[dict]:
    """Pick the most-likely speaker track in a shot.

    Strategy:
      1. Keep only tracks present for >= min_track_frames frames.
      2. If max mouth-variance >= talking_threshold, that track wins (= someone's clearly talking).
      3. Else fall back to the largest-area track (= prominent / center-of-attention face).

    Returns None if no track meets the minimum-frames bar.
    """
    if not tracks:
        return None
    significant = [t for t in tracks if len(t["frames"]) >= min_track_frames]
    if not significant:
        significant = tracks
    by_mouth = sorted(significant, key=lambda t: t["mouth_var"], reverse=True)
    if by_mouth[0]["mouth_var"] >= talking_threshold:
        return by_mouth[0]
    return max(significant, key=lambda t: t["avg_area"])


def _per_shot_crop_centers(
    scenes: List[Tuple[int, int]],
    per_frame: List[List[dict]],
    sw: int, sh: int,
    smoothing: float, deadband_px: int,
    stationary_mode: str,  # "auto" | "on" | "off"
    letterbox_min_faces: int = 3,
    letterbox_spread_frac: float = 0.40,
) -> Tuple[Dict[int, Tuple[int, int]], Dict[int, str], List[Dict]]:
    """Decide crop center / render mode per frame, scene by scene.

    Within each shot:
      1. Link face detections across frames into tracks.
      2. If >= letterbox_min_faces persistent tracks → LETTERBOX MODE
         (whole 16:9 frame scaled into the 9:16 canvas with black bars).
         The wide multi-speaker shot stays visually faithful.
      3. Otherwise pick the SPEAKER track (highest mouth-opening variance)
         and apply stationary-vs-tracking crop logic.

    Returns (centers, modes, diagnostics).
      centers[fi] = (cx, cy)       # ignored when mode is letterbox
      modes[fi]   = "crop" | "letterbox" | "center_fallback"
    """
    centers: Dict[int, Tuple[int, int]] = {}
    modes:   Dict[int, str]             = {}
    diagnostics: List[Dict] = []

    if not scenes:
        scenes = [(0, len(per_frame))]

    for s_start, s_end in scenes:
        s_end_clamped = min(s_end, len(per_frame))
        tracks = _build_tracks(per_frame, s_start, s_end_clamped)

        # Persistent tracks = appears in >= 5 frames (real subjects, not flickers)
        persistent = [t for t in tracks if len(t["frames"]) >= 5]
        n_persistent = len(persistent)

        # Spread metric: the WIDEST observed face-to-face distance across all
        # frames in this shot. If any single frame had 2+ faces spread > 50%
        # of frame width apart, no 9:16 crop can capture them — letterbox.
        # Per-frame max (not avg) so a wide opening shot still triggers even
        # if most of the shot is a closeup at a different camera angle.
        max_face_spread = 0.0
        for fi in range(s_start, s_end_clamped):
            faces_in_frame = per_frame[fi] if fi < len(per_frame) else []
            if len(faces_in_frame) >= 2:
                cxs = [f["cx"] for f in faces_in_frame]
                frame_spread = (max(cxs) - min(cxs)) / max(1, sw)
                if frame_spread > max_face_spread:
                    max_face_spread = frame_spread

        # B — Letterbox fallback: many concurrent faces OR wide-spread faces.
        # Also: even with one persistent track, if any frame has 2+ faces
        # spread > threshold of frame width, the shot contains a wide-shot
        # moment where no 9:16 crop fits everyone.
        n_raw = len(tracks)
        should_letterbox = (
            n_persistent >= letterbox_min_faces
            or n_raw >= letterbox_min_faces + 1   # noisy tracks: 4+ raw signals wide-shot
            or max_face_spread > letterbox_spread_frac
        )
        speaker = _pick_speaker(tracks)

        if should_letterbox:
            # SPEAKER-LOCKED LETTERBOX (Option B) — for letterbox shots with a
            # clear primary speaker (≤3 persistent faces), translate the
            # letterbox content horizontally to keep the speaker at output
            # center. Stabilizes source camera moves (push-ins, slow pans).
            #
            # For wider panels (4+ speakers), keep static letterbox so all
            # faces stay visible without sliding.
            use_tracked = (
                speaker is not None
                and speaker.get("frames")
                and n_persistent <= 3
                and speaker.get("mouth_var", 0) > 0.005   # has SOME mouth movement
            )
            if use_tracked:
                speaker_pos = {fi: f["cx"] for fi, f in speaker["frames"].items()}
                first_fi = min(speaker_pos.keys())
                last_cx = speaker_pos[first_fi]
                for fi in range(s_start, s_end):
                    if fi in speaker_pos:
                        # Smooth (10% chase, very gentle so we don't jitter)
                        last_cx = int(0.9 * last_cx + 0.1 * speaker_pos[fi])
                    centers[fi] = (last_cx, sh // 2)
                    modes[fi]   = "letterbox_tracked"
                diagnostics.append({
                    "shot":   [s_start, s_end],
                    "mode":   "letterbox_tracked",
                    "tracks": len(tracks),
                    "persistent_faces": n_persistent,
                    "max_face_spread_frac": round(max_face_spread, 2),
                    "speaker_mouth_var": round(speaker["mouth_var"], 4),
                })
            else:
                for fi in range(s_start, s_end):
                    centers[fi] = (sw // 2, sh // 2)
                    modes[fi]   = "letterbox"
                diagnostics.append({
                    "shot":   [s_start, s_end],
                    "mode":   "letterbox",
                    "tracks": len(tracks),
                    "persistent_faces": n_persistent,
                    "max_face_spread_frac": round(max_face_spread, 2),
                })
            continue

        if speaker is None or not speaker["frames"]:
            # No confident speaker — letterbox shows the full source frame
            # cleanly (whether it's a wide group shot of unrecognized faces
            # or genuine B-roll). Beats a blind center crop that would slice
            # off the edges of whatever's actually in the shot.
            for fi in range(s_start, s_end):
                centers[fi] = (sw // 2, sh // 2)
                modes[fi]   = "letterbox"
            diagnostics.append({
                "shot":   [s_start, s_end],
                "mode":   "letterbox_fallback",
                "tracks": len(tracks),
            })
            continue

        # Positions from the SPEAKER track only.
        cxs = [f["cx"] for f in speaker["frames"].values()]
        cys = [f["cy"] for f in speaker["frames"].values()]
        std_x   = statistics.stdev(cxs) if len(cxs) > 1 else 0.0
        median_x = int(statistics.median(cxs))
        median_y = int(statistics.median(cys))

        if stationary_mode == "on":
            use_stationary = True
        elif stationary_mode == "off":
            use_stationary = False
        else:
            use_stationary = std_x < deadband_px

        # Talker confidence summary for diagnostics
        n_tracks       = len(tracks)
        talker_score   = round(speaker["mouth_var"], 4)
        runner_up_var  = round(sorted((t["mouth_var"] for t in tracks), reverse=True)[1], 4) if n_tracks > 1 else None

        if use_stationary:
            for fi in range(s_start, s_end):
                centers[fi] = (median_x, median_y)
                modes[fi]   = "crop"
            diagnostics.append({
                "shot":          [s_start, s_end],
                "mode":          "stationary",
                "tracks":        n_tracks,
                "speaker_frames": len(speaker["frames"]),
                "speaker_mouth_var": talker_score,
                "runner_up_mouth_var": runner_up_var,
                "std_x":         round(std_x, 1),
                "center":        [median_x, median_y],
            })
        else:
            speaker_pos = {fi: (f["cx"], f["cy"]) for fi, f in speaker["frames"].items()}
            first_fi = min(speaker_pos.keys())
            last_x, last_y = speaker_pos[first_fi]
            for fi in range(s_start, s_end):
                if fi in speaker_pos:
                    new_x, new_y = speaker_pos[fi]
                    dx, dy = new_x - last_x, new_y - last_y
                    if dx * dx + dy * dy > deadband_px * deadband_px:
                        last_x = int(last_x + dx * smoothing)
                        last_y = int(last_y + dy * smoothing)
                centers[fi] = (last_x, last_y)
                modes[fi]   = "crop"
            diagnostics.append({
                "shot":          [s_start, s_end],
                "mode":          "tracking",
                "tracks":        n_tracks,
                "speaker_frames": len(speaker["frames"]),
                "speaker_mouth_var": talker_score,
                "runner_up_mouth_var": runner_up_var,
                "std_x":         round(std_x, 1),
            })

    for fi in range(len(per_frame)):
        centers.setdefault(fi, (sw // 2, sh // 2))
        modes.setdefault(fi, "center_fallback")
    return centers, modes, diagnostics


def _write_output(
    in_path: str, silent_out: str,
    centers: Dict[int, Tuple[int, int]],
    modes:   Dict[int, str],
    sw: int, sh: int, crop_w: int, crop_h: int, fps: float,
    blackout_top: float, blackout_bottom: float,
) -> None:
    """Write the cropped/letterboxed output silently. Audio is muxed back later.

    Per-frame render mode comes from `modes`:
      - "crop" / "center_fallback": standard 9:16 window crop at centers[fi]
      - "letterbox": full 16:9 source scaled to fit crop_w wide, centered
                     vertically in the crop_h canvas with black bars top/bottom.
                     Used for shots with too many speakers to fit one crop.
    """
    import cv2
    import numpy as np

    cap    = cv2.VideoCapture(in_path)
    writer = cv2.VideoWriter(silent_out, cv2.VideoWriter_fourcc(*"mp4v"), fps, (crop_w, crop_h))
    top_y    = int(sh * blackout_top) if blackout_top > 0 else 0
    bottom_y = int(sh * (1.0 - blackout_bottom)) if blackout_bottom > 0 else sh

    # Pre-compute letterbox dimensions (constant)
    lb_h = int(round(sh * crop_w / sw))   # scaled height when source fits crop_w wide
    lb_y_off = max(0, (crop_h - lb_h) // 2)
    lb_h = min(lb_h, crop_h)              # clamp if source aspect > target

    # Tracked-letterbox: scale source 1.15× canvas-wide so we have horizontal
    # room to translate, then shift to keep the speaker at output center.
    tracked_scale = 1.15
    tlb_w = int(round(crop_w * tracked_scale))
    tlb_h = int(round(sh * tlb_w / sw))
    tlb_y_off = max(0, (crop_h - tlb_h) // 2)
    tlb_h = min(tlb_h, crop_h)

    fi = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if top_y > 0:
                frame[:top_y, :] = 0
            if bottom_y < sh:
                frame[bottom_y:, :] = 0

            mode = modes.get(fi, "crop")

            if mode == "letterbox":
                # Static letterbox: scale full source to crop_w, center it
                scaled = cv2.resize(frame, (crop_w, lb_h), interpolation=cv2.INTER_AREA)
                canvas = np.zeros((crop_h, crop_w, 3), dtype=np.uint8)
                canvas[lb_y_off:lb_y_off + scaled.shape[0], :, :] = scaled
                writer.write(canvas)

            elif mode == "letterbox_tracked":
                # Speaker-locked letterbox: scale 1.15× canvas-wide and shift
                # horizontally so the speaker's source x lands at output-center.
                scaled = cv2.resize(frame, (tlb_w, tlb_h), interpolation=cv2.INTER_AREA)
                speaker_sx, _ = centers.get(fi, (sw // 2, sh // 2))
                # Where speaker lands in the scaled source
                speaker_scaled_x = int(speaker_sx * tlb_w / sw)
                # x_off: how to translate scaled content so speaker_scaled_x maps to crop_w/2
                x_off = (crop_w // 2) - speaker_scaled_x
                # Clamp so scaled source still covers the full canvas width
                # (no black gaps on edges):
                #   x_off >= crop_w - tlb_w   (right edge of scaled stays at canvas right or past)
                #   x_off <= 0                (left edge of scaled stays at canvas left or past)
                x_off = max(crop_w - tlb_w, min(0, x_off))

                canvas = np.zeros((crop_h, crop_w, 3), dtype=np.uint8)
                # src window in the scaled image
                src_x0 = -x_off            # >= 0
                src_x1 = src_x0 + crop_w   # <= tlb_w
                canvas[tlb_y_off:tlb_y_off + tlb_h, :, :] = scaled[:, src_x0:src_x1]
                writer.write(canvas)

            else:
                cx, cy = centers.get(fi, (sw // 2, sh // 2))
                x0 = max(0, min(sw - crop_w, cx - crop_w // 2))
                y0 = max(0, min(sh - crop_h, cy - crop_h // 2))
                writer.write(frame[y0:y0 + crop_h, x0:x0 + crop_w])
            fi += 1
    finally:
        writer.release()
        cap.release()


def _reframe(
    in_path: str,
    out_path: str,
    aspect: str,
    blackout_bottom: float = 0.0,
    blackout_top: float = 0.0,
    smoothing: float = 0.06,
    deadband_px: int = 24,
    scene_threshold: float = 27.0,
    stationary_mode: str = "auto",
) -> Dict:
    import cv2

    cap = cv2.VideoCapture(in_path)
    if not cap.isOpened():
        raise RuntimeError(f"could not open {in_path}")
    sw  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    sh  = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    cap.release()

    target = _ratio(aspect)
    if target < sw / sh:
        crop_h = sh
        crop_w = int(crop_h * target)
    else:
        crop_w = sw
        crop_h = int(crop_w / target)
    crop_w = max(2, crop_w - (crop_w % 2))
    crop_h = max(2, crop_h - (crop_h % 2))

    blackout_bottom = max(0.0, min(0.5, float(blackout_bottom)))
    blackout_top    = max(0.0, min(0.5, float(blackout_top)))

    print("[clip] step 1/3: scene detection", file=sys.stderr)
    scenes = _detect_scenes(in_path, threshold=scene_threshold)
    print(f"[clip]   → {len(scenes)} shot(s)", file=sys.stderr)

    print("[clip] step 2/3: multi-face landmarks (MediaPipe FaceLandmarker, every frame)", file=sys.stderr)
    per_frame_faces = _detect_all_faces_per_frame(in_path, sw, sh, blackout_top, blackout_bottom, max_faces=3)
    n_with_face   = sum(1 for ff in per_frame_faces if ff)
    n_total_faces = sum(len(ff) for ff in per_frame_faces)
    print(f"[clip]   → {n_with_face}/{len(per_frame_faces)} frames have ≥1 face, "
          f"{n_total_faces} total face detections", file=sys.stderr)

    print("[clip] step 3/3: per-shot speaker pick + crop centers + write", file=sys.stderr)
    centers, modes, diagnostics = _per_shot_crop_centers(
        scenes if scenes else [(0, len(per_frame_faces))], per_frame_faces,
        sw, sh, smoothing, deadband_px, stationary_mode,
    )
    # Used below for the sidecar
    faces_compat_count = n_with_face

    silent = out_path + ".silent.mp4"
    try:
        _write_output(in_path, silent, centers, modes, sw, sh, crop_w, crop_h, fps,
                      blackout_top, blackout_bottom)
        mux = [
            _ffmpeg_bin(), "-y", "-loglevel", "error",
            "-i", silent,
            "-i", in_path,
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "128k",
            "-map", "0:v:0", "-map", "1:a:0?",
            "-shortest",
            out_path,
        ]
        subprocess.run(mux, check=True)
    finally:
        if os.path.exists(silent):
            os.remove(silent)

    # Sidecar with scene boundaries + per-shot diagnostics — used by 08_verify.py
    scenes_seconds = [
        {"start_s": round(s / fps, 3), "end_s": round(e / fps, 3)}
        for s, e in (scenes if scenes else [(0, len(per_frame_faces))])
    ]
    sidecar = {
        "fps":         fps,
        "frame_count": len(per_frame_faces),
        "faces_found": faces_compat_count,
        "scenes":      scenes_seconds,
        "shots":       diagnostics,
    }
    Path(out_path).with_suffix(".scenes.json").write_text(json.dumps(sidecar, indent=2))

    for d in diagnostics:
        speaker_info = ""
        if "speaker_mouth_var" in d:
            ru = d.get("runner_up_mouth_var")
            speaker_info = f" speaker_var={d['speaker_mouth_var']}"
            if ru is not None:
                speaker_info += f" (runner_up={ru})"
        print(
            f"[clip]   shot {d['shot']}: mode={d['mode']} "
            f"tracks={d.get('tracks',0)}{speaker_info} std_x={d.get('std_x','-')}",
            file=sys.stderr,
        )

    return sidecar


def main() -> int:
    ap = argparse.ArgumentParser(description="Step 05 — cut + scene-aware reframe")
    ap.add_argument("source",                         help="source mp4 path")
    ap.add_argument("--start",            type=float, required=True)
    ap.add_argument("--end",              type=float, required=True)
    ap.add_argument("--out",                          required=True)
    ap.add_argument("--aspect",                       default="9:16")
    ap.add_argument("--blackout-bottom",  type=float, default=0.0,
                    help="mask bottom fraction (e.g. 0.28 for CNBC tickers)")
    ap.add_argument("--blackout-top",     type=float, default=0.0,
                    help="mask top fraction (banners)")
    ap.add_argument("--smoothing",        type=float, default=0.06,
                    help="chase rate per frame (tracking mode only)")
    ap.add_argument("--deadband",         type=int,   default=24,
                    help="movement threshold in px (also: stationary-mode cutoff)")
    ap.add_argument("--scene-threshold",  type=float, default=27.0,
                    help="PySceneDetect ContentDetector threshold (default 27)")
    ap.add_argument("--stationary-mode",              default="auto",
                    choices=["auto", "on", "off"],
                    help="auto = decide per shot by movement variance (default)")
    args = ap.parse_args()

    src = Path(args.source).expanduser().resolve()
    if not src.exists():
        print(f"ERROR: source not found: {src}", file=sys.stderr); return 2
    out = Path(args.out).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    cut_path = str(out) + ".cut.mp4"
    try:
        print(f"[clip] cutting {args.start:.1f}s → {args.end:.1f}s", file=sys.stderr)
        _cut(str(src), args.start, args.end, cut_path)
        print(
            f"[clip] reframing to {args.aspect} "
            f"(blackout top={args.blackout_top:.2f} bottom={args.blackout_bottom:.2f}, "
            f"smoothing={args.smoothing:.2f}, deadband={args.deadband}px, "
            f"scene_thr={args.scene_threshold}, stationary={args.stationary_mode})",
            file=sys.stderr,
        )
        _reframe(
            cut_path, str(out), args.aspect,
            blackout_bottom=args.blackout_bottom,
            blackout_top=args.blackout_top,
            smoothing=args.smoothing,
            deadband_px=args.deadband,
            scene_threshold=args.scene_threshold,
            stationary_mode=args.stationary_mode,
        )
    finally:
        if os.path.exists(cut_path):
            os.remove(cut_path)

    print(str(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
