#!/usr/bin/env python3
"""Cut + caption + verify-scan hand-picked candidates, snapped to sentence
boundaries inside pre-vetted clean windows. 4-way parallel, deterministic."""
import json, subprocess, os
from concurrent.futures import ThreadPoolExecutor

RUN = "/Users/akshat.v/.claude/skills/yt-shorts-for-x/output/run_2026-05-29"
VENV = "/Users/akshat.v/.claude/skills/yt-shorts-for-x/scripts/.venv/bin/python"
SCR = "/Users/akshat.v/.claude/skills/yt-shorts-for-x/scripts"
FFMPEG = "/Applications/meetily.app/Contents/MacOS/ffmpeg"

SRCMAP = {
    "greg": {"mp4": f"{RUN}/source/source_IFLY6L3YPGo.mp4",
             "transcript": f"{RUN}/source/source_IFLY6L3YPGo.transcript.json",
             "rankfile": f"{RUN}/source/IFLY6L3YPGo.rank.txt"},
    "mfm":  {"mp4": f"{RUN}/source/source_aozthyS67EM.mp4",
             "transcript": f"{RUN}/source/source_aozthyS67EM.transcript.json",
             "rankfile": f"{RUN}/source/aozthyS67EM.rank.txt"},
}

def segs(rankfile):
    out = []
    for ln in open(rankfile):
        a, b, _ = ln.rstrip("\n").split("\t", 2)
        out.append((float(a), float(b)))
    return out

def snap(rankfile, ws, we):
    S = segs(rankfile)
    starts = [a for a, b in S if a >= ws - 0.4 and a < we - 5]
    ends = [b for a, b in S if b <= we + 0.4 and b > ws + 5]
    cs = min(starts) if starts else ws
    ce = max(ends) if ends else we
    return round(cs, 2), round(ce, 2)

def run_one(c):
    src = SRCMAP[c["source"]]
    cid = c["id"]
    cs, ce = snap(src["rankfile"], c["wstart"], c["wend"])
    env = dict(os.environ, FFMPEG_BIN=FFMPEG)
    base = {"id": cid, "source": c["source"], "title": c.get("title", ""),
            "note": c.get("note", ""), "start": cs, "end": ce, "dur": round(ce - cs, 1)}
    clip = f"{RUN}/clips/{cid}.mp4"
    fin = f"{RUN}/final/{cid}.mp4"
    r = subprocess.run([VENV, f"{SCR}/05_clip.py", src["mp4"], "--start", str(cs), "--end", str(ce),
                        "--out", clip, "--aspect", "9:16", "--blackout-bottom", str(c.get("blackout", 0.0)),
                        "--smoothing", "0.06", "--deadband", "24", "--scene-threshold", "27",
                        "--stationary-mode", "auto"], env=env, capture_output=True, text=True)
    if r.returncode != 0:
        return {**base, "ok": False, "step": "clip", "err": r.stderr[-700:]}
    r = subprocess.run([VENV, f"{SCR}/06_caption.py", clip, "--transcript", src["transcript"],
                        "--clip-start", str(cs), "--clip-end", str(ce), "--out", fin],
                       env=env, capture_output=True, text=True)
    if r.returncode != 0:
        return {**base, "ok": False, "step": "caption", "err": r.stderr[-700:]}
    r = subprocess.run([VENV, f"{SCR}/08_verify.py", fin, "--scenes-from", f"{RUN}/clips/{cid}.scenes.json",
                        "--srt", f"{RUN}/final/{cid}.derived.srt"], env=env, capture_output=True, text=True)
    vj = f"{RUN}/final/{cid}.verify.json"
    frames = []
    if os.path.exists(vj):
        try:
            frames = [f["path"] for f in json.load(open(vj)).get("review_frames", [])]
        except Exception:
            pass
    return {**base, "ok": os.path.exists(fin) and os.path.exists(vj),
            "captioned": fin, "verify_json": vj, "n_frames": len(frames),
            "verr": r.stderr[-300:] if r.returncode != 0 else ""}

if __name__ == "__main__":
    cands = json.load(open(f"{RUN}/candidates.json"))
    # SEQUENTIAL: parallel runs cross-contaminate outputs (confirmed bug). Correctness > speed.
    with ThreadPoolExecutor(max_workers=1) as ex:
        results = list(ex.map(run_one, cands))
    json.dump(results, open(f"{RUN}/produce_results.json", "w"), indent=2)
    ok = sum(1 for r in results if r.get("ok"))
    print(f"\n=== produced {ok}/{len(results)} ===")
    for r in results:
        tag = "OK " if r.get("ok") else "FAIL"
        print(f"{tag} {r['id']:18s} {r.get('dur','?')}s frames={r.get('n_frames','?')} {r.get('step','')} {('| '+r.get('err','')[:90]) if not r.get('ok') else ''}")
