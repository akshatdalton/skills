#!/usr/bin/env bash
# fetch_media.sh <tweet_url_or_id> <out_dir> — download an X native video to <out_dir>/<tid>.mp4
#
# X video requires browser auth: yt-dlp --cookies-from-browser chrome. Without it you get
# "Bad guest token". We select a single progressive mp4 (-f best[ext=mp4]/best) so no ffmpeg
# merge step is needed (brew ffmpeg is broken on this machine).
#
# Prints the mp4 path on stdout (only). Idempotent: skips download if the file already exists.
set -uo pipefail
URL="${1:?tweet url or id required}"; OUT="${2:?out dir required}"
BROWSER="${X_COOKIES_BROWSER:-chrome}"
mkdir -p "$OUT"
case "$URL" in
  http*) TID="${URL##*/}"; TID="${TID%%\?*}" ;;
  *)     TID="$URL"; URL="https://x.com/i/status/$TID" ;;
esac
DEST="$OUT/$TID.mp4"
if [ -s "$DEST" ]; then echo "$DEST"; exit 0; fi
yt-dlp --quiet --no-warnings --no-progress \
  --cookies-from-browser "$BROWSER" \
  -f "best[ext=mp4]/best" \
  -o "$DEST" "$URL" 1>&2 || { echo "DOWNLOAD_FAILED $TID" >&2; exit 1; }
[ -s "$DEST" ] && echo "$DEST" || { echo "DOWNLOAD_EMPTY $TID" >&2; exit 1; }
