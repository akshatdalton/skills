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

## Step 2 — Rebase onto base

```bash
git fetch origin {baseRefName}
git rebase origin/{baseRefName}
```

Conflicts: read both sides. Prefer base for straightforward conflicts. **Ask user** for logic changes. `git rebase --continue` → force push.

## Step 3 — Identify all blockers

### A. Failing CI — always make BOTH calls:

1. **`get_check_runs`** ��� GitHub Actions. Look for `conclusion: "failure"`.
2. **`get_status`** — external CI (Eightfold internal: CI Test Suite, Pytest, Mypy, etc.). `get_check_runs` can be all-green while `get_status` shows failures — **always call both.**

Also scan **`get_comments`** for bot messages with "CHECKLIST VALIDATION ERRORS" — bot validators post as comments, invisible to check_runs/status.

**Auth-gated logs** (`stage.eightfold.ai/internal/s3viewer`): ask user to paste log contents. Never guess.

**Sandbox-required failures**: don't fix in code. Find top reviewer via `get_reviews` (most reviews, then most recent). Tell user to ask them to comment `needs_sandbox`.

### B. Unresolved review comments

- `get_review_comments`: keep `isResolved: false` + `isOutdated: false`
- `get_comments`: skip `[bot]` accounts
- Also read `body` of every `get_reviews` entry — reviewers embed action items in approval body

### C. Merge conflicts — resolved in Step 2 rebase

### D. PR description / checklist failures

1. Read `.github/PULL_REQUEST_TEMPLATE.md` (source of truth)
2. Compare with PR body — check bidirectionally (bot may inject extra mandatory items)
3. Fix: remove duplicate unchecked items, check mandatory boxes, **decode HTML entities** (`&#39;` → `'`)
4. `update_pull_request` via MCP → add `needs_ci` comment to re-trigger CI

### E. Impact analysis (code-review-graph)

Run with `base` = PR's `baseRefName`:
1. **`detect_changes_tool`** — risk-scored review guidance
2. **`get_impact_radius_tool`** — impacted functions/files, sibling files, downstream consumers
3. **`get_affected_flows_tool`** — execution flows through changed files

Use to: flag ripple effects across sibling files, surface unflagged downstream consumers, add discoveries to triage.

## Step 4 — Triage blockers

| Group | Label | When |
|---|---|---|
| 0 | **PR Metadata** | Checklist/body issues. Fix first, no code changes. |
| 1 | **Quick Wins** | Mechanical: typos, renames, dead code, imports. |
| 2 | **Medium** | Clear direction, needs thought: refactors, type hints, tests. |
| 3 | **Design** | Needs alignment first: architecture, requirements, tradeoffs. |
| 4 | **Not Ours** | Base branch failures, unrelated tests, infra issues. Document only. |

CI scoping: files not in PR → 4. Existed in master before PR → 4. Your files → 1-3. Checklist → always 0.

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

Close: one bullet per group theme, Group 4 recommendation, fix order 0→1→2→3, offer to implement.

## Step 6 — Implement

**Never commit/push without explicit user approval.**

Group 0: read template → fix body → `update_pull_request` → `needs_ci` comment.

Groups 1–3: implement → show changes → run tests via `/run-on-ec2` → ask approval → commit (no Claude co-author) → push → resolve threads:

```bash
gh api graphql -f query='mutation { resolveReviewThread(input: {threadId: "PRRT_..."}) { thread { isResolved } } }'
```

**After every action** — always close with: `Done. PR: https://github.com/{owner}/{repo}/pull/{number}`

### Reply policy

Reply only when reviewer asked something needing textual response (design, naming, architecture, security). For code fixes — the diff is the reply. Write as the PR author, never third-person.

---

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

## Design doc PR comments

Don't apply blindly. Analyse all first → group by theme → one at a time with approval → push back when warranted.

See [EXAMPLES.md](EXAMPLES.md) for examples.

---

## Workflow ending

Before completing, run `/project-context:update` with blockers resolved and current PR state.

```
───── workflow ─────
✓ Ticket: ENG-XXXXX
✓ PR: https://github.com/{owner}/{repo}/pull/{number}
✓ Blockers resolved: [count] CI fixes, [count] comments addressed
→ PR ready for merge
────────────────────
```

### CI watch cron

See `_shared/workflow-status.md` — "CI watch cron" section. Trigger: `needs_ci` was posted this run.
