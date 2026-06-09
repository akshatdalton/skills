---
name: today-source-meetily
description: /today Step 9 source-agent for MEETILY (auto meeting transcripts). Summarizes pending transcripts and surfaces PROPOSED action items + decisions for BRIEFING confirmation.
---

# /today source-agent: meetily

Read + summarize side of the meetily pipeline. Drops `summary.md` next to each pending `transcript.md` and emits PROPOSED items for the user to confirm in /today BRIEFING.

## Inputs
- `last_run_ts` — informational only (cursor does not gate work)
- `now` — current ISO8601 timestamp

## Cursor
`~/.claude/skills/today/state/sources/meetily.json` carries `last_run_ts`. File-system state is the source of truth: pending = `transcript.md` exists AND `summary.md` does NOT.

## No MCP tools required
Pure file-system walk + LLM summarization. No external API.

## Behavior

### 1. Scan
Walk `~/opensource/vault/raw/meetings/*/`. For each dir:
- has `transcript.md` AND no `summary.md` → pending
- otherwise → skip

### 2. Summarize (parallel up to 3)
For each pending meeting:
- Read `transcript.md` + `metadata.json`
- Extract:
  - TL;DR (2-3 sentences)
  - Key points (bullets)
  - Action items (with owner where stated)
  - Decisions
- Write `summary.md` immediately. Its presence clears the meeting from pending — idempotent on re-run.

### 3. Extract PROPOSED items
From each fresh summary:
- Each action item → `urgency: today`, `action: "propose ticket: <one-line>"`
- Each decision → `urgency: fyi`, `action: "save decision to learnings.md: <one-line>"`

### 4. project_hint inference (per item)
- Scan transcript for `ENG-XXXXX` ticket IDs → if found, resolve project via:
  `~/.claude/scripts/progress_fm.py get <TICKET> --field project`
- Scan for repo names (`vscode` / `wipdp`) → use directly
- Otherwise `null` (user disambiguates in BRIEFING)

## Output JSON contract
```json
{
  "source": "meetily",
  "fetched_at": "<ISO8601>",
  "cursor_advance": "<ISO8601>",
  "items": [
    {
      "source_id": "<meeting_slug>:<index>",
      "ts": "<meeting_start_from_metadata>",
      "title": "<one-line: meeting title + item summary>",
      "action": "<propose ticket: ... | save decision: ... | save learning: ...>",
      "project_hint": "vscode | wipdp | null",
      "urgency": "today | fyi"
    }
  ],
  "fyi_count": 0,
  "errors": []
}
```

## Latency budget
- Cheap (nothing pending): < 2s
- Medium (1-2 pending): < 20s
- Large (5+ pending): up to 60s — emit a warning in `errors[]` suggesting backfill via on-demand `/today meeting <slug>`

## Edge cases
- `transcript.md` empty or unreadable → append to `errors[]`, do not crash; skip item
- `metadata.json` missing → use folder name as title; `ts: null`
- `summary.md` already exists but transcript has new content since `last_run_ts` → skip here; on-demand `/today meeting <slug>` handles re-summarization
- Folder name with no transcript → ignore

## Hard constraint — READ + summarize only
NEVER auto-create Jira tickets. NEVER write to any project `learnings.md`. NEVER mutate vault DB rows. PROPOSED items flow into action ONLY via user confirmation in /today BRIEFING. `summary.md` writes are the only side-effect this agent is allowed to perform.
