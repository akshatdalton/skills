# IPython Debug Snippet Template

## Import Order (CRITICAL — never reorder)

```python
# 1. sys.path (if outside www dir)
import sys
sys.path.insert(0, '/home/ec2-user/vscode/www')

# 2. Low-level utils FIRST (break circular imports)
from utils import regex_utils, list_utils
from ats import stage_utils, ats_config_utils

# 3. user_login — MUST precede profile/apps imports
from user import user_login
ul = user_login.get_by_email('EMAIL', group_id='GROUP_ID')
print(f'ul: {ul}')

# 4. Profile/apps modules only NOW
from profile import profile as pr
# ... rest of snippet
```

**Why user_login first:** Profile/app modules assume user context exists during init.

## Full Step-by-Step Template

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

## Import Rules

Never guess imports. Grep first:
```bash
grep -r "def function_name\|class ClassName" www/ --include="*.py" -l
grep -n "^def \|^class " www/module/file.py | head -20
```

Verified imports:
- `from profile import profile as pr` — NOT `from profile import pr`
- `from profile import candidate` — for `candidate.get_profile(profile_id)`
- `from profile import stage_transition_utils`
- `from apps.user_profile_actions import get_position_by_id`

## Decode Encoded IDs

```python
from profile import profile as pr
profile_id = pr.decode_enc_id('Z5aZwdwjQV')
```
