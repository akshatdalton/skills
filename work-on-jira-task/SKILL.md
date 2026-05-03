---
name: work-on-jira-task
description: Structured workflow for working on Jira tasks — fetches ticket details, creates feature branch, discovers context, collaboratively plans the implementation, then implements after approval. Use when the user provides a Jira ticket URL (e.g., https://eightfoldai.atlassian.net/browse/ENG-12345), says "let's work on ENG-XXXXX", "pick up this ticket", or pastes any eightfoldai.atlassian.net URL.
---

# Work on Jira Task

Understand → plan → implement. Order matters.

## Step 0 — DB context surface (NEW — happens before lazy-load)

At task entry, surface a 3-line context summary built from vault DB reads, BEFORE asking the user anything. This eliminates the session-start paste burden (38 events in first 3 messages observed in past 14 days).

1. Determine `<repo>` (from `git remote get-url origin` short slug — `vscode`, `wipdp`, `magnetx`).
2. Read these vault files in parallel and synthesize a 3-line summary:
   - `~/opensource/vault/wiki/projects/<repo>/overview.md` (project context)
   - `~/opensource/vault/wiki/projects/<repo>/runbooks.md` (env setup, server start)
   - `~/opensource/vault/wiki/projects/<repo>/decisions.md` (prior decisions)
   - `~/opensource/vault/wiki/patterns/code-conventions.md` (coding rules)
   - `~/opensource/vault/wiki/projects/<repo>/open-threads.md` (any thread tied to this ticket — match by ENG-XXXXX in H2)
3. Surface a 3-line context summary BEFORE Step 0.5:

```
↳ <repo> context loaded:
  • <one-line about project + key tech>
  • <one-line about env: e.g., "tests on EC2 via /run-on-ec2" or "local pytest, source .venv first">
  • <one-line about prior decisions or open threads relevant to this ticket, OR "no related open threads">
```

This is a READ phase — do not block, do not ask questions. Just surface and proceed.

## Step 0.5 — Lazy-load work_hq (auto)

Run in this order, all auto, no prompts:

1. **Identification priority** — resolve TICKET_ID by precedence:
   - User-provided artifact in current prompt (Jira URL or GitHub PR URL) → HIGHEST priority
   - Fallback: current git branch name (regex `ENG-\d+`)
2. **work_hq lookup** — `python3 ~/.claude/work_hq/update.py get <TICKET_ID>`. If exists, load its `initiative_slug`, `shared_context`, `stage`. Surface:
   ```
   ↳ initiative=<slug> · ticket=<TICKET_ID> · branch=<name> · stage=<s>
   ```
3. **Initiative load** — if `initiative_slug` is set, read `~/opensource/vault/wiki/projects/<repo>/initiatives/<slug>/{charter,decisions,learnings,e2e-flow}.md` for the cross-repo evolving picture. (`<repo>` = the task's `repo` field from board.json. Initiative knowledge moved from work_hq → vault on 2026-05-03.)
4. **Cross-repo sibling check** — scan initiative's `ticket-graph.md` (still in `~/.claude/work_hq/initiatives/<slug>/ticket-graph.md` — operational, did not move to vault). If sibling tickets have open PRs in a DIFFERENT repo than `pwd`, surface ONCE:
   ```
   ↳ sibling work in flight: <repo>:<branch> → PR #<n>. Initiative context loaded.
   ```
5. **No initiative_slug yet** → suggest from existing `~/.claude/work_hq/initiatives/` slugs (substring match against ticket title/description) OR offer to create new slug. If still no match, **ASK the user to seed an initiative slug** (or accept "no initiative" if this ticket is standalone).

### Ask-to-seed rule (applies throughout this skill)

If at ANY step a required piece of context is missing (priority not on the Jira ticket, no design doc linked, ambiguous scope, no reference pattern, no test files when tests are required, no initiative slug, etc.) — **STOP and ASK the user to seed it**. Never invent or assume. One question at a time, then proceed.

## Step 1 — Fetch ticket

Extract ticket ID. Atlassian MCP `getJiraIssue` (cloudId: `eightfoldai.atlassian.net`). Display summary, description, acceptance criteria, linked docs.

**IMPL-\*:** Check `issuelinks` for linked ENG-\*. None → tell user to transition IMPL to "Code Fix Needed". No branch without ENG number.

## Step 2 — Branch

`akshat/ENG-<number>-<short-name>` (always ENG; 2-4 word suffix)

```bash
git checkout master && git pull origin master
git checkout -b akshat/ENG-[NUMBER]-[short-name]
```

Stacked: `git checkout -b akshat/ENG-[NUMBER]-[short-name] [parent-branch]`

Create only. No push yet.

**Register in work_hq + vault** (Memory writes at task-start lifecycle event):

```bash
REPO=$(git remote get-url origin | sed -E 's#.*/([^/.]+)(\.git)?$#\1#')   # "vscode" or "wipdp"
python3 ~/.claude/work_hq/update.py upsert <TICKET_ID> \
  --title "<jira summary>" --priority <P0|P1|P2 from Jira> --stage in-progress \
  --repo "$REPO" --branch "$(git branch --show-current)" \
  --jira "https://eightfoldai.atlassian.net/browse/<TICKET_ID>"
# If initiative is known/agreed:
python3 ~/.claude/work_hq/update.py set <TICKET_ID> --field initiative_slug=<slug>

# Vault writes — immediate, do not defer to /today refresh:
echo "$(date -u +%FT%TZ) work-on-jira-task: started <TICKET_ID> on $REPO branch $(git branch --show-current)" >> \
  ~/opensource/vault/wiki/log.md
# hot.md "Active Right Now" — replace the line for this <repo> via a small Python edit:
python3 - <<EOF
import re, os, datetime as dt
p = os.path.expanduser("~/opensource/vault/wiki/hot.md")
txt = open(p).read()
new = "- **$REPO**: <TICKET_ID> — $(git branch --show-current) — in-progress"
# Replace the line starting with "- **$REPO**:" under "## Active Right Now"
txt = re.sub(r"(## Active Right Now\s*(?:\n.*)*?)\n- \*\*$REPO\*\*:[^\n]*", r"\1\n" + new, txt, count=1)
open(p, "w").write(txt)
EOF
```

Adds the ticket to the initiative's `ticket-graph.md` (operational, stays in work_hq):

```bash
echo "- $(date -u +%F): ENG-${TICKET_NUM} ($REPO) — <title>" >> \
  ~/.claude/work_hq/initiatives/<slug>/ticket-graph.md
```

## Step 3 — Discover context

1. Grep repo for ticket ID/keywords
2. Check subdirs matching domain
3. Confluence via MCP if ticket links page
4. Fetch linked design docs/PRs

"See X for pattern" / "matches how Y works" → read references immediately. Simplest way to apply same pattern. Vague mentions ≠ refactoring scope.

**Inline context provided** → merge with findings, skip asking for more.
**No inline context + broad scope** → ask for class/component/file/CSS class to start from.

## Step 3.5 — Check existing plan

Check both before writing new:
1. `~/.claude/plans/tickets/{TICKET_ID}.md`
2. `~/.claude/projects/.../branches/{branch_name}/`

Exists → display, ask reuse or new. No plan → Step 4.

**Always persist** to `~/.claude/plans/tickets/{TICKET_ID}.md` immediately on create/modify.

## Step 4 — Plan

Delegate planning to superpowers — battle-tested for spec→plan handoff:

1. **Brainstorm** — `Skill(skill="superpowers:brainstorming")` with ticket details + Step 3 findings. Required for non-trivial tickets (>1 file or design decisions). Skip for trivial mechanical changes (typo fixes, single-line tweaks).
2. **Write plan** — `Skill(skill="superpowers:writing-plans")`. Persists to **`<repo>/plans/<TICKET_ID>.md`** (in-repo, superpowers convention). Step-by-step plan with verification checkpoints.
3. **Scope gate** — same as before: state IN scope vs deferred for "API not ready" / "wiring handled by team" / "match pattern X". Confirm before approval.
4. *"Does this approach make sense? Anything to adjust?"* — do not implement until explicit approval.

Persist plan reference + decisions into work_hq:

```bash
python3 ~/.claude/work_hq/update.py append-context <TICKET_ID> --doc "plans/<TICKET_ID>.md"
# For each material decision from brainstorming:
python3 ~/.claude/work_hq/update.py append-context <TICKET_ID> --decision "<one line>"
# Mirror to initiative decisions if cross-cutting (vault path; <repo> from board task):
echo "- $(date -u +%F) [<TICKET_ID>]: <decision>" >> \
  ~/opensource/vault/wiki/projects/<repo>/initiatives/<slug>/decisions.md
```

Legacy: the older `~/.claude/plans/tickets/<TICKET_ID>.md` path mentioned in Step 3.5 still gets read for back-compat, but new plans go to `<repo>/plans/<TICKET_ID>.md`.

## Step 5 — Implement

Follow approved plan. Deviate only if unexpected — explain first.

- Only modify ticket-relevant files
- Stacked: `git diff [parent-branch] --name-only` to verify no drift

For code conventions (method ordering, imports, testing, docs): read [references/code-conventions.md](references/code-conventions.md).

Grep codebase before inventing. Match existing patterns.

**Record files of interest into work_hq** — every materially-edited file enters the cross-branch shared_context:

```bash
for f in <modified-files>; do
  python3 ~/.claude/work_hq/update.py append-context <TICKET_ID> --file "$f"
done
```

### Test before declaring done

Before Step 6 (commit + PR), do this in order:

1. **Identify test files** for the code being changed:
   - vscode → look for `*.test.ts(x)`, `*.spec.ts(x)`, or `__tests__/` adjacent to each modified file
   - wipdp → look for `tests/test_<modname>.py` or `tests/<area>/test_*.py`
   - **If none exist** → record once in branch context: `↳ saved to branch context: no test files for <component> — skipped test run` and skip to step 4.

2. **Do NOT run lint on EC2** — pre-commit hook (vscode: husky; wipdp: ruff) handles lint before commit. EC2 time is for actual tests, not lint.

3. **Run identified tests** (BEFORE any push, unless explicitly told otherwise):
   - **vscode → `/run-on-ec2`** for unit/pytest tests (mandatory if test files exist AND VPN is up). For HTTP/endpoint integration tests against the live dev instance (akshat-v.dev.eightfold.ai), use **`/test-live-api`**. If VPN down or EC2 unreachable → record `↳ saved to branch context: EC2 unreachable, tests deferred — risk: <test files>` and proceed.
   - **wipdp → local pytest** is sufficient.
   - Both must pass before `git push`. The skill never declares "tests passing" without evidence.

4. **Surface manual verification** — if branch context has a `## Test Environment` section with sandbox URL + nav steps, surface them: "Verify manually at <sandbox>: <steps>" before declaring done. Do not block — just remind.

The skill never claims "tests passing" without evidence. "No test files exist" or "infra unavailable" are valid skip reasons ONLY when recorded in branch context.

## Step 6 — Commit and PR

Show: (1) files to stage, (2) commit message, (3) PR description. Single approval → add+commit+push+`/submit-pr` without pausing.

```bash
git add <file1> <file2> ...     # ticket-relevant only
git commit -m "ENG-XXXXX: Brief summary

What changed and why.
Fixes IMPL-XXXXXX."

git push -u origin <branch>
```

**Advance work_hq stage:**

```bash
python3 ~/.claude/work_hq/update.py set <TICKET_ID> --field stage=in-review
```

**Auto-detect repo** via `git remote get-url origin`:
- **wipdp** → prose: Summary (2-4 sentences) + JIRA TASK + TEST PLAN (bash block). Write to temp file, use `--body-file`.
- **vscode** → `/submit-pr` (own checklist)

After push: *"Ready? I'll run `/submit-pr`."*

---

## Passive context updates throughout

Whenever you learn a material fact during this skill — a key file, a root cause, a design decision — write it through immediately to work_hq:

```bash
python3 ~/.claude/work_hq/update.py append-context <TICKET_ID> --decision "<one-line>"
python3 ~/.claude/work_hq/update.py append-context <TICKET_ID> --file "<path>"
```

For initiative-level findings (decisions or learnings that apply beyond this ticket — vault paths, `<repo>` from board task):

```bash
echo "- $(date -u +%F) [<TICKET_ID>]: <decision>" >> ~/opensource/vault/wiki/projects/<repo>/initiatives/<slug>/decisions.md
echo "- $(date -u +%F): <learning>" >> ~/opensource/vault/wiki/projects/<repo>/initiatives/<slug>/learnings.md
```

Surface a one-liner `↳ saved to work_hq: ...`. Never ask first; never batch to the end.

## Workflow ending

```
───── workflow ─────
✓ Ticket    : ENG-XXXXX
✓ Branch    : akshat/ENG-XXXXX-short-name
✓ Initiative: <slug>   (if linked)
✓ Implemented + tests passing
✓ work_hq   : <TICKET_ID> → in-review
→ Next      : /submit-pr (auto-adds PR to /pr-watcher)
────────────────────

───── artifacts ─────
Jira       : https://eightfoldai.atlassian.net/browse/<TICKET_ID>
Plan       : <repo>/plans/<TICKET_ID>.md
Branch     : <repo>:akshat/ENG-XXXXX-short-name
Initiative : ~/opensource/vault/wiki/projects/<repo>/initiatives/<slug>/   (only if linked; ticket-graph stays in ~/.claude/work_hq/initiatives/<slug>/)
Board      : ~/.claude/work_hq/board.md  → task <TICKET_ID>
─────────────────────
```

Omit any line whose artifact wasn't created/touched.

PR watching is handled by `/submit-pr` — no separate step here.

---

## Data Contract

### Reads (DB) — at task entry, before implementation
- `~/opensource/vault/wiki/projects/<repo>/overview.md` — project context
- `~/opensource/vault/wiki/projects/<repo>/runbooks.md` — env setup, server start, gh account switch
- `~/opensource/vault/wiki/projects/<repo>/decisions.md` — prior decisions in this area
- `~/opensource/vault/wiki/patterns/code-conventions.md` — coding rules
- `~/opensource/vault/wiki/projects/<repo>/initiatives/<slug>/{charter,decisions,learnings,e2e-flow}.md` — when `initiative_slug` is on the board entry

### Reads (Memory)
- `~/.claude/work_hq/board.json[task_id]` — current state, branch, PR#, prior checkpoints
- `~/.claude/work_hq/initiatives/<slug>/ticket-graph.md` — sibling tickets in flight
- `~/opensource/vault/wiki/projects/<repo>/open-threads.md` — any thread tied to this ticket
- `~/opensource/vault/wiki/hot.md` — active state confirmation

### Writes (Memory)
- `~/.claude/work_hq/board.json` — stage=in-progress, branch, repo, initiative_slug, shared_context.{decisions[], files_of_interest[]}
- `~/.claude/work_hq/initiatives/<slug>/ticket-graph.md` — append new ticket entry
- `~/opensource/vault/wiki/projects/<repo>/initiatives/<slug>/{decisions,learnings}.md` — initiative-level findings (passive throughout)
- `~/opensource/vault/wiki/hot.md` — write "Active Right Now" line directly (do not wait for `/today` refresh)
- `~/opensource/vault/wiki/log.md` — append "started ENG-XXXXX"
- `~/opensource/vault/wiki/projects/<repo>/open-threads.md` — append H2 if blocker / parked-question encountered (per CLAUDE.md protocol)

### Local (skill-only)
- `~/.claude/plans/tickets/<TICKET_ID>.md` — legacy plan path (read for back-compat)
- `<repo>/plans/<TICKET_ID>.md` — new plan path (superpowers convention)

### Live external (not stored)
- Jira ticket via Atlassian MCP `getJiraIssue`
- Confluence via MCP if linked from ticket
