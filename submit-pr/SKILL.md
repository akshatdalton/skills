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

### 1e — Detect content type (drives auto-checklist)

Run once; cache the result for Phase 3 + Phase 4. The empirical 27-PR analysis showed the most frequent merge-time edits all derive from missing this step:

```bash
git diff --name-only origin/master...HEAD
```

Categorize by path patterns (first match wins):

| Path pattern | Flags set | Product area |
|---|---|---|
| `www/apps/tether_app/` | `IS_BACKEND` | **TM** |
| `www/career_hub/agents/` | `IS_BACKEND` | **TM** |
| `www/react/src/apps/careerHub/teamPlanning/.../ManagerWorkflows/` | `IS_UI` | **TM** |
| `www/connectors/`, `www/apps/connectors_app/` | `IS_BACKEND` | **DP** |
| Any `*.tsx`, `*.jsx`, `www/react/**` | `IS_UI` | infer from sibling cues; default **TM** |
| `endpoint_validation/schemes/**/*.json` OR new Flask route in `www/apps/**/*_api.py` | `IS_ENDPOINT` (additional) | (independent of area) |
| `*.py` only, no UI files | `IS_BACKEND_ONLY` | (suppress UI sub-tree in Phase 3) |

**Pre-check exactly one product area.** Never multiple. `IS_BACKEND` does NOT imply DP — DP is reserved for true customer-impact data-plane changes (connectors, RAG pipeline). Tether and Manager Agent backends are TM.

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
- **wipdp** → read `.github/PULL_REQUEST_TEMPLATE.md` for base shape (`## Summary` + `## Test plan`), then: **inject `## JIRA TASK:` section** (not in template but author convention; survives merge in 25/25 of Akshat's PRs), **promote `Test plan` → `## TEST PLAN:`** (uppercase + colon, dominant form 16/25), **NEVER inject vscode checklist sub-tree or `## GATE/CONFIG:`** (anti-patterns, evidence: PR #1, #3 had vscode-checklist stripped within minutes; `## GATE/CONFIG: NA` absent from 13/25 newer PRs, never reviewer-requested). See **WIPDP Body Reference** below for full rules.
- **vscode** or other → read `.github/PULL_REQUEST_TEMPLATE.md`, fill checklist per VSCode rules above.

**Draft mode:** User says "keep in draft" → `--draft`.

**CRITICAL:** Always read `.github/PULL_REQUEST_TEMPLATE.md` from filesystem — never reconstruct from memory. Use the **Read tool** (not Bash `cat`/`head`) — Bash truncates at arbitrary line counts and silently drops sections at the bottom of the file. MCP encodes special chars as HTML entities, breaks CI. **ALWAYS** write body to temp file, pass `--body-file`. Never inline.

Fill all sections, self-validate (Phase 4) before submitting.

---

## PR Body Reference

### Summary
2-3 sentences. What changed and why. No bullet lists, no markdown headers (`###`).

**Allowed inline bold sub-headers** (each followed by 1-2 prose lines, no nesting). These survive merge consistently — anything else gets stripped:
- `**Background:**` — one-line context
- `**Why a new API?**` — design rationale (or any `**Why ...?**` form)
- `**Depends on:** #<PR_number>` — chained PR
- `**Screenshot:**` — UI evidence (placeholder until upload; see Submit summary at end)

Good: prose paragraph + optional inline blocks above. Bad: bullet points, `### Error Handling` sub-headers, implementation minutiae.

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
5. **Fill all `_____` blanks** — replace with value or `N/A`. **Exception:** `[ ] No additional tests are needed because _____` — when the parallel "tests cover the changes" row is `[x]`, leave THIS row unchecked AND leave `_____` intact. Reviewers consistently tolerate this; filling it triggers re-edits (evidence: PRs #105216, #105712).
6. **Every section needs at least one `[x]`**
7. **Auto-pre-check based on 1e flags** (do not delegate to /get-pr-ready-to-merge — these are knowable at submit time):
   - `IS_UI=true` → `[x] UI changes have been verified for placement and positioning overflows for different screen sizes/zoom levels`
   - `PRODUCT_AREA` → exactly one of `[x] TM` / `[x] DP` / etc. **Never multiple.**
   - `IS_BACKEND_ONLY=true` → suppress entire UI sub-tree (i18n + A11y rows). Emit only the two summary lines: `[x] No user visible strings are introduced in this PR.` and `[x] This PR does not contain any UI changes.` Backend-only PRs that emit the full UI sub-tree get the sub-rows pruned at merge (evidence: #105216 stripped 4 rows).

**Mandatory sections** (CI fails if untouched): Product area, Handle Edge cases gracefully, Gate Control, Testing, A11y Compliance, AI Recruiter, Sandbox Refresh, PR Description for customer release.

**Always check last** (Phase 4 asserts these — submit blocks if missing):
- `[x] If scripts are used in DAGs, list tested regions: NA`
- `[x] If new dags in dags_config.json need to run in westus2...`
- `[x] I have gone through the updated checklist.` ← single most-flipped row at merge across the corpus; never ship without this

**Auto-added items** (do NOT add manually):

| Trigger | Items auto-added |
|---|---|
| `**/requirements.txt` or `**/package.json` changed | Package license, ownership, memory, design doc, GitHub bot |
| `scripts/airflow_v2/dags-*` or `www/airflow_v2/dags_config.json` changed | DAG regions, westus2, alarm config |
| `IS_ENDPOINT=true` (from 1e: `endpoint_validation/schemes/**/*.json` OR new Flask route in `www/apps/**/*_api.py`) | 4 endpoint-security rows: `login_required`, permissions check, `allowed_roles` registry entry, parameter validation |

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

**Frontend / manual:** Substitute `<env>` and `<sandbox>` from the Jira ticket's "test env" note. If Jira is silent, default sandbox host to `eightfolddemo-samyak4.dev2.eightfold.ai` — the recurring host across recent UI PRs. **Never ship the literal `<env>` / `<sandbox>` placeholders** — that's a Phase 4 self-validate fail.
```markdown
## TEST PLAN:
1. Log in as `<user>@<sandbox>.com` on https://<env>.eightfold.ai
2. Navigate to <path>
3. <action>
4. Expected: <result>
```

---

## WIPDP Body Reference

Evidence-backed rules from the 25-PR merged-body analysis (oldest-biased — March → May 2026). Stable across both eras unless tagged otherwise. Body length: ~11–20 lines modal (5× shorter than vscode).

### Body shape (mature merged form)

```markdown
## Summary

<2-5 sentence prose paragraph OR 2-5 bullet list — pick one based on PR type, see rule 1>

## JIRA TASK:
https://eightfoldai.atlassian.net/browse/ENG-XXXXXX

## TEST PLAN:
```bash
<single pytest command — default form>
```
```

That's it. No `## GATE/CONFIG:`. No checklist. No product-area row. No A11y / i18n rows.

### Rules

1. **`## Summary` header explicit. Body: 2–5 sentences (prose) OR 2–5 bullets — pick one, not both.** Prose for refactors/bugfixes; bullets for feature/multi-step changes. *(Evidence prose: #25, #36, #49, #54, #55, #57, #75. Evidence bullets: #5, #50, #56, #68, #69, #72, #73, #76, #78. Stable from #25 onward.)*

2. **Inject `## JIRA TASK:` even though template lacks it.** Standalone section, ENG-* URL. Survives merge in 25/25. *(Modal form #1–#76; do NOT switch to the recent `**Jira:**` inline form — only 3 PRs of evidence, not stable.)*

3. **`## TEST PLAN:` — uppercase + colon. Default body: single fenced ```bash block with one pytest command.** Multi-command bash blocks (ruff + pytest, cron install + run, inline PYEOF) are tolerated when justified. *(Evidence: #1, #2, #16, #18, #25, #36, #37, #49, #50, #54, #55, #57, #71, #72, #75, #76.)*

   **Exception — prompt-only / manual-verification PRs:** use `- [ ]` checkbox form instead of fenced bash. Detected by changed files being only `prompts/*.md` or `*.md` with no Python diff. *(Evidence: #68, #69, #73, #78 — all prompt or low-test changes.)*
   ```markdown
   ## TEST PLAN:
   - [ ] Verify `<scenario>` returns `<expected>`
   - [ ] Verify error path `<x>`
   ```

4. **Inline "Depends on" callout when this PR has a hard prereq.** Plain prose in the Summary body (not a separate section). *(Evidence: #57 "Depends on ENG-187990 (PR #56) — merge that first." Also #53 references the prior renamed PR. Stable.)*

5. **Inline bold sub-headers tolerated** when the PR has 2+ distinct sub-topics: `**Note:**`, `**Background:**`, `**Backward compatibility:**`, `**Lifecycle transitions:**`, `**Changes**`. Each followed by 1-2 prose lines or a short bullet list. *(Evidence: #50, #56, #71, #72, #76. Used in 5/25, never stripped at merge.)*

6. **Do NOT emit `## GATE/CONFIG: NA`** — leftover vscode-style filler. Present in 12/25 older PRs, absent in 13/25 (trending toward absence). Zero reviewer requests to add it. *(Recent shift, regression-safe because: Akshat is the only author and 7/9 of newest PRs omit it. Recommend stop injecting.)*

7. **Anti-pattern — NEVER inject vscode checklist sub-tree.** No `[x] DP`, `[x] TM`, no A11y / i18n / Sandbox Refresh rows. /submit-pr's earlier vscode logic must not bleed into the wipdp path. *(Evidence: PR #1 and #3 had vscode-checklist stripped within minutes of opening — author manually deleted.)*

8. **No checklist bot on wipdp.** No automated body validation. First-pass quality is purely an author concern — but reviewer expectations exist (none documented as comment edits in the corpus, all body edits were author-driven trimming).

---

## Phase 4 — Self-validate

Scan PR body before submitting. **Block submit on any failure.** Validations are repo-aware (Phase 1e `IS_VSCODE` / `IS_WIPDP` from `git remote get-url origin`).

### Both repos
1. **No HTML entities** — `&amp;`, `&#39;`, `&quot;` → decode. MCP encodes; CI/diff readers reject.
2. **No unfilled blanks** — no `_____` remaining (vscode exception: `[ ] No additional tests are needed because _____` may keep `_____` when unchecked, per Checklist rule 5).
3. **No literal `<env>` / `<sandbox>` placeholders** — substitute from Jira test-env note, or use the default sandbox host.

### vscode only (additional)
4. **vscode body shape** — body MUST contain ALL of: `## SUMMARY:`, `## JIRA TASK:`, `## GATE/CONFIG:`, `## CHECKLIST:`, `## TEST PLAN:` (uppercase + colons). This catches the wipdp-prose misroute (evidence: PRs #105343, #105542, #105518, #106396 created with wipdp shape, all fully rewritten before merge).
5. **Final-row check** — `[x] I have gone through the updated checklist.` is checked. Most-flipped row at merge across the corpus.
6. **Mandatory sections covered** — every checklist section has at least one `[x]`.

### wipdp only (additional)
7. **wipdp body shape** — body MUST contain ALL of: `## Summary` (capital S, no colon — matches template), `## JIRA TASK:` (uppercase + colon — Akshat convention, 25/25 survive merge), `## TEST PLAN:` (uppercase + colon — dominant form). Block if missing.
8. **wipdp anti-pattern check** — body MUST NOT contain vscode-checklist markers: `[ ] DP`, `[ ] TM`, `[ ] I have gone through the updated checklist`, `## GATE/CONFIG:`, `## CHECKLIST:`. If found, strip them — Akshat manually stripped these in early PRs (#1, #3); never inject in wipdp.
9. **wipdp Summary length** — between 2 and 5 prose sentences OR 2 to 5 bullets, not both. Reject empty Summary or 10+ line walls.

Submit only after all applicable validations pass.

---

## After submitting

```bash
gh pr checks <pr-number>
```

If CI fails: [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

Do **not** post top-level summary comment on the PR. Only reply to specific reviewer threads.

### Submit summary (chat-side notification — MANDATORY for create-mode)

Immediately after `gh pr create` returns, surface a structured summary in chat so the user can request fixes without opening GitHub. Skip on update-mode (description churn).

Format:

```
✓ PR #<N> submitted: <url>
  Title       : <title>
  Base        : <base-branch>
  Files       : <count> changed (<dominant-extension>)
  Product area: <PRODUCT_AREA> (auto-detected from 1e)
  Auto-checks : <comma-separated list of triggers that fired — UI overflow / endpoint security / DAG regions / package — only those that fired>
  Pre-checked : <count>/<total> checklist items
  Test plan   : pytest <path>   |   manual on <sandbox-host>
```

Then ask in plain prose (one line):

```
Anything to fix in the description before reviewers see it? Else CI runs.
```

**For UI PRs (`IS_UI=true` from 1e):** append a screenshot prompt below the summary:

```
↳ This is a UI PR. Reviewers will ask for a before/after screenshot.
   Paste the user-attachments URL here when ready and I'll insert it under
   `**Screenshot:**` via gh pr edit.
```

This stops the user from having to open GitHub to spot bad first-pass output, and surfaces the screenshot ask at the right moment (right after submit, before reviewers ping). Do NOT auto-inject a `**Screenshot:**` placeholder into the body — wait for the URL.

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
