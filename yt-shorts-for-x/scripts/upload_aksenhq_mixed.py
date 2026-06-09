#!/usr/bin/env python3
"""One-off uploader: 10 mp4 clips + 3 text files -> personal Google Drive.

Reuses the WORKING, tested gws-personal CLI helpers from 09_upload.py verbatim.
Idempotent: reuses existing folders/files by name (same fileIds on re-run).
Uploads only — never touches sharing or permissions.

Folder chain (under My Drive root):
    aksenHQ / clips / runs / 2026-05-29_aksenhq-mixed / clips

- 10 mp4s -> inner clips/ folder
- 3 text files -> run folder "2026-05-29_aksenhq-mixed" (NOT inner clips/)
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional


# ---- gws-personal CLI config (verbatim from 09_upload.py) ------------------
GWS_BIN = shutil.which("gws") or "/opt/homebrew/bin/gws"
GWS_CONFIG_DIR = "/Users/akshat.v/.config/gws-personal"
GWS_ENV = {**os.environ, "GOOGLE_WORKSPACE_CLI_CONFIG_DIR": GWS_CONFIG_DIR}


# ---- gws-personal CLI wrappers (verbatim from 09_upload.py) ----------------

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


# ---- helpers (verbatim from 09_upload.py) ----------------------------------

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


# ---- this job --------------------------------------------------------------

CLIPS_SRC_DIR = Path("/Users/akshat.v/.claude/skills/yt-shorts-for-x/output/run_2026-05-29/final")
MP4_NAMES = [
    "lb_actionapps.mp4",
    "m_empti.mp4",
    "g_digitalemployee.mp4",
    "lb_creator.mp4",
    "m_mediaempire.mp4",
    "greg_06.mp4",
    "lb_triathlon.mp4",
    "g_unpolished.mp4",
    "lb_aimedia.mp4",
    "g_niche.mp4",
]

# Text files -> run folder (NOT inner clips/). (local_path, drive_name, mime)
TEXT_FILES = [
    (Path("/Users/akshat.v/.claude/skills/yt-shorts-for-x/output/run_2026-05-29/final_selection.json"),
     "final_selection.json", "application/json"),
    (Path("/Users/akshat.v/.claude/skills/yt-shorts-for-x/output/run_2026-05-29/copy_drafts.md"),
     "copy_drafts.md", "text/markdown"),
    (Path("/Users/akshat.v/Documents/Claude/x_clips/POST_KIT.md"),
     "POST_KIT.md", "text/markdown"),
]


def main() -> int:
    # ---- preflight: confirm every source file exists before any upload ----
    missing = []
    for name in MP4_NAMES:
        if not (CLIPS_SRC_DIR / name).is_file():
            missing.append(str(CLIPS_SRC_DIR / name))
    for local_path, _, _ in TEXT_FILES:
        if not local_path.is_file():
            missing.append(str(local_path))
    if missing:
        print("ERROR: source file(s) not found:", file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)
        return 2

    results: list[tuple[str, str]] = []  # (drive_name, fileId)

    # ---- build idempotent folder chain ----
    print("[chain] aksenHQ", file=sys.stderr)
    aksenhq = ensure_folder("aksenHQ", None)
    print(f"        aksenHQ id={aksenhq}", file=sys.stderr)

    print("[chain] aksenHQ/clips", file=sys.stderr)
    clips = ensure_folder("clips", aksenhq)

    print("[chain] aksenHQ/clips/runs", file=sys.stderr)
    runs = ensure_folder("runs", clips)

    print("[chain] aksenHQ/clips/runs/2026-05-29_aksenhq-mixed", file=sys.stderr)
    run_folder = ensure_folder("2026-05-29_aksenhq-mixed", runs)

    print("[chain] .../2026-05-29_aksenhq-mixed/clips", file=sys.stderr)
    inner_clips = ensure_folder("clips", run_folder)

    # ---- upload 10 mp4s into inner clips/ ----
    for name in MP4_NAMES:
        src = CLIPS_SRC_DIR / name
        existing = find_file(name, inner_clips)
        fid = gws_upload(name, src, "video/mp4", inner_clips, existing_id=existing)
        verb = "updated" if existing else "created"
        print(f"[mp4] {verb} {name} -> {fid}", file=sys.stderr)
        results.append((name, fid))

    # ---- upload 3 text files into run folder ----
    for local_path, drive_name, mime in TEXT_FILES:
        existing = find_file(drive_name, run_folder)
        fid = gws_upload(drive_name, local_path, mime, run_folder, existing_id=existing)
        verb = "updated" if existing else "created"
        print(f"[txt] {verb} {drive_name} ({mime}) -> {fid}", file=sys.stderr)
        results.append((drive_name, fid))

    # ---- report ----
    run_url = f"https://drive.google.com/drive/folders/{run_folder}"
    print("\n=== RESULT (machine-readable) ===")
    print(json.dumps({
        "run_folder_id": run_folder,
        "run_folder_url": run_url,
        "inner_clips_id": inner_clips,
        "uploads": [{"filename": n, "fileId": f} for n, f in results],
    }, indent=2))
    print(f"\nRUN_FOLDER_URL: {run_url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
