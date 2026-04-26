---
name: debug-api
description: >
  Debug a failing Eightfold API endpoint by generating a reproducible IPython
  snippet, tracing the call chain, and pinpointing the exact line of failure.
  Trigger when user says "debug this API", "why is this failing", "trace this
  endpoint", or shares an API response with an error message.
---

# Debug API — Eightfold Backend

Goal: pinpoint exact line and reason for failure — not just reproduce it.

---

## Step 1 — Gather inputs

Collect (or extract from context):
- API endpoint + HTTP method (e.g. `POST /api/update_profile`)
- Failing response (e.g. `{"message": "Update operation failed", "response_success": []}`)
- User / group_id (e.g. `demo@grupobimbo-sandbox.com` / `grupobimbo-sandbox.com`)
- Entity IDs in request payload (profile_id, position_id, etc.)
- Encoded IDs needing decode (e.g. `Z5aZwdwjQV` → `pr.decode_enc_id(...)`)

---

## Step 2 — Trace call chain

Find the view handler:
```bash
grep -r "update_profile\|<endpoint_keyword>" www/apps/ --include="*.py" -l
```

Map full call chain as flow diagram before writing any snippet:
```
POST /api/update_profile
  │
  ├─► view handler  user_profile_view.py:1791
  │     validates request, extracts update_spec
  │
  ├─► validate_update_profile_request()  user_profile_view_utils.py:25
  │     parses update_spec JSON → returns update_dict
  │
  ├─► update_profile_and_enqueue_to_processor()  user_profile_view.py:1920
  │
  └─► iterate_and_execute_update_profile()  user_profile_view.py:2007
        loops over profile_ids
        calls get_position_by_id(ul, pid)
        → failure surfaces here as empty response_success
```

Read each function in chain. Identify **earliest point** that could return error before writing snippet.

---

## Step 3 — Check relevant gates

```python
from config import config
from user import user_login
ul = user_login.get_by_email('EMAIL', group_id='GROUP_ID')
print(ul.enabled_for('gate_name_gate'))
```

Common gates for profile write-back: `add_assessment_details_to_profile_data_before_writeback_gate`

---

## Step 4 — Write IPython debug snippet

### CRITICAL: Verify imports from actual source

Never guess imports. Grep first:
```bash
grep -r "def get_position_by_id\|class UserLogin" www/ --include="*.py" -l
grep -n "^def \|^class " www/user/user_login.py | head -20
```

Prevents wrong imports like `from profile import pr` (wrong) vs `from profile import profile as pr` (correct).

### Environment setup and execution order

Scripts run from **project root**: `/home/ec2-user/vscode/www`

Every snippet follows this exact order:

```python
# 1. Add www to path (if outside www dir)
import sys
sys.path.insert(0, '/home/ec2-user/vscode/www')

# 2. Pre-import low-level utils FIRST to break circular import locks
from utils import regex_utils
from utils import list_utils
from ats import stage_utils
from ats import ats_config_utils

# 3. user_login MUST come before any profile/apps imports
from user import user_login
ul = user_login.get_by_email('EMAIL', group_id='GROUP_ID')
print(f'ul: {ul}')

# 4. Only NOW import profile/apps modules
from profile import profile as pr
# ... rest of snippet
```

**Why user_login first:** Profile/app modules assume user context exists during initialization.

### Import rules
- `from profile import profile as pr` — NOT `from profile import pr`
- `from profile import candidate` — for `candidate.get_profile(profile_id)`
- `from profile import stage_transition_utils`
- `from apps.user_profile_actions import get_position_by_id`
- Always grep `www/<module>/` to confirm actual filename before importing

### Decode encoded IDs
```python
from profile import profile as pr
profile_id = pr.decode_enc_id('Z5aZwdwjQV')
```

### Structure: step by step with prints

Each step prints result before proceeding — lets user paste incrementally and see where it fails:

```python
# Step 1: setup + user_login (always first)
import sys
sys.path.insert(0, '/home/ec2-user/vscode/www')
from utils import regex_utils, list_utils
from ats import stage_utils, ats_config_utils
from user import user_login
ul = user_login.get_by_email('EMAIL', group_id='GROUP_ID')
print(f'ul: {ul}')

# Step 2: decode IDs
from profile import profile as pr
profile_id = pr.decode_enc_id('ENCODED_ID')
pid = 'POSITION_ID'
print(f'profile_id: {profile_id}')

# Step 3: position access
from apps.user_profile_actions import get_position_by_id
usp = get_position_by_id(ul, pid)
print(f'usp: {usp}')
if usp:
    print(f'  system_id: {usp.get_system_id()}')
    print(f'  ats_job_id: {usp.ats_job_id}')
    print(f'  is_ef_ats: {ats_config_utils.is_eightfold_ats(ul.get_group_id(), system_id=usp.get_system_id())}')

# Step 4: application lookup
from profile import candidate
profile_obj = candidate.get_profile(profile_id)
if usp:
    appl = profile_obj.applications().get_latest_active(usp.ats_job_id, job_system_id=usp.get_system_id())
    print(f'appl: {appl}')

# Step 5: simulate failing call with full traceback
import traceback
try:
    result = <the_failing_function>(ul, profile_id, update_data)
    print(f'result: {result}')
except Exception as e:
    print(f'EXCEPTION: {type(e).__name__}: {e}')
    traceback.print_exc()
```

---

## Step 5 — Run the snippet

**Auto-detect via `git remote get-url origin`:**

- **vscode repo** → Use `/run-on-ec2`. IPython snippets run on EC2 — packages not installed locally.
- **wipdp repo** → Run locally.

Before SSH, test connectivity:
```bash
ssh -o ConnectTimeout=5 -i ~/eightfold/id_rsa -o StrictHostKeyChecking=no ec2-user@172.31.27.248 echo ok 2>&1
```
If fails: *"VPN appears down — connect to VPN and try again."*

Always IPython, always step by step — never `python script.py`.

---

## Step 6 — Interpret output and pinpoint failure

When user shares output:
1. Identify which step printed `None`, empty, or threw exception
2. Read that function's source directly
3. State **exact file:line** and **reason** (e.g. "gate disabled", "appl is None so early return at line 2034", "ats_job_id mismatch")
4. Propose fix or next diagnostic step

---

## Wipdp server debugging

1. Read `scripts/dev-*.sh` for server startup command
2. Start/restart server if needed
3. Run health check to confirm it's up
4. If testing TetherAgent from vscode, verify `TetherAgent._base_url` points to correct wipdp instance

---

## Common failure patterns

| Symptom | Likely cause | Where to look |
|---|---|---|
| `response_success: []` | Early return in `iterate_and_execute_update_profile` | `user_profile_view.py:2007` |
| `appl` is `None` | `get_latest_active` found no matching application | `candidate.py` — check ats_job_id match |
| `usp` is `None` | Position not found or no access | `get_position_by_id` in `user_profile_actions.py` |
| Gate-guarded path skipped | Gate disabled for group | `ul.enabled_for('gate_name_gate')` |
| Circular import error | Missing pre-imports in setup | Add `from utils import regex_utils, list_utils` before other imports |
