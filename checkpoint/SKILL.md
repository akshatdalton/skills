---
name: checkpoint
description: Snapshot active strategy, last action, next step, and open threads into the current task's progress.md. Designed to make a fresh session productive in 30 seconds. Use when user types /checkpoint, OR when the PreToolUse hook surfaces "Context at X% — run /checkpoint" reminder, OR before any major hand-off (switching branches, ending session, before compaction). Manual invocation always works.
---

> For all per-ticket state mutations, see [shared progress policy](/Users/akshat.v/.claude/skills/_shared/progress-policy.md).

# Checkpoint

Append a snapshot of the active state into the current task's progress.md. The next session loading the task via `progress_fm.py get <TICKET_ID>` sees the latest checkpoint and is productive immediately — no need to re-derive what was happening.

## When invoked

- **Manual**: `/checkpoint` from user, or you decide to checkpoint at a logical hand-off point.
- **Auto from hook**: PreToolUse hook injects a system reminder when context ≥78% AND last checkpoint >5 min ago. When you see that reminder, invoke this skill via `Skill(skill="checkpoint")`.

## Storage

Checkpoints are stored newest-first in the `## Checkpoints` H2 section of `vault/wiki/projects/<repo>/progress/<TICKET>/progress.md`. Each entry is a one-line bullet appended via `progress_fm.py prepend-section`.

Example line:

```
- 2026-05-02 03:45 phase=implementing fix for review comment 3 of 5 | last_done=pushed fix for @samyak rename | next=address @rohit BaseAgentNode pushback | waiting=user OK on pushback wording | threads=resolve PRRT_xxx, rebase onto master
```

## Steps

1. **Resolve TICKET_ID** — same identification priority as other progress.md skills:
   - User-provided artifact in current prompt (Jira / PR URL) → highest
   - Fallback: `git branch --show-current` → regex `ENG-\d+`
   If neither yields a ticket, abort: *"No ticket resolvable. Cannot checkpoint without a task. Seed via /work-on-jira-task or share a Jira/PR URL."*

2. **Compose the checkpoint** — fixed fields, fill from current session state. If any required field is unknown, skip the checkpoint entirely (a half-checkpoint is worse than none).

   - **phase**: where we are — e.g., "implementing fix for review comment 3 of 5", "drafting plan after brainstorm"
   - **last_done**: one line — the last concrete action that produced an artifact (code change, test run, push, decision)
   - **next**: one line — the immediate next step planned
   - **waiting_on**: user input / external dep / CI / nothing
   - **open_threads**: array, max 5 short bullets
   - **strategy** (optional): one short paragraph max for non-obvious mental model bits. Omit if nothing to add.

3. **Write to progress.md** — prepend (newest-first) to `## Checkpoints` via `progress_fm.py`:

```bash
python3 ~/.claude/scripts/progress_fm.py prepend-section <TICKET_ID> --section "Checkpoints" \
  --line "<YYYY-MM-DD HH:MM> phase=<phase> | last_done=<last_done> | next=<next> | waiting=<waiting_on> | threads=<t1>, <t2> | strategy=<strategy or omit>"
```

This is the canonical record. `last-touched` is auto-bumped to today by progress_fm.py.

4. **Update debounce state** — write current Unix timestamp to `~/.claude/state/last-checkpoint-<session-id>.txt`.

5. **Surface one-liner**:

```
↳ checkpoint saved to <TICKET_ID>: <phase> → next: <next>
```

## Resume contract (used by progress.md lookup)

When `progress_fm.py get <TICKET_ID>` is called at session start (by `/ship-task`, `/work-on-jira-task`, etc.), the loader MUST:

1. Read the first bullet under `## Checkpoints` (newest) if present.
2. Surface a resume header BEFORE the rest of the task summary:

```
↳ resuming from checkpoint <YYYY-MM-DD HH:MM>: phase=<...>, next=<...>
   (waiting on: <...>; open threads: <t1>, <t2>, ...)
```

3. Do NOT auto-load older checkpoints — they're available for explicit lookup ("what was the strategy 2 hours ago?") but not in scope by default. Latest only.

4. If `## Checkpoints` section is empty/missing, skip the resume header silently.

## Anti-patterns

- Do NOT overwrite prior checkpoints — prepend, never replace. The full history is the trail.
- Do NOT save a checkpoint with empty fields — if `phase` is unknown or `last_done` is unclear, the checkpoint is worse than no checkpoint. Skip it.
- Do NOT auto-invoke without the hook reminder being in scope — checkpoints have a real cost (interrupts work) and should fire on the explicit signal.
- Do NOT include code snippets, full file contents, or long quotes — a checkpoint is a compass, not the map. Other context layers (initiative learnings, plans/) hold the detail.
- Do NOT write to legacy `memory/branches/<branch>/checkpoints/` paths — that's the deprecated project-context location. All new checkpoints go through progress.md `## Checkpoints` via `progress_fm.py prepend-section`.

---

## Data Contract

### Reads (DB)
- (none — checkpoint is about current session state, not past knowledge)

### Reads (Memory)
- `~/opensource/vault/wiki/projects/<repo>/progress/<TICKET_ID>/progress.md` — `## Checkpoints` section (via `progress_fm.py get`)
- session state (current branch, context window %) — live, not stored

### Writes (Memory)
- `~/opensource/vault/wiki/projects/<repo>/progress/<TICKET_ID>/progress.md` — prepend new bullet to `## Checkpoints` (via `progress_fm.py prepend-section`); `last-touched` is auto-bumped

### Local (skill-only)
- `~/.claude/state/last-checkpoint-<session-id>.txt` — debounce timestamp (ephemeral, per-session)

### Live external (not stored)
- (none)
