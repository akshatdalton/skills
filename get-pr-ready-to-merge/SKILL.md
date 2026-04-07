---
name: get-pr-ready-to-merge
description: Handle everything needed to get a PR into mergeable state — resolving review comments, fixing CI failures, handling stale branches, PR description/checklist issues, and all merge blockers. Use when the user asks to get a PR ready to merge, resolve PR comments, fix CI failures, handle merge conflicts, fix checklist validation, or make a PR mergeable. Also trigger on "fix CI on PR #N", "address review comments", "PR is blocked", or any GitHub PR URL shared with an expectation of action.
---

# Get PR Ready to Merge

Handles everything needed to get a PR into mergeable state: review comments, CI failures, stale branches, PR description/checklist validation, and all merge blockers.

Use GitHub MCP tools for all GitHub data access. Prefer them over `gh` CLI — fall back to `gh` only if MCP tools are unavailable.

If any `gh` or GitHub MCP call fails with a permission or "not found" error, check the active account before assuming the repo doesn't exist:
```bash
gh auth status
gh auth switch  # then retry the failing command
```
Only do this on failure — don't proactively switch accounts on every run.

---

## Workflow

### Step 1 — Confirm branch and PR status

Read the local branch first:
```bash
git branch --show-current
git remote get-url origin
```

- **PR number given**: fetch the PR via GitHub MCP and check its `headRefName`. If it doesn't match the local branch, **automatically switch** — `git checkout {headRefName}`. Never ask for confirmation.
- **No PR number**: search open PRs for `head:BRANCH repo:owner/repo`. If nothing found, stop and say so.
- Check `mergeable_state` to identify what kind of blocker you're dealing with: `"blocked"`, `"behind"`, `"dirty"`, etc.

---

### Step 2 — Sync with base branch

Rebase onto the latest base (`baseRefName` from the PR) before touching anything:

```bash
git fetch origin {baseRefName}
git rebase origin/{baseRefName}
```

If the rebase produces conflicts:
1. Read the conflicting files — understand what changed on each side
2. Prefer the base branch's version for straightforward conflicts (deleted/refactored code the current branch also touched compatibly)
3. **Ask the user** before resolving logic changes, non-trivial diffs, or anything where picking one side could silently break behaviour — show both sides concisely
4. `git rebase --continue` once all conflicts are resolved
5. Force push the rebased branch — GitHub will re-trigger CI automatically

---

### Step 3 — Identify all blockers

#### A. Failing CI checks

Fetch check runs for the PR via GitHub MCP. Look for `conclusion: "FAILURE"` or `conclusion: "ACTION_REQUIRED"`. Common failures: test suites, linters (mypy, ruff, pylint), type checkers, checklist validation.

**`get_check_runs` only covers GitHub Actions — it is blind to bot-comment-driven validators.**
Bot-based checklist validators (e.g. eightfoldbot) post their results as issue comments, not as check runs. A PR can show all check runs green while still having a failing checklist validation. **Always scan `get_comments` for bot messages containing "CHECKLIST VALIDATION ERRORS" or "Mandatory field not checked"**, regardless of what `get_check_runs` reports.

**If logs require authentication** (internal CI tools, private S3 buckets, etc.):
- **STOP** — ask the user: *"I need access to the CI logs to diagnose this. Can you paste the log contents from [URL]?"*
- Do not guess or proceed without the actual errors
- Once provided, determine if failures are in your changed files or inherited from the base branch

#### B. Unresolved review comments

Make two GitHub MCP calls:
- Get review comments: keep only `isResolved: false` and `isOutdated: false`
- Get issue comments: skip bot accounts (logins ending in `[bot]`)

Paginate until all comments are retrieved.

**Also read the `body` field of every review from `get_reviews`.** Reviewers sometimes embed action items or soft requests in the approval body rather than opening a thread — these are invisible to `get_review_comments` but are real asks that need to be addressed.

#### C. Merge conflicts

Visible in the PR's `mergeable` and `mergeable_state` fields. Resolved during the rebase in Step 2.

#### D. PR description / checklist validation failures

CI failing with "Mandatory field not checked" or "Checklist validation errors":

1. Read `.github/PULL_REQUEST_TEMPLATE.md` — this is the source of truth for the base template
2. Compare with the current PR body
3. **Check if a bot has edited the PR body.** The GitHub PR edit history may show `eightfoldbot` (or similar) as an editor. When a bot has edited the body, it may have injected extra mandatory checklist items that are **not in the template** but are still enforced by the validator. Compare the PR body bidirectionally — items in the body but absent from the template are likely bot-injected mandatory items and must be checked.
4. Identify the issue — common causes:
   - Duplicate checklist items (template updated, old unchecked version still in PR body)
   - Unchecked mandatory fields (including bot-injected ones)
   - Missing sections
5. Fix the PR body:
   - Remove duplicate unchecked items (keep the checked version)
   - Check mandatory boxes
   - **Decode HTML entities** before updating — GitHub MCP may encode `'` as `&#39;`, `&` as `&amp;`, etc. Always use plain characters
6. Update via GitHub MCP `update_pull_request`
7. Add `needs_ci` comment to re-trigger CI — PR body changes don't auto-trigger it:
   ```
   add_issue_comment(body="needs_ci", issue_number=PR_NUMBER, owner=OWNER, repo=REPO)
   ```

---

### Step 4 — Triage and categorise all blockers

Categorise every CI failure and review comment into one group:

| Group | Label | When to use |
|---|---|---|
| 0 | **PR Metadata** | Checklist validation, PR body issues, duplicate template items. Fix first — no code changes needed. |
| 1 | **Quick Wins** | Mechanical changes — typos, renames, removing dead code, simple import fixes. No design judgement needed. |
| 2 | **Medium Changes** | Direction is clear but requires thought — refactors, type hints, test fixes, logic restructuring. |
| 3 | **Design Discussion** | Needs alignment before any code — architectural disagreement, unclear requirements, tradeoffs. |
| 4 | **Not Our Problem** | CI failures inherited from base branch, unrelated test failures, infrastructure issues. Document, don't fix. |

When ambiguous between groups, use the higher number.

**CI scoping rules:**
- Errors in files **not touched by this PR** → Group 4
- Errors that **existed in master before this PR** → Group 4
- Errors **in your changed files** → Groups 1–3 based on complexity
- Checklist validation failures → always Group 0

---

### Step 5 — Present results

**Open** with a status summary:
```
Switched to `{head-branch}`, rebased onto `{base-branch}`.
Found X blockers: Y failing CI checks, Z unresolved comments.
Mergeable state: `{mergeable_state}`
```

**Per group**, numbered list. Each item:
```
{N}. [{CI|Review}] @{check-name or reviewer} — "{error or comment quote}"

   {Fix:|Add:|Remove:|Reply:|Skip:|Pushback warranted:} one-sentence action

   ```startLine:endLine:relative/path/to/file
   // actual lines — read the file, never guess
   ```
```

Rules:
- Numbers sequential across all groups — never restart per group
- Always read the file before citing — never leave code blocks empty or guessed
- Top-level PR comments with no line reference → omit code citation
- Include reviewer handle only when multiple reviewers are active
- Within each group: alphabetical by file, then line number; top-level comments last

**Close** with:
- One bullet per group describing the theme
- Explicit call-out of Group 4 items with a concrete recommendation
- Recommended fix order: Group 0 → 1 → 2 → 3 (skip 4)
- Offer to start implementing

---

### Step 6 — Implement with approval checkpoints

**Never commit or push without explicit user approval.**

#### Group 0 (PR Metadata):
1. Read `.github/PULL_REQUEST_TEMPLATE.md`
2. Fix PR body (remove duplicates, check mandatory boxes, decode HTML entities)
3. `update_pull_request` via GitHub MCP
4. Add `needs_ci` comment
5. Tell the user what was fixed and that CI is re-running

#### Groups 1–3 (code changes):
1. Implement changes
2. Show what changed — code citations for small changes, file-level summary for larger
3. Run relevant tests
4. **Ask for approval**: *"I've made these changes. Should I commit and push?"*
5. Wait for explicit confirmation (`"yes"`, `"do it"`, `"push it"`)
6. Commit with a descriptive message — **verify `git status` is clean before pushing**. Do **not** add Claude as a co-author in commit messages.
7. Push — GitHub triggers CI
8. **Resolve addressed threads** (see below)

Never skip the approval gate. You may have misunderstood the intent, made a logic error, or missed an edge case.

#### After pushing — resolve threads

Resolve every thread whose concern is addressed in code via GraphQL. Many CI validators are thread-resolution-driven (not just check-run-driven), so unresolved threads can block CI even when the code is correct:

```bash
gh api graphql -f query='mutation { resolveReviewThread(input: {threadId: "PRRT_..."}) { thread { isResolved } } }'
```

Collect all thread IDs from the GraphQL `reviewThreads` query (Step 3B) and resolve them in a loop after pushing.

#### Reply policy for review threads

**Only post a reply when the reviewer asked something requiring a textual response** — design tradeoffs, naming decisions, architectural proposals, security concerns.

**Do not reply** for:
- Type annotation fixes — the diff is the reply
- TODOs added to code — the TODO is the reply
- Dead code removed, renamed, restructured — the diff is the reply

Unnecessary replies add noise. The code change is the answer.

**When posting replies**: you are writing as the PR author/reviewer. Never refer to the user in third person (e.g. don't say "akshat flagged this" if you are posting as akshat). Write as if you are them.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Checklist re-validation not triggered | PR body updates don't auto-trigger CI | Add `needs_ci` comment |
| "Mandatory field not checked" despite item being checked | Duplicate item — one checked, one unchecked | Compare with template, remove unchecked duplicate, add `needs_ci` |
| All `get_check_runs` green but checklist validation still failing | Bot-driven checklist validator posts results as issue comments, not check runs | Scan `get_comments` for bot messages with "CHECKLIST VALIDATION ERRORS" |
| Mandatory item in PR body not present in template | Bot (eightfoldbot) injected extra mandatory items when it edited the body | Compare body vs template bidirectionally; bot-added items are still enforced |
| CI breaks after updating PR body via MCP | HTML entity encoding (`&#39;`, `&amp;`) | Always decode entities before updating; use plain characters |
| `url mismatch` in checklist validation | URL copied from MCP response (may be truncated) | Copy URL byte-for-byte from local `.github/PULL_REQUEST_TEMPLATE.md` |
| 422 on `gh api` with `in_reply_to` | `-f` sends strings; numeric fields need `-F` | Use `-F in_reply_to=<id>` (capital F) for integer fields in `gh api` |
| Push succeeds but PR shows no new commits | Changes weren't committed before pushing | Always check `git status` is clean before `git push` |
| CI still blocked after pushing code fixes | Addressed threads not resolved | Resolve each thread via GraphQL `resolveReviewThread` mutation after pushing |

---

## Special case: Design doc PR comments

When comments are on a **design document** (not code), don't apply them blindly.

1. **Analyse all comments first** — group by theme, identify conflicts between reviewers, note which need significant rework vs minor edits
2. **One comment at a time** — propose the revised content, explain what changed and why, ask *"Does this address the concern?"*, wait for approval, move to the next
3. **Push back when warranted** — if a suggestion breaks narrative flow, contradicts another reviewer, or introduces unnecessary depth, propose an alternative and explain why

This ensures reviewer intent is correctly captured and changes don't conflict with each other.

---

## Reference

See [EXAMPLES.md](EXAMPLES.md) for concrete agent output examples covering: mixed CI + review failures, auth-gated CI logs, and stale branch diagnosis.
