---
name: checkpoint
description: Snapshot active strategy, last action, next step, and open threads into the current branch's context file under a ## Checkpoints section. Designed to make a fresh session in this branch productive in 30 seconds. Use when user types /checkpoint, OR when the PreToolUse hook surfaces "Context at X% — run /checkpoint" reminder, OR before any major hand-off (switching branches, ending session, before compaction). Manual invocation always works; auto-invocation requires branch context to exist.
---

# Checkpoint

Append a snapshot of the active state into the branch context. The next session loads it via `/project-context:branch:read` and is productive immediately — no need to re-derive what was happening.

## When invoked

- **Manual**: `/checkpoint` from user, or you decide to checkpoint at a logical hand-off point.
- **Auto from hook**: PreToolUse hook injects a system reminder when context ≥78% AND last checkpoint >5 min ago AND branch context exists. When you see that reminder, invoke this skill via `Skill(skill="checkpoint")`.

## File layout

Each checkpoint is its OWN file under a sibling detail dir, named by ISO timestamp. The branch index file gets a `## Checkpoints` section listing them newest-first with one-line summaries — overview-with-lookups rule.

```
memory/branches/<branch-slug>.md                            ← branch index (gains ## Checkpoints section)
memory/branches/<branch-slug>/
  └── checkpoints/
      ├── 2026-04-30T16-45-22.md                            ← one full checkpoint per file
      ├── 2026-04-30T18-12-05.md
      └── ...
```

Filename format: `YYYY-MM-DDTHH-MM-SS.md` (ISO-8601 minus `:` since macOS filesystems hate them). Lexicographic sort = chronological sort.

## Steps

1. **Detect branch + resolve paths** — same branch-detection logic as `/project-context:branch:read`. Compute:
   - `branch_index = memory/branches/<branch-slug>.md`
   - `checkpoints_dir = memory/branches/<branch-slug>/checkpoints/`
   - `checkpoint_file = <checkpoints_dir>/$(date -u +%Y-%m-%dT%H-%M-%S).md`
   If `branch_index` doesn't exist, abort: "No branch context to checkpoint into. Seed one first." (Rare under auto-invocation — hook gates on branch index existence.)

2. **Compose the checkpoint** — fixed structure. Fill from current session state:

```markdown
# Checkpoint: <YYYY-MM-DD HH:MM TZ>

**Phase**: <where we are — e.g., "implementing fix for review comment 3 of 5", "drafting plan after brainstorm">
**Last done**: <one line — the last concrete action that produced an artifact (code change, test run, push, decision)>
**Next**: <one line — the immediate next step planned>
**Waiting on**: <user input / external dep / CI / nothing>
**Open threads**:
- <bullet>
- <bullet>
(max 5)
**Strategy notes**: <one paragraph max — non-obvious mental model bits. Skip section entirely if nothing to add.>
```

3. **Write the file** — `mkdir -p` the checkpoints dir, then write the full content to `checkpoint_file`. Never overwrite a prior checkpoint.

4. **Update branch index** — prepend a one-line entry at the top of the `## Checkpoints` section in `branch_index`. Create the section just below the front-matter / `**Project**:` line if it doesn't exist yet. Format:

```markdown
## Checkpoints
- 2026-04-30 16:45 — Phase: implementing fix for review comment 3 | Next: re-run EC2 tests → [checkpoints/2026-04-30T16-45-22.md](<branch-slug>/checkpoints/2026-04-30T16-45-22.md)
- 2026-04-30 14:12 — Phase: planning approach | Next: confirm with user → [checkpoints/2026-04-30T14-12-05.md](<branch-slug>/checkpoints/2026-04-30T14-12-05.md)
```

Newest at the top. Do NOT delete prior entries — they form the trail.

5. **Update debounce state** — write current Unix timestamp to `~/.claude/state/last-checkpoint-<session-id>.txt`.

6. **Surface one-liner**:

```
↳ checkpoint saved: <Phase value> → <relative checkpoint path>
```

## Resume contract (used by /project-context:branch:read)

When `/project-context:branch:read` loads a branch with a `## Checkpoints` section in its index file, it MUST:

1. **Identify latest** — top entry of the `## Checkpoints` section (newest-first). Fallback: `ls -1 <checkpoints_dir>/*.md | sort -r | head -1` if the section is missing or malformed.
2. **Read the latest checkpoint file fully** — load its contents into context.
3. **Surface the resume header** before the rest of the branch index:

```
↳ resuming from checkpoint <YYYY-MM-DD HH:MM>: Phase=<...>, Next=<...>
   (waiting on: <...>; open threads: <bullet1>, <bullet2>, ...)
```

4. **Do NOT auto-load older checkpoints** — they're available for explicit lookup ("what was the strategy 2 hours ago?") but not in scope by default. Latest only.

5. If no checkpoints exist yet, skip the resume header silently.

## Anti-patterns

- Do NOT overwrite prior checkpoints — append, never replace.
- Do NOT save a checkpoint with empty fields — if Phase is unknown or Last done is unclear, the checkpoint is worse than no checkpoint. Skip it.
- Do NOT auto-invoke without the hook reminder being in scope — checkpoints have a real cost (interrupts work) and should fire on the explicit signal.
- Do NOT include code snippets, full file contents, or long quotes — checkpoint is a compass, not the map. Other context layers hold the detail.
