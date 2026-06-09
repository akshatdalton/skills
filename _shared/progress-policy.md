# Shared progress.md mutation policy

> Single source of truth for per-ticket state across all engineering skills.
> Replaces the deprecated `~/.claude/work_hq/{board.json, update.py, today.json, needs_input.json, initiatives/}` stack.
> Linked from every skill that touches per-ticket state. See `~/.claude/scripts/progress_fm.py`.

## What progress.md is

The **canonical per-ticket artifact** at `~/opensource/vault/wiki/projects/{vscode,wipdp}/progress/<TICKET>/progress.md`.

The directory `progress/<TICKET>/` is the artifact **bundle** — also holds `plan.md` (from /think or /work-on-jira-task) and any other ticket-scoped files (design notes, screenshots, repro scripts). Don't invent new top-level stores for ticket-scoped content; drop new artifacts here.

## Frontmatter contract (machine state — read by /today, brain-recall, etc.)

```yaml
---
ticket: ENG-XXXXX            # required, immutable
title: "<one-line>"
project: vscode | wipdp      # required
branch: <git-branch> | null
pr: <number> | null
pr_state: OPEN | MERGED | CLOSED | null
state: new | implementing | in-review | merging | merged | abandoned
priority: P0 | P1 | P2 | null
bucket: today | backlog       # /today placement; default backlog
needs_input: <block or omit>  # ★ surfaces in /today when present
initiative: <slug> | null
created: YYYY-MM-DD
last-touched: YYYY-MM-DD      # auto-managed by progress_fm.py
session_ids: []               # brain-ingest writes
---
```

**`needs_input` shape** (when present):
```yaml
needs_input:
  reason: ci-failing | merge-conflict | judgment-call | ready-to-merge | group-3-design | group-5-external-actor | <other>
  action: "<one-line action verb>"
  added_at: <ISO-8601>
```

## Body contract (narrative + structured H2 sections)

Free-form markdown. Skills MAY append/prepend bullets to these conventional H2 sections via `progress_fm.py append-section` / `prepend-section`. Sections are created on first write.

| Section name | Idiom | Writers |
|---|---|---|
| `## Jira summary` | What the ticket asks for | seeded by /work-on-jira-task |
| `## Decision` (or `## Decision (locked)`) | Locked-in design choices | /think, brain-ingest, human |
| `## Status` | Current state in prose | brain-ingest |
| `## Files of interest` | Append-only list of touched paths | /work-on-jira-task on every materially-edited file |
| `## Checkpoints` | **Prepend** newest-first | /checkpoint |
| `## Decisions (migrated)` | One-time landing zone from board.json | progress_fm.py migrate |
| `## Session <id> (<date>) — <one-line>` | Per-session distillation block | brain-ingest (only writer) |
| `## Key references` | Important file paths, PRs, related tickets | brain-ingest, human |

**Body-write rule:** skills mid-flow may call `progress_fm.py append-section` (or `prepend-section` for newest-first idioms like Checkpoints) — these are convenience appends. **Brain-ingest remains the only writer of `## Session <id>` blocks** (per its own SKILL.md contract). Other sections are append-friendly.

## The CLI surface (use this, never the file directly)

```bash
# Read
~/.claude/scripts/progress_fm.py get <TICKET> [--field <name>]
~/.claude/scripts/progress_fm.py list [--filter state=todo,bucket=today] [--include-archived]

# Frontmatter mutate
~/.claude/scripts/progress_fm.py set <TICKET> --field state=in-review --field pr=12345
~/.claude/scripts/progress_fm.py needs-input add <TICKET> --reason ci-failing --action "fix CI on PR #12345"
~/.claude/scripts/progress_fm.py needs-input clear <TICKET>
~/.claude/scripts/progress_fm.py bucket set <TICKET> --to today

# Body H2 section ops
~/.claude/scripts/progress_fm.py append-section <TICKET> --section "Files of interest" --line "src/foo.py"
~/.claude/scripts/progress_fm.py prepend-section <TICKET> --section "Checkpoints" --line "2026-05-31 14:32 phase=ci-watch | next=address review | waiting=external CI"
```

`last-touched` is auto-updated to today's date on every mutation. Body is preserved byte-for-byte except in the targeted section.

## Anti-patterns (don't do these)

- ❌ Direct `Edit` / `Write` of progress.md from a skill — use `progress_fm.py` so the contract stays consistent.
- ❌ Writing per-ticket state outside `progress/<TICKET>/` — no new top-level stores.
- ❌ Reading entire progress.md body just to extract a frontmatter field — use `progress_fm.py get --field <name>` (cheap awk-then-yaml-parse).
- ❌ Inventing new frontmatter keys without updating this doc.
- ❌ Writing `## Session <id>` blocks outside of brain-ingest.
- ❌ Reading or writing any `~/.claude/work_hq/*` path — the directory is being retired in this initiative. If you see one, fail loudly.

## Migration from board.json (one-time, this initiative only)

`progress_fm.py migrate --dry-run` reads the legacy `~/.claude/work_hq/board.json` and plans:
- Frontmatter set: `state`, `branch`, `pr`, `pr_state`, `priority`, `initiative`, `bucket`, `ci_state`, `review_state`, `watcher_session_id`
- `needs_input` attach (from board.json's top-level or shared_context.needs_input)
- Body `## Files of interest` appends from `shared_context.files_of_interest[]`
- Body `## Checkpoints` prepends from `shared_context.checkpoints[]`
- Body `## Decisions (migrated)` appends from `shared_context.decisions[]`

Audit the diff per ticket, then `--apply`. After apply, board.json is deletable.
