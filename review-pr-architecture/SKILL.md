---
name: review-pr-architecture
description: Full PR review workflow — understand the change, surface concerns across architecture, code quality, naming, and safety, draft inline comments collaboratively with the user, then post as a GitHub review. Use when the user asks for a PR review, "any concerns?", "is this well-designed?", shares a PR URL, or wants to review before merging.
---

# PR Review

Full PR review workflow — understand the change, find concerns across architecture, code
quality, naming and safety, draft comments collaboratively with the user, then post as
inline GitHub review comments.

**Arguments**: a PR URL or `owner/repo#number`

---

## Workflow at a glance

```
Step 1 — Understand     fetch PR + diff, run explain-anything Arc B internally
Step 2 — Find concerns  architecture, naming, code quality, safety
Step 3 — Draft + align  present story + table, discuss each comment with user
Step 4 — Post           pending review → inline comments → iterate → submit
```

Do not skip or reorder steps. Never post comments the user hasn't seen.

---

## Step 1 — Understand the PR

Run `/explain-anything` (Arc B) **internally as context-building** — do not surface it as a
separate step to the user. The user invoked `/review-pr-architecture` and expects one coherent
flow: understand → find concerns → post.

Fetch in parallel:
- PR metadata: title, description, author, head commit SHA, files changed (`pull_request_read` with `get` and `get_files`)
- Full diff (`pull_request_read` with `get_diff`)
- Check out the branch to trace full call paths, not just the delta

```bash
gh pr view <PR> --repo <owner/repo> --json headRefName -q '.headRefName'
git fetch origin <branch> && git checkout <branch>
```

Never review from the diff alone. A finding in `service.py:177` means nothing without
`registry.py` and `config.py` checked out so you can trace the actual flow.

---

## Step 2 — Find concerns

### Architecture

**Separation of concerns**
- Orthogonal concepts fused in one class, identifier, or enum?
- Naming that lies about scope (e.g. `_output_guardrails` called on user input)?
- Layer inversion — a low-level module importing from a domain layer above it?

**Database design**
- Compound string identifiers vs proper composite keys?
- Test/dev config leaking into production schema (`_test` table names, `return 'test'` defaults)?

**Scalability**
- N×M anti-patterns that should be N+M (see Common Anti-Patterns)?
- What's the cost of adding one new dimension?

**Configuration and safety**
- Hardcoded URLs, secrets, or environment-specific values in source?
- State saved before a risky external call with no rollback on failure?
- Unconditional destructive operations with no guard?

---

### Code quality

**Unnecessary abstractions**
- `@lru_cache(maxsize=1)` wrapping a zero-argument function whose dependencies (config,
  settings) never change mid-process? That's a module-level variable with extra ceremony.
- Helper function with a single call site and no reuse case?

**Naming clarity**
- Does the name imply a scope, lifecycle, or behaviour the code doesn't have?
- Would renaming eliminate the need for a clarifying comment entirely?
- Constant name that conflates two concepts (e.g. `JWKS_CACHE_TTL_SECONDS` implying the
  client is also cycled, when only the key data cache is)?

**Dead or debug code**
- `if __name__ == '__main__':` blocks in production class files?
- Hardcoded personal emails, internal hostnames, or dev usernames in source?
- Commented-out code blocks left behind?

**Missing intent markers**
- Hardcoded `False` / `None` / `0` where the API has a real field — intentional or overlooked?
  A one-line comment makes it deliberate.
- `# TODO` with no linked ticket — code TODOs tend to stay permanently.

---

### Safety

- 🔴 Private keys or credentials in source — must fix before merge, rotate immediately
- `.dev.` / `.staging.` / personal usernames in URL string literals
- Fake streaming that blocks a worker thread for the full round-trip
- Missing transaction safety: state written before an external call that can fail

---

## Step 3 — Draft comments and align with user

Present findings as a story **before touching GitHub**. Structure:

**1. What this PR changes** — 2–3 sentences, zero context assumed.

**2. Story chapters** — one per concern, in the order a reader traces the code.
- Open with narrative (what this part does and why it changed)
- Code snippet **only when the code is the explanation** — suspicious pattern, hardcoded
  secret, fake implementation. The shortest slice that makes the point.
- Clean code: clickable file link, let the reader jump there. Don't paste to prove you read it.
- Weave concerns **at the moment they arise**, not saved for the end.

**3. Before-merge table** — compact summary; story already explained each item.

```
| 🔴 | [file.py:14](path/file.py#L14)        | Private key in source — rotate + read from env |
| 🟡 | [file.py:50–64](path/file.py#L50-L64) | Fake streaming — file a follow-up ticket       |
| 🟢 | [file.ts:285](path/file.ts#L285)       | Cancel fires onComplete — clarify UX intent    |
```

Severity:
- 🔴 Must fix before merge — security, production blocker, data loss risk
- 🟡 Should fix — scalability, duplication, poor separation of concerns, DB design
- 🟢 Nice to have — optimisation, naming, documentation gaps

**After presenting**, pause and ask the user:
- Which findings to post as inline comments?
- Any to drop, combine, or reframe?

Do not post anything until the user confirms.

---

### Comment writing guidelines

**Size**: 2–4 sentences. State the concern, explain why it matters, suggest the fix.
No monologue — the story chapter already gave the full context.

**Rename over comment**: if the name is the source of confusion, suggest renaming rather
than adding a clarifying comment. A better name fixes the problem at the source; a comment
next to a misleading name is just a patch.

```
❌ Add: # Controls key data cache, not client lifetime
✅ Rename: JWKS_CACHE_TTL_SECONDS → JWKS_KEY_CACHE_TTL_SECONDS
```

**Suggestion blocks**: when proposing a code replacement, include clean code only — no
inline comments inside the block unless the comment itself is the point. The code should
speak for itself; put the reasoning in the prose above it.

**Tone**: collegial, not prescriptive. "Consider renaming" not "You must rename".
State what you observed, why it's a concern, and what a fix looks like — let the author decide.

**File link formatting — critical**: every file reference must be a clickable markdown link.

```
✅ [dependency.py:17](operator_platform/api/auth/dependency.py#L17)
❌ `dependency.py:17`
❌ // dependency.py:17  (inside a code block — never clickable)
```

For ranges: `[file.py:50–64](path/file.py#L50-L64)`.

---

## Step 4 — Post as GitHub review

Once the user confirms which comments to post:

**1. Create a pending review** (omit `event` so it stays pending and editable)

```
pull_request_review_write(method="create", commitID=<head SHA>)
```

**2. Add inline comments** with `add_comment_to_pending_review`:
- `path`: relative file path from repo root
- `line`: line number in the new file (RIGHT side) the comment targets
- `startLine` + `startSide`: for multi-line ranges
- `side`: `RIGHT` for new/changed code, `LEFT` for removed code
- `subjectType`: `LINE`

**3. Show the user a summary** of all queued comments before submitting. Last chance to
edit or drop any comment.

**4. Submit** with the appropriate disposition:

```
pull_request_review_write(method="submit_pending", event=<disposition>)
```

| Disposition | When |
|---|---|
| `COMMENT` | Findings worth discussing; no hard blockers |
| `REQUEST_CHANGES` | One or more 🔴 items present |
| `APPROVE` | Clean PR; only 🟢 items or no concerns |

**Editing posted comments** — use `gh api` directly:

```bash
gh api repos/<owner>/<repo>/pulls/comments/<comment_id> \
  -X PATCH -f body='<revised text>'
```

Get comment IDs via `pull_request_read(method="get_review_comments")`.

---

## Common anti-patterns

### N×M compound identifier

```python
# ❌ Bad — N products × M providers = N×M enum values
class ConnectorName(StrEnum):
    BILLING_GOOGLE = 'billing_google'
    BILLING_MICROSOFT = 'billing_microsoft'
    HR_GOOGLE = 'hr_google'
    HR_MICROSOFT = 'hr_microsoft'

# ✅ Good — N + M values, shared OAuth logic in one base class
class ProductName(StrEnum):
    BILLING = 'billing'
    HR = 'hr'

class ConnectorType(StrEnum):
    GOOGLE = 'google'
    MICROSOFT = 'microsoft'
```

Red flag: enum values where removing one underscore-separated segment gives a duplicate.

---

### Test configuration leaking into production

```python
# ❌ Bad
class Integration(DBLoader):
    def get_default_db(self): return 'test'
    def tablename(self): return 'integrations_test_2'
```

Red flag: `'test'` as a default return value, `_test`/`_dev` suffix in table names.

---

### Hardcoded environment values

```python
# ❌ Bad — breaks in staging and production
def get_redirect_uri(self):
    return 'https://alice.dev.internal.company.com/connectors/oauth'

# ✅ Good
def get_redirect_uri(self):
    return settings.oauth_redirect_base_url + '/connectors/oauth'
```

Red flag: `.dev.` in URL literals, personal usernames, any `https://` that should vary per env.

---

### Missing transaction safety

```python
# ❌ Bad — row saved before external call that can fail
def oauth_callback(code):
    integration.save()
    tokens = exchange_code_for_token(code)   # failure → partial state in DB

# ✅ Good
def oauth_callback(code):
    tokens = exchange_code_for_token(code)
    integration.save()
```

---

### Unconditional destructive operations

```python
# ❌ Bad — no guard on existing data
def enable_connector():
    delete_all_integrations(org_id, connector_type)
    create_new_integration()
```

Red flag: `delete_all()` / `DELETE FROM` without a pre-check, no soft-delete option.

---

### Unnecessary lazy singleton

```python
# ❌ Misleading — lru_cache implies caching with potential expiry,
#    but maxsize=1 with no TTL is just a permanent singleton
@lru_cache(maxsize=1)
def _get_client() -> SomeClient:
    return SomeClient(settings.base_url)

# ✅ Honest — module-level variable, lives for process lifetime
_client = SomeClient(settings.base_url)
```

Red flag: `@lru_cache(maxsize=1)` on a zero-argument function whose dependencies (config,
settings) never change mid-process.

---

## Search tips

- **N×M pattern**: enum values where removing one segment gives a duplicate
- **Test bleed**: grep `'test'` in return values, `_test` in table names, `_dev` in defaults
- **Hardcoded env values**: grep `https://`, `.dev.`, `.staging.`, personal usernames
- **Naming lies**: read what a name implies, then check what the code actually does
- **Future cost framing**: when flagging a scalability issue, state the cost to fix now vs later

---

## Examples

- `example-explain-then-review.md` — algorithmic PR (conversational RAG pipeline); Arc B
  story, findings section after explanation
- `example-story-chapters-woven-concerns.md` — integration/wiring PR (adding a second agent
  backend); concerns woven into story chapters, compact before-merge table at end
