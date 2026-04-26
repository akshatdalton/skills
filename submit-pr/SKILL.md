---
name: submit-pr
description: Create or update GitHub pull requests following team standards — full workflow from git commit through PR creation and CI validation. Use when the user asks to create a PR, push changes, submit for review, update a PR description, or mentions pull requests. Handles PR template compliance, checklist bot validation, and GitHub MCP tool integration. Also trigger on "push and create PR", "submit this for review", "update the PR description", or "my PR is failing checklist validation".
---

# Submit Pull Request

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

## Phase 3 — Create or update PR

Check existing PR via GitHub MCP `list_pull_requests` filtered by `head:<branch>`.
- **Exists** → `update_pull_request`
- **None** → `create_pull_request`

**Auto-detect repo** via `git remote get-url origin`:
- **wipdp** → prose: Summary (2-4 sentences), JIRA TASK link, TEST PLAN (bash block). Write body to temp file, use `--body-file`.
- **vscode** or other → read `.github/PULL_REQUEST_TEMPLATE.md`, fill checklist.

**Draft mode:** User says "keep in draft" → `--draft`.

**CRITICAL:** Always read `.github/PULL_REQUEST_TEMPLATE.md` from filesystem — never reconstruct from memory. MCP encodes special chars as HTML entities, breaks CI. **ALWAYS** write body to temp file, pass `--body-file`. Never inline.

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

Before completing, run `/project-context:update` with PR URL and CI status.

```
───── workflow ─────
✓ Ticket: ENG-XXXXX
✓ Branch: akshat/ENG-XXXXX-short-name
✓ PR: https://github.com/{owner}/{repo}/pull/{number}
✓ CI: running
→ If CI fails: /get-pr-ready-to-merge
→ Consider: /schedule to set up CI watcher cron (CI takes ~4hrs)
────────────────────
```
