---
name: run-on-ec2
description: >
  Execute code, pytest, or IPython debugging on the remote EC2 dev instance.
  Python packages and dependencies are only installed on EC2 — nothing runs locally.
  Trigger when any code execution, pytest run, or debug snippet needs to be executed.
  Also use this skill as the execution backend for /debug-api snippets.
---

**Scope:** vscode/ repo only. For wipdp/ repo, run locally — do not SSH to EC2.

# Run on EC2

All code execution (pytest, IPython, scripts) happens on EC2. Packages not installed locally.

---

## Step 0 — Determine location

```bash
pwd
```

- **`/home/ec2-user/...`** → already on EC2 → **Mode A**
- **`/Users/akshat.v/...`** → local → **Mode B**

---

## Mode A — Already on EC2

### Pytest
```bash
source /home/ec2-user/test_env.sh
source /home/ec2-user/py3.13-virt/bin/activate
cd /home/ec2-user/vscode/www
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest <test_path> -v --noconftest
```

### IPython
```bash
source /home/ec2-user/test_env.sh
source /home/ec2-user/py3.13-virt/bin/activate
cd /home/ec2-user/vscode/www
ipython
```

---

## Mode B — Local (push → SSH → run)

### Step 0 — VPN check
```bash
ssh -o ConnectTimeout=5 -i ~/eightfold/id_rsa -o StrictHostKeyChecking=no ec2-user@172.31.27.248 echo ok 2>&1
```
If fails: *"VPN appears down — connect to VPN and try again."* Do not proceed until confirmed.

### Step 1 — Push
```bash
git push -u origin <branch>
```

### Step 2 — SSH, pull, run

**Pytest:**
```bash
ssh -i ~/eightfold/id_rsa -o StrictHostKeyChecking=no ec2-user@172.31.27.248 \
  "source /home/ec2-user/test_env.sh && \
   source /home/ec2-user/py3.13-virt/bin/activate && \
   cd /home/ec2-user/vscode/www && \
   git fetch origin && git checkout <branch> && git pull && \
   PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest <test_path> -v --noconftest"
```

**IPython** — SSH interactively:
```bash
ssh -i ~/eightfold/id_rsa -o StrictHostKeyChecking=no ec2-user@172.31.27.248
# then on EC2:
source /home/ec2-user/test_env.sh
source /home/ec2-user/py3.13-virt/bin/activate
cd /home/ec2-user/vscode/www
ipython
```

---

## EC2 Details

| Item | Value |
|---|---|
| Host | `ec2-user@172.31.27.248` |
| SSH key | `~/eightfold/id_rsa` |
| Repo path | `/home/ec2-user/vscode` |
| Python venv | `/home/ec2-user/py3.13-virt/bin/activate` |
| Env file | `/home/ec2-user/test_env.sh` |
| Test base dir | `/home/ec2-user/vscode/www/` |

---

## Required flags — never omit

| Flag | Why |
|---|---|
| `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` | **Required for all code execution.** Without it, pytest plugins auto-load and trigger boto3 SSL init, causing `super(SSLContext, SSLContext).options.__set__(self, value)` or `RecursionError: maximum recursion depth exceeded`. |
| `--noconftest` | Prevents conftest.py from auto-loading and hitting real AWS on import |
| `-v` | Verbose output |

**If you see either of these errors, fix is always `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`:**
```
super(SSLContext, SSLContext).options.__set__(self, value)
RecursionError: maximum recursion depth exceeded
```

Test paths always **relative to `/home/ec2-user/vscode/www/`**, e.g.: `connectors/tests/test_connector_api_server_utils.py`

Trailing "logging error" about CloudWatch is harmless — ignore.

---

## IPython debug snippets — import order

### 1. sys.path (if needed)
```python
import sys
sys.path.insert(0, '/home/ec2-user/vscode/www')
```

### 2. Low-level utils FIRST (break circular imports)
```python
from utils import regex_utils
from utils import list_utils
from ats import stage_utils
from ats import ats_config_utils
```

### 3. user_login — ALWAYS before profile/apps imports
```python
from user import user_login
ul = user_login.get_by_email('EMAIL', group_id='GROUP_ID')
print(f'ul: {ul}')
```

**Why:** Profile/app modules assume user context exists during init. Import user_login and obtain `ul` before anything downstream.

### 4. Everything else
```python
from profile import profile as pr
# ... rest of snippet
```

### Full template
```python
import sys
sys.path.insert(0, '/home/ec2-user/vscode/www')

from utils import regex_utils
from utils import list_utils
from ats import stage_utils
from ats import ats_config_utils

from user import user_login
ul = user_login.get_by_email('EMAIL', group_id='GROUP_ID')
print(f'ul: {ul}')

from profile import profile as pr
# ... rest of snippet
```

### Structure: step-by-step with prints

Each step prints before proceeding — paste incrementally, see where it fails:

```python
# Step 1: decode IDs
from profile import profile as pr
profile_id = pr.decode_enc_id('ENCODED_ID')
print(f'profile_id: {profile_id}')

# Step 2: call failing function
import traceback
try:
    result = the_failing_function(ul, profile_id)
    print(f'result: {result}')
except Exception as e:
    print(f'EXCEPTION: {type(e).__name__}: {e}')
    traceback.print_exc()
```

---

## Mode C — Read remote file

Always pull right branch before reading:
```bash
ssh -i ~/eightfold/id_rsa -o StrictHostKeyChecking=no ec2-user@172.31.27.248 \
  "cd /home/ec2-user/vscode && git fetch origin && git checkout <branch> && git pull && cat <file_path>"
```

---

## Import rules

Never guess imports. Grep first:
```bash
grep -r "def function_name\|class ClassName" www/ --include="*.py" -l
grep -n "^def \|^class " www/module/file.py | head -20
```

Verified imports:
- `from profile import profile as pr` — NOT `from profile import pr`
- `from profile import candidate`
- `from profile import stage_transition_utils`
- `from apps.user_profile_actions import get_position_by_id`

### Decode encoded IDs
```python
from profile import profile as pr
profile_id = pr.decode_enc_id('Z5aZwdwjQV')
```
