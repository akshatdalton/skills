---
name: get-pr-ready-to-merge
description: Handle everything needed to get a PR into mergeable state — resolving review comments, fixing CI failures, handling stale branches, PR description/checklist issues, and all merge blockers. Use when the user asks to get a PR ready to merge, resolve PR comments, fix CI failures, handle merge conflicts, fix checklist validation, or make a PR mergeable. Also trigger on "fix CI on PR #N", "address review comments", "PR is blocked", or any GitHub PR URL shared with an expectation of action.
---

# Get PR Ready to Merge

Use GitHub MCP tools (fall back to `gh` CLI). On permission/"not found" errors: `gh auth status` → `gh auth switch` → retry.

---

## Step 1 — Confirm branch + PR

```bash
git branch --show-current
git remote get-url origin
```

- **PR number given** → fetch via MCP, auto-switch to `headRefName` if different from local branch
- **No PR number** → search open PRs for `head:BRANCH repo:owner/repo`
- Check `mergeable_state`: `"blocked"`, `"behind"`, `"dirty"`, etc.

## Step 1.5 — Scope lock (kills "you screwed my PR" failure mode)

Build in-scope file allowlist BEFORE any edit:

1. From PR title + body, extract Jira ticket ID (`ENG-\d+`).
2. Pull Jira ticket via `mcp__claude_ai_Atlassian__getJiraIssue` → use summary + description.
3. `gh pr diff <pr> --name-only` → currently-changed files = baseline allowlist.
4. `python3 ~/.claude/work_hq/update.py get <TICKET_ID>` → also include `shared_context.files_of_interest[]` (cross-branch widening).
5. Combine into `SCOPE_ALLOWLIST` = baseline ∪ Jira-named files ∪ shared_context files.

**Hard rule:** any edit to a file outside `SCOPE_ALLOWLIST` requires explicit user confirmation:
*"<file> is outside this PR's scope (per Jira/PR title). Confirm to edit?"* Never silently expand scope.

## Step 2 — Conflicts-first hard gate

Conflicts must be resolved before review comments are loaded. Don't present "suggestions" while branch is dirty/behind.

```bash
git fetch origin {baseRefName}
if ! git merge-base --is-ancestor origin/{baseRefName} HEAD; then
  git rebase origin/{baseRefName}
fi
```

If `mergeable_state` ∈ {`dirty`, `behind`} or rebase has conflicts:
- Read both sides. Prefer base for straightforward conflicts. **Ask user** for logic changes.
- `git rebase --continue` → force push.
- **Do NOT proceed to Step 3** until rebase clean and `mergeable_state` ≠ `dirty`/`behind`.

```bash
python3 ~/.claude/work_hq/update.py append-context <TICKET_ID> --decision "rebased onto <base> at <sha>"
```

## Tooling rule (applies to all of Step 3)

**Use `gh` CLI for all GitHub interactions. Do NOT use `mcp__github__*` tools.** MCP is reserved for Atlassian (Jira) only. gh CLI is faster, supports parallel batched bash calls, and matches the user's preferred workflow.

## Step 3 — Identify all blockers

### A. Failing CI — fire ALL fetches in a SINGLE parallel batch (not sequential):

Run these as separate Bash tool calls in the same response (parallel execution). Each writes to a temp file so the next read can grep without re-fetching:

```bash
# Channel 1 — GitHub Actions check-runs
gh api repos/<owner>/<repo>/commits/<sha>/check-runs \
  --jq '[.check_runs[] | {name,status,conclusion,details_url}]' > /tmp/pr-<N>-checkruns.json

# Channel 2 — Commit statuses (external CI: NPM Test, Playwright, CI Test Suite, etc.)
gh api repos/<owner>/<repo>/commits/<sha>/status \
  --jq '{state, statuses: [.statuses[] | {context, state, target_url}]}' > /tmp/pr-<N>-status.json

# Channel 3 — Issue comments (bot checklist validators)
gh pr view <N> --repo <owner>/<repo> --json comments > /tmp/pr-<N>-comments.json

# Channel 4 — Reviews + review threads + pending review requests (individuals AND teams)
gh pr view <N> --repo <owner>/<repo> --json reviews,reviewDecision,mergeStateStatus,mergeable,reviewRequests > /tmp/pr-<N>-reviews.json
gh api graphql -f query='query { repository(owner:"<owner>",name:"<repo>"){ pullRequest(number:<N>){ reviewThreads(first:100){ nodes { id isResolved isOutdated comments(first:1){ nodes { body author{login} path line } } } } } } }' > /tmp/pr-<N>-threads.json

# For any pending team review requests, fetch members so you can name who to ping:
# jq -r '.reviewRequests[] | select(.__typename=="Team") | .slug' /tmp/pr-<N>-reviews.json \
#   | xargs -I{} gh api orgs/<owner>/teams/{}/members --jq '[.[].login]'
```

**HARD RULE: never fetch only check-runs. CI failure verdict requires reconciling both `check-runs` AND `status`.** False-green misroute observed in session c9c186d0 (ENG-191639) — check-runs reported 4/4 passing, but status reported 6 failing checks (NPM Test, Playwright, CI Test Suite Python, etc.). The skill skipped status and falsely concluded "no CI failures." Always parallel-fetch both.

**Verdict logic**: failing if EITHER channel has a `failure`/`error` state; pending if EITHER pending and neither failing; green only if both clear.

Also scan comments JSON for bot messages with "CHECKLIST VALIDATION ERRORS" — bot validators post as comments, invisible to check-runs/status.

**Auth-gated logs** (`stage.eightfold.ai/internal/s3viewer`) — auto-fetch via S3, never ask user:

```bash
LOG=/tmp/ci-<job>-<sha>.log
~/.claude/work_hq/fetch_ci_log.sh "<details_url>" > "$LOG"
tail -200 "$LOG"   # show only failing tail
```

Script reads AWS creds from `~/eightfold/wipdp/.env`. On AccessDenied/NoSuchKey, fall back to "ask user to paste" — last resort only. Surface the log path in the artifacts block.

**Sandbox-required failures**: don't fix in code. First check if `needs_sandbox` already exists in `/tmp/pr-<N>-comments.json` — look for any comment with body `needs_sandbox` from a non-bot account. If found, check whether the sandbox bot replied with the **current SHA** (grep bot reply bodies for the head SHA). If the sandbox already ran on the current SHA, it's done. If it ran on an older SHA, the push invalidated it — ask the top reviewer (most reviews, then most recent) to re-comment `needs_sandbox`. Never ask for a re-post when an up-to-date sandbox run already exists.

### B. Unresolved review comments

- `get_review_comments`: keep `isResolved: false` + `isOutdated: false`
- `get_comments`: skip `[bot]` accounts
- Also read `body` of every `get_reviews` entry — reviewers embed action items in approval body

### C. Merge conflicts — resolved in Step 2 rebase

### D. PR description / checklist failures

All PR body rules live in `/submit-pr` (single source of truth — checklist rules, mandatory sections, self-validation). To fix:
1. Follow `/submit-pr` Phase 3–4: read template with **Read tool**, fill checklist, self-validate
2. Also compare bidirectionally — bot may inject extra mandatory items not in template
3. Write body to temp file → `--body-file` → `update_pull_request`
4. Post `needs_ci` comment to re-trigger validation

### E. Impact analysis (code-review-graph)

Run with `base` = PR's `baseRefName`:
1. **`detect_changes_tool`** — risk-scored review guidance
2. **`get_impact_radius_tool`** — impacted functions/files, sibling files, downstream consumers
3. **`get_affected_flows_tool`** — execution flows through changed files

Use to: flag ripple effects across sibling files, surface unflagged downstream consumers, add discoveries to triage.

## Step 4 — Triage blockers

| Group | Label | When | Auto-loop? |
|---|---|---|---|
| 0 | **PR Metadata** | Checklist/body issues. Fix first, no code changes. | ✅ |
| 1 | **Quick Wins** | Mechanical: typos, renames, dead code, imports. | ✅ |
| 2 | **Medium** | Clear direction, needs thought: refactors, type hints, tests. | with approval |
| 3 | **Design** | Needs alignment first: architecture, requirements, tradeoffs. | ❌ STOP |
| 4 | **Not Ours** | Base branch failures, unrelated tests, infra issues. Document only. | ❌ |
| 5 | **External Actor** | `needs_sandbox`, awaiting reviewer approval, manual testing. | ❌ STOP |

CI scoping: files not in PR → 4. Existed in master before PR → 4. Your files → 1-3. Checklist → 0. Sandbox/reviewer-required → 5.

**Auto-loop policy:** Groups 0+1 may apply in CI loop without per-cycle approval (max 3 cycles). Groups 2+ require explicit user approval. Groups 3 and 5 surface "blocked on <X>" and stop the loop cleanly.

## Step 5 — Present results

Open: `Switched to {branch}, rebased onto {base}. Found X blockers: Y CI, Z comments. Mergeable: {state}`

Per group, numbered list:
```
{N}. [{CI|Review}] @{name} — "{quote}"
   {Fix:|Skip:|Pushback:} one-sentence action
   ```startLine:endLine:path
   // actual lines — read file, never guess
   ```
```

### Reviewer reply plan (tabular — MANDATORY before any push)

Before applying or pushing changes, present a single review-comment table covering ALL unresolved comments. CI commit-status checks (some bots) gate on threads being **resolved** — silently fixing code without resolving the thread leaves CI red. Likewise, a fix that needs no reply still needs the thread closed.

| # | Reviewer | Comment (quote) | Action | Reply to post (or "no reply — addressed by diff") | Resolve thread? |
|---|---|---|---|---|---|
| 1 | @samyak | "rename `tether_api_v2` to `tether_api_internal`" | code edit | _no reply — addressed by diff_ | ✅ after push |
| 2 | @rohit | "why not use the existing `BaseAgentNode`?" | reply only (pushback) | "Considered it — `BaseAgentNode` couples to LLM init which we don't need here. Keeping it lean." | ✅ after reply |
| 3 | @priya | "add a unit test for the empty-payload case" | code + reply | "Added in `test_proxy.py::test_empty_payload`. PTAL." | ✅ after push |
| 4 | @bot | "needs_sandbox" | external actor | _STOP — Group 5; ask top reviewer to comment `needs_sandbox`_ | ❌ — not ours to resolve |

Get user sign-off on the table BEFORE pushing or replying. Then on execution: post reply (Step 6) → push code (Step 6) → resolve thread via GraphQL `resolveReviewThread`. If the thread isn't resolved, the next CI tick will still see it open and may fail commit-status checks.

Close: one bullet per group theme, Group 4 recommendation, fix order 0→1→2→3, offer to implement.

## Step 6 — Implement

**Before applying any review comment**, invoke `Skill(skill="superpowers:receiving-code-review")` for that comment. It enforces: read, verify the technical claim, decide agree/pushback/clarify — *not* blind application. Prevents over-application.

If skill returns "pushback warranted" → reply on thread with reasoning, do NOT change code.
If "agree" → proceed to existing approval flow below.

**Never commit/push without explicit user approval.**

Group 0: follow `/submit-pr` Phase 3–4 rules (single source of truth for checklist) → fix body → `update_pull_request` → `needs_ci` comment.

**Critical:** `needs_ci` is **body-only**. After pushing code (Groups 1-3), do NOT post `needs_ci` — the push itself triggers CI. Posting it after a code push double-fires and confuses the bot. Only Group 0 (pure metadata edits with no commit) gets `needs_ci`.

Groups 1–3: implement → show changes → **test recommendation step (see below)** → ask approval → **delegate push to `/submit-pr` update-mode** → **post pending replies** (from the table column) → **resolve every thread marked ✅** in the table.

### Test recommendation step (between fix and push)

Before invoking `/submit-pr`, surface recommended tests based on repo + change diff. The skill does NOT push directly — `/submit-pr` is the single push entrypoint.

```
if repo == "wipdp":
    Recommend: source .venv && pytest <focused path>     (local; pytest.ini testpaths convention)

elif repo == "vscode":
    classify diff:
      • touches www/apps/*_app/ schemas/endpoints, endpoint_validation/,
        agents_app/, or any HTTP layer  → /test-live-api
      • touches backend Python (ops/, services/, lib/, except UI)  → /run-on-ec2
      • touches www/react/ only  → manual browser smoke test
                                    (surface npm command from runbooks.md)
      • mixed  → run both /test-live-api + /run-on-ec2
      • no recent EC2 server activity  → suggest runbooks.md "Server" section first

else (magnetx, etc.):
    based on repo's runbooks.md or skip with explicit note
```

Surface to user:
```
Recommended tests before push:
  • <skill or command> <args>
  • <skill or command> <args>   (if change touches multiple layers)
Run these now? (y/skip)
```

On `y` → invoke recommended skill(s); wait for green. On `skip` → log to `~/opensource/vault/wiki/log.md`: "tests skipped — user override on PR#<N>". Then in either case, hand off to `/submit-pr` update-mode.

**Hard rule on thread resolution.** A reviewer comment isn't "addressed" until its thread is `isResolved=true`. Some Eightfold CI commit-status checks (and reviewers' merge gates) only pass when 0 unresolved threads remain. After every code push or reply, walk the table and resolve each ✅ row. Don't leave this for "next iteration" — a stale unresolved thread keeps the PR red.

Resolution loop:
```bash
# For each thread_id in the table marked ✅:
gh api graphql -f query='mutation { resolveReviewThread(input: {threadId: "PRRT_..."}) { thread { isResolved } } }'
```

```bash
gh api graphql -f query='mutation { resolveReviewThread(input: {threadId: "PRRT_..."}) { thread { isResolved } } }'
```

**After every action** — always close with: `Done. PR: https://github.com/{owner}/{repo}/pull/{number}`

### Reply policy

Reply only when reviewer asked something needing textual response (design, naming, architecture, security). For code fixes — the diff is the reply. Write as the PR author, never third-person.

---

## Step 7 — Autonomous CI watch loop

After pushing fixes (Groups 0/1, plus any 2/3 explicitly approved), don't end with "CI is running" and walk away. Register a self-terminating loop that re-runs this skill until the PR is either ready-to-merge OR needs human input.

```bash
Skill(skill="loop", args="30m /get-pr-ready-to-merge <PR url>")
```

**Default to local in-session loop, NEVER cloud.** If `/loop` asks "set up cloud schedule instead?" via AskUserQuestion — always answer **"keep local"**. Only escalate to cloud if the user explicitly says "schedule on cloud" / "use CronCreate".

**Fallback when session closes.** The in-session `/loop` dies when Claude Code is closed. /ship-task captures this session's id on the task (`shared_context.watcher_session_id`); when the user next runs `/today`, it sees the failing PR, sees no live loop running, and surfaces `→ resume with: claude -r <session-id>`. The loop resumes naturally on reattach. So: schedule the loop here AND rely on /today as the cross-session bridge — they're complementary, not alternatives.

### Cadence policy (adaptive)

- **CI pending/running** → fire every **30m** for up to **8 iterations** (4h budget). Faster reaction to flaky CI re-runs while keeping the same overall budget.
- **Failure detected → fix pushed** → **reset counter to 0**. Each new push earns a fresh budget.
- **All green + no unresolved + approved** → STOP. Do not auto-merge — surface "ready to merge, your call" and exit.
- **Group 3 or Group 5 detected** → STOP. Surface blocker.
- **4h budget exhausted while still pending/running** → STOP. Surface "CI stuck pending after 4h".
- **3 consecutive iterations with same failures, no fix progress** → STOP. Surface "loop unproductive".

### Self-termination matrix

| Detected on a loop fire | Action |
|---|---|
| `mergeable_state == "clean"` AND no `changes_requested` | STOP — surface ready-to-merge |
| ONLY Group 4 + your-files green | STOP — as good as it gets; surface ready-to-merge |
| ANY Group 5 (External Actor) | STOP — "blocked on <actor>" |
| ANY Group 3 (Design) | STOP — "needs architectural decision" |
| Group 2 needing approval not pre-authorized | STOP — for explicit user OK |
| 8 iterations elapsed (4h), CI still pending, no failures | STOP — "CI stuck pending after 4h" |
| 3 iterations with identical failures, no successful fix | STOP — "loop unproductive" |

### State persistence between fires

```bash
# On loop entry, BEFORE work:
python3 ~/.claude/work_hq/update.py get <TICKET_ID>
# read shared_context.ci_loop = {iteration, last_failure_sig, started_at}

# After this iteration:
python3 ~/.claude/work_hq/update.py set <TICKET_ID> \
  --field "shared_context.ci_loop.iteration=<n>" \
  --field "shared_context.ci_loop.last_failure_sig=<hash-of-failing-checks>"

# On a successful push that fixed something — RESET:
python3 ~/.claude/work_hq/update.py set <TICKET_ID> \
  --field "shared_context.ci_loop.iteration=0"
```

### On exit, always

1. Stop the loop.
2. Update work_hq stage:
   ```bash
   # Ready-to-merge:
   python3 ~/.claude/work_hq/update.py set <TICKET_ID> --field stage=ready-to-merge
   python3 ~/.claude/work_hq/update.py needs-input add <TICKET_ID> \
     --reason "ready-to-merge" --action "merge the PR"

   # Blocked on external actor (Groups 3/5):
   python3 ~/.claude/work_hq/update.py set <TICKET_ID> --field stage=in-review
   python3 ~/.claude/work_hq/update.py needs-input add <TICKET_ID> \
     --reason "<group-3-design|group-5-external-actor>" --action "<one-line>"
   ```
3. Surface a final-state line + register the item in `~/.claude/work_hq/needs_input.json` so it appears in `/today`.

### Surface once on registration

```
↳ CI watch loop registered: /loop 30m on PR #<n>. Budget: 4h while pending (8 ticks); resets on each fix. Stops on ready-to-merge or human-required state.
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| Checklist re-validation not triggered | Add `needs_ci` comment |
| "Mandatory field not checked" despite checked | Duplicate item — remove unchecked dupe, `needs_ci` |
| check_runs green but merge box shows failures | Call `get_status` — external CI uses commit statuses |
| check_runs green but checklist failing | Scan `get_comments` for bot messages |
| Mandatory item not in template | Bot-injected — compare bidirectionally |
| CI breaks after MCP body update | Decode HTML entities first |
| `url mismatch` in checklist | Copy URL byte-for-byte from local template |
| 422 on `gh api` with `in_reply_to` | Use `-F` (capital) for numeric fields |
| Push but no new commits in PR | Check `git status` clean before push |
| CI blocked after code fixes pushed | Resolve threads via GraphQL |
| CI "requires sandbox" | Not a code defect. Top reviewer must comment `needs_sandbox` |
| `needs_sandbox` already in comments but full CI not run | Check if sandbox bot replied with the **current SHA** — if old SHA, push invalidated it; ask reviewer to re-comment. If current SHA, sandbox ran fine; wait for full CI results. |
| `REVIEW_REQUIRED` but all individual reviews approved | A **team reviewer** is pending — check `reviewRequests` for `__typename: "Team"` entries. Fetch members via `gh api orgs/{org}/teams/{slug}/members` and surface who to ping. |

## Design doc PR comments

Don't apply blindly. Analyse all first → group by theme → one at a time with approval → push back when warranted.

See [EXAMPLES.md](EXAMPLES.md) for examples.

---

## Passive context updates throughout

Per the passive-context-updates feedback rule, invoke `python3 ~/.claude/work_hq/update.py append-context <TICKET_ID> --decision "<info>"` whenever you discover a CI cause, fix approach, or new blocker — immediately, one-liner notification, never ask. Bubble up to `project:update` if the cause/decision affects the broader initiative.

## Workflow ending

Before completing, the final-state summary (blockers resolved, current PR state) is also auto-saved via `python3 ~/.claude/work_hq/update.py append-context <TICKET_ID> --decision "..."`.

```
───── workflow ─────
✓ Ticket          : ENG-XXXXX
✓ Rebase          : clean onto <base>
✓ Blockers fixed  : <N> CI, <M> comments
✓ work_hq         : <TICKET_ID> → <new stage>
✓ CI watch        : /loop 1h registered  (or: stopped, reason: <X>)
→ Status          : <ready-to-merge|blocked on <actor>|in CI loop>
────────────────────

───── artifacts ─────
Jira    : https://eightfoldai.atlassian.net/browse/<TICKET_ID>
PR      : https://github.com/{owner}/{repo}/pull/{number}
Branch  : <repo>:{headRefName}
Plan    : <repo>/plans/<TICKET_ID>.md       (only if it exists)
Board   : ~/.claude/work_hq/board.md  → task <TICKET_ID>
Initiative: ~/opensource/vault/wiki/projects/<repo>/initiatives/<slug>/   (only if linked)
Logs    : /tmp/ci-<job>-<sha>.log            (only if CI logs were fetched)
Loop    : /loop 30m /get-pr-ready-to-merge <pr-url>   (running | stopped: <reason>)
─────────────────────
```

Omit any line whose artifact wasn't touched in this run.

### DO NOT delegate to /pr-watcher

`/pr-watcher` only delivers ntfy notifications on PR state change — it does NOT triage failures, fetch logs, or auto-fix. Do not register `/pr-watcher` from this skill, even passively. The autonomous loop is **Step 7** (`/loop 1h /get-pr-ready-to-merge <pr-url>`), which re-invokes THIS skill so each tick can do real work. Misroute observed in session c9c186d0: skill ended with "ntfy notification if CI fails or goes green" — wrong tool, wasted the loop.

---

## Pre-entry: lazy-load context

In this order, on every entry (initial or loop fire):

1. `python3 ~/.claude/work_hq/update.py get <TICKET_ID>` (work_hq) — LEGACY back-compat reader. Skip silently if missing.
2. `python3 ~/.claude/work_hq/update.py get <TICKET_ID>` — **primary** source: cross-branch shared_context, scope, decisions, ci_state, review_state, ci_loop counter.
3. If task has `initiative_slug`, also load `~/opensource/vault/wiki/projects/<repo>/initiatives/<slug>/{charter,decisions,learnings,e2e-flow}.md` (`<repo>` from board task; initiative knowledge moved from work_hq → vault on 2026-05-03; `ticket-graph.md` stays in work_hq).

Run #2 + #3 even if PR is for a different repo than `pwd` — work_hq is project-agnostic.

### Ask-to-seed rule

If a required piece of context is missing (no Jira ticket linked from PR, ambiguous reviewer comment, no test files for code being changed, unknown initiative slug, etc.) — **STOP and ASK the user to seed it**. One question at a time, then proceed. Don't guess.

## work_hq updates (passive, throughout)

Use SHORT repo slug everywhere:

```bash
REPO=$(git remote get-url origin | sed -E 's#.*/([^/.]+)(\.git)?$#\1#')

# After CI fix-loop iteration:
python3 ~/.claude/work_hq/update.py set <TICKET_ID> \
  --field "ci_state=<green|failing|in_progress>"

# After review comment applied/replied:
python3 ~/.claude/work_hq/update.py set <TICKET_ID> \
  --field "review_state=<approved|changes_requested|commented>"

# When all green + 0 unresolved + approved:
python3 ~/.claude/work_hq/update.py set <TICKET_ID> --field stage=ready-to-merge

# When merged:
python3 ~/.claude/work_hq/update.py set <TICKET_ID> --field stage=merged

# For each CI cause/fix, append to learnings.md (vault path; <repo> from board task):
echo "- $(date -u +%FT%TZ): CI fix — <one line>" >> ~/opensource/vault/wiki/projects/<repo>/initiatives/<slug>/learnings.md
```

## Pre-push: re-test before pushing fixes

Before pushing a code fix, in order:

1. **Identify test files** for the modified code (same patterns as `/work-on-jira-task` Step 5: `*.test.ts(x)`/`*.spec.ts(x)`/`__tests__` for vscode, `tests/test_*.py` for wipdp). If none exist → record `↳ saved to branch context: no tests for <component> — skip` and proceed.

2. **Skip lint on EC2** — pre-commit hook handles it.

3. **Run identified tests** (BEFORE pushing fixes, unless explicitly told otherwise):
   - **vscode → `/run-on-ec2`** for unit/pytest tests (mandatory if files exist + VPN up; record skip reason in branch context if VPN down). For HTTP/endpoint integration tests against the live dev instance, use **`/test-live-api`**.
   - **wipdp → local pytest**.
   - Push only after tests pass. No exceptions without explicit user override.

4. Doc-only / comment-only fixes are skippable without recording.

---

## Data Contract

### Reads (DB)
- `~/opensource/vault/wiki/projects/<repo>/runbooks.md` — CI/sandbox how-to (S3 log fetching, sandbox triggers, gh account switch)
- `~/opensource/vault/wiki/patterns/code-conventions.md` — review reply style, no try/except unless asked, etc.
- `~/opensource/vault/wiki/projects/<repo>/decisions.md` — prior decisions referenced in review comments
- `~/opensource/vault/wiki/projects/<repo>/initiatives/<slug>/{charter,decisions,learnings,e2e-flow}.md` — when applicable

### Reads (Memory)
- `~/.claude/work_hq/board.json[task_id]` — current ci_state, review_state, ci_loop iteration, files_of_interest (scope allowlist seed)
- `~/opensource/vault/wiki/hot.md` — active task confirmation
- `~/opensource/vault/wiki/projects/<repo>/open-threads.md` — related threads

### Writes (Memory)
- `~/.claude/work_hq/board.json` — ci_state, review_state, ci_loop {iteration, started_at, last_failure_sig}
- `~/.claude/work_hq/needs_input.json` — on hard blocker (Group 3 design / Group 5 external actor) or ready-to-merge
- `~/opensource/vault/wiki/projects/<repo>/initiatives/<slug>/learnings.md` — CI fix learnings (one line per resolved cause)
- `~/opensource/vault/wiki/hot.md` — state transitions
- `~/opensource/vault/wiki/log.md` — per-event ("CI fixed: ruff", "review thread resolved", "Group 3 stop on PR#XXXX")
- `~/opensource/vault/wiki/projects/<repo>/open-threads.md` — when a review comment becomes a deferred thread (per CLAUDE.md protocol)

### Local (skill-only)
- `/tmp/pr-<N>-{checkruns,status,comments,reviews,threads}.json` — per-tick gh fetch caches, ephemeral
- `/tmp/ci-<job>-<sha>.log` — fetched CI log, ephemeral

### Live external (not stored)
- `gh` PR check-runs, status, reviews, comments, threads, file diffs
- CI logs from S3 via `~/.claude/work_hq/fetch_ci_log.sh`
