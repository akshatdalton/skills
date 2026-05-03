---
name: checkpoint
description: Snapshot active strategy, last action, next step, and open threads into the current task's work_hq entry. Designed to make a fresh session productive in 30 seconds. Use when user types /checkpoint, OR when the PreToolUse hook surfaces "Context at X% — run /checkpoint" reminder, OR before any major hand-off (switching branches, ending session, before compaction). Manual invocation always works.
---

# Checkpoint

Append a snapshot of the active state into the current task's work_hq entry. The next session loading the task via `update.py get <TICKET_ID>` sees the latest checkpoint and is productive immediately — no need to re-derive what was happening.

## When invoked

- **Manual**: `/checkpoint` from user, or you decide to checkpoint at a logical hand-off point.
- **Auto from hook**: PreToolUse hook injects a system reminder when context ≥78% AND last checkpoint >5 min ago. When you see that reminder, invoke this skill via `Skill(skill="checkpoint")`.

## Storage

Checkpoints are stored as a list inside the task's `shared_context.checkpoints` array in `~/.claude/work_hq/board.json`. Newest first. Each entry is a small object — not a separate file.

```json
{
  "id": "ENG-191517",
  "shared_context": {
    "checkpoints": [
      {"at": "2026-05-02T03:45:00Z", "phase": "...", "last_done": "...", "next": "...", "waiting_on": "...", "open_threads": ["..."], "strategy": "..."},
      ...
    ]
  }
}
```

## Steps

1. **Resolve TICKET_ID** — same identification priority as other work_hq skills:
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

3. **Write to work_hq** — append (newest-first) to `shared_context.checkpoints` via `update.py`:

```bash
python3 ~/.claude/work_hq/update.py append-context <TICKET_ID> --decision "checkpoint <YYYY-MM-DD HH:MM>: phase=<...> | next=<...> | waiting=<...>"
```

For the structured version, use a small Python invocation that reads board.json, prepends the new checkpoint object to `shared_context.checkpoints`, and writes back via `update.py set` with a JSON-encoded value:

```bash
python3 - <<EOF
import json, os, datetime as dt
p = os.path.expanduser("~/.claude/work_hq/board.json")
b = json.load(open(p))
t = next((x for x in b["tasks"] if x["id"] == "<TICKET_ID>"), None)
assert t, "task not found"
sc = t.setdefault("shared_context", {})
chk = sc.setdefault("checkpoints", [])
chk.insert(0, {
  "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
  "phase": "<phase>",
  "last_done": "<last_done>",
  "next": "<next>",
  "waiting_on": "<waiting_on>",
  "open_threads": ["<t1>", "<t2>"],
  "strategy": "<strategy or empty>",
})
t["last_updated"] = chk[0]["at"]
b["updated_at"] = chk[0]["at"]
json.dump(b, open(p, "w"), indent=2)
EOF
```

The `update.py append-context --decision` line is the human-readable mirror in the decisions list; the structured insert above is the canonical record.

4. **Update debounce state** — write current Unix timestamp to `~/.claude/state/last-checkpoint-<session-id>.txt`.

5. **Surface one-liner**:

```
↳ checkpoint saved to <TICKET_ID>: <phase> → next: <next>
```

## Resume contract (used by work_hq lookup)

When `update.py get <TICKET_ID>` is called at session start (by `/ship-task`, `/work-on-jira-task`, etc.), the loader MUST:

1. Read `shared_context.checkpoints[0]` (newest) if present.
2. Surface a resume header BEFORE the rest of the task summary:

```
↳ resuming from checkpoint <YYYY-MM-DD HH:MM>: phase=<...>, next=<...>
   (waiting on: <...>; open threads: <t1>, <t2>, ...)
```

3. Do NOT auto-load older checkpoints — they're available for explicit lookup ("what was the strategy 2 hours ago?") but not in scope by default. Latest only.

4. If `checkpoints` array is empty/missing, skip the resume header silently.

## Anti-patterns

- Do NOT overwrite prior checkpoints — prepend, never replace. The full history is the trail.
- Do NOT save a checkpoint with empty fields — if `phase` is unknown or `last_done` is unclear, the checkpoint is worse than no checkpoint. Skip it.
- Do NOT auto-invoke without the hook reminder being in scope — checkpoints have a real cost (interrupts work) and should fire on the explicit signal.
- Do NOT include code snippets, full file contents, or long quotes — a checkpoint is a compass, not the map. Other context layers (initiative learnings, plans/) hold the detail.
- Do NOT write to legacy `memory/branches/<branch>/checkpoints/` paths — that's the deprecated project-context location. All new checkpoints go through work_hq.

---

## Data Contract

### Reads (DB)
- (none — checkpoint is about current session state, not past knowledge)

### Reads (Memory)
- `~/.claude/work_hq/board.json[task_id]` — to find current task and its `shared_context.checkpoints[]`
- session state (current branch, context window %) — live, not stored

### Writes (Memory)
- `~/.claude/work_hq/board.json[task_id].shared_context.checkpoints[]` — prepend new checkpoint (newest-first); update `last_updated` and root `updated_at`

### Local (skill-only)
- `~/.claude/state/last-checkpoint-<session-id>.txt` — debounce timestamp (ephemeral, per-session)

### Live external (not stored)
- (none)
