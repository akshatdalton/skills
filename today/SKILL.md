---
name: today
description: Personal command center — your single source of truth for engineering work across vscode and wipdp. Polymorphic. /today renders the dashboard (priority order + Needs Your Input + Tomorrow). /today list shows a table view. /today plan enters daily-scope mode (set today/tomorrow ordered ticket lists). /today next starts the ★ task via /ship-task. /today ingest <dump> consumes meeting notes / discussion summaries into candidate tickets and decisions. Use when the user says "/today", "what should I work on", "where did I leave off", "show my board", "plan my day", "set today/tomorrow", or shares a meeting dump and wants it triaged into tasks.
---

# Today — Engineering Command Center (v0.2 — vault-backed)

Polymorphic skill. One entry point for all daily-planning + dashboard interactions. Routes by sub-mode argument.

**Source of truth (v0.2, post-migration):**
- **Tickets** live in `~/opensource/vault/wiki/projects/<repo>/progress/<ticket>/progress.md` frontmatter — vault is THE board.
- **Daily ordering** (today / tomorrow) lives in `~/.claude/work_hq/today.json` — operational state owned by /today, not project knowledge.
- **Needs-your-input items** live in each ticket's `progress.md` frontmatter under a `needs_input:` field. No separate file.
- `~/.claude/work_hq/board.json` is **deprecated** (Phase B migration done; vault is the single source). /today no longer reads it.

## Sub-modes

| Invocation | Mode | What it does |
|---|---|---|
| `/today` | render | Default. Show dashboard: Needs Your Input ★, Today's ordered list, Tomorrow, all P0/P1/P2. |
| `/today list` | list | Compact table view. Columns: priority · ticket · stage · repo · PR · initiative. |
| `/today plan` | plan | Interactive: set today_ids and tomorrow_ids ordered lists. Asks where each unplanned ticket fits. |
| `/today next` | next | Start the ★ task via `/ship-task`. |
| `/today ingest <dump>` | ingest | Parse a meeting/discussion dump → propose candidate tickets (via `/create-jira-ticket-with-reference`), decisions (into vault learnings.md), and priority placements. |
| `/today retro` | retro | Sprint wrap-up report (lazy-loaded; see `retro.md` in skill dir). |

## Pre-entry: refresh state (foundation hook)

On every invocation:

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
- `ticket`, `title`, `project` (vscode|wipdp), `branch`, `pr`, `pr_state`, `state`, `priority`, `initiative`, `created`, `last-touched`
- `needs_input` block if present (`{reason, action, added_at}`)
- `session_ids` (informational; not surfaced in dashboard)

This in-memory list IS the board. No `board.json` read. No per-file `Read` calls.

### Step 2 — Read today.json + stale-date check

Read `~/.claude/work_hq/today.json` (`{date, today_ids, tomorrow_ids, notes}`). If `today.json.date < <current date>`, immediately auto-carry forward via `update.py today set --today <current today_ids> --tomorrow <current tomorrow_ids>` (this stamps the new date; the stage-transition pass in step 3 will clean up any items that have since merged). Add a `(plan carried from <old-date>)` note in the dashboard header — no user intervention needed.

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
- merged → state `merged`, `pr_state: MERGED` (also remove from today/tomorrow)
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

## Mode: render (default)

Output format:

```
WORK HQ — <date>

★ NEEDS YOUR INPUT (<n>)
─────────────────────────────────────────────────────
  ENG-191942  merge-conflict      → rebase PR #70 onto main (CONFLICTING)
  ENG-191692  judgment-call       → review @samyak's naming comment
  ENG-184901  group-3-design      → decide index naming convention

TODAY (<n>)
─────────────────────────────────────────────────────
  1. P0  ENG-191517  in-review     vscode#105712  [agent-builder]
  2. P0  ENG-191692  todo          wipdp           [agent-builder]
  3. P1  ENG-185432  in-progress   vscode          [-]

TOMORROW (<n>)
─────────────────────────────────────────────────────
  1. P1  ENG-184567  todo          vscode          [-]

OTHER ACTIVE
─────────────────────────────────────────────────────
  P2  ENG-186208  todo          wipdp  [rag-pipeline]

PICK
  [N]   start task#N             [next]   start ★
  [plan] re-plan day             [list]   table view
  [ingest <text>] consume dump   [add ENG-N today|tomorrow]
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
[M1]   P1   ENG-184567   todo           vscode   -         -          (tomorrow)

NEEDS YOUR INPUT
ENG-191942  merge-conflict  → rebase PR #70 onto main (CONFLICTING)
```

T# = today position, M# = tomorrow (manana) position. Add `--include-archived` to also walk `progress/archive/` for full history.

## Mode: plan

Interactive daily scope-setting. Steps:

1. List all tasks with `state ∈ {todo, in-progress, in-review, ci, testing, ready-to-merge}` not yet placed in `today_ids` or `tomorrow_ids`.
2. For each, ask: *"Where does ENG-XXXXX go? [today / tomorrow / skip / archive]"* — accept ordered position too: "today 2".
3. Allow user to dump a free-form list: *"Today: ENG-191517, ENG-191692, ENG-185432. Tomorrow: ENG-184567."*
4. Apply via `update.py today set --today ID,ID --tomorrow ID,ID`.
5. Render the new plan.

Also clears `needs_input` blocks from progress.md frontmatter for any items the user marks resolved during planning (use a small inline edit, not update.py).

## Mode: next

1. Compute ★ (highest-priority ticket with `needs_input` block; if none, first in-progress in today_ids; if none, first todo in today_ids).
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
3. After ticket creation, ask where each new one fits in today/tomorrow plan (delegates to plan mode for placement).

> **Note on inbox**: the legacy `vault/wiki/inbox/` and `~/.claude/work_hq/inbox/` paths have been retired in v0. Dumps land directly into vault learnings.md initiative sections + new ticket progress files. No separate inbox queue.

## Mode: retro

Read `~/.claude/skills/today/retro.md` for full instructions (lazy-loaded — only when `/today retro` is invoked).

## Reactive integration (other skills push to /today via vault writes)

`/today` does not poll — other skills write directly to vault progress.md files:

| Skill | Effect on /today |
|---|---|
| `/create-jira-ticket-with-reference` | Creates `progress/<ticket>/progress.md` with `needs_input: {reason: new-ticket-priority, action: place in today/tomorrow plan}` so plan mode prompts placement |
| `/brain-ingest <ticket>` | Updates progress.md frontmatter (state, pr, pr_state, session_ids, last-touched). On merge: archives the ticket dir → /today no longer surfaces it. |
| `/ship-task` (loop self-terminate) | Updates progress.md frontmatter `needs_input` with stop reason; surfaces in ★ |
| `/work-on-jira-task` (start) | sets state=in-progress (via brain-ingest at session end if user fires it) |
| `/submit-pr` | sets state=in-review, pr=N (via brain-ingest at session end) |
| `/get-pr-ready-to-merge` | updates state, pr_state (via brain-ingest at session end) |
| Merged externally | next `/today` invocation auto-detects via gh refresh in step 3 |

## Storage layout (v0.2)

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

`update.py` is now scoped to today.json only. The `update.py set <id>` (board task fields) and `update.py needs-input add` commands are dead — direct progress.md frontmatter edits replace them.

**update.py cheatsheet (v0.2 — today.json only)**:
```bash
update.py today set --today ENG-A,ENG-B --tomorrow ENG-C   # replaces entire lists + stamps date
update.py today add <id>                                     # append to today_ids
update.py today remove <id>                                  # remove from today_ids or tomorrow_ids
```

For ticket frontmatter mutations (state, needs_input, etc.), use direct file edits on `vault/wiki/projects/<repo>/progress/<ticket>/progress.md`. No CLI helper needed — frontmatter is small enough to edit precisely.

## Workflow ending

```
───── /today ─────
mode      : <render|list|plan|next|ingest>
needs_input: <n>
today     : <n> tasks   (or: <ticket-id> started via /ship-task)
tomorrow  : <n> tasks
────────────────────

───── artifacts ─────
Vault     : ~/opensource/vault/wiki/projects/*/progress/*/progress.md
Today     : ~/.claude/work_hq/today.json
─────────────────────
```

---

## Data Contract

### Reads
- `~/opensource/vault/wiki/projects/{vscode,wipdp}/progress/ENG-*/progress.md` — all active tickets (frontmatter is the board entry)
- `~/.claude/work_hq/today.json` — today/tomorrow ordering
- (Optional, `--include-archived`): `~/opensource/vault/wiki/projects/*/progress/archive/ENG-*/progress.md`

### Writes
- `vault/wiki/projects/<repo>/progress/<ticket>/progress.md` — **frontmatter only** (state, pr_state, last-touched, needs_input). Body is brain-ingest's responsibility.
- `~/.claude/work_hq/today.json` — today/tomorrow ordering on `/today plan`
- `~/opensource/vault/wiki/projects/<repo>/learnings.md` — on `/today ingest` when initiative is known (append to "Initiative: <slug>" section as decisions/learnings)

### Local (skill-only)
- render templates, color codes (skill folder, not data)

### Live external (not stored)
- `gh` PR data — fetched in parallel for stage transitions
- Atlassian MCP — for stale Jira ticket refresh

### Deprecated reads (do NOT use in v0.2)
- `~/.claude/work_hq/board.json` — DERIVED from vault now; do not read
- `~/.claude/work_hq/needs_input.json` — moved into per-ticket frontmatter; do not read
- `~/opensource/vault/wiki/hot.md` — archived; do not read or write
- `~/opensource/vault/wiki/log.md` — archived; do not write
- `~/opensource/vault/wiki/projects/<repo>/initiatives/<slug>/{decisions,learnings}.md` — absorbed into `learnings.md` "## Initiative: <slug>" sections; the legacy paths are in `_archive/`
