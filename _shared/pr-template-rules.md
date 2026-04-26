# PR Template Rules (shared)

Referenced by: `/submit-pr`, `/get-pr-ready-to-merge`

## Source of truth
Always read `.github/PULL_REQUEST_TEMPLATE.md` from local filesystem. Never reconstruct from memory or MCP response.

## Body encoding
MCP encodes `'` → `&#39;`, `&` → `&amp;`. Always decode HTML entities before updating. Always write body to temp file, pass `--body-file`. Never inline.

## Checklist rules
1. Never delete any item — keep all `[ ]` lines verbatim
2. Only add `x`: `[ ]` → `[x]`, never remove
3. Never modify item text
4. URLs byte-for-byte identical
5. Fill all `_____` blanks with value or `N/A`
6. Every section needs at least one `[x]`

## Mandatory sections (CI fails if untouched)
Product area, Handle Edge cases gracefully, Gate Control, Testing, A11y Compliance, AI Recruiter, Sandbox Refresh, PR Description for customer release.

## Auto-added items (do NOT add manually)

| Trigger | Items |
|---|---|
| `**/requirements.txt` or `**/package.json` | Package license, ownership, memory, design doc, bot install |
| `scripts/airflow_v2/dags-*` or `dags_config.json` | DAG regions, westus2, alarm config |

Adding manually when not triggered → CI failure.

## Bot-injected items
Bot (eightfoldbot) may inject extra mandatory items not in template. Compare body vs template bidirectionally. Bot-added items still enforced.

## Re-triggering CI
PR body changes don't auto-trigger CI. Add `needs_ci` comment after body updates.

## Repo detection
`git remote get-url origin`:
- **wipdp** → prose: Summary + JIRA TASK + TEST PLAN (bash block)
- **vscode** → checklist from template
