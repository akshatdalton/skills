---
name: magnetx
description: MagnetX command center — session start dashboard for solo founder workflow. Polymorphic, mirrors /today shape. /magnetx renders dashboard (★ Needs Your Input + Today/Tomorrow + Phases + X streak + Decisions + PICK). /magnetx list shows compact table. /magnetx plan sets today/tomorrow ordered task lists. /magnetx next fires /magnetx-ship on the ★ task. /magnetx engage shortcuts to the daily X engagement loop. /magnetx ingest <dump> consumes brain dumps into Notion tasks + decisions + learnings. Use when user starts a session in magnetx directory, says "what should I work on", "show me status", "magnetx status", "where did I leave off", or invokes /magnetx. Also trigger when user seems unsure what to do next on MagnetX.
---

# /magnetx — MagnetX Command Center

Polymorphic skill. One entry point for daily-planning + dashboard interactions. Routes by sub-mode argument. Mirrors `/today` shape so muscle memory transfers from eightfold workflow.

## Sub-modes

| Invocation | Mode | What it does |
|---|---|---|
| `/magnetx` | render | Default. Show dashboard: ★ Needs Your Input, Today, Tomorrow, Phases, X Growth, Open Decisions, Sources, PICK + Recommendation. |
| `/magnetx list` | list | Compact table view. Columns: order · track · task · phase · status · priority · notion-id. |
| `/magnetx plan` | plan | Interactive: set `today_ids` + `tomorrow_ids` ordered lists. Free-form dump accepted. |
| `/magnetx next` | next | Fire `Skill(magnetx-ship)` on the ★ task. |
| `/magnetx engage` | engage | Shortcut: `Skill(magnetx-ship)` on most recent Engagement task (or create one). |
| `/magnetx ingest <dump>` | ingest | Parse meeting/idea dump → propose Notion tasks (typed for routing) + decisions + learnings. |

---

## Pre-entry: refresh state

On every invocation:

1. Read `~/.claude/skills/magnetx/cache.json` with Read tool.
2. If file valid + `updated_at` < 6h old → use cached data, skip Notion calls entirely.
3. If cache stale (>6h) or missing → kick off **single background agent** to refresh:
   - Fetch HQ Context page `34eecb1d-39d0-814e-b03e-c39f13d1c254` (`mcp__claude_ai_Notion__notion-fetch`)
   - Search Task Board data source `a119bf6a-603e-4f51-b602-fc7ffb4e445e` (group by Phase + Status)
   - Search X Tracker data source `4b9b90de-9252-4da7-a76c-f40fa89c610f` (last session date + streak)
   - Write back `cache.json` (preserve `today_ids`, `tomorrow_ids`, `shared_context`)
   - Render uses whatever's on disk — never blocks.
4. For In-Progress tasks: include `last_updated` for "stuck-Nd" detection.

**Tooling rule:** Notion MCP for tasks/HQ/tracker. `gh` CLI on `akshatdalton` for git/PR ops. Never the other way.

---

## Mode: render (default)

Output format. Generous spacing for iTerm2; no dense tables.

```
MAGNETX HQ — <date>

★ NEEDS YOUR INPUT (<n>)
─────────────────────────────────────────────────────
  STREAK    cold-9d            → /magnetx engage
  T-104     stuck-3d           → resume "Apify scoring batch"
  DEC-1     open-decision      → niche-pool seeding strategy
  THREAD    parked-12d         → review apify-actor-uptime

TODAY (<n>)
─────────────────────────────────────────────────────
  1.  build     Apify niche fingerprint        in-progress    [P0]
  2.  build     Daily engagement feed UI       todo           [P1]
  3.  content   "Why I built engagement-first" thread          todo           [P2]

TOMORROW (<n>)
─────────────────────────────────────────────────────
  1.  build     Reply angle suggester          todo           [P1]
  2.  decide    Pricing tier names             todo           [P1]

PHASES
─────────────────────────────────────────────────────
  ★ Build MVP            <done>/<total>    Last: <date>
    Validate             <done>/<total>    Last: <date>
    Personal X Growth    <done>/<total>    Last: <date>
    Concierge            SKIPPED
    Launch               <done>/<total>    Blocked on: <X>

X GROWTH
─────────────────────────────────────────────────────
  Streak: <N> days (last: <date>)

OPEN DECISIONS (<n>)
─────────────────────────────────────────────────────
  1. <one-liner>

SOURCES
─────────────────────────────────────────────────────
  HQ Context: https://www.notion.so/34eecb1d39d0814eb03ec39f13d1c254
  Task Board: https://www.notion.so/a119bf6a603e4f51b602fc7ffb4e445e
  X Tracker:  https://www.notion.so/4b9b90de92524da7a76cf40fa89c610f

PICK
  [N]      start task#N           [next]    fire /magnetx-ship on ★
  [plan]   re-plan day            [list]    table view
  [engage] daily X engagement     [ingest <text>]   consume dump

MY RECOMMENDATION
─────────────────────────────────────────────────────
**<phase>** is the move. <one-line why>.

1. <strongest reason>
2. <why other phases can wait>
3. <what becomes easier once this ships>

**First task: <task name>.** <one-line why this task>.

Want me to fire `/magnetx-ship` on it? Or <alternative>?
```

### ★ Needs Your Input — derivation rules

Computed at render time, NOT stored. Sources, in priority order:

| Trigger | Surfaces as | Action |
|---|---|---|
| X streak ≥ 7d cold (last_session_date older than 7d) | `STREAK  cold-Nd` | `/magnetx engage` |
| In-Progress task idle ≥ 2d | `<id>  stuck-Nd` | `/magnetx-ship <id>` |
| Open decision in HQ Context (status=Open) | `DEC-N  open-decision` | resolve via `/magnetx-ship` decide track |
| Phase change ready (last task of active phase done → next phase unblocks) | `PHASE  unblock` | review next phase tasks |
| Vault `projects/magnetx/open-threads.md` H2 with `Last touched` > 7d | `THREAD  parked-Nd` | review or close |

★ ordering: cold-streak (rebuilds habit) → stuck-build (releases throughput) → open-decision (unblocks future) → parked-thread (cleanup). If no needs_input items, ★ goes to first In-Progress task in TODAY; if none, first Todo in TODAY.

### MY RECOMMENDATION block

After PICK, **always** include a recommendation narrative (kept from original `/magnetx-hq`):
- Lead with phase, then justify (3–5 lines).
- Connect phases to each other; show ordering matters.
- End with "want me to fire /magnetx-ship?" call-to-action.

If needs_input is non-empty, recommend the top ★ item instead of the active phase.

---

## Mode: list

Compact table for scanning:

```
MAGNETX HQ — <date>

ORDER  TRACK    TASK                                 PHASE          STATUS         PRI    NOTION-ID
─────  ───────  ───────────────────────────────────  ─────────────  ─────────────  ─────  ──────────
[T1]   build    Apify niche fingerprint              Build MVP      in-progress    P0     T-104
[T2]   build    Daily engagement feed UI             Build MVP      todo           P1     T-87
[T3]   content  "Why I built engagement-first"       —              todo           P2     T-92
─────  ───────  ───────────────────────────────────  ─────────────  ─────────────  ─────  ──────────
[M1]   build    Reply angle suggester                Build MVP      todo           P1     T-90
[M2]   decide   Pricing tier names                   —              todo           P1     T-99
─────  ───────  ───────────────────────────────────  ─────────────  ─────────────  ─────  ──────────

NEEDS YOUR INPUT
STREAK  cold-9d        → /magnetx engage
DEC-1   open-decision  → niche-pool seeding strategy
```

T# = today position, M# = tomorrow.

---

## Mode: plan

Interactive daily scope-setting. Steps:

1. List all tasks with `Status ∈ {To Do, In Progress}` not yet placed in `today_ids` or `tomorrow_ids`.
2. For each, ask: *"Where does <task title> [<phase>] go? [today / tomorrow / skip]"* — accept ordered position too: "today 2".
3. Allow free-form dump: *"Today: T-104, T-87, T-92. Tomorrow: T-90."*
4. Write back to `cache.json`:
   ```json
   { "today_ids": [...], "tomorrow_ids": [...] }
   ```
5. Render the new plan via `render` mode.

Plan mode does NOT fire `/magnetx-ship`. Run `/magnetx next` after planning.

---

## Mode: next

1. Compute ★ (highest-priority needs_input item; if none, first in-progress in today_ids; if none, first todo in today_ids).
2. Surface: *"Starting <ID>: <title> [track=<t>]. Routing via /magnetx-ship."*
3. Invoke `Skill(skill="magnetx-ship", args="<task-id>")`.

---

## Mode: engage

Shortcut for daily X engagement loop:

1. Find most recent Engagement-type task in Notion (Status=To Do or In Progress).
2. If none exists, create one via `mcp__claude_ai_Notion__notion-create-pages` (Type=Engagement, Phase=Personal X Growth).
3. Invoke `Skill(skill="magnetx-ship", args="<task-id>")` — orchestrator routes to sell track → `/magnetx-engage`.

---

## Mode: ingest <dump>

Consume brain dumps, meeting notes, idea sessions:

1. Save raw to `~/opensource/vault/wiki/inbox/<date>-magnetx-<topic>.md`.
2. Extract:
   - **Candidate tasks** (action items, "we should do X") → propose Notion task creation, infer Type for routing (build/sell/content/decide/learn). Use `mcp__claude_ai_Notion__notion-create-pages` after user confirms.
   - **Decisions** (settled: "we'll go with Y") → append to vault `projects/magnetx/decisions.md` + Notion HQ Context "Settled Decisions".
   - **Open questions** → append to vault `projects/magnetx/open-threads.md` + Notion HQ Context "Open Product Decisions".
   - **Learnings** ("we discovered Z") → append to vault `projects/magnetx/learnings.md` (create if missing).
3. Show extracted items in a table; user confirms/edits before writing.
4. After task creation, ask placement: today/tomorrow/skip (delegate to plan mode).

---

## Reactive integration (other skills push to /magnetx)

`/magnetx` does not poll Notion mid-conversation — other skills write directly to Notion + cache:

| Skill | Effect on /magnetx |
|---|---|
| `/magnetx-ship` | Drives every track end-to-end. Notion writes (Status, Type backfill, Done, completion log); cache refresh; saves `session_id` to `shared_context`. Owns build pipeline (pickup logic folded in). |
| `/magnetx-engage` | Notion X Tracker: streak++ ; cache `x_tracker.streak` refresh; clears cold-streak ★ item. Called inside `/magnetx-ship` sell track. |
| `/think` | Vault: appends to `projects/magnetx/decisions.md`. Caller (orchestrator) writes Notion HQ Context "Settled Decisions". |
| `/aksenhq-*` | No state effect — content tools. Used inside `/magnetx-ship` content track. |
| `/scrape-x-profile` | No state effect — scraped data is research output, captured to vault by caller. |

Pattern: skills push state; `/magnetx` reads state.

---

## Watcher-status handoff

`/magnetx-ship` saves `cache.shared_context.session_id` on entry (via `/search-history current-id`). On `/magnetx` render, for any In-Progress task with a recorded session:

```
T-104  in-progress  build
       → resume with: claude -r <session_id>
       → or: /magnetx-ship T-104  (fresh session)
```

If absent → `→ no session recorded; run /magnetx-ship T-104`.

Never auto-schedule `/loop` or background watchers from `/magnetx`.

---

## Storage layout

```
~/.claude/skills/magnetx/
└── cache.json           operational state — Notion snapshot + today_ids + tomorrow_ids + shared_context

~/opensource/vault/wiki/projects/magnetx/    durable knowledge (DB)
├── overview.md          what MagnetX is, ICP, tech, GTM, decisions
├── decisions.md         architectural + product decisions (append-only)
├── open-threads.md      blockers, parked questions
└── learnings.md         (created on first /magnetx ingest learning)

~/opensource/vault/wiki/inbox/<date>-magnetx-<topic>.md     raw dumps from /magnetx ingest
```

Notion remains source of truth for tasks/decisions/streak. Cache = read-only snapshot for fast startup. Vault = durable knowledge tier.

---

## Workflow ending

```
───── /magnetx ─────
mode      : <render|list|plan|next|engage|ingest>
needs_input: <n>
today     : <n> tasks   (or: <task-id> started via /magnetx-ship)
tomorrow  : <n> tasks
streak    : <N> days
─────────────────────

───── artifacts ─────
Cache  : ~/.claude/skills/magnetx/cache.json
Notion : <HQ link> | <Task Board link>
Inbox  : ~/opensource/vault/wiki/inbox/<latest>   (only if ingested)
─────────────────────
```

---

## Data Contract

### Reads (Memory)
- `~/.claude/skills/magnetx/cache.json` — task snapshot + ordering + shared_context
- `~/opensource/vault/wiki/projects/magnetx/{overview,decisions,open-threads}.md` — surface "Recent Decisions" / "Parked Threads"

### Reads (DB, fallback only on cold cache)
- Notion HQ Context (`34eecb1d-39d0-814e-b03e-c39f13d1c254`)
- Notion Task Board DS (`a119bf6a-603e-4f51-b602-fc7ffb4e445e`)
- Notion X Tracker DS (`4b9b90de-9252-4da7-a76c-f40fa89c610f`)

### Writes (Memory)
- `cache.json` — on background refresh + on `/magnetx plan` (today_ids/tomorrow_ids) + on shared_context updates by `/magnetx-ship`
- `~/opensource/vault/wiki/inbox/<date>-magnetx-*.md` — on `/magnetx ingest`
- `~/opensource/vault/wiki/projects/magnetx/{decisions,open-threads,learnings}.md` — on `/magnetx ingest` extraction

### Writes (DB)
- Notion Task Board (new tasks) — on `/magnetx ingest` after user confirm
- Notion HQ Context (decisions) — on `/magnetx ingest` extraction

### Live external (not stored)
- Notion fetches in background refresh

---

## Git Identity

GitHub: **akshatdalton** (personal). Eightfold account → `gh auth switch` first. Never eightfold creds here.

## References

| What | ID |
|------|----|
| HQ Context | `34eecb1d-39d0-814e-b03e-c39f13d1c254` |
| Task Board | `a119bf6a-603e-4f51-b602-fc7ffb4e445e` |
| X Tracker | `4b9b90de-9252-4da7-a76c-f40fa89c610f` |
| Parent page | `304ecb1d-39d0-80f2-849b-c46d97e80672` |
| GitHub | akshatdalton/magnetx (monorepo, landing in landing/) |
| Vercel | magnetx.co |
