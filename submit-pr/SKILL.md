---
name: submit-pr
description: Create or update GitHub pull requests following team standards — full workflow from git commit through PR creation and CI validation. Use when the user asks to create a PR, push changes, submit for review, update a PR description, or mentions pull requests. Handles PR template compliance, checklist bot validation, and GitHub MCP tool integration. Also trigger on "push and create PR", "submit this for review", "update the PR description", or "my PR is failing checklist validation".
---

# Submit Pull Request

## Pre-entry: work_hq contract (mandatory — do not skip)

On entry, MUST invoke `python3 ~/.claude/work_hq/update.py get <TICKET_ID>` (work_hq) first. Surface one-line `↳ loaded ...` or `↳ no context yet`.

After PR is created/updated, MUST invoke `python3 ~/.claude/work_hq/update.py append-context <TICKET_ID> --decision "PR #<N> created at <url>, base=<branch>"` and surface `↳ saved to branch context: ...`. Also bubble up to project layer if this PR is part of a stack: appending to `~/opensource/vault/wiki/projects/<repo>/initiatives/<slug>/decisions.md` (one-line; initiative knowledge moved from work_hq → vault on 2026-05-03).

Never ask. Save and notify.

## Default: Fast Mode

Collapse all gates into single confirmation. Show: files to stage, commit message, PR title. Execute add+commit+push+create/update without pausing. Stop only on error.

**Explicit approval mode:** User says "step by step" or "confirm each step" → multi-gate workflow.

Use GitHub MCP tools. Fall back to `gh` CLI only if MCP unavailable.

---

## Phase 1 — Pre-flight

### 1a — Jira ticket

PR's `## JIRA TASK:` must link **ENG-\*** — never IMPL directly.

- **ENG-\*** in hand → use it.
- **IMPL-\*** → fetch via Atlassian MCP, check `issuelinks` for linked ENG-\*.
  - Found → use that ENG.
  - Not found → transition IMPL to "Code Fix Needed" (transition id `121` on `eightfoldai.atlassian.net`) — auto-creates ENG.

Note test env from Jira description for TEST PLAN.

### 1b — Branch name

Format: `akshat/ENG-<ticket_number>-<very-short-name>`

Flag if uses IMPL number or wrong format.

### 1c — Up to date

```bash
git fetch origin master
git log HEAD..origin/master --oneline   # should be empty
```

If behind: `git rebase origin/master`.

### 1d — Lint

```bash
ruff check <changed-files>
ruff format <changed-files>
npm run lint:fix:files <changed-files>   # JS/TS
```

Fix before proceeding.

---

## Phase 2 — Commit and push

Stage **only ticket-relevant files** — never `git add .`.

Show user: (1) files to stage, (2) commit message, (3) runs in one go. **Wait for approval, then run all three.**

Commit format:
```
ENG-XXXXX: Brief summary

What changed and why — motivation, not mechanics.
Fixes IMPL-XXXXXX.   ← if from customer IMPL
```

```bash
git add <file1> <file2> ...
git commit -m "..."
git push -u origin <branch>    # first push
```

Fix any hook failures before re-attempting.

---

## Phase 2.5 — Test gate (NEW — single push entrypoint enforcement)

Before pushing, the skill confirms tests have been run.

- **Invoked from `/get-pr-ready-to-merge` after fixes** OR **from `/work-on-jira-task` after Step 5 tests pass**: the upstream skill has already run tests. No prompt needed.
- **Standalone invocation** (user types `/submit-pr` directly): prompt:
  ```
  Have tests been run for the changes about to push? (Y/n)
  If no: recommended for this change:
    • <repo-specific test command from runbooks.md>
  ```
  On `n` → invoke the recommended test skill (`/run-on-ec2`, `/test-live-api`, or local pytest); resume after green. On `Y` → proceed.
  On user override `skip` → log to `~/opensource/vault/wiki/log.md`: "tests skipped — user override".

This guarantees `/submit-pr` is the single push entrypoint AND that no push happens without tests (or explicit override).

## Phase 3 — Create or update PR

Check existing PR via `gh pr view --json state,headRefName 2>/dev/null` (faster than MCP list).
- **Exists** → **update-mode**: `gh pr edit <N> --body-file <body.md>` for description changes; `git push` for code commits. Update `board.json` last_push_at + ci_state=pending.
- **None** → **create-mode**: `gh pr create` (or MCP `create_pull_request`).

**Auto-detect repo** via `git remote get-url origin`:
- **wipdp** → prose: Summary (2-4 sentences), JIRA TASK link, TEST PLAN (bash block). Write body to temp file, use `--body-file`.
- **vscode** or other → read `.github/PULL_REQUEST_TEMPLATE.md`, fill checklist.

**Draft mode:** User says "keep in draft" → `--draft`.

**CRITICAL:** Always read `.github/PULL_REQUEST_TEMPLATE.md` from filesystem — never reconstruct from memory. Use the **Read tool** (not Bash `cat`/`head`) — Bash truncates at arbitrary line counts and silently drops sections at the bottom of the file. MCP encodes special chars as HTML entities, breaks CI. **ALWAYS** write body to temp file, pass `--body-file`. Never inline.

Fill all sections, self-validate (Phase 4) before submitting.

---

## PR Body Reference

### Summary
2-3 sentences. What changed and why. No bullet lists, no headers.

Good: prose paragraph explaining problem + fix + pattern followed.
Bad: bullet points, "Error Handling" sub-sections, implementation minutiae.

### JIRA Task
```markdown
## JIRA TASK:
https://eightfoldai.atlassian.net/browse/ENG-XXXXX
```
Always ENG-*, never IMPL-*.

### Gate/Config
```markdown
## GATE/CONFIG:
NA
```
Or if gated: `[gate_name](https://stage.eightfold.ai/debug/config?config=gate_name)`

### Checklist rules

1. **Never delete any item** — keep all `[ ]` lines verbatim
2. **Only add `x`**: `[ ]` → `[x]`, never remove
3. **Never modify item text**
4. **URLs byte-for-byte identical** — especially "deploying all services" Atlassian URL
5. **Fill all `_____` blanks** — replace with value or `N/A`
6. **Every section needs at least one `[x]`**

**Mandatory sections** (CI fails if untouched): Product area, Handle Edge cases gracefully, Gate Control, Testing, A11y Compliance, AI Recruiter, Sandbox Refresh, PR Description for customer release.

**Always check last:**
- `[x] If scripts are used in DAGs, list tested regions: NA`
- `[x] If new dags in dags_config.json need to run in westus2...`
- `[x] I have gone through the updated checklist.`

**Auto-added items** (do NOT add manually):

| Trigger | Items auto-added |
|---|---|
| `**/requirements.txt` or `**/package.json` changed | Package license, ownership, memory, design doc, GitHub bot |
| `scripts/airflow_v2/dags-*` or `www/airflow_v2/dags_config.json` changed | DAG regions, westus2, alarm config |

Adding manually when not triggered → CI failure.

For checklist patterns: [references/checklist-patterns.md](references/checklist-patterns.md).

### Test Plan

**Backend (pytest):** Just the command, no prose.
```markdown
## TEST PLAN:
```bash
cd www && pytest path/to/test_file.py -v
```
```

**Frontend / manual:**
```markdown
## TEST PLAN:
1. Log in as `<user>@<sandbox>.com` on https://<env>.eightfold.ai
2. Navigate to <path>
3. <action>
4. Expected: <result>
```

---

## Phase 4 — Self-validate

Scan PR body before submitting:

1. **No HTML entities** — `&amp;`, `&#39;`, `&quot;` → decode. MCP encodes; CI rejects.
2. **No unfilled blanks** — no `_____` remaining.
3. **Mandatory sections covered** — every section has `[x]`.

Submit only after all pass.

---

## After submitting

```bash
gh pr checks <pr-number>
```

If CI fails: [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

Do **not** post top-level summary comment. Only reply to specific reviewer threads.

---

## Workflow ending

Before completing:
1. `python3 ~/.claude/work_hq/update.py append-context <TICKET_ID> --decision "<PR url + CI status>"` (existing).
2. **work_hq** — register PR on the task and advance stage:

```bash
REPO=$(git remote get-url origin | sed -E 's#.*/([^/.]+)(\.git)?$#\1#')
python3 ~/.claude/work_hq/update.py upsert <TICKET_ID> \
  --repo "$REPO" --branch "$(git branch --show-current)" --pr <PR_NUMBER> --stage in-review
```

Then surface:

```
───── workflow ─────
✓ Ticket    : ENG-XXXXX
✓ Branch    : akshat/ENG-XXXXX-short-name
✓ PR        : <url>
✓ CI        : running
✓ work_hq   : <TICKET_ID> → in-review
→ If CI fails: /get-pr-ready-to-merge   (or /ship-task <TICKET_ID>)
────────────────────

───── artifacts ─────
Jira       : https://eightfoldai.atlassian.net/browse/<TICKET_ID>
PR         : <url>
Branch     : <repo>:<branch>
Commit     : https://github.com/<owner>/<repo>/commit/<sha>
Plan       : <repo>/plans/<TICKET_ID>.md   (only if exists)
Initiative : ~/opensource/vault/wiki/projects/<repo>/initiatives/<slug>/   (only if linked; ticket-graph stays in ~/.claude/work_hq/initiatives/<slug>/)
Board      : ~/.claude/work_hq/board.md  → task <TICKET_ID>
─────────────────────
```

Omit any line whose artifact wasn't created in this run.

### Auto-add to /pr-watcher (passive)

After the PR is created/updated and CI is running, invoke `/pr-watcher` in ADD mode silently — do NOT ask first. Use `Skill(skill="pr-watcher", args="add <PR url>")`. The pr-watcher skill auto-starts `/loop 1h /pr-watcher` in this tab if not already running.

Surface a single line in chat:

```
✓ Watching #<N> via /pr-watcher (this tab is now the watcher — leave it open)
```

If the user objects in the next message, run `/pr-watcher remove <id>`.

---

## Data Contract

### Reads (DB)
- `~/opensource/vault/wiki/patterns/code-conventions.md` — PR body rules (minimal, no bullets, runnable test plan, no Co-Authored-By)
- `~/opensource/vault/wiki/projects/<repo>/runbooks.md` — gh account switch
- `<repo>/.github/PULL_REQUEST_TEMPLATE.md` — checklist template (in-repo, single source for the bot)

### Reads (Memory)
- `~/.claude/work_hq/board.json[task_id]` — branch, repo, ticket info, files_of_interest, current pr (for update-mode)

### Writes (Memory)
- `~/.claude/work_hq/board.json` — stage=in-review (create-mode), pr=#XXXX, last_push_at, ci_state=pending (update-mode)
- `~/opensource/vault/wiki/projects/<repo>/initiatives/<slug>/decisions.md` — append PR-creation/update line if part of an initiative stack
- `~/opensource/vault/wiki/hot.md` — active state → in-review or "pushed update to PR#XXXX"
- `~/opensource/vault/wiki/log.md` — "submitted vscode#XXXX" or "pushed update to vscode#XXXX"

### Local (skill-only)
- temp files for PR body via `--body-file` (ephemeral)

### Live external (not stored)
- `gh pr create` / `gh pr edit` / `git push`
- Atlassian MCP — for IMPL → ENG resolution

### Side effect
- in create-mode, auto-start `/pr-watcher add <pr>`
