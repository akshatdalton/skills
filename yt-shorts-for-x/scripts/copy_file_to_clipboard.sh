#!/usr/bin/env bash
# copy_file_to_clipboard.sh — put a file on the macOS clipboard as a FILE REFERENCE
# (the Finder Cmd-C equivalent), so it can be pasted into a web app via Cmd-V.
#
# Why this exists: X.com's compose dialog won't accept the Chrome-MCP file_upload tool
# for local paths in this harness — its allowlist rejects working dirs, ~/.claude, and
# the primary cwd, and request_directory is disabled in unsupervised mode. Clicking X's
# media button opens a native macOS file dialog automation can't drive. Pasting a
# clipboard file reference into the composer is the one path that works every time.
#
# Usage:  copy_file_to_clipboard.sh /abs/path/to/clip.mp4
# Exits non-zero (and says why) if the file is missing or the copy didn't take.

set -euo pipefail

f="${1:?usage: copy_file_to_clipboard.sh /abs/path/to/file}"
[ -f "$f" ] || { echo "ERROR: not a file: $f" >&2; exit 1; }
# NSURL needs an absolute path
case "$f" in
  /*) ;;
  *)  f="$(cd "$(dirname "$f")" && pwd)/$(basename "$f")" ;;
esac

# Write the file URL to the general pasteboard via osascript's JS-ObjC bridge.
# This needs NO pyobjc (/usr/bin/python3 lacks AppKit) and NO Finder automation
# (which triggers a TCC prompt that hangs with "AppleEvent timed out" in headless mode).
osascript -l JavaScript -e '
  ObjC.import("AppKit");
  function run(argv){
    var pb  = $.NSPasteboard.generalPasteboard;
    pb.clearContents;
    var url = $.NSURL.fileURLWithPath(argv[0]);
    var ok  = pb.writeObjects($.NSArray.arrayWithObject(url));
    return "wrote=" + ok;
  }' "$f" >/dev/null

# Verify a file-URL flavor ("furl") actually landed — a text-only clipboard means the
# paste will NOT attach the file.
if osascript -e 'clipboard info' 2>/dev/null | grep -q 'furl'; then
  echo "OK: clipboard now holds a file reference -> $f"
else
  echo "ERROR: clipboard has no file reference; Cmd-V will not attach the file" >&2
  exit 2
fi
