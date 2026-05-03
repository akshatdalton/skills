---
name: magnetx-ship
description: Idempotent end-to-end orchestrator for shipping a MagnetX task to its next user-input gate. Routes by task track (build/sell/content/decide/learn) inferred from Notion Type field. Owns the build pipeline entirely (pickup logic folded in). Calls /magnetx-engage for sell, /aksenhq-* skills for content, /think for decide, /scrape-x-profile for research. Halts only on user-input gates (deploy y/n, content publish, sell execute, decide judgment). Use when user says "/magnetx-ship <id>", "ship this magnetx task", "drive this to done", "/magnetx next", or pastes a Notion task URL/ID with intent to complete. Also fired automatically by /magnetx next.
---

# /magnetx-ship — MagnetX Task Orchestrator

Mirrors `/ship-task` for the MagnetX domain. **Idempotent + autonomous + halts only at user-input gates.** Inspects task's track + status, routes to the right unit skill, advances Notion state, and picks the next task when done.

You're the founder/CEO + sole engineer + sole salesperson. This skill removes "which skill do I run" from your workflow.

---

## Inputs

- `<task-id>` — Notion task ID (e.g., `T-104` or full UUID like `33fecb1d-39d0-8175-9468-fc19ff32481f`).
- `engage` — special token: shortcut to most recent Engagement task.
- `decide` — special token: shortcut to most recent Decision task or first open decision in HQ Context.
- No arg → operate on the ★ task from `~/.claude/skills/magnetx/cache.json` (highest-priority needs_input or first today_id).

---

## Step 0 — Pre-flight (always)

1. `gh auth status` — confirm `akshatdalton`. If not, run `gh auth switch` to akshatdalton. Never eightfold creds.
2. `cd ~/opensource/magnetx` if track is build or content.
3. Read vault `~/opensource/vault/wiki/projects/magnetx/{overview,decisions,open-threads}.md` to ground in current state.
4. Read `~/.claude/skills/magnetx/cache.json` for task snapshot + shared_context.
5. **Save session ID** for reattach: run `/search-history current-id` (or read `latest sessionId` from `~/.claude/history.jsonl` for current cwd) → write to `cache.shared_context.session_id` + `active_task_id`.

---

## Step 1 — Resolve track + stage

1. Fetch the Notion task via `mcp__claude_ai_Notion__notion-fetch` with task ID.
2. Read `Type` property → map to track:

| Notion Type | Track |
|---|---|
| `Code`, `Feature`, `Bug`, `Skill` | **build** |
| `Engagement` | **sell** |
| `X-Post`, `X-Reply`, `Thread` | **content** |
| `Decision`, `Open Question` | **decide** |
| `Research`, `Validate` | **learn** |

3. **If Type is missing or ambiguous:** ask the user once via inline prompt:
   ```
   Task <ID> "<title>" has no Type set. Which track?
   [1] build    [2] sell    [3] content    [4] decide    [5] learn
   ```
   On answer → `mcp__claude_ai_Notion__notion-update-page` to write Type back to the task. Future runs route automatically (self-healing, one-time friction per task).

4. Read current `Status` property: `To Do` | `In Progress` | `Done`.
   - `Done` → output "Task already Done. Suggesting next from today_ids." → call self with next task in `today_ids`. Stop if list exhausted.
   - `To Do` → set `In Progress` (Notion update) → continue.
   - `In Progress` → continue at the right step in track pipeline (resume).

---

## Step 2 — Route by track

### Track: BUILD

Pipeline (folded in, no separate pickup skill):

1. **Status → In Progress** in Notion (skip if already).
2. **Fetch full task context:** title, Notes, URL, Phase, Priority. Read Notes completely — it contains rationale and file paths.
3. **Surface to user:**
   ```
   NEXT TASK: <title>

     Track:    build
     Phase:    <phase>
     Priority: <priority>
     Status:   In Progress

   CONTEXT:
     <notes>

   FILES:
     <paths/URLs from notes>

   PREP:
     1. <first step inferred from notes>
     2. <second step>

   NOTION: <task URL>
   ```
4. **Implement in foreground.** User collaborates on code changes, you write/edit files. Run tests if present.
5. **At completion (user says "done" / tests pass):** prompt inline:
   ```
   ──────────────────────────────
   Build complete. (y/n) deploy to prod via vercel?
   ──────────────────────────────
   ```
6. On `y`:
   - Run `vercel --prod` from `~/opensource/magnetx/` (or the relevant subdir like `landing/`).
   - On success: continue to Step 3 (writeback).
   - On failure: surface error, halt — user fixes and re-invokes.
7. On `n`: halt with the standard halt block (Step 4). User can defer deploy.

Skill-type tasks (Notion Type=Skill): same pipeline, but "deploy" step is replaced by `cat ~/.claude/skills/<name>/SKILL.md` smoke-test invocation.

### Track: SELL

Pipeline:

1. Status → In Progress.
2. Invoke `Skill(skill="magnetx-engage")` (no args = Mode 1 daily session).
3. `/magnetx-engage` surfaces 5 engagement targets in browser flow.
4. **Halt at gate:** *"Engage with the surfaced targets in your browser. Reply 'done' here when finished."*
5. On user "done":
   - Increment streak in Notion X Tracker (`mcp__claude_ai_Notion__notion-update-page` on a new daily entry, or update today's).
   - Write back `cache.x_tracker.streak` + `cache.x_tracker.last_session_date`.
   - Continue to Step 3 (writeback) → mark Notion task Done.

If user invokes Mode 2 mid-session for an angle, that's fine — `/magnetx-engage` handles it. Orchestrator only resumes on "done".

### Track: CONTENT

Pipeline:

1. Status → In Progress.
2. Pick sub-skill based on task Notes / context:
   - Notes mentions a brain-dump / personal observation → `Skill(skill="aksenhq-dump-to-post")`
   - Notes mentions a product decode / decision → `Skill(skill="aksenhq-product-decode-pipeline")`
   - Notes mentions a tweet to reply to / source URL → `Skill(skill="aksenhq-x-reply-strategy")`
   - Otherwise ask user once: `[1] dump  [2] product-decode  [3] reply-strategy`.
3. **Always finish with** `Skill(skill="aksenhq-x-brand-voice")` for final voice + formatting pass on the draft.
4. **Halt at gate:** *"Draft ready. Publish on X, then reply 'done' here."*
5. On "done": continue to Step 3 → mark Notion task Done.

### Track: DECIDE

Pipeline:

1. Status → In Progress.
2. Invoke `Skill(skill="think")` anchored to MagnetX initiative. Pass the task title + Notes as the seed.
3. `/think` surfaces decision options + tradeoffs.
4. **Halt at judgment gate:** *"Decision menu surfaced above. Pick an option to settle, or reply 'park' to defer."*
5. On user pick:
   - Append to vault `~/opensource/vault/wiki/projects/magnetx/decisions.md` using the verbatim template (see Session Protocol).
   - Append to Notion HQ Context "Settled Decisions" via `mcp__claude_ai_Notion__notion-update-page`.
   - Append to `~/opensource/vault/wiki/log.md`.
   - Continue to Step 3 → mark Notion task Done.
6. On "park": no decisions write; append to `~/opensource/vault/wiki/projects/magnetx/open-threads.md`. Mark Notion task back to To Do (so it resurfaces).

### Track: LEARN

Pipeline:

1. Status → In Progress.
2. If task involves scraping → `Skill(skill="scrape-x-profile")` with handle from Notes.
3. Otherwise: surface research scope to user, foreground analysis.
4. **Halt at capture gate:** *"Research surfaced. Reply 'done' with key findings (one paragraph) and I'll capture to vault."*
5. On "done":
   - Append findings to `~/opensource/vault/wiki/projects/magnetx/learnings.md` (create if missing).
   - Append `~/opensource/vault/wiki/log.md` line.
   - Continue to Step 3 → mark Notion task Done.

---

## Step 3 — Writeback (on track completion)

After every successful track completion:

1. **Notion task Status → Done** via `mcp__claude_ai_Notion__notion-update-page`.
2. **HQ Context "Recently Completed Tasks Log":** append `{date, task name, one-line note}`. Update "Last Activity" for the task's phase.
3. **Cache refresh:** background single agent → re-fetch all 3 Notion sources → rewrite `cache.json` (preserve today_ids/tomorrow_ids). Don't block the user.
4. **Vault writebacks** per Session Protocol:
   - `wiki/hot.md` — update "Active Right Now" → "magnetx: <next task or 'no active task'>"
   - `wiki/log.md` — append `<timestamp> magnetx/notion: completed <task-id> <title>`
   - For DECIDE track: `decisions.md` (already done in track step)
   - For LEARN track: `learnings.md` (already done)
5. **Pick next task** from `cache.today_ids` (next item after completed one). If found: re-invoke `/magnetx-ship <next-id>` autonomously.
6. **Stop** when today_ids exhausted OR another gate hit OR user-initiated stop.

---

## Step 4 — Halt block (standard)

Use this verbatim when stopping at any user-input gate:

```
───── /magnetx-ship halted ─────
task     : <id>  <title>
track    : <track>
stage    : <ready-to-deploy | engage-execute | publish | judgment | park | capture>
reason   : <one-line reason>
resume   : <how user resumes — e.g., "reply 'deployed'", "say 'done' after publishing", "pick option 1/2/3">
session  : claude -r <session_id>   ← reattach this same session
fresh    : /magnetx-ship <id>       ← or start fresh
────────────────────────────────
```

Halt block writes to `cache.shared_context` so `/magnetx` render shows the resume info.

---

## Idempotency

`/magnetx-ship <ID>` works at any time on any task:

| Notion Status | Action |
|---|---|
| `To Do` | Set In Progress → run track pipeline from start. |
| `In Progress` | Resume at the right step. For build, that means: if cache.shared_context.stage = "ready-to-deploy", jump straight to deploy gate. |
| `Done` | No-op. Output: "Already Done. Picking next from today_ids." → call self. |

Re-invocation is always safe.

---

## Stop conditions (where we halt back to user)

1. **Build — deploy confirm.** Inline `(y/n) deploy to prod?`. On `y`, runs `vercel --prod`. On `n`, halts.
2. **Sell — execution.** Targets surfaced; user engages in browser; resume on "done".
3. **Content — publish.** Final voice-passed draft shown; user posts; resume on "done".
4. **Decide — judgment.** `/think` surfaces options; user picks or parks.
5. **Learn — capture.** Research surfaced; user provides one-paragraph findings.
6. **Type ambiguous** (Step 1) — one-time inline prompt, then write back.

Everything else (Notion status, cache refresh, completion log, picking next task, vault writebacks) is auto.

---

## Special tokens

- `engage` → find most recent Engagement task (or create one with Type=Engagement, Phase="Personal X Growth") → run sell track.
- `decide` → find most recent Decision/Open Question task, or pick first Open decision from HQ Context → run decide track.

---

## Workflow ending

```
───── /magnetx-ship ─────
task        : <id>  <title>
track       : <track>
stage       : <completed | halted-at-<gate>>
notion      : <task URL — Done if completed>
next-task   : <next id from today_ids, or "today_ids exhausted">
─────────────────────────
```

---

## Data Contract

### Reads (Memory)
- `~/.claude/skills/magnetx/cache.json` — task snapshot + today_ids + shared_context
- `~/opensource/vault/wiki/projects/magnetx/{overview,decisions,open-threads}.md` — context grounding

### Reads (DB)
- Notion task by ID (`mcp__claude_ai_Notion__notion-fetch`)
- HQ Context page when needed for decision context

### Writes (Memory)
- `~/.claude/skills/magnetx/cache.json` — `shared_context` updates (session_id, active_task_id, stage); cache refresh after Notion writes
- `~/opensource/vault/wiki/hot.md` — Active Right Now line for magnetx
- `~/opensource/vault/wiki/log.md` — append on stage transitions + completion
- `~/opensource/vault/wiki/projects/magnetx/{decisions,open-threads,learnings}.md` — on decide/learn track completion

### Writes (DB)
- Notion task Status (To Do → In Progress → Done)
- Notion task Type (one-time backfill on ambiguous Type)
- Notion HQ Context "Recently Completed Tasks Log" + "Last Activity"
- Notion HQ Context "Settled Decisions" on decide track
- Notion X Tracker streak entry on sell track (delegated to `/magnetx-engage`)

### Live external
- `vercel --prod` on build deploy gate
- `gh` CLI for git ops (akshatdalton)

---

## Git Identity

GitHub: **akshatdalton** (personal). Always verify `gh auth status` in Step 0. Eightfold creds → `gh auth switch` first. Never push eightfold credentials here.

## References

| What | ID |
|------|----|
| HQ Context | `34eecb1d-39d0-814e-b03e-c39f13d1c254` |
| Task Board | `a119bf6a-603e-4f51-b602-fc7ffb4e445e` |
| X Tracker | `4b9b90de-9252-4da7-a76c-f40fa89c610f` |
| GitHub | akshatdalton/magnetx (landing in landing/) |
| Vercel | magnetx.co |
