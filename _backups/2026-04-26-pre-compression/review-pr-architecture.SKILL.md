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
Step 3 — Draft + align  present story + table, discuss each comment with user
Step 4 — Post           pending review → inline comments → iterate → submit
```

Do not skip or reorder. Never post comments user hasn't seen.

---

## Step 1 — Understand the PR

Run `/explain-anything` (Arc B) **internally** — do not surface as separate step.

Fetch in parallel:
- PR metadata: title, description, author, head commit SHA, files changed (`pull_request_read` with `get` and `get_files`)
- Full diff (`pull_request_read` with `get_diff`)
- Check out branch to trace full call paths, not just delta

```bash
gh pr view <PR> --repo <owner/repo> --json headRefName -q '.headRefName'
git fetch origin <branch> && git checkout <branch>
```

Never review from diff alone. A finding in `service.py:177` means nothing without `registry.py` and `config.py` checked out to trace actual flow.

**Prior context:** Check for branch plan in `~/.claude/plans/tickets/` or `~/.claude/projects/.../branches/`. Use intent to evaluate whether implementation matches plan.

**Use `code-review-graph` MCP:** Run `detect_changes_tool` (base = PR's base branch) and `get_affected_flows_tool` to understand impacted execution flows.

---

## Step 2 — Find concerns

**Scope: entire PR** unless user explicitly restricts to specific files. File-specific diff URL = hint where to start, not scope restriction.

### Architecture

- Orthogonal concepts fused in one class/identifier/enum?
- Naming that lies about scope (e.g. `_output_guardrails` called on user input)?
- Layer inversion — low-level module importing from domain layer above?
- Compound string identifiers vs proper composite keys?
- Test/dev config leaking into production schema (`_test` table names, `return 'test'` defaults)?
- N×M anti-patterns that should be N+M? Cost of adding one new dimension?
- Hardcoded URLs, secrets, environment-specific values in source?
- State saved before risky external call with no rollback on failure?
- Unconditional destructive operations with no guard?

### Code quality

- `@lru_cache(maxsize=1)` on zero-arg function whose deps never change? That's a module-level variable with extra ceremony.
- Helper with single call site and no reuse case?
- Name implying scope/lifecycle/behaviour the code doesn't have?
- Would renaming eliminate need for clarifying comment?
- Constant name conflating two concepts?
- `if __name__ == '__main__':` in production class files?
- Hardcoded personal emails, internal hostnames, dev usernames in source?
- Commented-out code blocks?
- Hardcoded `False`/`None`/`0` where API has real field — intentional or overlooked?
- `# TODO` with no linked ticket?

### Safety

- Private keys or credentials in source — must fix before merge, rotate immediately
- `.dev.`/`.staging.`/personal usernames in URL literals
- Fake streaming blocking worker thread for full round-trip
- Missing transaction safety: state written before external call that can fail

**Cross-repo deps:** If Jira ticket references PRs in other repos, note this. Flag if current PR assumes unmerged code from other repo.

---

## Step 3 — Draft comments and align with user

Present findings as story **before touching GitHub**:

**1. What this PR changes** — 2–3 sentences, zero context assumed.

**2. Story chapters** — one per concern, in code-trace order.
- Open with narrative (what this part does, why it changed)
- Code snippet **only when code is the explanation** — suspicious pattern, hardcoded secret, fake implementation. Shortest slice that makes point.
- Clean code: clickable file link, let reader jump there.
- Weave concerns at moment they arise, not saved for end.

**3. Before-merge table:**

```
| 🔴 | [file.py:14](path/file.py#L14)        | Private key in source — rotate + read from env |
| 🟡 | [file.py:50–64](path/file.py#L50-L64) | Fake streaming — file a follow-up ticket       |
| 🟢 | [file.ts:285](path/file.ts#L285)       | Cancel fires onComplete — clarify UX intent    |
```

| Severity | Meaning |
|---|---|
| 🔴 | Must fix before merge — security, production blocker, data loss |
| 🟡 | Should fix — scalability, duplication, poor separation, DB design |
| 🟢 | Nice to have — optimisation, naming, doc gaps |

**After presenting**, pause. Ask which findings to post, any to drop/combine/reframe. Do not post until user confirms.

### Comment writing guidelines

**Size**: 2–4 sentences. State concern, explain why it matters, suggest fix.

**Rename over comment**: if name is source of confusion, suggest renaming. Better name fixes problem at source; comment next to misleading name is just a patch.

```
❌ Add: # Controls key data cache, not client lifetime
✅ Rename: JWKS_CACHE_TTL_SECONDS → JWKS_KEY_CACHE_TTL_SECONDS
```

**Suggestion blocks**: clean code only — no inline comments unless comment itself is the point.

**Tone**: collegial. "Consider renaming" not "You must rename". State observation, concern, fix — let author decide.

**File link formatting — critical**: every file reference = clickable markdown link.

```
✅ [dependency.py:17](operator_platform/api/auth/dependency.py#L17)
❌ `dependency.py:17`
❌ // dependency.py:17  (inside code block — never clickable)
```

Ranges: `[file.py:50–64](path/file.py#L50-L64)`.

---

## Step 4 — Post as GitHub review

Once user confirms which comments to post:

**1. Create pending review** (omit `event` so it stays pending/editable):
```
pull_request_review_write(method="create", commitID=<head SHA>)
```

**2. Add inline comments** with `add_comment_to_pending_review`:
- `path`: relative from repo root
- `line`: line number in new file (RIGHT side)
- `startLine` + `startSide`: for multi-line ranges
- `side`: `RIGHT` for new/changed, `LEFT` for removed
- `subjectType`: `LINE`

**3. Show summary** of queued comments before submitting. Last chance to edit/drop.

**4. Submit:**
```
pull_request_review_write(method="submit_pending", event=<disposition>)
```

| Disposition | When |
|---|---|
| `COMMENT` | Findings worth discussing; no hard blockers |
| `REQUEST_CHANGES` | One or more 🔴 items |
| `APPROVE` | Clean; only 🟢 or no concerns |

**Editing posted comments:**
```bash
gh api repos/<owner>/<repo>/pulls/comments/<comment_id> \
  -X PATCH -f body='<revised text>'
```
Get comment IDs via `pull_request_read(method="get_review_comments")`.

---

## Common anti-patterns

### N×M compound identifier
```python
# ❌ N products × M providers = N×M enum values
class ConnectorName(StrEnum):
    BILLING_GOOGLE = 'billing_google'
    BILLING_MICROSOFT = 'billing_microsoft'
    HR_GOOGLE = 'hr_google'
    HR_MICROSOFT = 'hr_microsoft'

# ✅ N + M values, shared OAuth logic in one base class
class ProductName(StrEnum):
    BILLING = 'billing'
    HR = 'hr'

class ConnectorType(StrEnum):
    GOOGLE = 'google'
    MICROSOFT = 'microsoft'
```
Red flag: enum values where removing one underscore-separated segment gives duplicate.

### Test config leaking into production
```python
# ❌
class Integration(DBLoader):
    def get_default_db(self): return 'test'
    def tablename(self): return 'integrations_test_2'
```
Red flag: `'test'` as default return, `_test`/`_dev` suffix in table names.

### Hardcoded environment values
```python
# ❌ Breaks in staging/production
def get_redirect_uri(self):
    return 'https://alice.dev.internal.company.com/connectors/oauth'

# ✅
def get_redirect_uri(self):
    return settings.oauth_redirect_base_url + '/connectors/oauth'
```
Red flag: `.dev.` in URL literals, personal usernames, any `https://` that varies per env.

### Missing transaction safety
```python
# ❌ Row saved before external call that can fail
def oauth_callback(code):
    integration.save()
    tokens = exchange_code_for_token(code)   # failure → partial state in DB

# ✅
def oauth_callback(code):
    tokens = exchange_code_for_token(code)
    integration.save()
```

### Unconditional destructive operations
```python
# ❌ No guard on existing data
def enable_connector():
    delete_all_integrations(org_id, connector_type)
    create_new_integration()
```
Red flag: `delete_all()`/`DELETE FROM` without pre-check, no soft-delete.

### Unnecessary lazy singleton
```python
# ❌ lru_cache implies caching with potential expiry,
#    but maxsize=1 with no TTL = permanent singleton
@lru_cache(maxsize=1)
def _get_client() -> SomeClient:
    return SomeClient(settings.base_url)

# ✅ Module-level variable, lives for process lifetime
_client = SomeClient(settings.base_url)
```
Red flag: `@lru_cache(maxsize=1)` on zero-arg function whose deps never change.

---

## Search tips

- **N×M pattern**: enum values where removing one segment gives duplicate
- **Test bleed**: grep `'test'` in return values, `_test` in table names, `_dev` in defaults
- **Hardcoded env values**: grep `https://`, `.dev.`, `.staging.`, personal usernames
- **Naming lies**: read what name implies, check what code actually does
- **Future cost framing**: state cost to fix now vs later

---

## Examples

- `example-explain-then-review.md` — algorithmic PR (conversational RAG pipeline); Arc B story, findings after explanation
- `example-story-chapters-woven-concerns.md` — integration/wiring PR (adding second agent backend); concerns woven into story chapters, compact before-merge table at end
