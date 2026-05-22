---
name: yt-shorts-for-x
description: Use when the user wants short vertical X/Twitter clips from a YouTube video or local mp4. Triggers on "make X clips from this video", "extract viral shorts from this YouTube link", "turn this podcast into X-ready clips", "find best moments for posting on X", or a YouTube URL paired with intent to post on X.
---

# yt-shorts-for-x

End-to-end workflow that turns a YouTube URL (or local mp4) into N captioned 9:16 clips ready to post on X. Claude is the orchestrator AND the LLM brain — every LLM-bound step runs in this conversation; every deterministic step is a Bash call to one of the scripts in `scripts/`.

## When to use

- "Make 3 X clips from `<youtube url>`"
- "Find the best 60-second moments in this podcast and crop them for X"
- "Turn this interview into 9:16 clips with captions"

**Don't use** for: full-video summarization, thumbnails, transcription-only, or non-vertical output. Use `gemini-youtube` MCP for plain summarization.

## Workflow contract — decoupled, file-based

Every step reads files and writes files. No step depends on another's in-memory state, so any step can be swapped or skipped without breaking adjacent steps.

| # | Step | Tool | In | Out |
|---|---|---|---|---|
| 00 | Setup | `bash scripts/setup.sh` (one-time) | — | `.venv` + BlazeFace model + deps |
| 01 | Download | `01_download.py <url>` | YouTube URL | local mp4 path (stdout) |
| 02 | Transcribe | `02_transcribe.py <mp4>` | mp4 | `<mp4>.transcript.json`, `<mp4>.srt` |
| 03 | Chunk (long videos) | `03_chunk.py <transcript.json>` | transcript JSON | chunk-JSON paths |
| **04** | **Classify + rank** | **Claude (in-context)** | transcript or chunk JSON | `highlights.raw.json` (≥ 2×N candidates) |
| 05 | Dedupe + top-N | `04_dedupe.py <raw.json> --top N` | raw highlights | `highlights.json` (top-N deduped) |
| 06 | Cut + scene-aware crop | `05_clip.py <mp4> --start S --end E --out <p>` | mp4 + interval | 9:16 mp4 + `<p>.scenes.json` sidecar |
| 07 | Burn captions | `06_caption.py <clip> --transcript <t.json> --clip-start S --clip-end E --out <p>` | clip + transcript | captioned mp4 |
| **08a** | **Auto jitter scan** | `08_verify.py <captioned_clip>` | captioned clip | `<clip>.verify.json` + review frames |
| **08b** | **Vision gate (Claude)** | **Claude (in-context)** | review frames | `<clip>.verify_result.json` with status PASS/REJECT |
| **09** | **Upload to gdrive** | `09_upload.py <run_dir> ...` (refuses without all PASS) | run dir + metadata | gdrive folder URL + manifest |
| 10 | Report | Claude reports to user | manifest + verify results | ranked list with gdrive URLs |

**Step 08 is a HARD GATE.** Step 09 refuses to upload any clip whose `<clip>.verify_result.json` doesn't exist or doesn't say `status: PASS`. Override only with `--skip-verify-gate` for debugging.

**Other skipping:** drop 03 if duration < 30 min. Drop 07 only if you want raw uncaptioned clips (you'll also need to skip 08 — verify expects captions burned in).

## Step 06 — Scene-aware crop (the Level B engine)

`05_clip.py` does three passes:
1. **PySceneDetect** finds scene boundaries inside the cut clip
2. **MediaPipe BlazeFace** detects faces on every frame (with top/bottom blackout if specified)
3. **Per-shot decision**: if speaker movement variance < deadband, **lock crop on median face position** (stationary mode); else smoothed + deadbanded tracking. Tracker state RESETS at every cut — never chase across one.

Emits a `<clip>.scenes.json` sidecar so step 08 knows where natural motion is expected.

**Key flags** (already proven on CNBC content):
- `--blackout-bottom 0.28` — masks lower-third graphics (tickers, banners)
- `--smoothing 0.06` — chase rate per frame
- `--deadband 24` — pixels of face shift before crop moves
- `--scene-threshold 27` — PySceneDetect content detector threshold (lower = more sensitive)
- `--stationary-mode auto` — auto-decide per shot (override `on`/`off` for forcing)

## Step 04 — Classify + rank (Claude does this in-context)

Read the transcript JSON. Note the content type (podcast / interview / tutorial / lecture / commentary / debate / vlog / other) and density (low / medium / high). Then rank highlights using this framework:

**Virality signals — ranked by impact:**
1. **HOOK MOMENTS** — statements that create immediate curiosity ("The secret is...", "Nobody talks about...", "I was completely wrong about...")
2. **EMOTIONAL PEAKS** — genuine surprise, laughter, anger, vulnerability, excitement; raw unscripted reactions
3. **OPINION BOMBS** — strong, polarizing, or counter-intuitive statements that trigger agree/disagree
4. **REVELATION MOMENTS** — surprising facts, stats, or confessions that reframe how the viewer thinks
5. **CONFLICT/TENSION** — disagreement, pushback, or a problem confronted head-on
6. **QUOTABLE ONE-LINERS** — a sentence that works as a standalone quote card
7. **STORY PEAKS** — the climax or twist of an anecdote; the payoff moment
8. **PRACTICAL VALUE** — a concrete tip, hack, or insight the viewer can immediately apply

**Rules:**
- Every highlight must open with a strong HOOK — a line that grabs attention within the first 3 seconds
- Duration sweet spot: **45–90 seconds**. Shorter (20–44s) only for a perfect one-liner. Longer (91–140s) only when a story arc needs full context to land.
- **Hard cap: 140 seconds** (X free tier video limit — never exceed).
- Never cut mid-sentence — each clip must feel complete.
- Score 0–100 on viral potential, NOT general quality.
- Aim for ~2× the user's `num_clips` target so dedupe has headroom (e.g. 6 candidates for `num_clips=3`).
- Each highlight: identify the single best `hook_sentence` (the opening line) and a one-sentence `virality_reason`.

**Output:** write to `output/highlights.json` with this exact shape:

```json
{
  "highlights": [
    {
      "title": "The one mistake that cost me $50K",
      "start_time": 124.3,
      "end_time": 187.6,
      "score": 92,
      "hook_sentence": "Nobody talks about this, but it killed my first startup...",
      "virality_reason": "Opens with a number + regret, peaks on a contrarian lesson"
    }
  ]
}
```

For long videos: run step 03 first, rank each chunk separately, add the chunk's `_offset` to every `start_time`/`end_time` before merging, then pass the merged file to step 05.

## Step 08 — Verify (mandatory two-stage gate)

### 08a — Automated jitter scan

`08_verify.py <captioned_clip.mp4>` runs:
1. Loads scene boundaries from the `<clip>.scenes.json` sidecar
2. Computes mean optical flow magnitude per 0.5s window (Farneback, downsampled)
3. Flags windows whose flow exceeds threshold AND aren't near a known scene cut
4. Extracts strategic review frames at:
   - `t = 0.5s` (opening) · `t = duration/2` (mid) · `t = duration − 0.5s` (closing)
   - `t = cut ± 0.3s` for each scene boundary
   - `t = window_mid` for each flagged suspicious window
5. Writes `<clip>.verify.json` with scores + frame paths

### 08b — Claude vision gate (this is YOU)

You (Claude) MUST:
1. Read every review frame from `<clip>.verify.json`
2. Score each frame on:
   - Face centered horizontally? Head + shoulders fully visible?
   - Captions readable, not clipped, not mid-word?
   - Anything unwanted (news ticker, banner edges, logos)?
3. Cross-frame check: within the same shot, is framing consistent? At scene cuts, is the change expected (different speaker / camera angle) and clean?
4. Write `<clip>.verify_result.json` with this shape:

```json
{
  "status": "PASS" | "REJECT",
  "verified_at": "ISO-8601 Z",
  "verifier": "claude-vision",
  "clip": "short_NN_slug.mp4",
  "frames_checked": N,
  "per_frame": [
    {"label": "opening", "t": 0.5, "speaker": "...", "centered": true,
     "head_visible": true, "captions_clean": true, "issues": []}
  ],
  "cross_frame_check": {
    "consistent_within_speaker_segments": true,
    "scene_cuts_handled_cleanly": true,
    "notes": "..."
  },
  "reason": "PASS — short human-readable summary"
}
```

**PASS criteria (all must hold):**
- Every individual frame: face centered, head/shoulders visible, captions clean, no unwanted overlays
- Cross-frame: speaker stays consistently framed within a shot; scene cuts produce expected (not chase) framing changes

**On REJECT:** the orchestrator decides next move — re-cut with stricter settings (`--smoothing 0.03 --deadband 36`), re-rank with a tighter start/end, or skip this highlight. Re-run 08a + 08b on the new output.

## Step 09 — Upload to gdrive (gated on PASS)

After step 08 produces a PASS verdict per clip, upload to `aksenHQ/clips/` in gdrive. The script (`09_upload.py`) handles bootstrap (README.md + CLAUDE.md + index.json on first run), is idempotent, and **refuses to upload any clip without a `verify_result.json` status=PASS**.

```bash
.venv/bin/python scripts/09_upload.py <run_dir> \
    --video-id     <youtube_id> \
    --youtube-url  <full_url> \
    --title        "<human-readable title>" \
    --slug         <kebab-slug>        # optional, default = slugify(title)
    --content-type <commentary|podcast|interview|tutorial|lecture|debate|vlog|other> \
    --density      <low|medium|high>
    # --skip-verify-gate  ← DANGEROUS, debugging only
```

**Gdrive layout:**

```
aksenHQ/clips/
├── README.md                         ← human description (do not auto-overwrite)
├── CLAUDE.md                         ← LLM ops context — READ THIS WHEN TOUCHING PAST RUNS
├── index.json                        ← master catalogue
└── runs/<YYYY-MM-DD>_<video_id>_<slug>/
    ├── manifest.json                 ← per-run source of truth
    ├── transcript.json
    ├── highlights.raw.json
    └── clips/<rank>_<score>_<slug>.mp4
```

**Looking up past runs:** read `aksenHQ/clips/CLAUDE.md` (lives in gdrive itself) → it documents the index schema, manifest schema, and how to mark clips as posted. The skill stays thin; the operational context lives next to the data.

**To look up a past run from this skill:** download `aksenHQ/clips/index.json`, grep by video_id / title / date, then fetch `runs/<run_id>/manifest.json` for clip details + gdrive fileIds.

## Step 10 — Reporting back

Show the user a ranked table: `#  score  start→end  title  hook  gdrive_clip_url`. Include the run's gdrive folder URL at the top so they can open the whole bundle. Skip the transcript unless asked. Surface failures verbatim — never claim success for a clip whose ffmpeg or upload returned non-zero, or whose verify was REJECT.

## Tunable knobs

- `num_clips` — how many to keep after dedupe (default: 3)
- `aspect` — `9:16` (default), `1:1`, `4:5`
- `--format` on step 01 — source resolution (`360`/`480`/`720`/`1080`)
- `--model` on step 02 — `tiny` / `base` (default) / `small` / `medium` / `large-v3`
- `--style` on step 06 — libass force_style string for caption appearance
- `FFMPEG_BIN` env — defaults to `/Applications/meetily.app/Contents/MacOS/ffmpeg` (system Homebrew ffmpeg is broken on this machine)

## Failure modes — handle, don't paper over

- **Whisper produced zero segments** → likely no detectable speech or wrong language. Retry step 02 with `--language en` (or correct ISO-639-1).
- **ffmpeg "Library not loaded: libx265"** → Homebrew ffmpeg is broken. The scripts default to Meetily's bundled binary; only hit this if `FFMPEG_BIN` is overridden.
- **OpenCV finds no faces** → script falls back to centred crop. If clips look off, re-run with a wider `--aspect` (e.g. `4:5`).
- **Highlight ranker returned < num_clips after dedupe** → show what survived, don't pad with low-score filler.

## Done criteria

- Every clip has `<clip>.verify_result.json` with `status: PASS` written by Claude
- N captioned 9:16 mp4s uploaded to `aksenHQ/clips/runs/<run_id>/clips/` in gdrive
- `manifest.json` (with verify status per clip) in gdrive + local cache at `<run_dir>/manifest.json`
- `index.json` in gdrive includes the new run entry (idempotent on re-run)
- Each clip shown to the user with `score`, `hook_sentence`, `virality_reason`, gdrive URL, verify status
- No silently-failed clips, uploads, or REJECTed clips reaching gdrive
