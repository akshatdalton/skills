#!/usr/bin/env bash
# transcribe.sh <wav> [out_txt] — transcribe a 16 kHz wav with Meetily's whisper.cpp
# large-v3-turbo (Metal). Prints the transcript path on stdout (only).
# Env overrides: WHISPER_CLI, WHISPER_MODEL.
set -uo pipefail
WAV="${1:?wav required}"
OUT="${2:-${WAV%.wav}.txt}"
WCLI="${WHISPER_CLI:-$HOME/opensource/meetily/backend/whisper.cpp/build/bin/whisper-cli}"
WMODEL="${WHISPER_MODEL:-$HOME/Library/Application Support/meetily-rec/models/ggml-large-v3-turbo.bin}"
[ -x "$WCLI" ]   || { echo "MISSING whisper-cli: $WCLI" >&2; exit 1; }
[ -f "$WMODEL" ] || { echo "MISSING model: $WMODEL" >&2; exit 1; }
[ -s "$WAV" ]    || { echo "MISSING/empty wav: $WAV" >&2; exit 1; }
OF="${OUT%.txt}"   # whisper -of wants the path WITHOUT extension; it appends .txt
# whisper prints the transcript to stdout too — redirect to stderr so our stdout is just the path.
"$WCLI" -m "$WMODEL" -f "$WAV" -otxt -of "$OF" -nt 1>&2 || { echo "WHISPER_FAILED" >&2; exit 1; }
[ -s "$OUT" ] && echo "$OUT" || { echo "TRANSCRIPT_EMPTY" >&2; exit 1; }
