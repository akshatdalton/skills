---
name: today
description: Personal command center — your single source of truth for engineering work across vscode and wipdp. Polymorphic. /today renders the dashboard (priority order + Needs Your Input + Backlog). /today list shows a table view. /today plan enters scope mode (set today vs backlog via the `bucket` field, or by dragging in the Obsidian Kanban board). /today next starts the ★ task via /ship-task. /today ingest <dump> consumes meeting notes / discussion summaries into candidate tickets and decisions. Use when the user says "/today", "what should I work on", "where did I leave off", "show my board", "plan my day", "set today/backlog", or shares a meeting dump and wants it triaged into tasks.
---

# Today — Engineering Command Center (v0.2 — vault-backed)

Polymorphic skill. One entry point for all daily-planning + dashboard interactions. Routes by sub-mode argument.

**Source of truth (v0.3, Obsidian-Kanban-backed):**
- **Tickets** live in `~/opensource/vault/wiki/projects/<repo>/progress/<ticket>/progress.md` frontmatter — vault is THE board.
- **Today vs Backlog** lives in each ticket's `progress.md` frontmatter under a `bucket: today | backlog` field (default `backlog`). This replaces today.json's today_ids/tomorrow_ids.
- **The Obsidian board** at `~/opensource/vault/Tasks.md` is a projection of the vault you can edit by dragging cards. `~/.claude/work_hq/kanban.py` syncs both ways: readback at the start of every /today, render at the end.
- **Needs-your-input items** live in each ticket's `progress.md` frontmatter under a `needs_input:` field. No separate file.
- `~/.claude/work_hq/board.json` and `today.json` are **deprecated** — /today reads neither; `bucket` frontmatter + `Tasks.md` replace them. (Legacy skills may still write today.json; harmless.)

## Sub-modes

| Invocation | Mode | What it does |
|---|---|---|
| `/today` | render | Default. Show dashboard: Needs Your Input ★, Today's ordered list, Tomorrow, all P0/P1/P2. |
| `/today list` | list | Compact table view. Columns: priority · ticket · stage · repo · PR · initiative. |
| `/today plan` | plan | Interactive: set each ticket's `bucket` (today vs backlog). Asks where each unplanned ticket fits. |
| `/today next` | next | Start the ★ task via `/ship-task`. |
| `/today ingest <dump>` | ingest | Parse a meeting/discussion dump → propose candidate tickets (via `/create-jira-ticket-with-reference`), decisions (into vault learnings.md), and priority placements. |
| `/today retro` | retro | Sprint wrap-up report (lazy-loaded; see `retro.md` in skill dir). |
| `/today meetings` | meetings | List auto-recorded meeting transcripts awaiting a summary. |
| `/today meeting <slug\|latest>` | meeting | Summarize a recorded meeting → write `summary.md` + surface TL;DR / action items / decisions; offer to ingest items. |

## Pre-entry: refresh state (foundation hook)

On every invocation:

### Step 0 — Fold in Obsidian board edits (Kanban readback)

Before reading the vault, pull any card drags from the Obsidian Kanban board (`~/opensource/vault/Tasks.md`) back into vault frontmatter, so the in-memory board reflects them:

```bash
python3 ~/.claude/work_hq/kanban.py readback
```

This writes `state` / `bucket` changes into each affected `progress.md` (split-by-field rule: your drag wins for today/backlog placement, automation wins for PR-driven stage). Unknown/draft cards are left untouched. No-op if `Tasks.md` doesn't exist yet.

### Step 1 — Build the in-memory board by walking vault (frontmatter ONLY)

**Critical efficiency rule:** /today only needs YAML frontmatter from each progress.md (~15 lines). The body is hundreds of lines per ticket and is brain-recall's territory, not /today's. **NEVER use the `Read` tool to load progress.md files** — that wastes context on body content you don't need.

Use a **single Bash call** that extracts frontmatter from ALL active progress files in one shot:

```bash
for f in ~/opensource/vault/wiki/projects/{vscode,wipdp}/progress/ENG-*/progress.md; do
  [ -f "$f" ] || continue
  echo "=== $f ==="
  awk '/^---$/{c++; if(c==2)exit; next} c==1{print}' "$f"
done
```

For `/today list --include-archived`, also walk `progress/archive/ENG-*/progress.md` in the same loop.

The output is a single block of `=== <path> ===` headers followed by frontmatter blocks. Parse this in-memory.

For each ticket, extract:
- `ticket`, `title`, `project` (vscode|wipdp), `branch`, `pr`, `pr_state`, `state`, `priority`, `bucket` (today|backlog; default backlog), `initiative`, `created`, `last-touched`
- `needs_input` block if present (`{reason, action, added_at}`)
- `session_ids` (informational; not surfaced in dashboard)

This in-memory list IS the board. No `board.json` read. No per-file `Read` calls.

### Step 2 — Derive Today / Backlog from bucket

No today.json read. Each in-memory ticket already carries `bucket` (today | backlog, default backlog) from Step 1. **Today** = `bucket == today`; **Backlog** = `bucket == backlog`. bucket persists in frontmatter (set by your Obsidian drags via Step 0, or by plan mode), so there is no daily date/carry-forward to manage.

### Step 3 — Refresh PR state in parallel (gh CLI, NOT GitHub MCP)

**Repo → GH mapping** (use these exact prefixes; do not guess org names):
```
vscode   →   GH_HOST=github.com gh ... --repo EightfoldAI/vscode
wipdp    →   GH_HOST=github.com gh ... --repo EightfoldAI/wipdp
```

For each in-memory ticket with `pr` set, fire **all** PR fetches as separate Bash tool calls in the **same** response (parallel):
```bash
GH_HOST=github.com gh pr view <N> --repo EightfoldAI/<repo> --json state,mergeable,mergeStateStatus,reviewDecision,statusCheckRollup,headRefOid,mergedAt
```
For each PR's `headRefOid`, also fetch the **commit status** channel in parallel (catches external CI like NPM Test, Playwright, CI Test Suite):
```bash
GH_HOST=github.com gh api repos/EightfoldAI/<repo>/commits/<sha>/status --jq '.state'
GH_HOST=github.com gh api repos/EightfoldAI/<repo>/commits/<sha>/check-runs --jq '[.check_runs[]|.conclusion]'
```

Reconcile both channels — task is `ci`-failing if EITHER has a failure. Apply auto-stage-transitions:
- merged → state `merged`, `pr_state: MERGED` (renders in the Done lane; brain-ingest archives it off the board on merge)
- approved + both channels green + 0 unresolved → `ready-to-merge` + add `needs_input: {reason: ready-to-merge, action: "merge it"}`
- any channel reports `failure` → `ci` + add `needs_input: {reason: ci-failing, action: "fix CI on PR #N"}`
- else → keep `in-review`

### Step 4 — Refresh stale Jira state in parallel

For each task WITHOUT a PR (stage todo/in-progress) OR with `last-touched > 1h old` — batch-call `mcp__claude_ai_Atlassian__getJiraIssue` in parallel to refresh title, status, sprint, priority, assignee. This is the only place Atlassian MCP is used; GitHub data always comes from `gh`. **Before the first Atlassian call**, run `ToolSearch select:mcp__claude_ai_Atlassian__getJiraIssue` to load the schema — it is deferred and not callable without this step.

### Step 5 — Write changes back to vault (frontmatter only, surgical edits)

For each ticket whose state changed in steps 3-4, **rewrite ONLY the YAML frontmatter** of its `progress.md` — never touch the body. Update: `state`, `pr_state`, `priority`, `last-touched: <today>`, and add/remove `needs_input` block.

**How to write efficiently** (avoid loading the body):
- Use `Edit` tool with a precise old-string → new-string replacement targeting only the frontmatter line(s) that changed (e.g., replacing `state: in-review` with `state: merged`). Edit doesn't require Reading the whole file first.
- For multi-field updates, use a small Bash + `sed` one-liner targeting only the YAML region (lines between the first two `---` markers).
- Do NOT use the `Read` tool on progress.md as a precursor to writing — you already have the frontmatter in memory from Step 1.

> **Vault write rule:** /today is permitted to update progress.md *frontmatter* (machine-managed metadata). The *body* of progress.md remains brain-ingest's territory (per CLAUDE.md). This separation means /today can keep state fresh without bumping into brain-ingest's session-distillation responsibility.

### Step 6 — Tooling rule

`gh` CLI for GitHub, Atlassian MCP for Jira, never the other way.

### Step 7 — Watcher-status check (per task with PR + CI failing)

`/loop` and `/pr-watcher` die when the user closes Claude Code, so a "watcher running" status is only meaningful in a live session. For each task where CI is failing, check `shared_context.watcher_session_id` (set by `/ship-task` on entry — currently still in board.json's transitional shared_context; will move to progress.md frontmatter when /ship-task migrates):
- If absent → render `→ no watcher session recorded`
- If present → render `→ resume with: claude -r <watcher_session_id>` (this session has the implementation context — reattaching is faster than starting fresh)

User can either `claude -r <id>` to reattach or run `/ship-task <TICKET>` from the current session. Never auto-schedule /loop, CronCreate, or /pr-watcher from /today.

### Step 8 — Render the Obsidian board (Kanban render)

After all vault writes (steps 3–5), regenerate the board so Obsidian reflects the fresh state:

```bash
python3 ~/.claude/work_hq/kanban.py render
```

Lanes are Backlog | To Do | In Progress | In Review | Done (lane = function of `state` + `bucket`). Card order within each lane and the `%% kanban:settings %%` block are preserved across renders.

## Mode: render (default)

Output format:

```
WORK HQ — <date>

★ NEEDS YOUR INPUT (<n>)
─────────────────────────────────────────────────────
  ENG-191942  merge-conflict      → rebase PR #70 onto main (CONFLICTING)
  ENG-191692  judgment-call       → review @samyak's naming comment
  ENG-184901  group-3-design      → decide index naming convention

TODAY (<n>)        — bucket == today
─────────────────────────────────────────────────────
  1. P0  ENG-191517  in-review     vscode#105712  [agent-builder]
  2. P0  ENG-191692  todo          wipdp           [agent-builder]
  3. P1  ENG-185432  in-progress   vscode          [-]

BACKLOG (<n>)      — bucket == backlog
─────────────────────────────────────────────────────
  P0  ENG-193205  new           wipdp  [source-integration-polish]
  P1  ENG-184567  todo          vscode [-]

MEETINGS — needs summary (<n>)    — auto-recorder; omit this block if none pending
─────────────────────────────────────────────────────
  2026-06-01-tm-india-retro     30m   [meet 2026-06-01-tm-india-retro]

PICK
  [N]   start task#N             [next]   start ★
  [plan] re-plan day             [list]   table view
  [ingest <text>] consume dump   [add ENG-N today|backlog]
  [meet <slug>] summarize meeting
```

★ = highest-priority item with `needs_input` set in frontmatter. If none, ★ goes to the first in-progress ticket in TODAY.

## Mode: list (table)

Compact table for scanning:

```
WORK HQ — <date>

ORDER  PRI  TICKET       STAGE          REPO     PR        INITIATIVE
─────  ───  ───────────  ─────────────  ───────  ────────  ──────────────
[T1]   P0   ENG-191517   in-review      vscode   #105712   agent-builder
[T2]   P0   ENG-191692   todo           wipdp    -         agent-builder
[T3]   P1   ENG-185432   in-progress    vscode   -         -
─────  ───  ───────────  ─────────────  ───────  ────────  ──────────────
[B1]   P1   ENG-184567   todo           vscode   -         -          (backlog)

NEEDS YOUR INPUT
ENG-191942  merge-conflict  → rebase PR #70 onto main (CONFLICTING)
```

T# = today position, B# = backlog position. Add `--include-archived` to also walk `progress/archive/` for full history.

## Mode: plan

Interactive scope-setting — sets each ticket's `bucket`. (You can also just drag cards between **Backlog** and the working lanes in Obsidian; the next `/today` readback folds it in.) Steps:

1. List todo-ish tickets (`state ∈ {new, planning, todo, in-progress, in-review, ci, testing, ready-to-merge}`), grouped by current `bucket`.
2. Ask which to pull into **today** vs push to **backlog**. Accept a free-form list: *"Today: ENG-191517, ENG-191692. Backlog: ENG-184567."*
3. Apply by editing each ticket's `bucket:` frontmatter field directly (small inline Edit — no CLI helper).
4. Run `python3 ~/.claude/work_hq/kanban.py render`, then render the dashboard.

Also clears `needs_input` blocks from progress.md frontmatter for any items the user marks resolved during planning (small inline edit).

## Mode: next

1. Compute ★ (highest-priority ticket with `needs_input` block; if none, first in-progress with `bucket == today`; if none, first todo with `bucket == today`).
2. Surface: *"Starting <TICKET_ID>: <title> [state=<s>]. Routing via /ship-task."*
3. `cd` to the right repo if needed (based on the ticket's `project` frontmatter field).
4. `git checkout` the branch if it exists (from `branch` frontmatter).
5. Invoke `Skill(skill="ship-task", args="<TICKET_ID>")`.

## Mode: ingest <dump>

Consume meeting notes, discussion summaries, brain dumps. Steps:

1. Extract:
   - **Candidate tickets** (action items, "we should do X") → propose `/create-jira-ticket-with-reference` for each, infer initiative if discussion is about an existing one. The skill writes the new ticket's `progress.md` directly to vault.
   - **Decisions** ("we agreed to use Y") → append to the relevant initiative section in `~/opensource/vault/wiki/projects/<repo>/learnings.md` (find/create `## Initiative: <slug>` section). Skip if no clear initiative — surface to the user instead.
   - **Learnings** ("we discovered Z") → same destination as decisions.
2. Show extracted items in a table; ask the user to confirm/edit each before creating tickets.
3. After ticket creation, ask where each new one fits — today or backlog (delegates to plan mode for placement). New tickets default to backlog.

> **Note on inbox**: the legacy `vault/wiki/inbox/` and `~/.claude/work_hq/inbox/` paths have been retired in v0. Dumps land directly into vault learnings.md initiative sections + new ticket progress files. No separate inbox queue.

## Mode: retro

Read `~/.claude/skills/today/retro.md` for full instructions (lazy-loaded — only when `/today retro` is invoked).

## Meeting transcripts (auto-recorder integration)

The headless `meetily-rec` recorder (calendar-armed via launchd; see
`~/opensource/meetily/frontend/src-tauri/headless/README.md`) drops one transcript per meeting at
`~/opensource/vault/raw/meetings/<date>-<slug>/transcript.md` (+ `metadata.json`). /today is where you
turn those raw transcripts into summaries + action items on demand — the recorder captures &
transcribes locally; Claude does the thinking.

**Scan (cheap — run during render, after Step 8):** a transcript with no `summary.md` is pending:
```bash
for d in ~/opensource/vault/raw/meetings/*/; do
  [ -f "$d/transcript.md" ] && [ ! -f "$d/summary.md" ] && echo "PENDING $(basename "$d")"
done
```
Show pending ones in the render's **MEETINGS** block (duration from `metadata.json`) and add
`[meet <slug>]` to PICK. If none pending, omit the block entirely.

### Mode: meetings
List `raw/meetings/*/` (newest first): summary status (✓ summarized / ○ pending), date, duration, and
the `[meet <slug>]` action. Read-only.

### Mode: meeting <slug | latest>
1. Resolve `latest` = newest `raw/meetings/*/` dir. Read its `transcript.md` + `metadata.json`.
2. **Summarize** — don't paraphrase; extract:
   - **TL;DR** (2–3 sentences)
   - **Key points** (the discussion)
   - **Action items** (owner + task where stated)
   - **Decisions** ("we agreed to …")
   Note: transcripts have no speaker labels yet — attribute only where the words make it clear.
3. Write `raw/meetings/<slug>/summary.md` (frontmatter: `meeting`, `date`, `source: today-summary`)
   and surface it inline. Writing `summary.md` is what clears it from the pending list.
4. **Offer to route items** (ask first, same confirm-first rule as ingest): action items → candidate
   tickets via `/create-jira-ticket-with-reference`; decisions/learnings → the relevant initiative's
   `learnings.md`. This hands off to **ingest mode** with the summary as the dump.

## Reactive integration (other skills push to /today via vault writes)

`/today` does not poll — other skills write directly to vault progress.md files:

| Skill | Effect on /today |
|---|---|
| `/create-jira-ticket-with-reference` | Creates `progress/<ticket>/progress.md` with `needs_input: {reason: new-ticket-priority, action: place in today/backlog plan}` so plan mode prompts placement |
| `/brain-ingest <ticket>` | Updates progress.md frontmatter (state, pr, pr_state, session_ids, last-touched). On merge: archives the ticket dir → /today no longer surfaces it. |
| `/ship-task` (loop self-terminate) | Updates progress.md frontmatter `needs_input` with stop reason; surfaces in ★ |
| `/work-on-jira-task` (start) | sets state=in-progress (via brain-ingest at session end if user fires it) |
| `/submit-pr` | sets state=in-review, pr=N (via brain-ingest at session end) |
| `/get-pr-ready-to-merge` | updates state, pr_state (via brain-ingest at session end) |
| Merged externally | next `/today` invocation auto-detects via gh refresh in step 3 |

## Storage layout (v0.3)

> v0.3: `bucket` frontmatter + `~/opensource/vault/Tasks.md` (Obsidian Kanban, synced by `kanban.py`) replace today.json's role. today.json + update.py are now deprecated alongside board.json — /today reads none of them. The ASCII diagram below predates this; the source-of-truth bullets at the top are authoritative.

```
~/opensource/vault/wiki/projects/                    ← single source of truth for tickets
├── vscode/progress/
│   ├── ENG-XXXXX/
│   │   ├── progress.md                              # frontmatter = board entry; body = task narrative
│   │   └── plan.md                                  # original plan (created by /work-on-jira-task or /think)
│   └── archive/
│       └── ENG-YYYYY/{progress.md, plan.md}
└── wipdp/progress/                                   (same shape)

~/.claude/work_hq/                                    ← operational state owned by /today (NOT vault)
├── today.json                                        # {date, today_ids[], tomorrow_ids[], notes}
├── update.py                                         # CLI helper for today.json mutations only
├── fetch_ci_log.sh                                   # utility (CI log access)
└── (deprecated, kept for back-compat reading until skills fully migrate:)
    ├── board.json                                    # NO LONGER MAINTAINED — derived from vault
    ├── needs_input.json                              # NO LONGER MAINTAINED — moved to progress.md frontmatter
    ├── board.md                                      # rendered board (stale)
    ├── initiatives/                                  # absorbed into vault learnings.md initiative sections
    └── inbox/                                        # empty / deprecated
```

`update.py` (today.json mutator) is **deprecated** along with today.json; `bucket` frontmatter + `kanban.py` replace it. Direct progress.md frontmatter edits replace the old `update.py set`/`needs-input` commands.

**kanban.py cheatsheet**:
```bash
python3 ~/.claude/work_hq/kanban.py readback   # fold Obsidian drags -> vault frontmatter (run at /today start)
python3 ~/.claude/work_hq/kanban.py render     # vault -> Tasks.md (run at /today end)
python3 ~/.claude/work_hq/kanban.py sync       # readback then render
python3 ~/.claude/work_hq/kanban.py migrate    # one-time: seed bucket:today from today.json
```

For ticket frontmatter mutations (state, `bucket`, needs_input, etc.), edit `vault/wiki/projects/<repo>/progress/<ticket>/progress.md` directly. `bucket: today|backlog` controls Today vs Backlog placement.

## Workflow ending

```
───── /today ─────
mode      : <render|list|plan|next|ingest>
needs_input: <n>
today     : <n> tasks   (or: <ticket-id> started via /ship-task)
backlog   : <n> tasks
────────────────────

───── artifacts ─────
Vault     : ~/opensource/vault/wiki/projects/*/progress/*/progress.md
Board     : ~/opensource/vault/Tasks.md  (Obsidian Kanban)
─────────────────────
```

---

## Data Contract

### Reads
- `~/opensource/vault/wiki/projects/{vscode,wipdp}/progress/ENG-*/progress.md` — all active tickets (frontmatter is the board entry)
- `~/opensource/vault/Tasks.md` — the Obsidian Kanban board; read back at /today start via `kanban.py` (drags fold into `bucket`/`state`)
- (Optional, `--include-archived`): `~/opensource/vault/wiki/projects/*/progress/archive/ENG-*/progress.md`
- `~/opensource/vault/raw/meetings/*/{transcript.md, metadata.json}` — auto-recorder output; scanned (transcript without `summary.md` = pending) and read on `/today meeting <slug>`

### Writes
- `vault/wiki/projects/<repo>/progress/<ticket>/progress.md` — **frontmatter only** (state, bucket, pr_state, last-touched, needs_input). Body is brain-ingest's responsibility.
- `~/opensource/vault/Tasks.md` — regenerated at /today end via `kanban.py render`
- `~/opensource/vault/wiki/projects/<repo>/learnings.md` — on `/today ingest` when initiative is known (append to "Initiative: <slug>" section as decisions/learnings)
- `~/opensource/vault/raw/meetings/<slug>/summary.md` — on `/today meeting <slug>` (the on-demand meeting summary; its presence clears the meeting from the pending list)

### Local (skill-only)
- render templates, color codes (skill folder, not data)

### Live external (not stored)
- `gh` PR data — fetched in parallel for stage transitions
- Atlassian MCP — for stale Jira ticket refresh

### Deprecated reads (do NOT use)
- `~/.claude/work_hq/today.json` — replaced by `bucket` frontmatter; do not read
- `~/.claude/work_hq/board.json` — DERIVED from vault now; do not read
- `~/.claude/work_hq/needs_input.json` — moved into per-ticket frontmatter; do not read
- `~/opensource/vault/wiki/hot.md` — archived; do not read or write
- `~/opensource/vault/wiki/log.md` — archived; do not write
- `~/opensource/vault/wiki/projects/<repo>/initiatives/<slug>/{decisions,learnings}.md` — absorbed into `learnings.md` "## Initiative: <slug>" sections; the legacy paths are in `_archive/`
