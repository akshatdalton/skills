#!/usr/bin/env python3
"""Step 08 — Upload a run's artifacts to gdrive via the gws-personal CLI.

Default workflow step. Uploads to `aksenHQ/clips/runs/<run-id>/`:
- manifest.json     (built fresh by this script)
- transcript.json
- highlights.raw.json
- clips/<rank>_<score>_<slug>.mp4   (renamed final/* in rank order)

On first run, bootstraps aksenHQ/clips/ with README.md, CLAUDE.md, index.json.
README + CLAUDE are written once; never overwritten on subsequent runs so the
user can edit them. index.json is download → modify → update each run.

Idempotent: re-running on the same run dir replaces existing artifacts in place
(same fileIds), and the run's entry in index.json gets updated.

Contract:
    in:  local run dir containing
         - source/*.transcript.json
         - highlights.raw.json
         - highlights.json
         - final/short_*.mp4    (output of step 07)
    out: prints run gdrive folder URL + local manifest.json path to stdout
         mirrors manifest.json into the local run dir

Decoupled: no imports from other steps. Calls `gws-personal` CLI via subprocess.

Usage:
    python 08_upload.py <run_dir> \\
        --video-id FG5JsLHPW_I \\
        --youtube-url https://www.youtube.com/watch?v=FG5JsLHPW_I \\
        --title "Amodei + Dimon CNBC recap" \\
        [--slug amodei-dimon-cnbc] \\
        [--content-type commentary --density high]
"""
import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional


# gws-personal is a shell alias: `GOOGLE_WORKSPACE_CLI_CONFIG_DIR=$HOME/.config/gws-personal gws`
# Subprocess doesn't see shell aliases — replicate it here.
GWS_BIN = shutil.which("gws") or "/opt/homebrew/bin/gws"
GWS_CONFIG_DIR = os.path.expanduser("~/.config/gws-personal")
GWS_ENV = {**os.environ, "GOOGLE_WORKSPACE_CLI_CONFIG_DIR": GWS_CONFIG_DIR}


README_CONTENT = """# @aksenHQ X clips library

Auto-generated 9:16 captioned clips from long-form YouTube videos, processed
by the `yt-shorts-for-x` Claude Code skill.

Each source video gets its own folder under `runs/` with the full pipeline
output: transcript, ranked candidates with virality reasoning, and the final
captioned mp4s ready to post on X.

`index.json` is the master catalogue — every run, its title, posting status,
and gdrive folder id.

See `CLAUDE.md` for the operational context Claude needs whenever it touches
this folder.
"""


CLAUDE_MD = """# @aksenHQ clips library — Claude context

This folder is managed by the `yt-shorts-for-x` skill. Read this before
finding, updating, or extending the clip library.

## Layout

```
aksenHQ/clips/
├── README.md            ← human description
├── CLAUDE.md            ← (this file)
├── index.json           ← master catalogue of all runs
└── runs/
    └── <run-id>/
        ├── manifest.json
        ├── transcript.json
        ├── highlights.raw.json
        └── clips/<rank>_<score>_<slug>.mp4
```

## Naming

- `run_id` = `YYYY-MM-DD_<youtube_video_id>_<slug>`
- Clip filename = `<rank>_<score>_<slug>.mp4` — rank-ordered, score visible

## index.json schema

```json
{
  "runs": [
    {
      "run_id": "2026-05-19_FG5JsLHPW_I_amodei-dimon-cnbc",
      "video_id": "FG5JsLHPW_I",
      "youtube_url": "https://www.youtube.com/watch?v=...",
      "title": "Amodei + Dimon CNBC recap",
      "created_at": "2026-05-19T07:35:00Z",
      "gdrive_folder_id": "1AbC...",
      "n_clips": 3,
      "posted_count": 0
    }
  ]
}
```

## manifest.json schema (per run)

```json
{
  "video_id": "...",
  "youtube_url": "...",
  "title": "...",
  "duration_seconds": 322.15,
  "content_type": "commentary",
  "density": "high",
  "created_at": "ISO-8601 Z",
  "gdrive_folder_id": "...",
  "highlights": [
    {
      "rank": 1, "score": 94,
      "start_time": 191.22, "end_time": 244.74,
      "title": "...", "hook_sentence": "...", "virality_reason": "...",
      "clip_gdrive_id": "...",
      "clip_filename": "1_94_unemployment.mp4",
      "posted_to_x": false, "post_url": null, "posted_at": null
    }
  ]
}
```

## Looking up a past run

1. Read `index.json` → grep by `video_id`, `title`, or `created_at`
2. Open `runs/<run_id>/manifest.json` for full clip details
3. mp4s live under `runs/<run_id>/clips/`

## Marking a clip as posted

When a clip lands on X, update both files (gdrive update preserves fileId):
1. `runs/<run_id>/manifest.json` — set `highlights[i].posted_to_x = true`,
   `post_url`, `posted_at` on the matching entry.
2. `index.json` — bump `posted_count` for that run.
"""


INDEX_SEED = {"runs": []}


# ---------- gws-personal CLI wrappers --------------------------------------

def _run(args: list, cwd: Optional[str] = None) -> dict:
    """Run a gws command, return parsed JSON from stdout.

    cwd: gws-personal validates that --upload paths resolve inside cwd.
         For uploads, pass the upload file's parent dir here and use the
         basename in the --upload arg.
    """
    cmd = [GWS_BIN] + args
    result = subprocess.run(cmd, capture_output=True, text=True, check=False,
                            env=GWS_ENV, cwd=cwd)
    if result.returncode != 0:
        print(f"ERROR: {' '.join(cmd)}", file=sys.stderr)
        print(f"  stderr: {result.stderr.strip()}", file=sys.stderr)
        print(f"  stdout: {result.stdout.strip()}", file=sys.stderr)
        sys.exit(2)
    out = result.stdout.strip()
    if not out:
        return {}
    start = min((i for i in (out.find("{"), out.find("[")) if i >= 0), default=-1)
    return json.loads(out[start:]) if start >= 0 else {}


def gws_list(query: str, fields: str = "files(id,name)") -> list:
    return _run([
        "drive", "files", "list",
        "--params", json.dumps({"q": query, "fields": fields}),
    ]).get("files", [])


def gws_create_folder(name: str, parent_id: Optional[str] = None) -> str:
    body = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
    if parent_id:
        body["parents"] = [parent_id]
    return _run(["drive", "files", "create", "--json", json.dumps(body)])["id"]


def gws_upload(name: str, local_path: Path, mime: str, parent_id: str,
               existing_id: Optional[str] = None) -> str:
    """Create or update a file. Returns file id.

    Runs the CLI with cwd=local_path.parent and passes only the basename to
    --upload, so gws-personal's "inside cwd" validation passes.
    """
    local_path = Path(local_path).resolve()
    parent_dir = str(local_path.parent)
    basename   = local_path.name

    if existing_id:
        resp = _run([
            "drive", "files", "update",
            "--params", json.dumps({"fileId": existing_id}),
            "--upload", basename,
            "--upload-content-type", mime,
        ], cwd=parent_dir)
        return resp.get("id", existing_id)
    body = {"name": name, "mimeType": mime, "parents": [parent_id]}
    resp = _run([
        "drive", "files", "create",
        "--json", json.dumps(body),
        "--upload", basename,
        "--upload-content-type", mime,
    ], cwd=parent_dir)
    return resp["id"]


def gws_download_text(file_id: str) -> str:
    """Get file content as text. files.get with alt=media writes text content
    to stdout (the --output flag is only honored for binary responses)."""
    result = subprocess.run(
        [GWS_BIN, "drive", "files", "get",
         "--params", json.dumps({"fileId": file_id, "alt": "media"})],
        capture_output=True, text=True, check=True, env=GWS_ENV,
    )
    return result.stdout


# ---------- helpers --------------------------------------------------------

def find_folder(name: str, parent_id: Optional[str] = None) -> Optional[str]:
    parent = f"'{parent_id}'" if parent_id else "'root'"
    q = (f"name = '{name}' and "
         f"mimeType = 'application/vnd.google-apps.folder' and "
         f"{parent} in parents and trashed = false")
    matches = gws_list(q)
    return matches[0]["id"] if matches else None


def find_file(name: str, parent_id: str) -> Optional[str]:
    q = f"name = '{name}' and '{parent_id}' in parents and trashed = false"
    matches = gws_list(q)
    return matches[0]["id"] if matches else None


def ensure_folder(name: str, parent_id: Optional[str] = None) -> str:
    return find_folder(name, parent_id) or gws_create_folder(name, parent_id)


def upload_text_file(name: str, content: str, mime: str, parent_id: str,
                     skip_if_exists: bool = False) -> str:
    """Upload content as a text file. Reuses fileId on update."""
    existing = find_file(name, parent_id)
    if existing and skip_if_exists:
        return existing
    tmp = Path(f"/tmp/.gws_up_{os.getpid()}_{name}")
    tmp.write_text(content, encoding="utf-8")
    try:
        return gws_upload(name, tmp, mime, parent_id, existing_id=existing)
    finally:
        tmp.unlink(missing_ok=True)


def slugify(s: str, max_len: int = 50) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s[:max_len].rstrip("-") or "untitled"


# ---------- main flow ------------------------------------------------------

def bootstrap_clips_root() -> str:
    """Ensure aksenHQ/clips/ exists; seed README + CLAUDE + empty index."""
    aksenhq = ensure_folder("aksenHQ")
    clips   = ensure_folder("clips", aksenhq)
    upload_text_file("README.md", README_CONTENT, "text/markdown", clips, skip_if_exists=True)
    upload_text_file("CLAUDE.md", CLAUDE_MD,    "text/markdown", clips, skip_if_exists=True)
    if not find_file("index.json", clips):
        upload_text_file("index.json", json.dumps(INDEX_SEED, indent=2),
                         "application/json", clips)
    return clips


def load_index(clips_id: str) -> tuple[dict, str]:
    fid = find_file("index.json", clips_id)
    if not fid:
        return INDEX_SEED.copy(), upload_text_file(
            "index.json", json.dumps(INDEX_SEED, indent=2),
            "application/json", clips_id,
        )
    try:
        text = gws_download_text(fid)
        return json.loads(text), fid
    except (json.JSONDecodeError, subprocess.CalledProcessError):
        # Corrupted — fall back to seed so we don't lose this run
        return INDEX_SEED.copy(), fid


def main() -> int:
    ap = argparse.ArgumentParser(description="Step 08 — upload run to gdrive")
    ap.add_argument("run_dir",       help="local run dir, e.g. ~/opensource/magnetx/output/yt-<id>")
    ap.add_argument("--video-id",    required=True)
    ap.add_argument("--youtube-url", required=True)
    ap.add_argument("--title",       required=True)
    ap.add_argument("--slug",        default=None,  help="default: slugify(title)")
    ap.add_argument("--content-type", default=None, help="commentary / podcast / ...")
    ap.add_argument("--density",      default=None, help="low / medium / high")
    ap.add_argument("--skip-verify-gate", action="store_true",
                    help="DANGEROUS: upload without checking verify_result.json. Use only for debugging.")
    args = ap.parse_args()

    run_dir = Path(args.run_dir).expanduser().resolve()
    if not run_dir.exists():
        print(f"ERROR: run dir not found: {run_dir}", file=sys.stderr); return 2

    transcript_path = next(iter((run_dir / "source").glob("*.transcript.json")), None)
    raw_path        = run_dir / "highlights.raw.json"
    top_path        = run_dir / "highlights.json"
    final_dir       = run_dir / "final"

    for p, label in [(transcript_path, "source/*.transcript.json"),
                     (raw_path, "highlights.raw.json"),
                     (top_path, "highlights.json"),
                     (final_dir, "final/")]:
        if p is None or not Path(p).exists():
            print(f"ERROR: missing artifact: {label}", file=sys.stderr); return 2

    final_clips = sorted(final_dir.glob("short_*.mp4"))
    if not final_clips:
        print(f"ERROR: no short_*.mp4 in {final_dir}", file=sys.stderr); return 2

    selected   = json.loads(top_path.read_text())["highlights"]
    transcript = json.loads(transcript_path.read_text())
    if len(selected) != len(final_clips):
        print(f"WARN: {len(selected)} highlights vs {len(final_clips)} clips — pairing by sorted order",
              file=sys.stderr)

    # ===== VERIFY GATE — every clip must have a verify_result.json with status=PASS =====
    if not args.skip_verify_gate:
        verify_results = []
        gate_fail = []
        for clip in final_clips:
            vr_path = clip.with_suffix(".verify_result.json")
            if not vr_path.exists():
                gate_fail.append(f"{clip.name}: missing {vr_path.name}")
                verify_results.append(None)
                continue
            try:
                vr = json.loads(vr_path.read_text())
            except json.JSONDecodeError as e:
                gate_fail.append(f"{clip.name}: malformed verify_result.json ({e})")
                verify_results.append(None)
                continue
            if vr.get("status") != "PASS":
                gate_fail.append(f"{clip.name}: status={vr.get('status', 'UNKNOWN')} — {vr.get('reason', '(no reason)')}")
            verify_results.append(vr)

        if gate_fail:
            print("ERROR: verify gate blocks upload — fix or override with --skip-verify-gate", file=sys.stderr)
            for f in gate_fail:
                print(f"  ✗ {f}", file=sys.stderr)
            return 3
        print(f"[upload] verify gate: PASS ({len(verify_results)}/{len(final_clips)} clips approved)", file=sys.stderr)
    else:
        print("[upload] WARN: verify gate skipped via --skip-verify-gate", file=sys.stderr)
        verify_results = [None] * len(final_clips)

    slug   = args.slug or slugify(args.title)
    date   = dt.datetime.utcnow().strftime("%Y-%m-%d")
    run_id = f"{date}_{args.video_id}_{slug}"

    for i, h in enumerate(selected):
        h["rank"]          = i + 1
        h["clip_filename"] = f"{h['rank']}_{int(h['score'])}_{slugify(h['title'], 40)}.mp4"

    # --- gdrive ops ---
    print(f"[upload] bootstrapping aksenHQ/clips/", file=sys.stderr)
    clips_root = bootstrap_clips_root()
    runs_id    = ensure_folder("runs", clips_root)
    run_folder = ensure_folder(run_id, runs_id)
    clips_sub  = ensure_folder("clips", run_folder)

    print(f"[upload] transcript.json", file=sys.stderr)
    upload_text_file("transcript.json", transcript_path.read_text(),
                     "application/json", run_folder)

    print(f"[upload] highlights.raw.json", file=sys.stderr)
    upload_text_file("highlights.raw.json", raw_path.read_text(),
                     "application/json", run_folder)

    for h, src, vr in zip(selected, final_clips, verify_results):
        print(f"[upload] clip {h['rank']}: {h['clip_filename']}", file=sys.stderr)
        existing = find_file(h["clip_filename"], clips_sub)
        fid = gws_upload(h["clip_filename"], src, "video/mp4", clips_sub, existing_id=existing)
        h["clip_gdrive_id"] = fid
        h["verify"] = {
            "status":       vr.get("status") if vr else "SKIPPED",
            "verifier":     vr.get("verifier") if vr else None,
            "verified_at":  vr.get("verified_at") if vr else None,
            "reason":       vr.get("reason") if vr else None,
        }

    manifest = {
        "video_id":         args.video_id,
        "youtube_url":      args.youtube_url,
        "title":            args.title,
        "duration_seconds": transcript.get("duration", 0),
        "content_type":     args.content_type,
        "density":          args.density,
        "created_at":       dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "gdrive_folder_id": run_folder,
        "highlights":       [
            {**h, "posted_to_x": False, "post_url": None, "posted_at": None}
            for h in selected
        ],
    }
    manifest_text = json.dumps(manifest, indent=2)
    print(f"[upload] manifest.json", file=sys.stderr)
    upload_text_file("manifest.json", manifest_text, "application/json", run_folder)
    (run_dir / "manifest.json").write_text(manifest_text, encoding="utf-8")

    print(f"[upload] updating index.json", file=sys.stderr)
    index_data, index_fid = load_index(clips_root)
    index_data["runs"] = [r for r in index_data.get("runs", []) if r.get("run_id") != run_id]
    index_data["runs"].append({
        "run_id":           run_id,
        "video_id":         args.video_id,
        "youtube_url":      args.youtube_url,
        "title":            args.title,
        "created_at":       manifest["created_at"],
        "gdrive_folder_id": run_folder,
        "n_clips":          len(selected),
        "posted_count":     0,
    })
    index_data["runs"].sort(key=lambda r: r.get("created_at", ""), reverse=True)
    tmp_idx = Path(f"/tmp/.gws_idx_{os.getpid()}.json")
    tmp_idx.write_text(json.dumps(index_data, indent=2), encoding="utf-8")
    try:
        gws_upload("index.json", tmp_idx, "application/json", clips_root, existing_id=index_fid)
    finally:
        tmp_idx.unlink(missing_ok=True)

    print(f"\n[upload] done")
    print(f"run_id:    {run_id}")
    print(f"gdrive:    https://drive.google.com/drive/folders/{run_folder}")
    print(f"manifest:  {run_dir / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
