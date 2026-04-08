---
name: debug-api
description: >
  Debug a failing Eightfold API endpoint by generating a reproducible IPython
  snippet, tracing the call chain, and pinpointing the exact line of failure.
  Trigger when user says "debug this API", "why is this failing", "trace this
  endpoint", or shares an API response with an error message.
---

# Debug API — Eightfold Backend

Structured workflow for debugging a failing API endpoint in this codebase.
The goal is to pinpoint the exact line and reason for failure — not just reproduce it.

---

## Step 1 — Gather inputs

Ask for (or extract from context):
- The **API endpoint** + HTTP method (e.g. `POST /api/update_profile`)
- The **failing response** (e.g. `{"message": "Update operation failed", "response_success": []}`)
- The **user / group_id** to reproduce with (e.g. `demo@grupobimbo-sandbox.com` / `grupobimbo-sandbox.com`)
- Any **entity IDs** in the request payload (profile_id, position_id, etc.)
- Any **encoded IDs** that need decoding (e.g. `Z5aZwdwjQV` → `pr.decode_enc_id(...)`)

---

## Step 2 — Trace the call chain

Grep the codebase to find the view handler:

```bash
grep -r "update_profile\|<endpoint_keyword>" www/apps/ --include="*.py" -l
```

Then read the handler and map the full call chain as a flow diagram before writing any snippet:

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

Read each function in the chain. Identify the **earliest point** that could return the error before writing the snippet.

---

## Step 3 — Check relevant gates

Before running anything, check gates that guard the failing code path:

```python
# In IPython (after setup below)
from config import config
from user import user_login
ul = user_login.get_by_email('EMAIL', group_id='GROUP_ID')
print(ul.enabled_for('gate_name_gate'))
```

Common gates for profile write-back flows:
- `add_assessment_details_to_profile_data_before_writeback_gate`

---

## Step 4 — Write the IPython debug snippet

### CRITICAL: Verify imports from actual source files before writing the snippet

**Never guess imports.** Before writing any snippet, grep the actual module files to confirm the correct import paths:

```bash
# Find where a function/class is actually defined
grep -r "def get_position_by_id\|class UserLogin" www/ --include="*.py" -l

# Check what a module exports
grep -n "^def \|^class " www/user/user_login.py | head -20
```

This prevents wrong imports like `from profile import pr` (wrong) vs `from profile import profile as pr` (correct) — always verify from source.

---

### CRITICAL: Environment setup and execution order

Scripts must be run from the **project root**: `/home/ec2-user/vscode/www`

Every snippet MUST follow this exact order:

```python
# 1. Add www to path (if running outside the www dir)
import sys
sys.path.insert(0, '/home/ec2-user/vscode/www')

# 2. Pre-import low-level utils FIRST to break circular import locks
from utils import regex_utils
from utils import list_utils
from ats import stage_utils
from ats import ats_config_utils

# 3. user_login MUST come before any profile/apps imports
#    Many modules depend on a live user context being established first
from user import user_login
ul = user_login.get_by_email('EMAIL', group_id='GROUP_ID')
print(f'ul: {ul}')

# 4. Only NOW import profile/apps modules
from profile import profile as pr
# ... rest of the snippet
```

**Why user_login first:** Profile and app modules often have initialization paths that assume a user context exists. Getting `ul` before anything else prevents subtle failures in downstream imports.

---

### Import rules (verified against source)
- `from profile import profile as pr` — NOT `from profile import pr`
- `from profile import candidate` — for `candidate.get_profile(profile_id)`
- `from profile import stage_transition_utils`
- `from apps.user_profile_actions import get_position_by_id` — import individually, not bulk
- Always grep `www/<module>/` to confirm the actual filename before importing

### Decode encoded IDs before use
```python
from profile import profile as pr
profile_id = pr.decode_enc_id('Z5aZwdwjQV')
```

### Structure: step by step with prints between each step

Write the snippet so each logical step prints its result before proceeding.
This lets the user paste it incrementally into IPython and see exactly where it fails:

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

# Step 5: simulate the failing call with full traceback
import traceback
try:
    result = <the_failing_function>(ul, profile_id, update_data)
    print(f'result: {result}')
except Exception as e:
    print(f'EXCEPTION: {type(e).__name__}: {e}')
    traceback.print_exc()
```

---

## Step 5 — Execution instructions to give the user

Always tell the user:

```
Run this in a fresh IPython session:

  source /home/ec2-user/py3.13-virt/bin/activate
  cd /home/ec2-user/vscode/www        ← must run from here
  ipython

Then paste each block step by step. Share the output after each step.
```

Do NOT tell the user to run `python script.py` — always IPython, always step by step.

---

## Step 6 — Interpret output and pinpoint failure

When the user shares output:
1. Identify which step printed `None`, empty, or threw an exception
2. Read that function's source code directly
3. State the **exact file:line** and **reason** (e.g. "gate disabled", "appl is None so early return at line 2034", "ats_job_id mismatch")
4. Propose the fix or next diagnostic step

---

## Common failure patterns in this codebase

| Symptom | Likely cause | Where to look |
|---|---|---|
| `response_success: []` | Early return in `iterate_and_execute_update_profile` | `user_profile_view.py:2007` |
| `appl` is `None` | `get_latest_active` found no matching application | `candidate.py` — check ats_job_id match |
| `usp` is `None` | Position not found or user has no access | `get_position_by_id` in `user_profile_actions.py` |
| Gate-guarded path skipped | Gate disabled for this group | Check with `ul.enabled_for('gate_name_gate')` |
| Circular import error | Missing pre-imports in setup block | Add `from utils import regex_utils, list_utils` before other imports |
