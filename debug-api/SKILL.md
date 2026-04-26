---
name: debug-api
description: >
  Debug a failing Eightfold API endpoint by generating a reproducible IPython
  snippet, tracing the call chain, and pinpointing the exact line of failure.
  Trigger when user says "debug this API", "why is this failing", "trace this
  endpoint", or shares an API response with an error message.
---

# Debug API — Eightfold Backend

Goal: pinpoint exact line and reason — not just reproduce.

---

## Step 1 — Gather inputs

Collect from context:
- API endpoint + method (e.g. `POST /api/update_profile`)
- Failing response (e.g. `{"message": "Update operation failed"}`)
- User / group_id
- Entity IDs in payload (profile_id, position_id, etc.)
- Encoded IDs needing decode (e.g. `Z5aZwdwjQV` → `pr.decode_enc_id(...)`)

---

## Step 2 — Trace call chain

Find view handler:
```bash
grep -r "update_profile\|<endpoint_keyword>" www/apps/ --include="*.py" -l
```

Map full chain as flow diagram before writing snippet:
```
POST /api/update_profile
  ├─► view handler  user_profile_view.py:1791
  ├─► validate_update_profile_request()  user_profile_view_utils.py:25
  ├─► update_profile_and_enqueue_to_processor()  user_profile_view.py:1920
  └─► iterate_and_execute_update_profile()  user_profile_view.py:2007
```

Read each function. Identify **earliest** possible error point before writing snippet.

---

## Step 3 — Check gates

```python
from config import config
from user import user_login
ul = user_login.get_by_email('EMAIL', group_id='GROUP_ID')
print(ul.enabled_for('gate_name_gate'))
```

---

## Step 4 — Write IPython debug snippet

### CRITICAL: Verify imports from source

Never guess. Grep first:
```bash
grep -r "def get_position_by_id\|class UserLogin" www/ --include="*.py" -l
```

### Import order + full template

See [references/debug-snippet-template.md](references/debug-snippet-template.md) for:
- Exact import order (sys.path → low-level utils → user_login → profile/apps)
- Full step-by-step template with prints
- Import rules and verified imports
- ID decoding

**Key rule:** user_login MUST come before profile/apps imports. Profile modules assume user context during init.

### Structure: step by step with prints

Each step prints before proceeding — paste incrementally, see where it fails.

---

## Step 5 — Run snippet

Use `/run-on-ec2` for execution — it handles environment detection (vscode→EC2, wipdp→local), VPN checks, and import ordering. Do not duplicate EC2 connection logic here.

Always IPython, always step by step — never `python script.py`.

---

## Step 6 — Interpret and pinpoint

When user shares output:
1. Which step printed `None`, empty, or threw exception?
2. Read that function's source
3. State **exact file:line** + **reason** (gate disabled, appl None, ats_job_id mismatch)
4. Propose fix or next diagnostic

---

## Wipdp server debugging

1. Read `scripts/dev-*.sh` for startup command
2. Start/restart if needed
3. Health check to confirm up
4. If testing TetherAgent from vscode, verify `TetherAgent._base_url` points to correct wipdp instance

---

## Common failures

| Symptom | Likely cause | Where to look |
|---|---|---|
| `response_success: []` | Early return in `iterate_and_execute_update_profile` | `user_profile_view.py:2007` |
| `appl` is `None` | `get_latest_active` no matching application | `candidate.py` — check ats_job_id |
| `usp` is `None` | Position not found / no access | `get_position_by_id` in `user_profile_actions.py` |
| Gate-guarded path skipped | Gate disabled for group | `ul.enabled_for('gate_name_gate')` |
| Circular import error | Missing pre-imports | Add `from utils import regex_utils, list_utils` first |

---

## Workflow ending

After pinpointing failure, offer next action:
- *"/create-jira-ticket-with-reference to track bug? Or fix directly via /work-on-jira-task?"*

Run `/project-context:update` with root cause, exact file:line, and proposed fix.
