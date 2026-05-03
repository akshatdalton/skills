---
name: ship-task
description: Idempotent end-to-end orchestrator for shipping a Jira ticket. Routes by current work_hq stage to /work-on-jira-task → /submit-pr → /get-pr-ready-to-merge with autonomous CI watch loop. Stops only on user-input criteria (Group 3 design, Group 5 external actor, judgment-call review comment, ready-to-merge). Use when the user says "ship ENG-XXXXX", "/ship-task ENG-XXXXX", "let's complete this ticket end-to-end", "drive this to merge", or shares a Jira/PR URL with intent to take it through to merged state.
---

# Ship Task — End-to-End Orchestrator

One entry point for the ship-loop stage of an initiative. Idempotent: invoke whenever, it picks up from current state and drives forward until it hits a stop criterion.

## Pre-entry: lazy-load context (foundation hook)

Run in this exact order, all auto, no prompts:

1. **Identification priority** — resolve TICKET_ID:
   - Highest: user-provided artifact in current prompt (Jira URL, GitHub PR URL)
   - Fallback: current `git branch --show-current` → regex `ENG-\d+`
2. **work_hq lookup** — `python3 ~/.claude/work_hq/update.py get <TICKET_ID>` → load stage, repo, branch, pr, initiative_slug, shared_context, ci_loop counter.
3. **Initiative load** — if `initiative_slug` is set, read `~/opensource/vault/wiki/projects/<repo>/initiatives/<slug>/{charter,decisions,learnings,e2e-flow}.md` (`<repo>` = task's `repo` field; initiative knowledge moved from work_hq → vault on 2026-05-03; `ticket-graph.md` stays in work_hq).
4. **No initiative yet** → suggest existing slugs (substring match) or offer to create.
4.5. **Capture session-id (silent)** — record the current Claude Code session-id on the task so a future `/today` invocation can tell the user *how to resume into the session that already has implementation context*. The /loop-based CI watch dies when the session closes (observed sessions c9c186d0 and 19f4e417), so `/today` is now the polling entry-point: it surfaces failures and offers `claude -r <session-id>` to reattach.

   ```bash
   SID=$(/search-history current-id 2>/dev/null || echo "")   # silent; empty if not resolvable
   if [ -n "$SID" ]; then
     python3 ~/.claude/work_hq/update.py set <TICKET_ID> \
       --field "shared_context.watcher_session_id=$SID" \
       --field "shared_context.watcher_session_at=$(date -u +%FT%TZ)"
   fi
   ```
   Do NOT surface this to the user — it's a silent metadata write. Surface only happens later, in `/today`, if the PR is found failing without an active watcher.
5. **Live state enrichment (parallel, mandatory)** — fire all of these in a SINGLE batch (multiple Bash tool calls in one response) before deciding the route. Do NOT serialize.

   **Tooling rule: use `gh` CLI for GitHub, `mcp__claude_ai_Atlassian__*` for Jira. Do NOT use `mcp__github__*` — gh is the user's preferred path.**

   - **If `pr` is set** (stage in-review/ci/testing/ready-to-merge): parallel-fetch
     ```bash
     gh pr view <N> --repo <owner>/<repo> --json state,isDraft,mergeable,mergeStateStatus,reviewDecision,headRefOid,baseRefName,headRefName > /tmp/pr-<N>-meta.json &
     gh api repos/<owner>/<repo>/commits/<sha>/check-runs --jq '[.check_runs[] | {name,status,conclusion}]' > /tmp/pr-<N>-checkruns.json &
     gh api repos/<owner>/<repo>/commits/<sha>/status --jq '{state, statuses:[.statuses[] | {context,state}]}' > /tmp/pr-<N>-status.json &
     gh pr view <N> --repo <owner>/<repo> --json reviews,comments > /tmp/pr-<N>-reviews.json &
     wait
     ```
     Reconcile check-runs + status. CI is failing if EITHER reports `failure`/`error`; pending if EITHER pending and neither failing.
     **MANDATORY: fetch both channels.** Skipping `commits/<sha>/status` caused a false-green misroute in session c9c186d0 (check-runs all green, status 6-failing).
   - **If no PR yet** (stage todo/in-progress) OR board snapshot >1h old: fetch `mcp__claude_ai_Atlassian__getJiraIssue` for current description, status, sprint, assignee, comments. Don't trust board's stale title/priority for planning.
   - **Stage auto-correction**: if live state contradicts board (board says `in-review` but `mergeStateStatus=clean` + approved → `ready-to-merge`; board says `ci` but both channels green → reclassify), call `update.py upsert --stage <correct>` BEFORE routing. Surface: `↳ stage corrected: <old> → <new> (reason)`.

Surface ONCE on entry:

```
↳ initiative=<slug> · ticket=<TICKET_ID> · branch=<name> · stage=<s>  · pr=<#|none>
```

### Ask-to-seed rule

If at ANY point during the orchestration a required field is missing (no ticket resolvable, no initiative known, ambiguous priority, missing test files, unknown reviewer thread context, no design doc for a Group 3 decision, etc.) — **STOP and ASK the user to seed it**. The orchestrator is autonomous *between* known stop points; missing info is a stop point. One question at a time. Never invent.

## Stage routing

Based on `stage` from work_hq:

| Stage | Route to |
|---|---|
| `todo` | `/work-on-jira-task <TICKET_ID>` → on completion, fall through to `in-progress` |
| `in-progress` | implement (resume superpowers plan) → `/submit-pr` → fall through |
| `in-review` | `/get-pr-ready-to-merge <pr-url>` (with autonomous CI watch loop registered) |
| `ci` / `testing` | resume CI watch loop |
| `ready-to-merge` | STOP — surface "merge it, your call" + add to needs_input queue |
| `merged` / `archived` | STOP — already done |

## Autonomous loop policy (inherited from /get-pr-ready-to-merge)

- **Loop target is `/get-pr-ready-to-merge <pr-url>`, NOT `/pr-watcher`.** /pr-watcher only delivers ntfy notifications; it doesn't triage or fix. The autonomous loop must re-invoke `/get-pr-ready-to-merge` so each tick fetches logs, classifies failures, and applies fixes when possible.
- Schedule via the `loop` skill: `Skill(skill="loop", args="30m /get-pr-ready-to-merge <pr-url>")`.
- **Default to local in-session loop, NEVER cloud.** If `/loop` asks "set up cloud schedule instead?" via AskUserQuestion — always answer **"keep local"**. Only escalate to cloud if the user explicitly says "schedule on cloud" / "use CronCreate".
- Cadence: 30m while CI pending/running, max 8 iterations (4h budget). Resets on any successful fix push.
- Stop conditions (the 4 user-selected criteria):
  1. Group 3 — design / architecture decision
  2. Group 5 — external actor (needs_sandbox, awaiting reviewer, manual peer test)
  3. Judgment-call reviewer comment (gated by `superpowers:receiving-code-review`)
  4. Ready-to-merge — never auto-merge
- On stop: `update.py needs-input add <TICKET_ID>` so it surfaces in `/today`.

### Fallback when session closes

The in-session `/loop` dies when Claude Code is closed (observed sessions c9c186d0 and 19f4e417). To bridge across session restarts:
- Step 4.5 already saved this session's id on the task as `shared_context.watcher_session_id`.
- When the user next runs `/today` (in any session), it parallel-fetches commit-status + check-runs for every PR. If a PR is failing AND no live in-session loop is detected, `/today` surfaces `→ resume with: claude -r <watcher_session_id>` so the user can reattach to the session that already has implementation context — and the loop resumes naturally.
- The user can always start fresh via `/ship-task <TICKET>` from a new session if they prefer.
- Stop conditions (the 4 user-selected criteria):
  1. Group 3 — design / architecture decision
  2. Group 5 — external actor (needs_sandbox, awaiting reviewer, manual peer test)
  3. Judgment-call reviewer comment (gated by `superpowers:receiving-code-review`)
  4. Ready-to-merge — never auto-merge
- On stop: `update.py needs-input add <TICKET_ID>` so it surfaces in `/today`.

## Test workflow inheritance

**Hard rule: run tests BEFORE every push, unless the user explicitly says otherwise.**

When implementing or applying CI fixes:
- **wipdp** → local pytest is sufficient
- **vscode**:
  - Unit / pytest tests → `/run-on-ec2` (mandatory if VPN up; record skip reason in branch context if not)
  - HTTP / endpoint integration tests against live dev instance → `/test-live-api`
- **Lint** — do not run on EC2; pre-commit hook handles it (vscode: husky; wipdp: ruff)
- **Doc-only / comment-only changes** → skippable without recording

The push step proceeds only after tests pass. The autonomous loop respects this gate too — a failing test cancels the push and surfaces back to user input.

## Workflow ending

Always update work_hq + surface artifacts. Compose from the sub-skills' artifact blocks plus:

```
───── workflow ─────
✓ Initiative : <slug>
✓ Ticket     : <TICKET_ID>
✓ Stage      : <new stage>  (was <prev stage>)
✓ Loop       : <registered 30m × 4h | stopped: <reason>>
→ Next       : <ready-to-merge: merge it | blocked-on-actor: ping <X> | running: see /today>
────────────────────

───── artifacts ─────
Jira       : https://eightfoldai.atlassian.net/browse/<TICKET_ID>
PR         : <url>   (if exists)
Branch     : <repo>:<branch>
Plan       : <repo>/plans/<TICKET_ID>.md   (if exists)
Initiative : ~/opensource/vault/wiki/projects/<repo>/initiatives/<slug>/  (charter/decisions/learnings/e2e-flow)
Board      : ~/.claude/work_hq/board.md  → task <TICKET_ID>
Today      : /today  (see Needs Your Input if loop stopped)
─────────────────────
```

Omit any line whose artifact wasn't created/touched.

## Why /ship-task vs the underlying skills

- **Use `/ship-task`** when you want the ENTIRE flow handled — pick up wherever, drive to stop. Best for "I want to start this ticket and have it ship" OR "this PR has comments, address them and merge".
- **Use individual skills** (`/work-on-jira-task`, `/submit-pr`, `/get-pr-ready-to-merge`) when you want fine control over a single stage without auto-progression.

---

## Data Contract

### Reads (DB)
- `~/opensource/vault/wiki/projects/<repo>/decisions.md` — prior decisions (light, for orchestrator context)
- `~/opensource/vault/wiki/projects/<repo>/initiatives/<slug>/{charter,decisions,learnings,e2e-flow}.md` — when `initiative_slug` is set

### Reads (Memory)
- `~/.claude/work_hq/board.json[task_id]` — current stage, route by it
- `~/.claude/work_hq/initiatives/<slug>/ticket-graph.md` — sibling tickets

### Writes (Memory)
- `~/.claude/work_hq/board.json` — stage transitions, watcher_session_id
- `~/.claude/work_hq/needs_input.json` — on stop conditions
- `~/opensource/vault/wiki/hot.md` — active stage transitions
- `~/opensource/vault/wiki/log.md` — per-stage event ("routed to /submit-pr", "shipped ENG-XXXXX")

### Local (skill-only)
- (none; orchestrator state lives in board.json)

### Live external (not stored)
- `gh` PR data (parallel batch fetch on entry)
- Atlassian MCP — for stale Jira refresh
