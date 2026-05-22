---
name: brain-ingest
description: Use when the user fires `/brain-ingest <ticket>` after working on a state-machine skill session (or before /clear) to capture progress AND immediately uplift settled learnings to project `learnings.md` — no waiting for PR merge. Also: `/brain-ingest` (no arg) for catch-up sweeps. WRITE SIDE of Akshat's vault brain. Distills session content into `~/opensource/vault/wiki/projects/<project>/progress/<ticket>/progress.md` (per-task), copies the matching plan from `~/.claude/plans/` into `progress/<ticket>/plan.md` on first ingest, and uplifts learnings to `learnings.md` every invocation. On PR merge: strips PR-state tags and archives the progress directory. Pairs with `/brain-recall`.
---

# /brain-ingest (v0.2)

## Purpose

Stateless skill sessions accumulate knowledge in conversation that dies on `/clear`. `/brain-ingest` is the write-side — distill what just happened into the vault brain so the next session AND adjacent tickets can benefit immediately.

**Core invariant (changed from v0.1):** uplift to `learnings.md` happens on EVERY per-ticket invocation, not just on PR merge. Adjacent work shouldn't have to wait for a PR review cycle to benefit from cross-task knowledge transfer. Tags handle the in-review uncertainty.

**Only writer** to `progress/<ticket>/progress.md` and `learnings.md`. State-machine skills do NOT write these.

## Vault layout

```
~/opensource/vault/wiki/projects/<project>/
  learnings.md                                          # durable project brain (you uplift here every per-ticket invocation)
  .brain-ingest-state.json                              # { "last_sync_timestamp": "..." } — catch-up sweep cursor
  progress/
    <ticket>/                                           # per-ticket directory
      progress.md                                       # state + in-flight learnings (you write here per session)
      plan.md                                           # copied from ~/.claude/plans/ on first ingest
    archive/
      <ticket>/                                         # merged tickets (you move whole directory here on merge)
        progress.md
        plan.md
```

Active v0 projects: **vscode** and **wipdp** ONLY.

## Invocation forms

| Form | Behavior |
|---|---|
| `/brain-ingest <ticket>` | Per-ticket distill + uplift. Writes session content into `progress/<ticket>/progress.md`. **Always** uplifts settled+tentative learnings to `learnings.md` (tentative ones get a PR-state tag). On first ingest, copies any matching plan to `progress/<ticket>/plan.md`. On detected merge: strips PR-state tags from prior uplifted entries, then moves the progress dir to `archive/`. |
| `/brain-ingest` (no arg) | Catch-up sweep using `last_sync_timestamp`. Distills project-level learnings (not tied to a specific ticket) into `learnings.md`. |
| `/brain-ingest <project> --sweep` | Same as above with explicit project. |

## Per-ticket flow (`/brain-ingest ENG-XXXXX`)

### Step 1 — Resolve project
cwd → repo, or directory-existence probe (`projects/<vscode|wipdp>/progress/<ENG-XXXXX>/` or archive), or branch.
If neither exists, fall back to `gh pr list --search "ENG-XXXXX" --repo EightfoldAI/<repo>` for both repos to determine which one owns the ticket.

### Step 2 — Locate or BOOTSTRAP ticket directory

**This step is mandatory. Do NOT skip even if dir is missing.** If `progress/<ENG-XXXXX>/` doesn't exist, **YOU MUST create it**. Bootstrapping a missing dir is your primary responsibility on first ingest — not an error.

- Check `<vault>/projects/<project>/progress/<ENG-XXXXX>/` (active)
- Check `<vault>/projects/<project>/progress/archive/<ENG-XXXXX>/` (already-merged; if found, abort with "ticket already archived; nothing to ingest" — unless user explicitly says re-ingest)
- If neither: `mkdir -p <vault>/projects/<project>/progress/<ENG-XXXXX>/` AND continue to Step 3

### Step 3 — Bootstrap progress.md if missing

Create `progress.md` with frontmatter:
```yaml
---
ticket: ENG-XXXXX
title: <fetch via gh pr view OR Atlassian MCP getJiraIssue>
project: <project>
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

### Step 4 — Plan file handling (per CLAUDE.md "Plan file convention")

1. Check `<vault>/projects/<project>/progress/<ENG-XXXXX>/plan.md` first. If it already exists (a plan-creating skill wrote it directly per convention), **do not overwrite**. Skip plan migration.
2. Otherwise, look for legacy plan in `~/.claude/plans/`:
   - First: `~/.claude/plans/tickets/ENG-XXXXX.md` (exact match)
   - Then: grep `~/.claude/plans/*.md` for "ENG-XXXXX" in filename or content
   - Take most recent by mtime
3. If found in legacy: `cp` to `<vault>/.../plan.md`. Don't delete the original.

### Step 5 — Identify and capture session content

- Get current session ID via `/search-history current-id` (MUST do this — Step 6 needs it).
- Skip if already in frontmatter `session_ids`.
- If `last_sync_timestamp` is older than other recent sessions touching this ticket, include them too.

Distill the session(s) into `progress.md`'s freeform section. Append, don't replace prior content. Capture:
- Plan refinements (changes from initial `plan.md`)
- What was implemented/tested in this session (contextual — NOT file-by-file diffs; PR carries that)
- Decisions made for this task
- Blockers, open questions, what to pick up next session
- Anything a fresh session would need to resume

**Use H2 headings per session for consistency**: `## Session <session_id_short> (YYYY-MM-DD) — <one-line summary>`. This makes the file scannable and easy to evolve.

### Step 6 — Update frontmatter

- Append the new session ID(s) to `session_ids` (this is mandatory; v0.1 had a bug here)
- Update `last-touched: <today>`
- Update `state` if changed (implementing → in-review → merging → merged)
- Set `pr: <number>` if PR exists (`gh pr list --head <branch>`)
- Set `pr_state` from `gh pr view <pr> --json state`

### Step 7 — UPLIFT to learnings.md (always — no merge gate)

This is the new behavior in v0.2. Every per-ticket invocation uplifts.

Walk the session content from Step 5. Categorize each potential learning:

**Settled learnings (write directly to `learnings.md`, no tag):**
- Gotchas / environment quirks (e.g., npm bug, worktree push refspec)
- Runbook commands you actually ran successfully
- Conventions adopted from corrections in this session
- Project-overview corrections (architectural facts that pre-existed)
- Observed runtime behavior

**Tentative learnings (write to `learnings.md` with `[in-review: PR #N]` tag):**
- Decisions about how the code SHOULD work (PR may get reviewed away)
- Architecture choices the PR introduces
- New entities/modules the PR creates
- Anything that depends on the PR landing as currently written

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

### Step 8 — Detect PR merge → strip tags + archive

After Step 7, if `gh pr view <pr> --json state` returns `MERGED`:
- Walk `learnings.md` for any `[in-review: PR #<N>]` tags matching this ticket's PR. Strip them. The learnings are now finalized.
- If a tagged decision turned out wrong (reviewer pushed back; final code differs from what was uplifted): UPDATE the section to reflect the final state, then strip the tag.
- Move the whole ticket directory: `mv progress/<ticket>/ progress/archive/<ticket>/`. Preserves progress.md AND plan.md AND any other artifacts.

### Step 9 — Detect PR abandon/revert

If `pr_state == CLOSED` (not MERGED), or user passes `--abandon`:
- Walk `learnings.md` for `[in-review: PR #<N>]` matching this ticket's PR. Either remove those entries or keep with `[abandoned: PR #N]` annotation if they're still useful as "we tried this and it didn't land".
- Move progress to `archive/` like merge case.

### Step 10 — Update sync state and report

- Update `.brain-ingest-state.json` `last_sync_timestamp` to now (ISO 8601 UTC).
- Report:
  - Paths of files written/updated
  - Session(s) captured
  - Learnings uplifted (with tag status)
  - Whether merge/archive fired

## Catch-up flow (`/brain-ingest`, no arg)

1. Resolve project from cwd.
2. Read `.brain-ingest-state.json` `last_sync_timestamp`.
3. Scan raw sources for entries with `timestamp > last_sync_timestamp` AND `project == <this project>`:
   - `~/.claude/history.jsonl`
   - `~/.claude/sessions/*.md`
   - `~/.claude/projects/-Users-akshat-v-eightfold-<project>/memory/*.md` (recently changed auto-memory)
4. For each session/transcript:
   - Skip if its session_id is already in some `progress/<ticket>/progress.md` `session_ids` (per-ticket flow handled it).
   - Otherwise extract project-level signals (new conventions, runbook commands, architecture facts not tied to a single ticket).
5. **Evolve `learnings.md`** sections in place (never duplicate).
6. Update `last_sync_timestamp` to now.
7. Report sections updated and sessions processed.

## What NEVER to write

- `~/opensource/vault/wiki/CLAUDE.md` — manual only
- `~/opensource/vault/wiki/index.md` — manual only
- `~/.claude/plans/`, `~/.claude/sessions/`, `~/.claude/history.jsonl`, `~/.claude/work_hq/` — RAW / deprecated operational state, read-only
- `_archive/**` — historical
- Any file outside `~/opensource/vault/wiki/projects/<vscode|wipdp>/`

## Promotion to global CLAUDE.md

If a correction/rule has appeared in 2+ tickets across 2+ projects, surface a "promotion candidate" line at end of report:
> Promotion candidate: rule "<text>" appeared in <list>. Consider adding to wiki/CLAUDE.md.

User decides whether to promote.

## Self-test (covers v0.1 → v0.2 changes)

In `cwd=~/eightfold/wipdp` on branch `akshat/ENG-XXXXX-foo`, fire `/brain-ingest ENG-XXXXX`:
1. Project = wipdp. Progress path = `wiki/projects/wipdp/progress/ENG-XXXXX/`.
2. **If file missing: create the dir AND `progress.md` with frontmatter. This is your job.**
3. Look for plan in vault first; if absent, look in `~/.claude/plans/`. Copy if found.
4. Get current session_id via `/search-history current-id`. Append to `session_ids` (mandatory).
5. Distill session content as `## Session <id> (YYYY-MM-DD) — <one-liner>` block in body.
6. **Uplift settled+tentative learnings to learnings.md regardless of PR state.** Tentative ones get `[in-review: PR #N]` tag.
7. `gh pr view <pr> --json state` → if MERGED: strip tags from learnings.md, archive progress dir.
8. Update `.brain-ingest-state.json`.
9. Report.
