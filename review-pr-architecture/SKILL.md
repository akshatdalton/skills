---
name: review-pr-architecture
description: Review pull requests for architectural soundness — separation of concerns, database design, scalability, code reuse, configuration management, and safety patterns. Use when the user asks for an architectural review, asks "is this well-designed?", "any architectural concerns?", shares a PR that adds new DB models, enums, or base classes, or when examining OAuth/integration/connector patterns. Also trigger when a PR looks structurally correct but something feels off about the design.
---

# Review PR Architecture

Systematic approach to reviewing PRs for architectural soundness, not just correctness.

---

## Step 1 — Verify the repo, then checkout the branch

Resolve the repo from the PR URL (e.g. `EightfoldAI/vscode`) and compare it to the current
working directory. If they differ, stop and alert the user before doing anything else.

```bash
gh pr view <PR> --repo <owner/repo> --json headRefName -q '.headRefName'
git fetch origin <branch> && git checkout <branch>
```

Never analyse a PR from the diff alone. The diff shows only what changed — the branch gives you
the full surrounding code, call paths, and module structure. A finding in `service.py:177` means
nothing without `registry.py` and `config.py` checked out so you can trace the actual flow.

---

## How to present the review

The output has three parts, in this order:

**1. What this system does**
Two to three sentences, zero context assumed. Name the components, describe the data flow,
and say what the PR changes in one breath. A senior intern should be able to follow it.

**2. Story chapters — one per PR concern**
Walk through the changes as a story, numbered sections, in the order a reader would trace the
code. For each chapter:
- Open with 1–2 sentences of narrative explaining what this part does and why it changed
- Drop in a code snippet **only when the code itself is the explanation** — a suspicious
  pattern, a fake implementation, a hardcoded secret. The shortest slice that makes the point.
- For everything else — setup code, clean implementations, call sites — use a clickable file
  link and let the reader jump there. Don't paste code just to prove you read it.
- Weave in concerns **at the moment they arise**, not saved for a separate section at the end.
  A reader who encounters a concern right after understanding the surrounding code retains it.

**3. Before-merge table**
A compact reference checklist at the end. The story already explained each item — the table
is just the summary.

```
| 🔴 | [file.py:14](path/file.py#L14)       | Private key in source — rotate + read from env |
| 🟡 | [file.py:50–64](path/file.py#L50-L64) | Fake streaming — file a ticket               |
| 🟢 | [file.ts:285](path/file.ts#L285)       | Cancel fires onComplete — clarify UX intent  |
```

Severity guide:
- 🔴 Must fix before merge — security, production blocker, data loss risk
- 🟡 Should fix — scalability, duplication, poor separation of concerns, DB design
- 🟢 Nice to have — optimisation, naming, documentation gaps

---

## File link formatting — critical

Markdown links are clickable. Inline code refs and code-block comments are not.

```
✅ [tether_service.py:108](www/career_hub/agents/chat/tether_service.py#L108)
❌ `tether_service.py:108`
❌ // tether_service.py:108   (inside a code block — never clickable)
```

Every file reference must be a markdown link: `[file.py:N](path/file.py#LN)`.
For ranges: `[file.py:50–64](path/file.py#L50-L64)`.

---

## What to look for

**Separation of concerns**
- Are orthogonal concepts conflated in identifiers or class names?
- Can components be decoupled for better reuse?

**Database design**
- Compound string identifiers vs proper composite keys?
- Test/dev configuration leaking into production schema?

**Scalability**
- N×M anti-patterns that should be N+M?
- What's the cost of adding a new dimension?

**Code reuse**
- Logic duplicated across variants when it could live in a base class?
- Patterns reusable across similar features?

**Configuration and safety**
- Hardcoded URLs, secrets, or environment-specific values in source?
- State saved before a risky external call, with no rollback on failure?
- Unconditional destructive operations with no guard?

---

## Common anti-patterns

### Compound identifier anti-pattern

```python
# ❌ Bad — N products × M providers = N×M enum values
class ConnectorName(StrEnum):
    BILLING_GOOGLE = 'billing_google'
    BILLING_MICROSOFT = 'billing_microsoft'
    HR_GOOGLE = 'hr_google'
    HR_MICROSOFT = 'hr_microsoft'
```

Adding a new provider means one value per product. OAuth logic duplicates per variant.
Queries like "all Google connectors" need `LIKE '%_google'`.

```python
# ✅ Good — N + M values total, shared OAuth logic in one base class
class ProductName(StrEnum):
    BILLING = 'billing'
    HR = 'hr'

class ConnectorType(StrEnum):
    GOOGLE = 'google'
    MICROSOFT = 'microsoft'
```

Red flags: enum values where removing one underscore-separated segment gives a duplicate.

---

### Test configuration leaking into production code

```python
# ❌ Bad
class Integration(DBLoader):
    def get_default_db(self):
        return 'test'                  # should be 'main'
    def tablename(self):
        return 'integrations_test_2'   # should be 'integrations'
```

Red flags: `'test'` as a default return value, `_test`/`_dev` suffix in table names.

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

Red flags: `.dev.` in URL string literals, personal usernames, any hardcoded `https://`
that should vary per environment.

---

### Missing transaction safety

```python
# ❌ Bad — row saved before external call that can fail
def oauth_callback(code):
    integration.save()
    tokens = exchange_code_for_token(code)  # can fail → partial state in DB

# ✅ Good
def oauth_callback(code):
    tokens = exchange_code_for_token(code)
    integration.save()   # only reached if token exchange succeeded
```

---

### Unconditional destructive operations

```python
# ❌ Bad — no guard on existing data
def enable_connector():
    delete_all_integrations(org_id, connector_type)
    create_new_integration()
```

Red flags: `delete_all()` / `DELETE FROM` without a pre-check, no soft-delete option.

---

## Search tips

- **N×M pattern**: enum values where removing one segment gives a duplicate — two concepts are fused
- **Test bleed**: grep for `'test'` in return values, `_test` in table names, `_dev` in defaults
- **Hardcoded env values**: grep for `https://`, `.dev.`, `.staging.`, or any personal username
- **Future cost framing**: when flagging a scalability issue, state the cost to fix now vs later

---

## Examples

Two worked examples showing the output format in practice:

- `example-explain-then-review.md` — algorithmic PR (conversational RAG pipeline); concerns are
  structural enough to warrant a dedicated findings section after the explanation
- `example-story-chapters-woven-concerns.md` — integration/wiring PR (adding a second agent
  backend); concerns woven into story chapters as they arise, compact before-merge table at end
