---
name: brain-ingest-bg
description: Use when the user fires `/brain-ingest-bg` (or asks to "ingest in the background", "run brain-ingest without blocking", "capture this session in the background"). BACKGROUND launcher for the vault brain — fires `/brain-ingest` for the CURRENT session in a detached headless `claude` (Sonnet, minimal MCP) so the main loop never blocks. Pairs with `/brain-recall` (which arms it) and `/brain-ingest` (the foreground write skill this wraps). Also auto-fired by Claude at session wrap-up when brain-recall has armed an ingest, and by the Stop-hook queue drainer.
---

# /brain-ingest-bg (v0.1)

## Purpose

`/brain-ingest` is a foreground skill — running it blocks Akshat's session. This wrapper runs the SAME skill in a **detached headless `claude -p`** so it never blocks. It's the non-blocking firing path Akshat asked for: he keeps working (or `/clear`s) while the background instance distills the session into the vault.

Cheap by design: **Sonnet** + **minimal MCP** (`~/.claude/brain-ingest-mcp.json`) → ~$0.50–1.00/run vs ~$2–8 on Opus-with-all-MCP.

## When to fire

- **User types `/brain-ingest-bg`** — fire for the current session, now.
- **Claude self-fires at wrap-up** — if `/brain-recall` armed this session (a `~/.claude/brain-ingest-queue/<id>.json` marker exists, and the recall output left the 🧠 nudge in context), launch this when the session reaches a natural end (user says "done", switches tasks, signals `/clear`, or a substantial task just completed). Non-blocking — launch and keep going.
- **Stop-hook drainer** — fires automatically for any `pending` marker (see `~/.claude/hooks/brain-ingest-drain.sh`).

## Flow

1. **Resolve project** from cwd → repo slug (`vscode` | `wipdp` | `magnetx`), same rules as `/brain-recall`. If cwd isn't a managed repo, check the armed marker's `project` field; else ask.
2. **Get current session id** — run `/search-history current-id` (or read the live `~/.claude/projects/<encoded-cwd>/<id>.jsonl` filename).
3. **Launch detached** — never block:
   ```bash
   nohup ~/.claude/scripts/brain-ingest-bg.sh <project> --resume <session_id> \
     >> ~/.claude/brain-ingest-queue/logs/launch.log 2>&1 &
   ```
   The script forks the session (`--resume --fork-session`), runs `/brain-ingest`, serializes on a per-project lock so it can't clobber a concurrent ingest, and fires a desktop notification on completion. It SKIPs throwaway/meta sessions automatically.
4. **Mark the marker done** — `~/.claude/brain-ingest-queue/<id>.json` → `status: "launched"` (the drainer won't re-fire it).
5. **Tell the user, briefly**: "🧠 ingest launched in background for <session> — you'll get a desktop ping when it lands. Keep working." Then continue; do NOT wait on it.

## Notes

- This wrapper does NOT do the distillation itself in-session — that would be foreground. It only launches the detached worker.
- For a project-level catch-up (not a specific session), use `~/.claude/scripts/brain-ingest-bg.sh <project> --sweep` instead.
- Result/cost land in `~/.claude/brain-ingest-queue/logs/<project>-<ts>.json`.
- Pairs with `/brain-recall` (arms it) and `/brain-ingest` (foreground write side it wraps).
