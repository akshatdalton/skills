#!/usr/bin/env python3
"""Step 01 — Download a YouTube video to a local mp4.

Contract:
    in:  youtube_url (or file:// URL, or local file path)
    out: prints local mp4 path to stdout

Decoupled: no imports from other steps. Caches by YouTube video_id.

Usage:
    python 01_download.py <url> [--out-dir output] [--format 720]
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


def _extract_video_id(source: str):
    parsed = urlparse(source)
    host = (parsed.netloc or "").lower().removeprefix("www.")
    if host in ("youtu.be",):
        return (parsed.path.lstrip("/").split("/", 1)[0]) or None
    if "youtube.com" in host:
        if parsed.path.startswith("/watch"):
            return parse_qs(parsed.query).get("v", [""])[0] or None
        m = re.search(r"/(?:shorts|embed|live)/([^/?#&]+)", parsed.path)
        if m:
            return m.group(1)
    return None


def _resolve_local(source: str):
    parsed = urlparse(source)
    if parsed.scheme == "file":
        raw = unquote(parsed.path)
        if parsed.netloc and parsed.netloc not in ("", "localhost"):
            raw = f"//{parsed.netloc}{raw}"
        p = Path(raw).expanduser()
        if p.exists() and p.is_file():
            return str(p.resolve())
        raise SystemExit(f"file:// URL does not exist: {source}")
    if parsed.scheme in ("http", "https"):
        return None
    p = Path(source).expanduser()
    if p.exists() and p.is_file():
        return str(p.resolve())
    if any(sep in source for sep in (os.sep, "/")) or source.startswith(("~", ".")):
        raise SystemExit(f"local path does not exist: {source}")
    return None


def _format_selector(fmt: str) -> str:
    try:
        h = int(fmt)
    except ValueError:
        h = 720
    return f"bestvideo[height<={h}][ext=mp4]+bestaudio[ext=m4a]/best[height<={h}][ext=mp4]/best"


def main() -> int:
    ap = argparse.ArgumentParser(description="Step 01 — download")
    ap.add_argument("url", help="YouTube URL, file:// URL, or local path")
    ap.add_argument("--out-dir", default="output", help="cache directory (default: output)")
    ap.add_argument("--format", default="720", help="max height: 360/480/720/1080 (default: 720)")
    args = ap.parse_args()

    if local := _resolve_local(args.url):
        print(local)
        return 0

    try:
        import yt_dlp
    except ImportError:
        print("ERROR: yt-dlp not installed. Run scripts/setup.sh first.", file=sys.stderr)
        return 2

    os.makedirs(args.out_dir, exist_ok=True)
    vid = _extract_video_id(args.url)
    if vid:
        for ext in (".mp4", ".mkv", ".webm"):
            cached = Path(args.out_dir) / f"source_{vid}{ext}"
            if cached.exists():
                print(str(cached.resolve()))
                return 0

    print(f"[download] {args.url} @ {args.format}p", file=sys.stderr)
    ffmpeg_bin = os.environ.get("FFMPEG_BIN", "/Applications/meetily.app/Contents/MacOS/ffmpeg")
    ydl_opts = {
        "format": _format_selector(args.format),
        "outtmpl": os.path.join(args.out_dir, "source_%(id)s.%(ext)s"),
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
    }
    if os.path.isfile(ffmpeg_bin) and os.access(ffmpeg_bin, os.X_OK):
        ydl_opts["ffmpeg_location"] = ffmpeg_bin
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(args.url, download=True)
        path = ydl.prepare_filename(info)
        if not os.path.exists(path):
            stem, _ = os.path.splitext(path)
            for ext in (".mp4", ".mkv", ".webm"):
                if os.path.exists(stem + ext):
                    path = stem + ext
                    break

    print(str(Path(path).resolve()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
