---
name: today
description: Personal command center — your single source of truth for engineering work across vscode and wipdp. Polymorphic. /today renders the dashboard (priority order + Needs Your Input + Tomorrow). /today list shows a table view. /today plan enters daily-scope mode (set today/tomorrow ordered ticket lists). /today next starts the ★ task via /ship-task. /today ingest <dump> consumes meeting notes / discussion summaries into candidate tickets and decisions. Use when the user says "/today", "what should I work on", "where did I leave off", "show my board", "plan my day", "set today/tomorrow", or shares a meeting dump and wants it triaged into tasks.
---

# Today — Engineering Command Center

Polymorphic skill. One entry point for all daily-planning + dashboard interactions. Routes by sub-mode argument.

## Sub-modes

| Invocation | Mode | What it does |
|---|---|---|
| `/today` | render | Default. Show dashboard: Needs Your Input ★, Today's ordered list, Tomorrow, all P0/P1/P2. |
| `/today list` | list | Compact table view. Columns: priority · ticket · stage · repo · PR · initiative. |
| `/today plan` | plan | Interactive: set today_ids and tomorrow_ids ordered lists. Asks where each unplanned ticket fits. |
| `/today next` | next | Start the ★ task via `/ship-task`. |
| `/today ingest <dump>` | ingest | Parse a meeting/discussion dump → propose candidate tickets (via `/create-jira-ticket-with-reference`), decisions (into initiative), and priority placements. |
| `/today retro` | retro | Sprint wrap-up report: query all sprint tickets, calculate Done vs Planned SP (trusting current Jira values — run after you've reverted any automation-inflated SPs), draft Akshat's row, offer to prepend the Sprint section to the retro doc. |

## Pre-entry: refresh state (foundation hook)

On every invocation:

1. Read `~/.claude/work_hq/board.json`, `today.json`, `needs_input.json`. **Stale-date check:** if `today.json.date < today`, immediately auto-carry forward by running `update.py today set --today <current today_ids joined by comma> --tomorrow <current tomorrow_ids joined by comma>` (this stamps the new date; the stage-transition pass in step 2 will clean up any items that have since merged). Add a `(plan carried from <old-date>)` note in the dashboard header — no user intervention needed.

**Repo → GH mapping** (use these exact prefixes; do not guess org names):
```
vscode   →   GH_HOST=github.com gh ... --repo EightfoldAI/vscode
wipdp    →   GH_HOST=github.com gh ... --repo EightfoldAI/wipdp
```

2. **For each task with `pr`** — refresh in parallel using `gh` CLI (NOT GitHub MCP). Fire **all** PR fetches as separate Bash tool calls in the **same** response so they run concurrently. Use the Repo → GH mapping above so the first batch always succeeds:
   ```bash
   GH_HOST=github.com gh pr view <N> --repo EightfoldAI/<repo> --json state,mergeable,mergeStateStatus,reviewDecision,statusCheckRollup,headRefOid,mergedAt
   ```
   Then for each PR's `headRefOid`, also fetch the **commit status** channel in parallel (catches external CI like NPM Test, Playwright, CI Test Suite):
   ```bash
   GH_HOST=github.com gh api repos/EightfoldAI/<repo>/commits/<sha>/status --jq '.state'
   GH_HOST=github.com gh api repos/EightfoldAI/<repo>/commits/<sha>/check-runs --jq '[.check_runs[]|.conclusion]'
   ```
   Reconcile both channels — task is `ci`-failing if EITHER has a failure. Apply auto-stage-transitions:
   - merged → `merged` (also remove from today/tomorrow)
   - approved + both channels green + 0 unresolved → `ready-to-merge` + add to needs_input ("merge it")
   - any channel reports `failure` → `ci` + add to needs_input ("ci-failing → /ship-task <id>")
   - else → keep `in-review`
3. **For each task WITHOUT a PR** (stage todo/in-progress) OR with `last_updated` > 1h old — batch-call `mcp__claude_ai_Atlassian__getJiraIssue` in parallel to refresh title, status, sprint, priority, assignee. This is the only place Atlassian MCP is used; GitHub data always comes from `gh`. **Before the first Atlassian call**, run `ToolSearch select:mcp__claude_ai_Atlassian__getJiraIssue` to load the schema — it is deferred and not callable without this step.
4. Write back via `update.py set` for any changes.

**Tooling rule:** gh CLI for GitHub, Atlassian MCP for Jira, never the other way.

**4.5. Auto-render `vault/wiki/hot.md` (single source of truth bridge):** after the work_hq refresh, rewrite the "Active Right Now" section of `~/opensource/vault/wiki/hot.md` from the post-refresh state. This closes the divergence between work_hq and vault — every dashboard render keeps the vault hot.md current. Format:

```
## Active Right Now
- **vscode**: <ENG-XXX> — <branch> — <stage>  (or "no active task")
- **wipdp**: <ENG-XXX> — <branch> — <stage>
- **magnetx**: <task>  (if any in board)
```

Source: top in-progress / in-review item per repo from `today.json × board.json`. If a repo has no in-flight task, write "no active task". This is a REWRITE of just that section; preserve other sections (Open Threads, Last Session, Recent Corrections) verbatim.

Also append to `~/opensource/vault/wiki/log.md` only on `/today plan` (scope changed) or `/today ingest`. Don't log every render — too noisy.

5. **Watcher-status check (per task with PR + CI failing).** /loop and /pr-watcher die when the user closes Claude Code, so a "watcher running" status is only meaningful in a live session. For each task where CI is failing, check `shared_context.watcher_session_id` (set by /ship-task on entry):
   - If absent → render `→ no watcher session recorded`
   - If present → render `→ resume with: claude -r <watcher_session_id>` (this is the session that already has the implementation context — reattaching is faster than starting fresh)
   The user can then either `claude -r <id>` to reattach, or run `/ship-task <TICKET>` from the current session to triage from scratch. Never auto-schedule /loop, CronCreate, or /pr-watcher from /today.

## Mode: render (default)

Output format:

```
WORK HQ — <date>

★ NEEDS YOUR INPUT (<n>)
─────────────────────────────────────────────────────
  ENG-191517  ci-failing          → /ship-task ENG-191517   (or: claude -r 19f4e417-…)
  ENG-191692  judgment-call       → review @samyak's naming comment
  ENG-184901  group-3-design      → decide index naming convention
  ENG-191639  ci-failing          → no watcher session recorded; run /ship-task ENG-191639

TODAY (<n>)
─────────────────────────────────────────────────────
  1. P0  ENG-191517  in-review     vscode#105712  [agent-builder]
  2. P0  ENG-191692  todo          wipdp           [agent-builder]
  3. P1  ENG-185432  in-progress   vscode          [-]

TOMORROW (<n>)
─────────────────────────────────────────────────────
  1. P1  ENG-184567  todo          vscode          [-]
  2. P2  ENG-184901  testing       wipdp           [gate-cleanup]

OTHER ACTIVE
─────────────────────────────────────────────────────
  P2  ENG-186208  todo          wipdp  [rag-pipeline]

PICK
  [N]   start task#N             [next]   start ★
  [plan] re-plan day             [list]   table view
  [ingest <text>] consume dump   [add ENG-N today|tomorrow]
```

★ = highest-priority item needing your input. If no needs_input items, ★ goes to the first in-progress task in TODAY.

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
[M2]   P2   ENG-184901   testing        wipdp    #62       gate-cleanup (tomorrow)
─────  ───  ───────────  ─────────────  ───────  ────────  ──────────────

NEEDS YOUR INPUT
ENG-191517  ready-to-merge  → merge the PR
ENG-191692  judgment-call   → review @samyak naming comment
```

T# = today position, M# = tomorrow (manana) position.

## Mode: plan

Interactive daily scope-setting. Steps:

1. List all tasks with `stage ∈ {todo, in-progress, in-review, ci, testing, ready-to-merge}` not yet placed in `today_ids` or `tomorrow_ids`.
2. For each, ask: *"Where does ENG-XXXXX go? [today / tomorrow / skip / archive]"* — accept ordered position too: "today 2".
3. Allow user to dump a free-form list: *"Today: ENG-191517, ENG-191692, ENG-185432. Tomorrow: ENG-184567."*
4. Apply via `update.py today set --today ID,ID --tomorrow ID,ID`.
5. Render the new plan.

Also clears `needs_input` items the user marks resolved during planning.

## Mode: next

1. Compute ★ (highest-priority needs_input item; if none, first in-progress in today_ids; if none, first todo in today_ids).
2. Surface: *"Starting <TICKET_ID>: <title> [stage=<s>]. Routing via /ship-task."*
3. `cd` to the right repo if needed (based on task's `repo` field).
4. `git checkout` the branch if it exists.
5. Invoke `Skill(skill="ship-task", args="<TICKET_ID>")`.

## Mode: ingest <dump>

Consume meeting notes, discussion summaries, brain dumps. Steps:

1. Save raw to `~/opensource/vault/wiki/inbox/<date>-<topic>.md` (vault inbox; `/brain-ingest` weekly routes it). Legacy `~/.claude/work_hq/inbox/` path no longer used for new dumps but kept for back-compat reading.
2. Extract:
   - **Candidate tickets** (action items, "we should do X") → propose `/create-jira-ticket-with-reference` for each, infer initiative if discussion is about an existing one.
   - **Decisions** ("we agreed to use Y") → append to `~/opensource/vault/wiki/projects/<repo>/initiatives/<slug>/decisions.md` if initiative known (`<repo>` from board task with this initiative_slug), otherwise queue with the dump. Initiative knowledge moved from work_hq → vault on 2026-05-03.
   - **Learnings** ("we discovered Z") → append to vault `~/opensource/vault/wiki/projects/<repo>/initiatives/<slug>/learnings.md`.
3. Show extracted items in a table; ask user to confirm/edit each before creating tickets.
4. After ticket creation, ask where each new one fits in today/tomorrow plan (delegates to plan mode for placement).

## Mode: retro

Read `~/.claude/skills/today/retro.md` for full instructions (lazy-loaded — only when `/today retro` is invoked).

## Reactive integration (other skills push to /today)

`/today` does not poll — other skills write directly to the same files:

| Skill | Effect on /today |
|---|---|
| `/create-jira-ticket-with-reference` | adds ticket to board + `needs-input add --reason "new-ticket-priority"` so plan mode prompts placement |
| `/ship-task` (loop self-terminate) | `needs-input add` with stop reason; surfaces in ★ Needs Your Input |
| `/work-on-jira-task` (start) | sets stage=in-progress; appears in dashboard |
| `/submit-pr` | sets stage=in-review; PR appears |
| `/get-pr-ready-to-merge` | updates ci_state, review_state |
| Merged externally | next `/today` invocation auto-detects via gh refresh and archives |

## Storage layout

```
~/.claude/work_hq/                  ← operational state (Memory tier)
├── board.json                      all tasks (read+write)
├── today.json                      {date, today_ids[], tomorrow_ids[], notes}
├── needs_input.json                {items: [{task_id, reason, action, added_at}]}
├── inbox/<date>.md                 legacy ingest dumps (kept for back-compat; new dumps go to vault inbox)
└── initiatives/<slug>/
    └── ticket-graph.md             (only this stays in work_hq — operational pointer)

~/opensource/vault/wiki/            ← durable knowledge (DB tier) + live state (Memory tier)
├── hot.md                          live "Active Right Now" (auto-rendered by /today)
├── log.md                          append-only event log
├── inbox/                          new dumps land here for /brain-ingest weekly routing
└── projects/<repo>/initiatives/<slug>/
    ├── charter.md                  (moved from work_hq on 2026-05-03)
    ├── decisions.md                
    ├── learnings.md                
    └── e2e-flow.md                 
```

work_hq mutations go through `python3 ~/.claude/work_hq/update.py`. Never edit JSONs by hand. Vault files are markdown — append directly.

**update.py cheatsheet** (all common patterns; `--field` accepts `key=value`):
```bash
# task fields
update.py set <id> --field stage=merged --field merged_at=2026-05-02T00:14:07Z --field ci_state=green
update.py set <id> --field priority=P1 --field title="new title"

# today/tomorrow list
update.py today set --today ENG-A,ENG-B --tomorrow ENG-C   # replaces entire lists + stamps date
update.py today add <id>                                     # append to today_ids
update.py today remove <id>                                  # remove from today_ids or tomorrow_ids

# needs_input
update.py needs-input add <id> --reason ci-failing --action "fix CI on #105712"
update.py needs-input clear <id>                             # removes all items for that task
```

## Workflow ending

```
───── /today ─────
mode      : <render|list|plan|next|ingest>
needs_input: <n>
today     : <n> tasks   (or: <ticket-id> started via /ship-task)
tomorrow  : <n> tasks
────────────────────

───── artifacts ─────
Board     : ~/.claude/work_hq/board.md
Today     : ~/.claude/work_hq/today.json
Inbox     : ~/opensource/vault/wiki/inbox/<latest>   (only if ingested; legacy work_hq inbox kept for back-compat)
Hot       : ~/opensource/vault/wiki/hot.md   (auto-refreshed on render/plan)
─────────────────────
```

---

## Data Contract

### Reads (DB)
- (none for the dashboard render — DB context is loaded on task entry by `/work-on-jira-task`, not here)

### Reads (Memory)
- `~/.claude/work_hq/board.json` — all tasks
- `~/.claude/work_hq/today.json` — today/tomorrow ordering
- `~/.claude/work_hq/needs_input.json` — blocking items
- `~/opensource/vault/wiki/hot.md` — for "Last Session" + "Recent Corrections" surfacing
- `~/opensource/vault/wiki/projects/*/open-threads.md` — multi-day blockers (filtered to in-flight)

### Writes (Memory)
- `~/opensource/vault/wiki/hot.md` — refresh "Active Right Now" section from `today.json` × `board.json` after every render or `/today plan` (auto-sync; closes the divergence loop)
- `~/opensource/vault/wiki/log.md` — append on `/today plan` (scope changed) and `/today ingest` (dump consumed)
- `~/.claude/work_hq/today.json` — write today/tomorrow ordering on `/today plan`
- `~/opensource/vault/wiki/projects/<repo>/initiatives/<slug>/{decisions,learnings}.md` — on `/today ingest` when initiative is known
- `~/opensource/vault/wiki/inbox/<date>-<slug>.md` — raw dump landing site on `/today ingest`

### Local (skill-only)
- render templates, color codes (skill folder, not data)

### Live external (not stored)
- `gh` PR data — fetched in parallel for stage transitions
- Atlassian MCP — for stale Jira ticket refresh
