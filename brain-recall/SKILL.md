---
name: brain-recall
description: Use when the user fires `/brain-recall` alongside or before any state-machine skill (work-on-jira-task, submit-pr, get-pr-ready-to-merge, ship-task) — or any time they want project context loaded into the session. Resolves the active project from cwd / branch / ticket arg. **Tiered v1 load:** auto-loads per-project `charter.md` + `log.md` (tail) + `learnings.md`; lazy-loads `decisions.md` + `initiatives/<slug>/{charter,decisions,learnings}.md` only when in scope or explicitly cited. Reads `progress/<ticket>/progress.md` + `progress/<ticket>/plan.md` if a ticket resolves. READ-ONLY — never writes. Pairs with `/brain-ingest`. Add `--v2` to ALSO load context from the claude-obsidian vault at `~/opensource/claude-obsidian-test/` — reads hot.md + searches wiki for pages matching the ticket/topic. Useful when the ticket or topic has previously been ingested via `/brain-ingest --v2`.
---

# /brain-recall (v1)

## Purpose

Stateless skills lose context across `/clear`. `/brain-recall` is the read-side of Akshat's vault brain — load the relevant `learnings.md`, `progress/<ticket>/progress.md`, and `progress/<ticket>/plan.md` into the session so whatever skill fires next has full project + task context.

**Never writes the brain.** Read-only with respect to the vault (`learnings.md`, `progress/`). Pair with `/brain-ingest` for the write side.

> One operational exception (NOT brain content): the final **arm step** writes a tiny queue marker under `~/.claude/brain-ingest-queue/` — operational state, never inside `wiki/`. This is what makes the forgotten-ingest problem self-correcting (see "Arm background ingest" below).

## Vault layout (v1, post-vault-v1)

```
~/opensource/vault/wiki/
  CLAUDE.md, index.md, log.md                            # standing instructions + catalog + vault-root meta event log
  projects/                                              # 5 active projects, all on the same 4-file pattern
    <project>/                                           # vscode | wipdp | magnetx | claude-code | meetily
      charter.md                                         # AUTO-LOAD — project-defining one-pager + nav index (~50 lines)
      learnings.md                                       # AUTO-LOAD — cross-cutting durable lessons (gotchas, runbooks, conventions); NOT initiative-scoped
      decisions.md                                       # LAZY — project-wide decisions (Why/Trade/Source format); read on grep/cite
      log.md                                             # AUTO-LOAD (tail only ~20 entries) — append-only event timeline
      initiatives/                                       # LAZY — only when slug/ticket resolves into scope
        <slug>/
          charter.md
          decisions.md
          learnings.md
          progress/                                      # per-ticket (vscode/wipdp) or per-task (magnetx) work
            <ticket-or-task>/
              progress.md
              plan.md
      # magnetx-only: notion-tasks.md (Notion board dump, AUTO-LOAD for magnetx)
      # wipdp-only: runbooks/<topic>.md (lazy, on topic-grep)
```

Active projects: **vscode**, **wipdp**, **magnetx**, **claude-code**, **meetily**. (magnetx-landing, claude-code-sessions, tweet-analysis remain deferred.)

**Per-project quirks:**
- **magnetx** — no Jira tickets; progress dirs use task slugs (`build-mvp`, `yt-shorts`, `landing`, ...); no GitHub PR merge detection (Notion is source of truth via `notion-tasks.md`).
- **claude-code** — the meta-project: skills, hooks, vault itself live here. Initiatives are vault-meta + workflow-tooling work.
- **meetily** — sister to claude-code; standalone Rust/Tauri repo with calendar-daemon initiative + runbook.md tracking.

## Invocation forms

| Form | Behavior |
|---|---|
| `/brain-recall` | Auto-resolve project from cwd. If branch matches `akshat/ENG-XXXXX-*`, also load the ticket's progress + plan. |
| `/brain-recall ENG-XXXXX` | Explicit ticket (vscode/wipdp). Resolve project by checking which project's `progress/<ticket>/` directory exists. Load learnings, progress, and plan. |
| `/brain-recall <initiative>` | magnetx only. `<initiative>` = `build-mvp` \| `yt-shorts` \| `landing` \| etc. Load magnetx learnings + the initiative's progress/plan. |
| `/brain-recall <project>` | Load project's `learnings.md` only. Useful when reading without ticket/initiative context. |
| `/brain-recall <PR URL or Jira URL>` | Extract ticket → resolve project → load everything. |
| `/brain-recall <Notion task URL>` | magnetx only. Extract initiative from Notion context → load magnetx learnings + matching progress dir if any. |

## Read order — Tiered v1

> **Tiered load principle** (per vault-v1 decisions): the only files worth auto-loading are the project's index (charter.md) + the recent-events tail (log.md) + the cross-cutting brain (learnings.md). Everything else — decisions.md, initiative dirs, runbooks — is **lazy-loaded** on grep, on explicit cite, or when a ticket/slug resolves into scope. This caps the per-recall context tax that dense AGENTS.md-style auto-loads incur.

### Step 1 — Resolve `<project>` (first hit wins)

- cwd → `git remote get-url origin` → repo slug (`vscode` | `wipdp` | `magnetx` | `claude-code` | `meetily`); OR cwd path contains `/opensource/magnetx` → project = `magnetx`; OR cwd path is under `~/.claude/` or `~/opensource/vault/` → project = `claude-code`
- explicit ticket arg `ENG-\d+` → probe `~/opensource/vault/wiki/projects/{vscode,wipdp}/progress/<ticket>/` AND `~/opensource/vault/wiki/projects/{vscode,wipdp}/initiatives/*/progress/<ticket>/` AND the archive paths; whichever resolves determines the project
- explicit initiative slug arg (no `ENG-` prefix) → probe `~/opensource/vault/wiki/projects/*/initiatives/<slug>/`; if found → project + initiative resolved
- branch name `akshat/ENG-XXXXX-*` → same as ticket arg above
- user-pasted artifact URL (Jira/PR URL) → extracted ticket → directory lookup
- user-pasted Notion task URL → project = `magnetx`


If no resolution and no explicit `<project>`, ask which of the 5 projects, or load global `CLAUDE.md` only.

### Step 2 — Eager tier (always read for the resolved project)

Always read these per-project files in this order:

1. `~/opensource/vault/wiki/projects/<project>/charter.md` — the index + project-defining one-pager. Tells you what the project IS and where to navigate next.
2. `~/opensource/vault/wiki/projects/<project>/log.md` — but only the **tail** (last ~20 entries; use `tail -n 25` or read with explicit offset to skip the header). The header is metadata; the tail is "what just happened."
3. `~/opensource/vault/wiki/projects/<project>/learnings.md` — cross-cutting durable lessons.
4. **magnetx only:** also read `notion-tasks.md` (current task board state).

### Step 3 — Lazy tier (read ONLY if triggered)

Do NOT auto-load these. Read on:

- **`decisions.md`** — read when (a) user's query is decision-shaped ("why did we choose X", "what was the decision on Y"), (b) user explicitly cites a decision, or (c) a grep across the project for the queried term hits decisions.md.
- **`initiatives/<slug>/{charter.md, decisions.md, learnings.md}`** — read when (a) the ticket / initiative slug resolved in Step 1 maps to this initiative, (b) user explicitly mentions the initiative, or (c) the eager-tier learnings.md "Initiatives" pointer table indicates relevance to the user's current question.
- **`runbooks/<topic>.md`** (wipdp) — read when the user's query matches a runbook topic (e.g. "agent-builder e2e", "deploy", "ec2").

### Step 4 — Ticket scope (if ticket/initiative resolved in Step 1)

Probe the directory with explicit filesystem checks (mandatory — never skip or infer absence from memory):

- Run: `ls ~/opensource/vault/wiki/projects/<project>/progress/<ticket-or-task>/` OR `ls ~/opensource/vault/wiki/projects/<project>/initiatives/<slug>/progress/<ticket-or-task>/`
- If neither returns anything, try the `archive/` variants.
- Only after ALL filesystem probes return nothing should you conclude "no progress directory yet".
- Once located, read `progress.md` (active task state + in-flight learnings) and `plan.md` (initial plan if exists).
- ALSO load the matching initiative's eager tier (initiative charter + initiative learnings) since you've resolved into its scope.

### Step 5 — Surface as prose summary

- One short paragraph: what this project is (from charter), what's active (from log.md tail), what's relevant from learnings to the user's current task (if discernible).
- List which files were read with paths. Note which tier each came from (eager / lazy / ticket).
- If a progress file exists: surface state (frontmatter), what's been done, what's next.
- If a plan file exists: highlight the plan's section/step list.
- If user gave an artifact (Jira/PR URL): fetch its content (`gh pr view`, `mcp__claude_ai_Atlassian__getJiraIssue`) and weave in.
- If user gave a Notion URL (magnetx): fetch via Notion MCP and weave in.

### Step 6 — Never write anything to the vault

(The arm step writes a queue marker under `~/.claude/brain-ingest-queue/`, which is operational state — NOT inside `wiki/`.)

## What NOT to read

- `~/opensource/vault/wiki/_archive/**` — does NOT exist anymore (deleted in vault-v1 Phase 1, 2026-05-31); the path is gone. If you ever see a reference to it in older skills/files, treat as a stale pointer.

- `~/.claude/sessions/**`, `~/.claude/history.jsonl` — raw inputs for `/brain-ingest`, not for recall.
- Auto-memory `~/.claude/projects/<encoded-cwd>/memory/` — fallback only. Only surface if a fact isn't in `learnings.md`, and prefix with `↳ note: read from auto-memory fallback (<path>) — vault gap`.

## Output structure

```
**Project:** <vscode|wipdp|magnetx|claude-code|meetily>
**Read (eager tier):**
- `projects/<project>/charter.md`
- `projects/<project>/log.md` (last ~20 entries)
- `projects/<project>/learnings.md`
- `projects/magnetx/notion-tasks.md` (magnetx only)

**Read (lazy — only if triggered):**
- `projects/<project>/decisions.md` (if user query was decision-shaped)
- `projects/<project>/initiatives/<slug>/{charter,decisions,learnings}.md` (if slug/ticket resolved into scope)
- `projects/<project>/runbooks/<topic>.md` (if topic matched a runbook)

**Read (ticket/task scope):**
- `projects/<project>/[initiatives/<slug>/]progress/<ticket-or-task>/progress.md` (or "no progress yet")
- `projects/<project>/[initiatives/<slug>/]progress/<ticket-or-task>/plan.md` (or "no plan recorded")

**Project snapshot:**
<2-4 sentences from charter + log-tail + learnings — what this project is, what just happened recently, what's most relevant>

**Task context (if ticket/initiative in scope):**
- State: <state from frontmatter>
- Branch / PR (vscode/wipdp/meetily): <values from frontmatter>
- Notion task (magnetx): <task name + current Notion status if URL was provided>
- Done so far: <summary from progress.md body>
- Next: <next-action signals from progress.md>

**From the plan (if exists):**
<key bullets from plan.md — what was decided to build, in what order>

**Relevant prior learnings:**
- <bulleted, cited to specific section anchors in learnings.md or initiative learnings.md>

**Recent activity (from log.md tail):**
- <2-4 most recent log entries that are relevant — skill firings, ticket lifecycle, decisions>

**Next suggested step:**
<one line — typically the state-machine skill to fire next>

🧠 **Continuous ingest armed for this session.** From now until session end: drop `🧠 capture: <one-liner>` breadcrumbs at every natural beat (learning surfaced, decision made, sub-task done, gotcha discovered), and fire `/brain-ingest --bg` every ~5–10 breadcrumbs or at clean transitions — non-blocking; a cheap headless worker forks the session and writes to the vault while you keep working. You don't need to remember any of this; the Stop-hook drainer fires a final `--bg` as backstop. See brain-recall's "Continuous mode" section for the pattern.
```

## Arm background ingest (final step — always run)

Recall is the half Akshat reliably fires; ingest is the half he forgets. So recall ARMS the ingest before it ends. This is operational state, not brain content.

1. Get the current session id: `python3 ~/.claude/skills/search-history/scripts/current_id.py --quiet`.
2. Write the marker:
   ```bash
   mkdir -p ~/.claude/brain-ingest-queue
   cat > ~/.claude/brain-ingest-queue/<session_id>.json <<EOF
   {"session_id":"<id>","project":"<vscode|wipdp|magnetx>","ticket":"<ENG-XXXX|initiative|null>","armed_at":"<ISO8601>","status":"pending"}
   EOF
   ```
3. Emit the 🧠 line shown in the output block above so the obligation lives in Claude's context.

**What consumes the marker:**
- **Claude self-fires** `/brain-ingest --bg` at continuous-mode beats AND at a natural wrap-up (task done, task switch, `/clear` intent) — because the 🧠 line is in context. Non-blocking.
- **Akshat fires** `/brain-ingest --bg` himself anytime — also non-blocking. (Legacy `/brain-ingest-bg` trigger phrase still routes here.)
- **Stop-hook drainer** (`~/.claude/hooks/brain-ingest-drain.sh`) fires any still-`pending` marker as a backstop (calls the launcher script directly, doesn't need the skill).

The marker stays `pending` across continuous-mode fires (don't flip to `launched` until the FINAL wrap-up fire or the Stop-hook drainer flips it) — that way the drainer remains armed as a safety net even after mid-session fires happen.

## Continuous mode — capture throughout the session, not just at wrap-up

**Default ON.** From the moment `/brain-recall` runs (or the first `/brain-ingest --bg` fires, whichever comes first), the session enters continuous-ingest mode for the rest of its life. Akshat shouldn't have to remember to ingest, and shouldn't be blocked while it happens.

### Main-session Claude's role — active but cheap (drop breadcrumbs, fire periodically)

At every natural beat, drop a brief inline marker in your reply:

```
🧠 capture: <one-line idea of what's worth remembering>
```

Beats that warrant a breadcrumb:
- A learning surfaced ("the bug was caused by X")
- A decision made ("going with approach B because C")
- A sub-task done ("auth middleware refactor: done")
- A runbook command that worked end-to-end
- A gotcha / environment quirk discovered
- A file written / a test fixed / an error root-caused
- A correction the user gave you ("don't do X here because Y")

**Don't breadcrumb (false-positives pollute the vault):**
- Pure tool output ("ls returned 12 files")
- Intermediate reasoning that hasn't settled ("I'm thinking we should…")
- Restating what the user just said
- Trivial actions ("opened the file", "ran the test" — only breadcrumb the OUTCOME if non-obvious)
- Anything you might walk back in the next 2 turns
- Status updates with no new fact ("still working on it")

Breadcrumbs are the "idea of what should be captured" — you don't decode, you don't write to the vault yourself. Just leave the breadcrumb and keep working. The BG worker does the decoding.

**Periodically fire `/brain-ingest --bg`** at clean transition points:
- Every ~5–10 breadcrumbs
- Every ~30 min of substantive work
- When a sub-task / step completes cleanly
- Before any context-pressure event (compaction nudge, /clear intent, branch switch)

Non-blocking — fire and continue. Multiple fires per session are safe (the worker dedupes via session_ids + delta-capture; see brain-ingest Step 5).

**Never defer a fire to "save tokens" — that's the wrong instinct.** Firing `/brain-ingest --bg` costs ~50 tokens of your context (one Bash call + a one-line ack to the user). Deferring under context pressure is exactly when capture matters most — if you defer and the session compacts or crashes, the breadcrumbs are lost. When you feel "I'll batch this for wrap-up": fire NOW, then continue. The dollar cost (~$0.50–1.00 per fire) is the BG worker's, not the live session's.

### BG worker's role — passive (read forked session, write deltas)

Each `--bg` fire spawns a fresh headless `claude -p` (Sonnet, minimal MCP) that:
1. Forks the live session via `--resume --fork-session` (the original main session is NEVER mutated — the worker only reads a copy).
2. Reads the breadcrumbs + surrounding conversational context.
3. Identifies what's settled (concepts / runbook commands / decisions / corrections).
4. Writes to `progress/<ticket>/progress.md` as a delta H2 block (appended, not replacing) and uplifts to `learnings.md` in-place.
5. Fires a desktop notification when done. No interaction with the live session.

Cost per fire: ~$0.50–1.00. Cost per session in continuous mode: ~$2–6 (4–8 fires). Comparable to one Opus-with-all-MCP wrap-up ingest, with the added benefit that captures happen incrementally and survive crashes / forced /clears / tab closes.

### Why this beats wrap-up-only ingest

- **Crash-safe:** if the session crashes, `/clear` is forced, or the tab closes, prior beats are already in the vault.
- **Adjacent-ticket benefit is immediate:** sister work picks up learnings as they settle, not after a long session ends.
- **`progress.md` evolves in real time:** Akshat sees the brain getting richer throughout the work.
- **No EOD ritual:** Akshat doesn't have to remember to ingest. The skill makes it automatic.

### De-dup is the BG worker's job, not yours

Keep firing without worrying about duplicates. The worker checks `progress/<ticket>/progress.md` frontmatter:
- If session_id NOT in `session_ids` → full capture, add to `session_ids`.
- If session_id IS in `session_ids` AND new conversation content exists since `last-touched` → DELTA capture (append a new H2 sub-block titled `## Session <id_short> (YYYY-MM-DD HH:MM) — continuous capture #N — <one-line>`). `session_ids` stays deduped.
- If session_id IS in `session_ids` AND no new content → no-op write, just update `last-touched`.

See brain-ingest Step 5 ("Identify and capture session content") for the implementation.

### Disabling continuous mode (rare)

If a session genuinely shouldn't be ingested (throwaway exploration, sensitive content, demo session), do one of:
- Don't run `/brain-recall` for this session.
- Manually delete the marker: `rm ~/.claude/brain-ingest-queue/<session_id>.json` after recall but before any beats.
- Pass `--no-continuous` to `/brain-recall` (recall will still load the brain but won't arm the marker).

## Pairs with

- `/brain-ingest <ticket>` — write side. Distills the current session into `progress/<ticket>/progress.md`; on first ingest, copies any matching plan from `~/.claude/plans/` to `progress/<ticket>/plan.md`. Fire after state-machine skill sessions end.
- `/brain-ingest` (no arg) — catch-up sweep using `.brain-ingest-state.json` `last_sync_timestamp`.
- `/brain-ingest --bg` — non-blocking background launch mode of `/brain-ingest` (detached `claude -p`, Sonnet). Fired by the arm step above. Use this instead of plain `/brain-ingest` when you don't want to block. (As of v0.3 of brain-ingest, the standalone `/brain-ingest-bg` skill is retired; that trigger phrase still works as an alias.)

---

## --v2 mode: Obsidian wiki context layer (runs AFTER the standard recall above)

Add `--v2` to any `/brain-recall` invocation to ALSO pull context from the claude-obsidian vault at `~/opensource/claude-obsidian-test/`. Standard brain-recall runs first in full — `--v2` appends an obsidian context block at the end of the recall output.

**Triggers:**
- `/brain-recall --v2` (auto-resolve project + obsidian context)
- `/brain-recall ENG-XXXXX --v2` (ticket-scoped + obsidian)
- `/brain-recall vscode --v2` (project-scoped + obsidian)
- `/brain-recall --v2 <topic>` where `<topic>` is a free-text query (e.g. "oncall alarm", "logo resolution") — the ticket resolver still runs normally; topic is passed to the obsidian search

### V2 Step 1 — Read hot.md

**Always.** Read `~/opensource/claude-obsidian-test/wiki/hot.md`. This is the ~500-word session carry-forward. Pull only the most recent 2 session blocks (the rest is historical noise). Surface them under `📚 Obsidian — Recent context`.

If the file doesn't exist or the vault is missing: skip and warn: "⚠️ Obsidian vault not found at ~/opensource/claude-obsidian-test/ — skipping --v2 step."

### V2 Step 2 — Search wiki for ticket/topic

Build a search query from what was resolved in the standard recall:

| What was resolved | Search terms |
|---|---|
| Ticket `ENG-XXXXX` | The ticket number + ticket title keywords |
| Project only (`vscode`) | Project name + recent log.md tail keywords |
| Free-text `<topic>` arg | The topic verbatim |
| Nothing resolved | cwd basename + any recent `🧠 capture:` breadcrumbs in this session |

**Grep the wiki:**
```bash
grep -rl "<term1>\|<term2>" ~/opensource/claude-obsidian-test/wiki/ | grep -v "hot.md\|log.md\|index.md"
```

**Read the top 3 matching pages** (priority order: concept pages > entity pages > source pages). Skip pages already covered by hot.md.

For each page read, extract:
- The first-move checklist or key content (not the whole page — just the actionable section)
- Any cross-linked pages that look directly relevant (read at most 1 level of links)

### V2 Step 3 — Append obsidian context block to recall output

After the standard brain-recall output (`Project snapshot`, `Relevant prior learnings`, etc.), append:

```
---
📚 Obsidian vault context (--v2):

**Recent sessions** (from hot.md):
<2 most recent session blocks, trimmed to 3-4 sentences each>

**Relevant wiki pages found:**
- [[ConceptPage]] — <one-sentence summary of what it contains>
  Key: <the most actionable line — a checklist step, a command, a decision>
- [[EntityPage]] — <role/identity + most useful field>

**Not found in wiki:** <list any ticket/topic terms that returned zero matches — signals a gap to ingest>
```

### V2 Step 4 — Flag wiki gaps

If the ticket or topic has NO matching pages in the obsidian vault, add to the output:

```
💡 Wiki gap: nothing for "<term>" in the obsidian vault.
   After this session, run: /brain-ingest ENG-XXXXX --v2
   to capture this session's learnings as searchable wiki pages.
```

This closes the loop — recall surfaces the gap, ingest fills it.

### V2 Notes

- **Read-only.** `--v2` on brain-recall NEVER writes to the obsidian vault. That's brain-ingest's job.
- **Low context cost.** hot.md + 3 concept pages = ~2,000 tokens max. Don't load more than 3 wiki pages even if many match.
- **Precedence.** If brain-recall's own learnings.md already covers the topic fully (e.g., the App Platform alarm runbook is already in vscode/learnings.md), skip the obsidian page for that topic — no need to duplicate it in the recall output. Surface the obsidian page only if it adds something NOT in learnings.md (e.g. a structured checklist, an entity page with PD IDs, a source page with a full code trace).
- **Invocation form table** (for quick reference):

| Form | What it loads |
|---|---|
| `/brain-recall --v2` | Standard recall (auto-project) + hot.md + wiki search on project keywords |
| `/brain-recall ENG-XXXXX --v2` | Standard recall (ticket) + hot.md + wiki search on ticket + title |
| `/brain-recall vscode --v2` | Standard recall (project-only) + hot.md + wiki search on "vscode" |
| `/brain-recall --v2 oncall alarm` | Standard recall (auto-project) + hot.md + wiki search on "oncall alarm" |
