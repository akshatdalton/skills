---
name: search-history
description: >
  Search past Claude Code conversation sessions using vague hints.
  Trigger when user says "find that chat where...", "search my history for...",
  "remember when we did X", asks to locate a past session, or asks about
  activity in a date range ("what did I work on last week?", "show sessions from May 10-17").
---

# Search Chat History

## CRITICAL: Always use extract_transcripts.py

**NEVER grep `~/.claude/history.jsonl` directly.** That file only indexes CLI sessions and
misses all desktop app sessions. The authoritative source is:

```
~/.claude/scripts/extract_transcripts.py
```

Use it for every mode below without exception.

---

## Mode Selection

| User intent | Mode |
|---|---|
| Date range / activity overview | **Date Range** |
| "find that chat where..." / keyword | **Keyword Search** |
| "show full transcript of session X" | **Full Transcript** |
| "current-id" | **Current Session ID** |

---

## Date Range Mode

For: "what did I work on this week?", "show sessions May 10–17", "last 3 days", etc.

### Step 1 — Run summary

```bash
python3 ~/.claude/scripts/extract_transcripts.py \
  --from "FROM_DATE" \
  --to "TO_DATE" \
  --format summary
```

Accepted date formats: `"2026-05-10"`, `"7 days ago"`, `"last monday"`, `"yesterday"`, `"today"`.
Omit `--to` to default to now. Add `--project NAME` to scope to one project.

Examples:
```bash
python3 ~/.claude/scripts/extract_transcripts.py --from "last monday" --to "today" --format summary
python3 ~/.claude/scripts/extract_transcripts.py --from "2026-05-10" --to "2026-05-17" --format summary
python3 ~/.claude/scripts/extract_transcripts.py --from "7 days ago" --project magnetx --format summary
```

### Step 2 — Present grouped by project

```
## Activity: [date range]

### ~/opensource/magnetx  (3 sessions)
- 2026-05-16 · abc123… · 61u/121a turns · "can you fetch: ..."
- ...

### ~/eightfold/wipdp  (8 sessions)
- ...

### Themes
- [what was worked on, decisions, tickets]
```

### Step 3 — Offer git cross-reference

Offer: *"Check `git log --author=Akshat --since=DATE` for commits not in chat?"*

---

## Keyword Search Mode

For: "find that chat where...", "remember when we did X", "session about topic Y".

### Step 1 — Run summary over a wide window, then grep the JSONL files

```bash
# Get candidate sessions
python3 ~/.claude/scripts/extract_transcripts.py \
  --from "30 days ago" --format summary 2>&1 | grep -i "KEYWORD"
```

If that surfaces candidates, note their session IDs. Then grep the raw JSONL for precision:

```bash
grep -ril "KEYWORD" ~/.claude/projects/ --include="*.jsonl" | grep -v subagents
```

### Step 2 — Extract full transcript of matching session

```bash
python3 ~/.claude/scripts/extract_transcripts.py \
  --session SESSION_UUID_PREFIX \
  --format markdown
```

### Step 3 — Present

- **Session ID** + **date** + **project**
- **Summary**: what was debugged/built/decided
- Key messages in order
- Group duplicates by topic

---

## Full Transcript Mode

For: "show me the full transcript of session X" or analyzing a specific session.

```bash
# Readable
python3 ~/.claude/scripts/extract_transcripts.py \
  --session SESSION_UUID_PREFIX \
  --format markdown

# Structured (for analysis / training data)
python3 ~/.claude/scripts/extract_transcripts.py \
  --session SESSION_UUID_PREFIX \
  --format jsonl
```

To export a date range to files:
```bash
python3 ~/.claude/scripts/extract_transcripts.py \
  --from "2026-05-10" --to "2026-05-17" \
  --format jsonl \
  --out ~/transcripts/
```

---

## Current Session ID Mode

For `/search-history current-id`.

```bash
python3 -c "
import os
from pathlib import Path
project = os.getcwd()
proj_dir = project.replace('/', '-').lstrip('-')
p = Path.home() / '.claude' / 'projects' / proj_dir
if p.exists():
    files = sorted([f for f in p.glob('*.jsonl') if 'subagents' not in str(f)],
                   key=lambda x: x.stat().st_mtime, reverse=True)
    if files:
        print(files[0].stem)
"
```

Print the session ID and the project it matched. Show last user message to confirm.

---

## Limitations

- Thinking block content is not stored (empty in JSONL) — not recoverable
- Sessions auto-delete after 30 days (set `cleanupPeriodDays` in `~/.claude/settings.json` to extend)
- `history.jsonl` — do not use, incomplete

---

## Workflow ending

After presenting results, offer: *"Want me to export these sessions as JSONL for training data?"*
