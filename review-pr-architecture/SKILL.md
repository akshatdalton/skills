---
name: review-pr-architecture
description: Full PR review workflow — understand the change, surface concerns across architecture, code quality, naming, and safety, draft inline comments collaboratively with the user, then post as a GitHub review. Use when the user asks for a PR review, "any concerns?", "is this well-designed?", shares a PR URL, or wants to review before merging.
---

# PR Review

**Arguments**: PR URL or `owner/repo#number`

## Workflow

```
Step 1 — Understand     fetch PR + diff, run explain-anything Arc B internally
Step 2 — Find concerns  architecture, naming, code quality, safety
Step 3 — Draft + align  present story + table, discuss with user
Step 4 — Post           pending review → inline comments → iterate → submit
```

Never skip/reorder. Never post unseen comments.

---

## Step 1 — Understand

Run `/explain-anything` (Arc B) **internally**.

Fetch in parallel:
- PR metadata: title, desc, author, head SHA, files (`pull_request_read` with `get`/`get_files`)
- Full diff (`pull_request_read` with `get_diff`)
- Check out branch to trace full call paths

```bash
gh pr view <PR> --repo <owner/repo> --json headRefName -q '.headRefName'
git fetch origin <branch> && git checkout <branch>
```

Never review from diff alone. Trace actual flow through checked-out code.

**Prior context:** Check branch plan in `~/.claude/plans/tickets/` or `~/.claude/projects/.../branches/`. Evaluate if impl matches plan.

**Use `code-review-graph` MCP:** `detect_changes_tool` + `get_affected_flows_tool` for impacted flows.

---

## Step 2 — Find concerns

**Scope: entire PR** unless user restricts. File-specific diff URL = hint, not scope.

### Architecture
- Orthogonal concepts fused in one class/identifier/enum?
- Name lies about scope? (e.g. `_output_guardrails` called on input)
- Layer inversion — low-level importing from domain above?
- Compound string IDs vs proper composite keys?
- Test/dev config leaking into production schema?
- N*M patterns that should be N+M? Cost of adding one dimension?
- Hardcoded URLs, secrets, env-specific values?
- State saved before risky external call with no rollback?
- Unconditional destructive ops with no guard?

### Code quality
- `@lru_cache(maxsize=1)` on zero-arg func with static deps? Module-level var with ceremony.
- Single-callsite helper with no reuse case?
- Name implying wrong scope/lifecycle/behaviour?
- Renaming would eliminate clarifying comment?
- Constant conflating two concepts?
- `if __name__ == '__main__':` in production class?
- Personal emails, internal hostnames, dev usernames?
- Commented-out code? Hardcoded `False`/`None`/`0` where API has real field?
- `# TODO` with no linked ticket?

### Safety
- Private keys/credentials in source — must fix + rotate
- `.dev.`/`.staging.`/personal usernames in URLs
- Fake streaming blocking worker for full round-trip
- State written before external call that can fail

**Cross-repo deps:** Flag if PR assumes unmerged code from other repo.

---

## Step 3 — Draft and align

Present findings as story **before touching GitHub**:

**1. What changed** — 2-3 sentences, zero context assumed.

**2. Story chapters** — one per concern, code-trace order.
- Narrative first (what this does, why changed)
- Code snippet **only when code IS the explanation** — suspicious pattern, hardcoded secret
- Clickable file link, let reader jump there
- Weave concerns at moment they arise

**3. Before-merge table:**

```
| 🔴 | [file.py:14](path/file.py#L14)        | Private key — rotate + env var |
| 🟡 | [file.py:50–64](path/file.py#L50-L64) | Fake streaming — follow-up ticket |
| 🟢 | [file.ts:285](path/file.ts#L285)       | Cancel fires onComplete — clarify |
```

| Severity | Meaning |
|---|---|
| 🔴 | Must fix — security, prod blocker, data loss |
| 🟡 | Should fix — scalability, duplication, design |
| 🟢 | Nice to have — naming, docs, optimization |

**Pause.** Ask which to post, any to drop/reframe. Do not post until confirmed.

### Comment guidelines

**Size**: 2-4 sentences. Concern, why it matters, fix.

**Rename over comment**: better name fixes problem; comment next to misleading name is patch.

**Suggestion blocks**: clean code only — no inline comments unless comment is the point.

**Tone**: collegial. "Consider renaming" not "You must rename".

**File links — critical**: every reference = clickable markdown link.
```
✅ [dependency.py:17](operator_platform/api/auth/dependency.py#L17)
❌ `dependency.py:17`
```
Ranges: `[file.py:50–64](path/file.py#L50-L64)`.

---

## Step 4 — Post as GitHub review

**1. Create pending review** (omit `event`):
```
pull_request_review_write(method="create", commitID=<head SHA>)
```

**2. Add inline comments** via `add_comment_to_pending_review`:
- `path`: relative from repo root
- `line`: RIGHT side line number
- `startLine` + `startSide`: multi-line ranges
- `side`: `RIGHT` new/changed, `LEFT` removed
- `subjectType`: `LINE`

**3. Show summary** of queued comments. Last chance to edit/drop.

**4. Submit:**
```
pull_request_review_write(method="submit_pending", event=<disposition>)
```

| Disposition | When |
|---|---|
| `COMMENT` | Worth discussing, no blockers |
| `REQUEST_CHANGES` | One or more 🔴 |
| `APPROVE` | Clean, only 🟢 or none |

**Edit posted comments:**
```bash
gh api repos/<owner>/<repo>/pulls/comments/<comment_id> -X PATCH -f body='<text>'
```
Get IDs via `pull_request_read(method="get_review_comments")`.

---

## Anti-patterns and search tips

See [references/anti-patterns.md](references/anti-patterns.md) for code examples.

## Examples

- `example-explain-then-review.md` — algorithmic PR; Arc B + findings
- `example-story-chapters-woven-concerns.md` — integration PR; concerns woven into story
