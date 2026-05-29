#!/usr/bin/env python3
"""Compose a 9:16 'show the screen' clip: the full 16:9 source frame placed in a
vertical canvas over a blurred fill of itself. Used for screenshare / demo /
multi-speaker moments where a tight face-crop would hide the content.

Pairs with 06_caption.py (run it after, with a large --style for 1080x1920).
Usage: letterbox_clip.py <src> --start S --end E --out out.mp4 [--w 1080 --h 1920]
"""
import argparse, subprocess, os, sys

FF = os.environ.get("FFMPEG_BIN", "/Applications/meetily.app/Contents/MacOS/ffmpeg")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("--start", type=float, required=True)
    ap.add_argument("--end", type=float, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--w", type=int, default=1080)
    ap.add_argument("--h", type=int, default=1920)
    a = ap.parse_args()
    dur = round(a.end - a.start, 3)
    W, H = a.w, a.h
    vf = (
        f"[0:v]split=2[bg][fg];"
        f"[bg]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=18:3,eq=brightness=-0.07[bgb];"
        f"[fg]scale={W}:-2[fgs];"
        f"[bgb][fgs]overlay=(W-w)/2:200[v]"
    )
    cmd = [FF, "-y", "-loglevel", "error",
           "-ss", str(a.start), "-i", a.source, "-t", str(dur),
           "-filter_complex", vf, "-map", "[v]", "-map", "0:a?",
           "-c:v", "libx264", "-crf", "20", "-preset", "veryfast", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", a.out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-1500:], file=sys.stderr)
        return 1
    print(a.out)
    return 0

if __name__ == "__main__":
    sys.exit(main())
