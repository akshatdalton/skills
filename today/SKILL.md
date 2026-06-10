---
name: today
description: Personal command center — your single source of truth for engineering work across vscode and wipdp. Polymorphic. /today renders the dashboard (priority order + Needs Your Input + Backlog). /today list shows a table view. /today plan enters scope mode (set today vs backlog via the `bucket` field, or by dragging in the Obsidian Kanban board). /today next starts the ★ task via /ship-task. /today ingest <dump> consumes meeting notes / discussion summaries into candidate tickets and decisions. Use when the user says "/today", "what should I work on", "where did I leave off", "show my board", "plan my day", "set today/backlog", or shares a meeting dump and wants it triaged into tasks.
---

> For all per-ticket state mutations, see [shared progress policy](/Users/akshat.v/.claude/skills/_shared/progress-policy.md).

# Today — Engineering Command Center (v0.2 — vault-backed)

Polymorphic skill. One entry point for all daily-planning + dashboard interactions. Routes by sub-mode argument.

**Source of truth (v0.3, Obsidian-Kanban-backed):**
- **Tickets** live in `~/opensource/vault/wiki/projects/<repo>/progress/<ticket>/progress.md` frontmatter — vault is THE board.
- **Today vs Backlog** lives in each ticket's `progress.md` frontmatter under a `bucket: today | backlog` field (default `backlog`). Edited via `progress_fm.py bucket set`.
- **The Obsidian board** at `~/opensource/vault/Tasks.md` is a projection of the vault you can edit by dragging cards. `~/.claude/skills/today/scripts/kanban.py` syncs both ways: readback at the start of every /today, render at the end.
- **Needs-your-input items** live in each ticket's `progress.md` frontmatter under a `needs_input:` field. No separate file.

## Sub-modes

| Invocation | Mode | What it does |
|---|---|---|
| `/today` | render | Default. Show dashboard: Needs Your Input ★, Today's ordered list, Tomorrow, all P0/P1/P2. |
| `/today list` | list | Compact table view. Columns: priority · ticket · stage · repo · PR · initiative. |
| `/today plan` | plan | Interactive: set each ticket's `bucket` (today vs backlog). Asks where each unplanned ticket fits. |
| `/today next` | next | Start the ★ task via `/ship-task`. |
| `/today ingest <dump>` | ingest | Parse a meeting/discussion dump → propose candidate tickets (via `/create-jira-ticket-with-reference`), decisions (into vault learnings.md), and priority placements. |
| `/today retro` | retro | Sprint wrap-up report (lazy-loaded; see `retro.md` in skill dir). |
| `/today oncall [page\|triage\|sheet] …` | oncall | On-call command center for the TM/Career Hub primary rotation: live PagerDuty incidents, due-date-ordered triage tickets, follow-ups, incident-diagnosis playbook (lazy-loaded; see `oncall.md`). `triage` is now a thin alias for the standalone `/rca` skill, where RCA discipline lives. |
| `/today meetings` | meetings | List auto-recorded meeting transcripts awaiting a summary. |
| `/today meeting <slug\|latest>` | meeting | Summarize a recorded meeting → write `summary.md` + surface TL;DR / action items / decisions; offer to ingest items. |

## Pre-entry: refresh state (foundation hook)

On every invocation:

### Step 0 — Fold in Obsidian board edits (Kanban readback)

Before reading the vault, pull any card drags from the Obsidian Kanban board (`~/opensource/vault/Tasks.md`) back into vault frontmatter, so the in-memory board reflects them:

```bash
python3 ~/.claude/skills/today/scripts/kanban.py readback
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

`/loop` and `/pr-watcher` die when the user closes Claude Code, so a "watcher running" status is only meaningful in a live session. For each task where CI is failing, check `watcher_session_id` in progress.md frontmatter (set by `/ship-task` on entry):
- If absent → render `→ no watcher session recorded`
- If present → render `→ resume with: claude -r <watcher_session_id>` (this session has the implementation context — reattaching is faster than starting fresh)

User can either `claude -r <id>` to reattach or run `/ship-task <TICKET>` from the current session. Never auto-schedule /loop, CronCreate, or /pr-watcher from /today.

### Step 8 — Render the Obsidian board (Kanban render)

After all vault writes (steps 3–5), regenerate the board so Obsidian reflects the fresh state:

```bash
python3 ~/.claude/skills/today/scripts/kanban.py render
```

Lanes are Backlog | To Do | In Progress | In Review | Done (lane = function of `state` + `bucket`). Card order within each lane and the `%% kanban:settings %%` block are preserved across renders.

### Step 9 — BRIEFING gather + stitch (new in v0.4)

The ★ BRIEFING block above the existing dashboard is what makes /today an HQ instead of just an engineering board. Six parallel source agents fan out, each returns a structured JSON envelope, brain-recall correlates each item to active vault state, and the result renders above NEEDS YOUR INPUT.

**Dispatch — single-message parallel via `superpowers:dispatching-parallel-agents`:**

Invoke six general-purpose subagents in ONE response (six tool calls in one message — true parallel). Each subagent's prompt is the corresponding spec file's content, with the cursor JSON's `last_run_ts` and current `now` substituted in.

| Subagent | Spec file | Cursor file |
|---|---|---|
| 1 | `~/.claude/skills/today/sources/gcal.md` | `~/.claude/skills/today/state/sources/gcal.json` |
| 2 | `~/.claude/skills/today/sources/meetily.md` | `~/.claude/skills/today/state/sources/meetily.json` |
| 3 | `~/.claude/skills/today/sources/gmail.md` | `~/.claude/skills/today/state/sources/gmail.json` |
| 4 | `~/.claude/skills/today/sources/slack.md` | `~/.claude/skills/today/state/sources/slack.json` |
| 5 | `~/.claude/skills/today/sources/github-review.md` | `~/.claude/skills/today/state/sources/github-review.json` |
| 6 | `~/.claude/skills/today/sources/jira-new.md` | `~/.claude/skills/today/state/sources/jira-new.json` |

Each subagent returns a JSON envelope per the contract in its spec file:

```json
{
  "source": "<name>",
  "fetched_at": "<ISO8601>",
  "cursor_advance": "<ISO8601>",
  "items": [
    {"source_id":"...","ts":"...","title":"...","action":"...","project_hint":"vscode|wipdp|null","urgency":"now|today|fyi"}
  ],
  "fyi_count": <int>,
  "errors": []
}
```

**Latency budget for the whole step: under 30s.** Surface a timing footer in the BRIEFING during v0.4 stabilization; remove once stable.

**Stitch step — correlate to active tickets/initiatives:**

For each item across all six sources, when `project_hint` is set OR the title contains an `ENG-\d+` pattern, run a quick correlation:
- Match against active progress.md frontmatter (use `~/.claude/scripts/progress_fm.py list`)
- If the item references a known ticket, attach `correlated_ticket: ENG-XXXXX` and surface inline as `(→ ENG-XXXXX)` in the render
- If the item references a known initiative (via project's initiative dir), attach `correlated_initiative: <slug>` and surface as `(→ initiative: <slug>)`

This is what makes the BRIEFING feel connected to the rest of the board instead of being a separate inbox.

**Cursor advance — only after successful render:**

After Step 10 (BRIEFING render) completes successfully, write each subagent's `cursor_advance` value back to its cursor file:

```python
import json, pathlib
for r in results:  # list of subagent JSON envelopes
    if r.get("errors"):
        continue  # don't advance cursor on error
    cf = pathlib.Path.home() / ".claude/skills/today/state/sources" / f"{r['source']}.json"
    cur = json.loads(cf.read_text())
    cur["last_run_ts"] = r["cursor_advance"]
    cur["fetched_count"] = len(r["items"])
    cf.write_text(json.dumps(cur, indent=2))
```

If /today crashes mid-render, cursors stay at their previous value — the next run re-shows the items.

### Step 9.5 — Wiki hot-cache read (v2 brain; inline, NO subagent)

Also read the LAST line of `~/.claude/brain-ingest-queue/status.jsonl` (if it exists): the most recent background brain-ingest run. If its `ts` is within the last 24h, render one footer line: `🧠 Last bg ingest: <project> <status> ($<cost>, <relative time>)` — and if `status` is `error`, add `→ check <log path>`. This replaces the old desktop notifications as the visibility channel.

Read the TOP session block only (first `## <date> — ...` block, ~150 words) of `~/opensource/claude-obsidian-test/wiki/hot.md`. Zero-latency, no agent. Two uses:

1. **Render** one footer line in the BRIEFING: `📚 Wiki: <one-line gist of the top block> — [[Page A]] · [[Page B]]` (the 2-3 most actionable wikilinks from that block). Skip the line entirely if the vault is missing or the top block is older than 7 days (stale context is worse than none).
2. **Correlate**: if a BRIEFING item's topic matches a wikilink in the block (e.g. an oncall page arriving while `[[On-call Triage Pattern]]` is hot), append `(📚 wiki has context)` to that item — it tells Akshat a `/brain-recall --v2 <topic>` will be warm.

When Akshat picks a task (`/today next` or names a ticket), suggest `/brain-recall <ticket> --v2` as the kickoff if the wiki has matching pages (quick check: `cd ~/opensource/claude-obsidian-test && python3 scripts/bm25-index.py query "<ticket topic>"` — only when a topic is known; never block the render on it).

### Step 10 — Render the ★ BRIEFING block

Render the BRIEFING above the existing dashboard. Block layout (omit any sub-block where `items[]` is empty and `fyi_count == 0`; otherwise collapse to a single line like `(no new since HH:MM)`):

```
★ BRIEFING (<n total action items across sources>)
─────────────────────────────────────────────────────
  📅 MEETINGS TODAY (<n>)             [from gcal]
    09:30  Sprint review · @prabh + @samyak           [join (meetily armed)]
    14:00  1:1 with @manager                          [join]

  🎙  MEETILY — PROPOSED (<n>)         [from meetily; need user confirm]
    [2026-05-30-design-review]
      → propose ticket: "Add OWASP scan to wipdp CI"
      → save decision: "Q3 focus = source-integration-polish" (→ initiative: rag-for-tm)

  💬 SLACK — action (<n>, since <last_run_ts>)        [from slack]
    #eng-vscode   @prabh: "review the diff before EOD?"  (→ ENG-191517)
    #wipdp-pod    @samyak: "RAG eval still failing — owner?"

  📧 GMAIL — action (<n of M unread since <ts>)       [from gmail]
    @legal-team: Re: data retention v3 — needs sign-off
    (<noise_count> noise filtered)

  🔍 GITHUB REVIEW QUEUE (<n>)         [from github-review]
    vscode#105800  @prabh    agent-builder: add streaming         3d old
    wipdp#4521     @samyak   rag-eval-pipeline: fix flaky test    1d old

  📋 JIRA — new assignments (<n> since <ts>)          [from jira-new]
    ENG-194001  P1  vscode  todo  (assigned by @lead)
```

The existing dashboard renders BELOW the BRIEFING, unchanged. PICK block adds `[confirm meetily]` when proposed items are pending.

### Step 11 — Tooling rule reminder

Source agents use the tools listed in their spec. The /today main thread:
- gh CLI for the dashboard's existing PR refresh (Step 3) — unchanged
- Atlassian MCP for the dashboard's existing Jira refresh (Step 4) — unchanged
- progress_fm.py for any frontmatter writes — see [shared progress policy](/Users/akshat.v/.claude/skills/_shared/progress-policy.md)
- NEVER `slack_send_*` / `slack_schedule_*` anywhere in this skill tree — per `[[feedback-slack-send-requires-caps-yes]]`

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
4. Run `python3 ~/.claude/skills/today/scripts/kanban.py render`, then render the dashboard.

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

## Mode: oncall

Read `~/.claude/skills/today/oncall.md` for full instructions (lazy-loaded — only when `/today oncall …` is invoked). Drives the TM/Career Hub primary on-call rotation: live PagerDuty incidents (service `P0IHZZS`, schedule `PBWVBGY`), due-date-ordered triage tickets, daily follow-ups, the incident-diagnosis DB playbook, and the per-sprint tracking sheet. Sub-args: `page <id>` (run diagnosis, never auto-ack), `triage <TICKET>` (thin alias for `/rca <TICKET>` — RCA discipline lives in the standalone `/rca` skill; adds the `TM on call` PR label if `/ship-task` is taken), `sheet` (log statuses). When `aws` is unauthed, surface the AWS console link instead of failing.

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

## Storage layout (v0.4 — work_hq retired)

```
~/opensource/vault/wiki/projects/                    ← single source of truth for tickets
├── vscode/progress/
│   ├── ENG-XXXXX/
│   │   ├── progress.md                              # frontmatter = board entry; body = task narrative
│   │   └── plan.md                                  # original plan (created by /work-on-jira-task or /think)
│   └── archive/
│       └── ENG-YYYYY/{progress.md, plan.md}
└── wipdp/progress/                                   (same shape)

~/.claude/scripts/progress_fm.py                      ← CLI helper for progress.md frontmatter + section mutations
~/.claude/skills/today/scripts/kanban.py              ← Obsidian Kanban sync (readback / render)
~/.claude/skills/get-pr-ready-to-merge/scripts/fetch_ci_log.sh  ← CI log fetcher (used by /get-pr-ready-to-merge)
```

For ticket frontmatter mutations (state, `bucket`, needs_input, etc.), use `progress_fm.py set <TICKET> --field …` / `progress_fm.py bucket set <TICKET> --to today` / `progress_fm.py needs-input add|clear`. `bucket: today|backlog` controls Today vs Backlog placement.

**kanban.py cheatsheet**:
```bash
python3 ~/.claude/skills/today/scripts/kanban.py readback   # fold Obsidian drags -> vault frontmatter (run at /today start)
python3 ~/.claude/skills/today/scripts/kanban.py render     # vault -> Tasks.md (run at /today end)
python3 ~/.claude/skills/today/scripts/kanban.py sync       # readback then render
```

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
- `~/opensource/vault/wiki/projects/{vscode,wipdp}/progress/ENG-*/progress.md` — all active tickets (frontmatter is the board entry); read via `~/.claude/scripts/progress_fm.py list` or inline awk
- `~/opensource/vault/Tasks.md` — the Obsidian Kanban board; read back at /today start via `kanban.py` (drags fold into `bucket`/`state`)
- (Optional, `--include-archived`): `~/opensource/vault/wiki/projects/*/progress/archive/ENG-*/progress.md`
- `~/opensource/vault/raw/meetings/*/{transcript.md, metadata.json, summary.md}` — meetily-rec output + auto-summaries (transcript without `summary.md` = pending for the meetily source agent)
- `~/.claude/skills/today/state/sources/<source>.json` — six per-source cursor files for the BRIEFING block (Step 9)
- `~/.claude/skills/today/sources/<source>.md` — six source-agent spec files (passed as subagent prompts in Step 9)

### Writes
- `vault/wiki/projects/<repo>/progress/<ticket>/progress.md` — frontmatter via `~/.claude/scripts/progress_fm.py` (see [shared progress policy](/Users/akshat.v/.claude/skills/_shared/progress-policy.md)); body is brain-ingest's responsibility
- `~/opensource/vault/Tasks.md` — regenerated at /today end via `kanban.py render`
- `~/opensource/vault/wiki/projects/<repo>/learnings.md` — on `/today ingest` when initiative is known (append to "Initiative: <slug>" section as decisions/learnings)
- `~/opensource/vault/raw/meetings/<slug>/summary.md` — auto-written by the meetily source agent in Step 9 OR on `/today meeting <slug>` (the on-demand path; presence clears it from pending)
- `~/.claude/skills/today/state/sources/<source>.json` — cursor advance written after successful BRIEFING render (Step 9)

### Local (skill-only)
- `~/.claude/skills/today/scripts/kanban.py` + `.kanban_state.json` — Obsidian sync (moved from `~/.claude/work_hq/` in v0.4)
- render templates, color codes (skill folder, not data)

### Live external (not stored)
- `gh` PR data — fetched in parallel for stage transitions
- Atlassian MCP — for stale Jira ticket refresh
- Source agents (Step 9) fetch live data per their specs; the main thread never persists message bodies, just the cursor + BRIEFING render

### Deprecated reads (do NOT use)
- `~/.claude/work_hq/**` — DELETED in v0.4. Per-ticket state is in vault progress.md (read via progress_fm.py); operational state for /today is under `state/sources/`.
- `~/opensource/vault/wiki/hot.md` — archived; do not read or write
- `~/opensource/vault/wiki/log.md` — archived; do not write
- `~/opensource/vault/wiki/projects/<repo>/initiatives/<slug>/{decisions,learnings}.md` — absorbed into `learnings.md` "## Initiative: <slug>" sections; the legacy paths are in `_archive/`
