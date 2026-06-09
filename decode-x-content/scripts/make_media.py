#!/usr/bin/env python3
"""make_media.py <mp4> <out_dir> [--frames N] [--width PX]

Produce two artifacts for a downloaded clip, using imageio-ffmpeg's *static* ffmpeg
(the Homebrew ffmpeg on this machine is broken — missing libx265):

  <out_dir>/audio/<tid>.wav    16 kHz mono PCM (what whisper.cpp expects)
  <out_dir>/sheets/<tid>.jpg   horizontal contact sheet of N evenly-spaced keyframes

Prints ONE json line: {tid, wav, has_audio, sheet, duration_sec}
has_audio=false means a silent screen-recording — a real, common case, NOT an error.
"""
import os, re, sys, json, argparse, subprocess, tempfile
import imageio_ffmpeg

FF = imageio_ffmpeg.get_ffmpeg_exe()


def run(args):
    return subprocess.run([FF, *args], capture_output=True, text=True)


def duration(mp4):
    err = run(["-i", mp4]).stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err)
    if not m:
        return 0.0
    h, mn, s = m.groups()
    return int(h) * 3600 + int(mn) * 60 + float(s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mp4")
    ap.add_argument("out_dir")
    ap.add_argument("--frames", type=int, default=6)
    ap.add_argument("--width", type=int, default=360)
    a = ap.parse_args()

    tid = os.path.splitext(os.path.basename(a.mp4))[0]
    adir = os.path.join(a.out_dir, "audio")
    sdir = os.path.join(a.out_dir, "sheets")
    os.makedirs(adir, exist_ok=True)
    os.makedirs(sdir, exist_ok=True)
    wav = os.path.join(adir, f"{tid}.wav")
    sheet = os.path.join(sdir, f"{tid}.jpg")
    dur = duration(a.mp4)

    # --- audio: 16k mono wav (skip cleanly if there is no audio stream) ---
    r = run(["-y", "-i", a.mp4, "-vn", "-ac", "1", "-ar", "16000", wav])
    has_audio = r.returncode == 0 and os.path.exists(wav) and os.path.getsize(wav) > 2048
    if not has_audio and os.path.exists(wav):
        try:
            os.remove(wav)
        except OSError:
            pass

    # --- contact sheet: N keyframes at evenly spaced timestamps, hstacked ---
    n = max(1, a.frames)
    with tempfile.TemporaryDirectory() as td:
        shots = []
        for i in range(n):
            t = dur * (i + 0.5) / n if dur > 0 else 0
            shot = os.path.join(td, f"{i:02d}.jpg")
            run(["-y", "-ss", f"{t:.2f}", "-i", a.mp4, "-frames:v", "1",
                 "-vf", f"scale={a.width}:-1", "-q:v", "3", shot])
            if os.path.exists(shot) and os.path.getsize(shot) > 0:
                shots.append(shot)
        if len(shots) > 1:
            ins = []
            for s in shots:
                ins += ["-i", s]
            filt = "".join(f"[{i}:v]" for i in range(len(shots))) + f"hstack=inputs={len(shots)}[v]"
            run(["-y", *ins, "-filter_complex", filt, "-map", "[v]", "-q:v", "3", sheet])
        elif shots:
            run(["-y", "-i", shots[0], "-q:v", "3", sheet])

    print(json.dumps({
        "tid": tid,
        "wav": wav if has_audio else None,
        "has_audio": has_audio,
        "sheet": sheet if os.path.exists(sheet) else None,
        "duration_sec": round(dur, 1),
    }))


if __name__ == "__main__":
    main()
