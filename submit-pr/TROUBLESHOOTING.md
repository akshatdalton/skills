# PR Troubleshooting Guide

---

## Checklist Bot Failures

### "Default options missing for: [item]"

**Cause**: Checklist item text doesn't match template exactly, or item was deleted.

**Fix**:
1. Read local `.github/PULL_REQUEST_TEMPLATE.md`
2. Find the exact line — copy it byte-for-byte (including URLs, apostrophes, spacing)
3. Never reconstruct from memory or from an MCP response

```bash
cat .github/PULL_REQUEST_TEMPLATE.md
```

**Common culprits**:
- The "deploying all services" line with the long Atlassian URL — copy from template, not from MCP
- Apostrophes (`'`) encoded as `&#39;` from MCP response
- Missing spaces or punctuation

---

### "Blank field detected"

**Cause**: A `_____` blank was left unfilled.

**Fix**: Fill every `_____` with a specific value or `N/A`.

```markdown
❌  - [ ] Memory impact: _____
✅  - [ ] Memory impact: N/A
```

---

### "URL mismatch"

**Cause**: URL in a checklist item doesn't match the template exactly.

**Fix**: Copy the entire line from `.github/PULL_REQUEST_TEMPLATE.md` — do not copy from an MCP response. MCP responses may truncate URLs (e.g. missing `/spaces/EP/` path segments).

---

### Checklist validation errors (missing mandatory fields)

Common errors and their fixes:

| CI error | Fix |
|---|---|
| `Mandatory field not checked: If scripts are used in DAGs...` | Add: `[x] If scripts are used in DAGs, list tested regions: NA` |
| `Mandatory field not checked: If new dags in dags_config.json...` | Add: `[x] If new dags in dags_config.json need to run in westus2...` |
| `Mandatory field not checked: I have gone through the updated checklist.` | Add: `[x] I have gone through the updated checklist.` |
| `Number of options selected for 'Handle Edge cases gracefully' is not in range 1-inf` | Check at least one option under that section |

---

## HTML Entity Encoding

**Symptom**: CI fails after updating PR body via GitHub MCP. Apostrophes appear as `&#39;`, ampersands as `&amp;`.

**Cause**: GitHub MCP encodes special characters as HTML entities when reading/writing PR bodies.

**Fix**: Always decode before writing. Plain text characters only — never HTML entities.

Decode map:
- `&#39;` → `'`
- `&amp;` → `&`
- `&gt;` → `>`
- `&lt;` → `<`

Or in Python: `import html; html.unescape(body)`

**Source of truth**: always read PR body text from local `.github/PULL_REQUEST_TEMPLATE.md`, never from an MCP response.

---

## Pre-Push Hook Failures

### Linting errors

```bash
ruff check <file>           # see issues
ruff check --fix <file>     # auto-fix where possible
ruff format <file>          # format
ruff check <file>           # verify clean
```

Common: unused imports (F401), line too long (E501), missing docstrings (D100–D107).

---

### Test failures

```bash
pytest path/to/test_file.py -v              # run file
pytest path/to/test_file.py -vv --tb=long   # full output
pytest path/to/test_file.py::Class::method  # single test
```

---

## Git Issues

### Wrong files staged

```bash
git reset                                # unstage all
git diff <parent-branch> --name-only     # see your actual changes
git add <file1> <file2>                  # stage only your files
```

---

### Branch created from wrong base

```bash
git branch -vv                                         # check current base
git checkout <correct-base>
git checkout -b <new-branch>
git cherry-pick <commit-sha>                           # replay your commits

# Or rebase onto correct base
git rebase --onto <correct-base> <wrong-base> <branch>
```

---

## GitHub MCP Issues

### PR not found when searching

When searching by head branch, include the org prefix:
```
head: "<org>:<branch-name>"   ✅
head: "<branch-name>"          ❌
```

Alternatively:
```bash
gh pr list --limit 20          # see all open PRs with exact branch names
```

### Reproduce checklist failures locally

```bash
git checkout <branch-name>
python -c 'from services.github_bot import checklist_utils; checklist_utils.validate_checklist_from_pr(<pr-number>, use_local=True)'
```

---

### "missing required parameter" from MCP tool

Check the GitHub MCP tool's parameter schema for required fields. Common required params: `owner`, `repo`, `pullNumber`. Make sure all are provided.

---

## Quick Diagnostic Commands

```bash
# What changed
git status
git diff --name-only
git diff <parent-branch> --name-only

# Validate locally
pytest <path> -v
ruff check <path>
ruff format --check <path>

# PR status
gh pr list --head <branch-name>
gh pr view <pr-number>
gh pr checks <pr-number>
gh pr checks <pr-number> --watch

# Template
cat .github/PULL_REQUEST_TEMPLATE.md
```

---

## Prevention Checklist

Before pushing:
- [ ] Tests pass: `pytest <path> -v`
- [ ] Linting clean: `ruff check <files> && ruff format <files>`
- [ ] Only relevant files staged (no `git add .`)
- [ ] Branch is based on correct parent

Before creating PR:
- [ ] Read local `.github/PULL_REQUEST_TEMPLATE.md`
- [ ] Checked a recent similar PR for checklist patterns
- [ ] Summary is 2–3 sentences, no bullet sections
- [ ] All `_____` blanks filled with values or `N/A`
- [ ] Checklist items copied exactly — text unmodified
- [ ] Test plan is minimal (command only for backend, steps for UI)
