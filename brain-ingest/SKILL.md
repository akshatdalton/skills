---
name: brain-ingest
description: Use when the user fires `/brain-ingest <ticket>` (foreground default), `/brain-ingest <ticket> --bg` (background launch — detached headless claude, non-blocking), legacy `/brain-ingest-bg`, says "ingest in background"/"without blocking", or fires `/brain-ingest` (no arg) for catch-up sweeps — after a state-machine skill session (or before /clear) to capture progress AND uplift settled learnings to project `learnings.md` (no PR-merge gate). WRITE SIDE of Akshat's vault brain. Distills session content into `progress/<ticket>/progress.md`, copies plan from `~/.claude/plans/` on first ingest, uplifts learnings to `learnings.md` every invocation. On PR merge: strips PR-state tags and archives the progress dir. `--bg` also auto-fires at session wrap-up from a /brain-recall-armed marker and from the Stop-hook drainer. Pairs with `/brain-recall`. Add `--v2` to ALSO write structured wiki pages into the claude-obsidian vault at `~/opensource/claude-obsidian-test/` (source page + concept pages + entity pages via wiki-ingest pattern).
---

# /brain-ingest (v1, post-vault-v1)

## Purpose

Stateless skill sessions accumulate knowledge in conversation that dies on `/clear`. `/brain-ingest` is the write-side — distill what just happened into the vault brain so the next session AND adjacent tickets can benefit immediately.

**Core invariant (since v0.2):** uplift to `learnings.md` happens on EVERY per-ticket invocation, not just on PR merge. Adjacent work shouldn't have to wait for a PR review cycle to benefit from cross-task knowledge transfer. Tags handle the in-review uncertainty.

**New in v0.3:** the BG-launcher mode (`--bg`) is folded into this skill. The previous `/brain-ingest-bg` skill is retired — its trigger phrases now route here and choose the BG branch.

**New in v1 (post-vault-v1, 2026-05-31):**
- 5 active projects now (vscode, wipdp, magnetx + **claude-code, meetily**), all on the unified 4-file pattern (charter / decisions / learnings / log).
- Per-project `log.md` exists — **every brain-ingest invocation must append a one-line event entry** to the relevant project's `log.md` (the recall side reads this tail eagerly).
- Initiative dirs (`projects/<project>/initiatives/<slug>/{charter,decisions,learnings}.md`) are first-class. When a ticket resolves into an initiative, uplift goes to the initiative's learnings.md FIRST (initiative-scoped); only generalize to project-level learnings.md when the lesson applies project-wide.

**Only writer** to `progress/<ticket>/progress.md`, `learnings.md`, and `log.md`. State-machine skills do NOT write these.

## Vault layout (v1, post-vault-v1)

```
~/opensource/vault/wiki/projects/<project>/                # vscode | wipdp | magnetx | claude-code | meetily
  charter.md                                              # project index — you DO NOT routinely write here (manual on scope change)
  learnings.md                                            # cross-cutting project brain — you uplift here (project-wide lessons only)
  decisions.md                                            # project-wide decisions — you may append (Why/Trade/Source format)
  log.md                                                  # append-only event timeline — YOU APPEND a one-liner every invocation
  .brain-ingest-state.json                                # { "last_sync_timestamp": "..." } — catch-up sweep cursor
  initiatives/
    <slug>/                                               # per-initiative scope
      charter.md
      decisions.md                                        # initiative-scoped decisions — you may append here
      learnings.md                                        # initiative-scoped lessons — you uplift FIRST when ticket resolves to this initiative
      progress/
        <ticket-or-task>/
          progress.md                                     # state + in-flight learnings (per-ticket write target)
          plan.md                                         # copied from ~/.claude/plans/ on first ingest
        archive/
          <ticket-or-task>/
            progress.md
            plan.md
  # Legacy flat path (vscode/wipdp/magnetx) — for tickets NOT under any initiative dir:
  progress/<ticket-or-task>/{progress.md, plan.md}
  progress/archive/<ticket-or-task>/
```

Active projects: **vscode**, **wipdp**, **magnetx**, **claude-code**, **meetily**.

**Per-project quirks:**
- **magnetx** — no Jira tickets; tasks use slugs (`build-mvp`, `yt-shorts`, `landing`); no GitHub PR merge detection (Notion is the task-lifecycle source of truth); GitHub account is `akshatdalton`.
- **claude-code** — vault-meta + workflow-tooling work. Tickets here are usually skill/hook/workflow changes, not Jira tickets.
- **meetily** — sister to claude-code; standalone Rust/Tauri repo (`akshatdalton/meetily`). Single live initiative: `meetily-calendar-daemon`.

## Invocation forms

| Form | Behavior |
|---|---|
| `/brain-ingest <ticket>` | **Foreground.** vscode/wipdp per-ticket distill + uplift. Writes session content into `progress/<ticket>/progress.md`. **Always** uplifts settled+tentative learnings to `learnings.md` (tentative ones get a PR-state tag). On first ingest, copies any matching plan to `progress/<ticket>/plan.md`. On detected merge: strips PR-state tags from prior uplifted entries, then moves the progress dir to `archive/`. |
| `/brain-ingest <initiative>` | **Foreground, magnetx only.** Same as above but `<initiative>` = `build-mvp` \| `yt-shorts` \| `landing` \| etc. No PR merge detection; no `[in-review]` tags needed. `archive/` move happens when user confirms the initiative is done. |
| `/brain-ingest` (no arg) | **Foreground.** Catch-up sweep using `last_sync_timestamp`. Distills project-level learnings (not tied to a specific ticket/initiative) into `learnings.md`. |
| `/brain-ingest <project> --sweep` | **Foreground.** Same as catch-up sweep but with explicit project. |
| `/brain-ingest --bg`<br>`/brain-ingest <ticket> --bg`<br>`/brain-ingest <project> --bg --sweep` | **Background launch.** Do NOT run the flow in-session. Detach a headless `claude -p` (Sonnet, minimal MCP) which itself runs the matching foreground form. Non-blocking; ~$0.50–1.00/run. See "Background mode" below. |
| `/brain-ingest-bg ...` | **Legacy alias** for `... --bg`. Same routing — go to BG flow. |

## Mode routing — decide FIRST

Before doing anything else, decide foreground vs background:

- **Background** if the trigger matches ANY of: contains `--bg` flag, is `/brain-ingest-bg` (legacy alias), user phrasing is "in background"/"without blocking"/"non-blocking"/"don't block me", or Claude self-fires at session wrap-up from a `/brain-recall`-armed marker → **jump to "Background mode" section below.** Do NOT run the per-task or catch-up flow in-session.
- **Foreground (default)** otherwise → run the per-task flow (single ticket/initiative arg) or catch-up flow (no arg, or `--sweep`) inline in this session.

`--bg` is not "skip the work" — it's "delegate the work to a cheap non-blocking instance that will run the exact same foreground flow inside itself".

## Background mode (`--bg`) — non-blocking launcher

The default flow runs in-session, which blocks Akshat. Adding `--bg` (or the legacy `/brain-ingest-bg` trigger, or phrasing like "ingest in background"/"without blocking") delegates the work to a **detached headless `claude -p`** on **Sonnet** with a **minimal MCP** config (`~/.claude/brain-ingest-mcp.json`). Cheap by design: ~$0.50–1.00/run vs ~$2–8 on Opus-with-all-MCP. Main loop never blocks.

### When background mode fires

- **User types `/brain-ingest --bg`** (or `/brain-ingest <ticket> --bg`, or legacy `/brain-ingest-bg`, or "ingest this in the background") — fire for the current session, now.
- **Continuous-mode beats** — once `/brain-recall` has armed the session (or any prior `--bg` has fired in this session), Claude main-session fires `--bg` at every clean transition: ~every 5–10 `🧠 capture:` breadcrumbs, ~30 min of substantive work, when a sub-task completes, or before any context-pressure event (compaction, `/clear` intent, branch switch). This is the **default** post-recall mode — don't wait for wrap-up. See brain-recall's "Continuous mode" section for the full pattern.
- **Claude self-fires at wrap-up** — final fire at session end (user says "done", switches tasks, signals `/clear`). Non-blocking.
- **Stop-hook drainer** — fires automatically for any `pending` marker (see `~/.claude/hooks/brain-ingest-drain.sh`). The drainer calls the launcher script directly — guaranteed backstop when both Akshat and Claude forget.

### BG flow (per call)

1. **Resolve project** from cwd → repo slug (`vscode` | `wipdp` | `magnetx`), same rules as Step 1 of the per-task flow. If cwd isn't a managed repo, check the armed marker's `project` field; else ask.
2. **Get current session id** — `python3 ~/.claude/skills/search-history/scripts/current_id.py --quiet`. Skip this step for the `<ticket> --bg` and `--bg --sweep` variants — they don't need a session id.
3. **Launch detached** — never block. Pick the launcher invocation by variant:

   | Trigger | Launcher command |
   |---|---|
   | `/brain-ingest --bg` (current session, auto-resolve ticket) | `nohup ~/.claude/scripts/brain-ingest-bg.sh <project> --resume <session_id> >> ~/.claude/brain-ingest-queue/logs/launch.log 2>&1 &` |
   | `/brain-ingest <ticket> --bg` (explicit ticket) | `nohup ~/.claude/scripts/brain-ingest-bg.sh <project> --ticket <ticket> >> ~/.claude/brain-ingest-queue/logs/launch.log 2>&1 &` |
   | `/brain-ingest <project> --bg --sweep` | `nohup ~/.claude/scripts/brain-ingest-bg.sh <project> --sweep >> ~/.claude/brain-ingest-queue/logs/launch.log 2>&1 &` |
   | Natural-language BG trigger ("ingest in background", "without blocking") with NO ticket mentioned | Same as `/brain-ingest --bg` row above — use the `--resume <session_id>` variant. The headless instance figures out the ticket from session context. |
   | Natural-language BG trigger with explicit ticket ("ingest ENG-12345 in the background") | Same as `/brain-ingest <ticket> --bg` row — use the `--ticket <ticket>` variant. |
   | Legacy `/brain-ingest-bg` (no args) | Same as `/brain-ingest --bg` — `--resume <session_id>` variant. |

   The script forks the session (`--resume --fork-session` for the resume variant), runs `/brain-ingest`, serializes on a per-project lock so it can't clobber a concurrent ingest, and fires a desktop notification on completion. It SKIPs throwaway/meta sessions automatically.

   **Live-session safety (important):** the resume variant uses `claude -p --resume <sid> --fork-session ...`. The `--fork-session` flag means the headless instance reads the source session's conversation history into a BRAND-NEW session id (a new jsonl file under `~/.claude/projects/<encoded-cwd>/`) and runs in THAT. The original live session is treated as read-only — nothing the worker writes lands in the main session's history. Continuous-mode firings are therefore safe: every fire creates its own independent fork; multiple workers can run for the same source session without ever stepping on the live conversation or each other. This is also why Step 5 of the per-task flow has the "record `<sid>` not your fork id" note — the worker is in a fork, not the original.
4. **Mark the marker done** — if a marker exists at `~/.claude/brain-ingest-queue/<session_id>.json`, flip `status: "launched"` (the drainer won't re-fire it).
5. **Tell the user, briefly**: "🧠 ingest launched in background for <session> — you'll get a desktop ping when it lands. Keep working." Then continue; do NOT wait on it.

### BG notes

- **`--bg` does NOT run the per-task / catch-up flow in-session.** It only launches the detached worker. The actual write side runs inside that worker, going through the same Step 1–10 / catch-up flow this skill documents.
- Result/cost land in `~/.claude/brain-ingest-queue/logs/<project>-<ts>.json`.
- The launcher script `brain-ingest-bg.sh` is the same one called by `brain-ingest-drain.sh` — keep the script name as-is; it's internal plumbing referenced by the hook and by `brain-catchup-batch.sh`.

---

## Per-task flow (`/brain-ingest ENG-XXXXX` or `/brain-ingest <initiative>`) — FOREGROUND only

> If the trigger has `--bg`, you should NOT be here. Go back to "Background mode" above.

### Step 1 — Resolve project

**vscode/wipdp path:**
cwd → repo slug (`vscode` or `wipdp`), or directory-existence probe (`projects/{vscode,wipdp}/progress/<ENG-XXXXX>/` or archive), or branch `akshat/ENG-XXXXX-*`.
If neither resolves, fall back to `gh pr list --search "ENG-XXXXX" --repo EightfoldAI/<repo>` for both repos.

**magnetx path:**
cwd path contains `/opensource/magnetx`, or `git remote get-url origin` returns `akshatdalton/magnetx`, or arg has no `ENG-` prefix and a probe of `projects/magnetx/progress/<arg>/` succeeds → project = `magnetx`.
No Jira/PR lookup needed. GitHub account is `akshatdalton`.

### Step 2 — Locate or BOOTSTRAP ticket/initiative directory

**This step is mandatory. Do NOT skip even if dir is missing.** If the directory doesn't exist, **YOU MUST create it**. Bootstrapping is your primary responsibility on first ingest — not an error.

- Check `<vault>/projects/<project>/progress/<ticket-or-initiative>/` (active)
- Check `<vault>/projects/<project>/progress/archive/<ticket-or-initiative>/` (already archived; if found, abort with "already archived; nothing to ingest" — unless user explicitly says re-ingest)
- If neither: `mkdir -p <vault>/projects/<project>/progress/<ticket-or-initiative>/` AND continue to Step 3

### Step 3 — Bootstrap progress.md if missing

**vscode/wipdp — use this frontmatter:**
```yaml
---
ticket: ENG-XXXXX
title: <fetch via gh pr view OR Atlassian MCP getJiraIssue>
project: <vscode|wipdp>
branch: <git branch>
pr: <number or null>
pr_state: <OPEN|MERGED|CLOSED or null>
state: <new|implementing|in-review|merging|merged|abandoned>
priority: <P0|P1|P2 from Jira or null>
created: <today YYYY-MM-DD>
last-touched: <today YYYY-MM-DD>
session_ids: []
---

# ENG-XXXXX — <title>

(body to be filled by Step 5)
```

**magnetx — use this frontmatter instead:**
```yaml
---
task: <initiative name, e.g. build-mvp>
title: <human-readable title>
project: magnetx
notion-task: <Notion task URL or null>
state: <scaffolded|in-progress|blocked|done>
last-touched: <today YYYY-MM-DD>
session_ids: []
---

# <initiative> — <title>

(body to be filled by Step 5)
```
*No `branch`, `pr`, `pr_state`, or `priority` fields for magnetx — those are Jira/GitHub concepts.*

### Step 4 — Plan file handling (per CLAUDE.md "Plan file convention")

**vscode/wipdp:**
1. Check `<vault>/projects/<project>/progress/<ENG-XXXXX>/plan.md` first. If it already exists (a plan-creating skill wrote it directly per convention), **do not overwrite**. Skip plan migration.
2. Otherwise, look for legacy plan in `~/.claude/plans/`:
   - First: `~/.claude/plans/tickets/ENG-XXXXX.md` (exact match)
   - Then: grep `~/.claude/plans/*.md` for "ENG-XXXXX" in filename or content
   - Take most recent by mtime
3. If found in legacy: `cp` to `<vault>/.../plan.md`. Don't delete the original.

**magnetx:**
1. Check `<vault>/projects/magnetx/progress/<initiative>/plan.md` first. If already exists, **do not overwrite**.
2. Otherwise, look in `~/.claude/plans/<initiative>.md` or `~/.claude/plans/magnetx-<initiative>.md`.
3. If found: `cp` to `<vault>/.../plan.md`. Don't delete the original.

### Step 5 — Identify and capture session content

- Get current session ID via `python3 ~/.claude/skills/search-history/scripts/current_id.py --quiet` (MUST do this — Step 6 needs it).
- **Continuous-mode dispatch** (decides full vs delta capture):
  - If session_id is NOT in frontmatter `session_ids` → **full capture**: distill everything from this session, append session_id to `session_ids`. Use H2 heading `## Session <id_short> (YYYY-MM-DD) — <one-line summary>`.
  - If session_id IS in `session_ids` AND new conversation content exists since `last-touched` → **delta capture**: distill ONLY the new content (the conversation past the last H2 block's last covered turn). Do NOT re-process content already in prior blocks. Do NOT append session_id (it's already there — keep deduped). Use H2 heading `## Session <id_short> (YYYY-MM-DD HH:MM) — continuous capture #N — <one-line>` where N is `(count of existing blocks for this session_id) + 1` starting at 2.
  - If session_id IS in `session_ids` AND no new content → no-op write; just bump `last-touched` in frontmatter and skip the body append.
- If `last_sync_timestamp` is older than other recent sessions touching this ticket/initiative, include them too (always full capture for those — they're new session_ids).

When capturing (full OR delta), distill into `progress.md`'s freeform section. **Append, never replace.** Look for:
- Plan refinements (changes from initial `plan.md`)
- What was implemented/tested (contextual — NOT file-by-file diffs; PR carries that)
- Decisions made for this task
- Blockers, open questions, what to pick up next session
- **`🧠 capture:` breadcrumbs** the main-session Claude left (continuous-mode signal — each one names a settled idea worth keeping)
- Anything a fresh session would need to resume

**Note on forked sessions:** if you're a headless `claude -p` worker launched by `brain-ingest-bg.sh --resume <sid> --fork-session`, your OWN session_id (the fork id from the jsonl filename) is NOT the work source. The ORIGINAL session id is `<sid>` — the value the launcher passed in. Record `<sid>` in `session_ids`, not your fork id. (The launcher captures `<sid>` in the log line for you to read back if needed.)

### Step 6 — Update frontmatter

**vscode/wipdp:**
- Append the new session ID(s) to `session_ids` (this is mandatory; v0.1 had a bug here)
- Update `last-touched: <today>`
- Update `state` if changed (implementing → in-review → merging → merged)
- Set `pr: <number>` if PR exists (`gh pr list --head <branch>`)
- Set `pr_state` from `gh pr view <pr> --json state`

**magnetx:**
- Append the new session ID(s) to `session_ids`
- Update `last-touched: <today>`
- Update `state` if changed (scaffolded → in-progress → blocked → done)
- No `pr` / `pr_state` fields

### Step 7 — UPLIFT to learnings.md (always — no merge gate)

This is the new behavior in v0.2. Every per-task/initiative invocation uplifts.

Walk the session content from Step 5. Categorize each potential learning:

**Settled learnings (write directly to `learnings.md`, no tag):**
- Gotchas / environment quirks (e.g., npm bug, worktree push refspec)
- Runbook commands you actually ran successfully
- Conventions adopted from corrections in this session
- Project-overview corrections (architectural facts that pre-existed)
- Observed runtime behavior

**Tentative learnings — vscode/wipdp only (write to `learnings.md` with `[in-review: PR #N]` tag):**
- Decisions about how the code SHOULD work (PR may get reviewed away)
- Architecture choices the PR introduces
- New entities/modules the PR creates
- Anything that depends on the PR landing as currently written

**magnetx: no `[in-review]` tags.** There is no PR review gate. All learnings are settled immediately — write them directly without any tag.

**Tag format example** in learnings.md:
```markdown
### Cache enabled agent ID per type [in-review: PR #86]
`AgentStore._enabled_by_type: dict[AgentType, str]` module-level cache. `get_enabled_agent(type)` is cache-first; `update_agent` invalidates on enable/disable. Avoids O(n) S3 list_objects on every chat turn (~20s latency at scale).
```

When updating `learnings.md`:
- **Always evolve in place.** If a section already covers the topic, rewrite/extend that section. NEVER append a duplicate section with the same topic.
- Pick the right section: Project overview / Runbooks / Conventions / Decisions / Initiative: <slug>
- Update `last-revised: YYYY-MM-DD` in frontmatter
- Cite the source PR/ticket inline where relevant

### Step 8 — Detect completion → strip tags + archive

**vscode/wipdp:** After Step 7, if `gh pr view <pr> --json state` returns `MERGED`:
- Walk `learnings.md` for any `[in-review: PR #<N>]` tags matching this ticket's PR. Strip them. The learnings are now finalized.
- If a tagged decision turned out wrong (reviewer pushed back; final code differs from what was uplifted): UPDATE the section to reflect the final state, then strip the tag.
- Move the whole ticket directory: `mv progress/<ticket>/ progress/archive/<ticket>/`. Preserves progress.md AND plan.md AND any other artifacts.

**magnetx:** No PR state to check. Archive when the user explicitly says the initiative is done:
- No tags to strip (learnings are untagged).
- Move the initiative directory: `mv progress/<initiative>/ progress/archive/<initiative>/`.

### Step 9 — Detect abandon/revert

**vscode/wipdp:** If `pr_state == CLOSED` (not MERGED), or user passes `--abandon`:
- Walk `learnings.md` for `[in-review: PR #<N>]` matching this ticket's PR. Either remove those entries or keep with `[abandoned: PR #N]` annotation if they're still useful as "we tried this and it didn't land".
- Move progress to `archive/` like merge case.

**magnetx:** If user passes `--abandon` or confirms the initiative was dropped: move to archive.

### Step 10 — Append to per-project log.md (MANDATORY, v1+)

After Steps 1–9 finish, append a one-liner to `~/opensource/vault/wiki/projects/<project>/log.md`. This is the eager-tier "what just happened" tail that `/brain-recall` reads on every recall — if you skip this, the recall side won't surface that this ingest ran.

Format: `<ISO-timestamp> brain-ingest: <ticket-or-slug> — <one-line summary of what was captured / state change / learnings uplifted>`

Examples:
- `2026-05-31T14:02:11Z brain-ingest: ENG-194688 — capacity matrix re-eval distilled; LLM-enrichment is the wall (not memory). PR #N in-review.`
- `2026-05-31T14:30:00Z brain-ingest: yt-shorts — letterbox_tracked mode shipped; verified speaker locks across push-ins. Skill updated.`
- `2026-05-31T16:45:00Z brain-ingest: (catch-up sweep) — 3 sessions processed; project-level learnings: structlog singleton convention promoted.`

Use append, never overwrite. Don't write log entries for SKIPped throwaway sessions.

### Step 11 — Update sync state and report

- Update `.brain-ingest-state.json` `last_sync_timestamp` to now (ISO 8601 UTC).
- Report:
  - Paths of files written/updated (including the log.md line)
  - Session(s) captured
  - Learnings uplifted (with tag status; note whether they went to initiative-scoped or project-scoped learnings.md)
  - Whether merge/archive fired

## Catch-up flow (`/brain-ingest`, no arg)

1. Resolve project from cwd.
2. Read `.brain-ingest-state.json` `last_sync_timestamp`.
3. Scan raw sources for entries with `timestamp > last_sync_timestamp` AND `project == <this project>`:
   - `~/.claude/history.jsonl`
   - `~/.claude/sessions/*.md`
   - `~/.claude/projects/-Users-akshat-v-eightfold-<project>/memory/*.md` (eightfold projects)
   - `~/.claude/projects/-Users-akshat-v-opensource-magnetx/memory/*.md` (magnetx)
4. For each session/transcript:
   - Skip if its session_id is already in some `progress/<ticket-or-initiative>/progress.md` `session_ids` (per-task flow handled it).
   - Otherwise extract project-level signals (new conventions, runbook commands, architecture facts not tied to a single ticket/initiative).
5. **Evolve `learnings.md`** sections in place (never duplicate).
6. Update `last_sync_timestamp` to now.
7. Report sections updated and sessions processed.

## What NEVER to write

- `~/opensource/vault/wiki/CLAUDE.md` — manual only
- `~/opensource/vault/wiki/index.md` — manual only
- `~/.claude/plans/`, `~/.claude/sessions/`, `~/.claude/history.jsonl`, `~/.claude/work_hq/` — RAW / deprecated operational state, read-only
- `_archive/**` — historical
- Any file outside `~/opensource/vault/wiki/projects/<vscode|wipdp|magnetx>/`

## Promotion to global CLAUDE.md

If a correction/rule has appeared in 2+ tickets across 2+ projects, surface a "promotion candidate" line at end of report:
> Promotion candidate: rule "<text>" appeared in <list>. Consider adding to wiki/CLAUDE.md.

User decides whether to promote.

## Self-test (covers v0.1 → v0.2 changes)

**Eightfold path** — `cwd=~/eightfold/wipdp`, branch `akshat/ENG-XXXXX-foo`, fire `/brain-ingest ENG-XXXXX`:
1. Project = wipdp. Progress path = `wiki/projects/wipdp/progress/ENG-XXXXX/`.
2. **If file missing: create the dir AND `progress.md` with vscode/wipdp frontmatter. This is your job.**
3. Look for plan in vault first; if absent, look in `~/.claude/plans/`. Copy if found.
4. Get current session_id via `python3 ~/.claude/skills/search-history/scripts/current_id.py --quiet`. Append to `session_ids` (mandatory).
5. Distill session content as `## Session <id> (YYYY-MM-DD) — <one-liner>` block in body.
6. **Uplift settled+tentative learnings to learnings.md regardless of PR state.** Tentative ones get `[in-review: PR #N]` tag.
7. `gh pr view <pr> --json state` → if MERGED: strip tags from learnings.md, archive progress dir.
8. Update `.brain-ingest-state.json`.
9. Report.

**magnetx path** — `cwd=~/opensource/magnetx`, fire `/brain-ingest build-mvp`:
1. Project = magnetx (cwd or no `ENG-` prefix). Progress path = `wiki/projects/magnetx/progress/build-mvp/`.
2. **If file missing: create the dir AND `progress.md` with magnetx frontmatter (no `pr`/`pr_state` fields).**
3. Look for plan in vault first; if absent, check `~/.claude/plans/build-mvp.md` or `~/.claude/plans/magnetx-build-mvp.md`.
4. Get current session_id via `python3 ~/.claude/skills/search-history/scripts/current_id.py --quiet`. Append to `session_ids`.
5. Distill session content as `## Session <id> (YYYY-MM-DD) — <one-liner>` block.
6. **Uplift ALL learnings as settled (no `[in-review]` tags — there is no PR review gate for magnetx).**
7. No PR merge check. Archive only when user explicitly says initiative is done.
8. Update `.brain-ingest-state.json`.
9. Report.

---

## --v2 mode: Obsidian wiki-ingest layer (runs AFTER the standard flow above)

Add `--v2` to any invocation form to also write structured wiki pages into the claude-obsidian vault at `~/opensource/claude-obsidian-test/`. Standard brain-ingest runs first in full — `--v2` is a post-step that consumes everything the standard flow produced PLUS all session artifacts.

**Triggers:**
- `/brain-ingest ENG-XXXXX --v2`
- `/brain-ingest --v2` (catch-up sweep + obsidian)
- `/brain-ingest ENG-XXXXX --v2 --bg` (background, obsidian step runs inside the headless worker)

### V2 Step 1 — Collect all artifacts from this session

Pull together everything to feed into the obsidian wiki. Collect:

1. **progress.md just written** — the per-ticket distillation (most valuable; already structured)
2. **plan.md** (if exists at `vault/wiki/projects/<project>/progress/<ticket>/plan.md`)
3. **Any files WRITTEN in this session** — scan the session transcript for Write/Edit tool calls; collect the resulting file paths. Include:
   - HTML reports written to vault or anywhere (`brain-comparison-report.html`, etc.)
   - Markdown docs written to vault (tech specs, design docs, etc.)
   - `.raw/` files dropped during the session
   - Anything in `~/.claude/plans/` touched this session
4. **Session learnings** — from the `🧠 capture:` breadcrumbs in the session (these are already in progress.md but worth calling out)
5. **Any memory files** — check `~/.claude/projects/<encoded-cwd>/memory/*.md` for entries updated this session

Do NOT re-read the full session JSONL transcript — the progress.md distillation already captures it. The breadcrumbs + plan + artifacts are the signal.

### V2 Step 2 — Write the .raw/ source file

Synthesize a single `.raw/<slug>-<YYYY-MM-DD>.md` file at `~/opensource/claude-obsidian-test/.raw/`.

**Slug:** `<ticket>` (e.g. `ENG-196489`) or `<initiative>` (e.g. `build-mvp`) or for sweeps: `<project>-sweep`.

**Check the manifest first** (`~/opensource/claude-obsidian-test/.raw/.manifest.json`). If this slug has already been ingested today (`ingested_at == today`), append `-2` to the slug to avoid colliding.

**Format for the .raw/ file:**

```markdown
---
source: brain-ingest-v2
ticket: <ENG-XXXXX or initiative slug>
project: <vscode|wipdp|magnetx|claude-code|meetily>
session_id: <id>
date: <YYYY-MM-DD>
artifacts:
  - <list of artifact paths that were consumed>
---

# <ticket/slug> — <title> (<YYYY-MM-DD>)

## Session Summary
<2-4 sentence summary of what happened: what was built/investigated/fixed, key decisions, outcome>

## What Was Done
<bullet list from progress.md body — actionable items only, not boilerplate>

## Decisions Made
<decisions from this session — each one as: Decision: X | Reason: Y | Trade-off: Z>

## Key Technical Findings
<code paths, patterns, root causes, runbook commands verified this session>

## Open Items / Next Session
<what was left open; what the next person (or future Akshat) needs to pick up>

## Learnings Captured
<the 🧠 capture: breadcrumbs, cleaned up as bullet points>

## Plan (if exists)
<paste the plan.md content, or a summary if it's very long>

## Artifacts Generated
<list of files written this session with one-line descriptions>
```

### V2 Step 3 — Run wiki-ingest on the .raw/ file

Follow the wiki-ingest pattern to create typed wiki pages from the source file. For each `.raw/<slug>-<date>.md`:

**Always create:**
- `wiki/sources/<slug>-<YYYY-MM-DD>.md` — the source page with everything from the raw file, formatted with frontmatter (`type: source`, `source_file`, `ingested`, `tags`, `related`)

**Create concept pages** for any of these found in the raw content:
- A new alarm class encountered
- A new code pattern established (e.g. "gate enable procedure")
- A triage methodology used
- A technical mechanism explained (e.g. "rank-cap eviction in entities_v2")
- Anything that would be useful as a standalone checklist or reference

**Create entity pages** for:
- People mentioned by name with a role (engineers, on-call contacts, owners)
- Services / systems with IDs (PagerDuty service IDs, AWS accounts)
- Integrations or external systems

**Wikilink everything.** Cross-link to existing pages in the vault (concept pages, entity pages) using `[[Page Name]]` syntax. If a concept page already exists for a topic (e.g. `[[App Platform Net Error Rate Alarm]]`), link to it rather than creating a duplicate.

**Dedup check before creating:** `grep -rl "<concept name>" ~/opensource/claude-obsidian-test/wiki/concepts/` — if a highly similar page exists already, UPDATE it with new information rather than creating a new page.

### V2 Step 4 — Update vault metadata

After creating pages:

1. **hot.md** (`~/opensource/claude-obsidian-test/wiki/hot.md`) — prepend a new session block at the top of the "Recent Context" section:
   ```
   ## <YYYY-MM-DD> — <ticket/slug> (<one-line summary>)
   <3-5 sentences: what happened, key findings, open items, pages created>
   ```
   Keep hot.md under 800 words total — trim the oldest entries if it grows beyond that.

2. **log.md** (`~/opensource/claude-obsidian-test/wiki/log.md`) — prepend a new entry at the top:
   ```
   ## [<YYYY-MM-DD>] ingest | <slug> — <one-liner>
   - Source: brain-ingest-v2 (session <id_short>)
   - Pages created: <list>
   - Key insight: <one sentence>
   ```

3. **index.md** — add new pages to the appropriate domain section (or create the section if the domain doesn't exist yet).

4. **.manifest.json** — update with the new source file entry: `hash`, `ingested_at`, `pages_created`.

### V2 Step 5 — Report

After the standard brain-ingest report, append:

```
📚 Obsidian wiki-ingest (--v2):
  Raw file: ~/opensource/claude-obsidian-test/.raw/<slug>-<date>.md
  Pages created:
    - wiki/sources/<slug>-<date>.md
    - wiki/concepts/<ConceptName>.md (new | updated)
    - wiki/entities/<EntityName>.md (new | updated)
  hot.md: updated
  log.md: updated
```

### V2 Notes

- **Never overwrite** an existing `.raw/` file — always append `-2`, `-3` etc. if the manifest shows a same-day ingest.
- **Never duplicate** concept/entity pages — dedup-check before creating; update in place if one exists.
- **wiki-ingest is forgiving** — fewer pages is fine. One source page + one concept page is a valid output if the session was narrow. Don't manufacture entities just to fill a quota.
- **The obsidian vault path is fixed**: `~/opensource/claude-obsidian-test/`. If this path is wrong or absent, skip the v2 step and warn: "⚠️ Obsidian vault not found at ~/opensource/claude-obsidian-test/ — skipping --v2 step."
