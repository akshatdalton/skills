---
name: submit-pr
description: Create or update GitHub pull requests following team standards — full workflow from git commit through PR creation and CI validation. Use when the user asks to create a PR, push changes, submit for review, update a PR description, or mentions pull requests. Handles PR template compliance, checklist bot validation, and GitHub MCP tool integration. Also trigger on "push and create PR", "submit this for review", "update the PR description", or "my PR is failing checklist validation".
---

# Submit Pull Request

Full workflow for creating GitHub PRs that pass CI validation on first submission.

Use GitHub MCP tools for all GitHub operations. Fall back to `gh` CLI only if MCP tools are unavailable.

---

## Phase 1 — Pre-flight checks

Run these before touching git. Catch problems now, not after CI fails.

### 1a — Confirm the Jira ticket

The PR's `## JIRA TASK:` must link to an **ENG-\*** ticket — never an IMPL ticket directly.

- If you have an **ENG-\*** ticket already: use it.
- If you have an **IMPL-\*** ticket: fetch it via Atlassian MCP and check `issuelinks` for a linked ENG-\* issue.
  - If one exists: use that ENG ticket.
  - If none exists: the IMPL ticket needs to be transitioned to "Code Fix Needed" first (transition id `121` on `eightfoldai.atlassian.net`) — this auto-creates the ENG ticket. Do this before proceeding.

Also note the test environment from the Jira description (customer sandbox URL, user credentials) — you'll need it for the TEST PLAN.

### 1b — Verify branch name

Branch must follow: `akshat/ENG-<ticket_number>-<very-short-name>`

Examples: `akshat/ENG-187846-notes-btn-fix`, `akshat/ENG-186208-text-normalization`

If the branch uses an IMPL number or doesn't follow this format, flag it to the user before continuing.

### 1c — Check branch is up to date

```bash
git fetch origin master
git log HEAD..origin/master --oneline   # should be empty
```

If behind: `git rebase origin/master` before committing.

### 1d — Lint changed files

```bash
# Python
ruff check <changed-files>
ruff format <changed-files>

# JS/TS — husky runs this on commit automatically,
# but catch it early:
npm run lint:fix:files <changed-files>
```

Fix any errors before proceeding to commit.

---

## Phase 2 — Commit and push

### Identify files to stage

```bash
git diff --name-only          # see all changed files
```

Stage **only files relevant to this ticket** — never `git add .`. If there are pre-existing unrelated changes from another branch, leave them unstaged.

### Get one approval, then do it all

Show the user:
1. The list of files to be staged
2. The proposed commit message
3. That you'll add + commit + push in one go

**Wait for explicit approval. Then run all three commands without pausing between them.**

Commit message format:
```
ENG-XXXXX: Brief summary of the change

What changed and why — focus on motivation, not mechanics.
Fixes IMPL-XXXXXX.   ← include if this came from a customer IMPL ticket
```

```bash
git add <file1> <file2> ...
git commit -m "..."
git push -u origin <branch-name>    # first push
# or: git push                      # subsequent pushes
```

Pre-push hooks run automatically (lint, tests). Fix any hook failures before re-attempting.

---

## Phase 3 — Create or update the PR

### Check for existing PR

Use GitHub MCP `list_pull_requests` filtered by `head:<branch-name>`.

- **PR exists** → update it (use `update_pull_request`)
- **No PR** → create it (use `create_pull_request`)

### Build the PR body

**CRITICAL:** Always read `.github/PULL_REQUEST_TEMPLATE.md` from the local filesystem — never reconstruct it from memory or an MCP response. MCP encodes special characters as HTML entities which breaks CI validation.

Fill all sections as described below, then **self-validate before submitting** (see Phase 4).

---

## PR Body Reference

### Summary

2–3 sentences. Explain what changed and why — no bullet lists, no headers.

✅ Good:
```
The Notes button in the TM Project Pipeline inline profile was visible but
unresponsive. ProfileNotesPanelContainer — which listens for the custom DOM
event fired by the button — was not mounted in the projectMarketplaceManager
app. Adding it here mirrors the existing pattern in careerHub/App.js.
```

❌ Bad: bullet points, "Error Handling" / "Code Quality" sub-sections, implementation minutiae.

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

Or if gated:
```markdown
## GATE/CONFIG:
[gate_name](https://stage.eightfold.ai/debug/config?config=gate_name)
```

### Checklist rules

1. **Never delete any checklist item** — keep all `[ ]` lines verbatim from the template
2. **Only add `x`**: change `[ ]` → `[x]`, never remove items
3. **Never modify item text** — copy exactly
4. **URLs byte-for-byte identical** — especially the "deploying all services" Atlassian URL
5. **Fill all `_____` blanks** — replace with a value or `N/A`, never leave blank
6. **Every section needs at least one `[x]`** — CI fails on empty sections

**Mandatory sections** (CI fails if untouched):

- **Product area** — check at least one: TM / TA / TD / DP / etc.
- **Handle Edge cases gracefully** — check at least one:
  - `[x] None return values are handled gracefully` ← backend
  - `[x] Undefined/Null return values are handled in react/JS gracefully` ← frontend
  - `[x] API errors have been handled in react to show correct user facing message`
  - `[x] Backend service errors (search, microservice etc) have been handled correctly in python`
- **Gate Control** — either gated instructions, or one of the "not gated because" reasons
- **Testing** — tests cover changes, or justify why not
- **A11y Compliance** — UI changes tested, or "no UI changes"
- **AI Recruiter** — applicable or not
- **Sandbox Refresh** — applicable or not
- **PR Description for customer release** — required or not required

**Always check last:**
- `[x] If scripts are used in DAGs, list tested regions: NA`
- `[x] If new dags in dags_config.json need to run in westus2, westus2 has been added as a region in the dag json.`
- `[x] I have gone through the updated checklist.`

**Auto-added items** (do NOT add manually — CI bot adds these when triggered):

| Trigger | Items auto-added |
|---|---|
| `**/requirements.txt` or `**/package.json` changed | Package license, ownership, memory usage, design doc, GitHub bot install |
| `scripts/airflow_v2/dags-*` or `www/airflow_v2/dags_config.json` changed | DAG regions, westus2 validation, alarm config |

Adding these manually when not triggered causes CI validation failures.

### Common checklist patterns

**Backend / data-plane (DP):**
```markdown
- [x] DP
- [x] Regression testing is not required because new data-plane module, no customer impact
- [x] It is a bug-fix/usability fix that is common for all group_ids and safe to rollout
- [x] This change is easy to read, review, debug and maintain
- [x] None return values are handled gracefully
- [x] Not applicable  ← Product Security
- [x] No additional tests are needed because _____
- [x] No user visible strings are introduced in this PR.
- [x] This PR does not contain any UI changes.
- [x] Not applicable - This change does not impact AI Recruiter functionality.
- [x] Not Applicable - This change is not related to DjSafe Schema.
- [x] Description not required
- [x] If scripts are used in DAGs, list tested regions: NA
- [x] If new dags in dags_config.json need to run in westus2, westus2 has been added as a region in the dag json.
- [x] I have gone through the updated checklist.
```

**Frontend / UI (TM/TA/TD):**
```markdown
- [x] TM   ← or TA, TD — whichever applies
- [x] This change could affect the performance of:
  - [x] TM Marketplace   ← or relevant area
- [x] Regression testing is not required because _____
- [x] It is a bug-fix/usability fix that is common for all group_ids and safe to rollout
- [x] This change is easy to read, review, debug and maintain
- [x] Undefined/Null return values are handled in react/JS gracefully
- [x] Not applicable  ← Product Security
- [x] No additional tests are needed because _____
- [x] No user visible strings are introduced in this PR.
- [x] This PR does not contain any UI changes.   ← or keyboard/axe tested
- [x] Not applicable - This change does not impact AI Recruiter functionality.
- [x] Not Applicable - This change is not related to DjSafe Schema.
- [x] Description [customer-facing changelog]: _____
- [x] If scripts are used in DAGs, list tested regions: NA
- [x] If new dags in dags_config.json need to run in westus2, westus2 has been added as a region in the dag json.
- [x] I have gone through the updated checklist.
```

### Test Plan

**Backend (pytest coverage):**
```markdown
## TEST PLAN:
```bash
cd www && pytest path/to/test_file.py -v
```
```
Just the command. No prose.

**Frontend / customer-facing (manual steps):**
```markdown
## TEST PLAN:
1. Log in as `<user>@<sandbox>.com` on https://<env>.eightfold.ai
2. Navigate to <specific path>
3. <action>
4. Expected: <what should happen>
```
Use credentials and URLs from the Jira ticket description.

---

## Phase 4 — Self-validate before submitting

Before calling `create_pull_request` or `update_pull_request`, scan the PR body:

1. **No HTML entities** — search for `&amp;`, `&#39;`, `&quot;`. Decode to plain text if found. MCP encodes these; CI validators reject them.
2. **No unfilled blanks** — search for `_____`. Every one must be replaced.
3. **Mandatory sections covered** — every section listed above has at least one `[x]`.

Only submit after all three pass.

---

## After submitting

```bash
gh pr checks <pr-number>     # monitor CI status
```

If CI fails, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

Do **not** post a top-level comment summarising changes — reviewers read the diff. Only post replies to specific reviewer threads.
