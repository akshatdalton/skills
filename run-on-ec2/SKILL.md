---
name: run-on-ec2
description: >
  Execute code, pytest, or IPython debugging on the remote EC2 dev instance.
  Python packages and dependencies are only installed on EC2 — nothing runs locally.
  Trigger when any code execution, pytest run, or debug snippet needs to be executed.
  Also use this skill as the execution backend for /debug-api snippets.
---

**Scope:** vscode/ repo only. wipdp/ → run locally, no SSH.

# Run on EC2

All code execution happens on EC2. Packages not installed locally.

---

## Step 0 — Determine location

- **`/home/ec2-user/...`** → already on EC2 → **Mode A**
- **`/Users/akshat.v/...`** → local → **Mode B**

---

## Mode A — On EC2

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

### VPN check
```bash
ssh -o ConnectTimeout=5 -i ~/eightfold/id_rsa -o StrictHostKeyChecking=no ec2-user@172.31.27.248 echo ok 2>&1
```
Fails → *"VPN appears down — connect and retry."* Do not proceed.

### Push then SSH+run

**Pytest:**
```bash
git push -u origin <branch>
ssh -i ~/eightfold/id_rsa -o StrictHostKeyChecking=no ec2-user@172.31.27.248 \
  "source /home/ec2-user/test_env.sh && \
   source /home/ec2-user/py3.13-virt/bin/activate && \
   cd /home/ec2-user/vscode/www && \
   git fetch origin && git checkout <branch> && git pull && \
   PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest <test_path> -v --noconftest"
```

**IPython** — SSH interactively, then source env + activate + cd + ipython.

---

## EC2 Details

| Item | Value |
|---|---|
| Host | `ec2-user@172.31.27.248` |
| SSH key | `~/eightfold/id_rsa` |
| Repo | `/home/ec2-user/vscode` |
| Venv | `/home/ec2-user/py3.13-virt/bin/activate` |
| Env file | `/home/ec2-user/test_env.sh` |
| Test base | `/home/ec2-user/vscode/www/` |

---

## Required flags — never omit

| Flag | Why |
|---|---|
| `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` | Without it, pytest plugins trigger boto3 SSL init → `SSLContext` error or `RecursionError`. |
| `--noconftest` | Prevents conftest from hitting real AWS on import |
| `-v` | Verbose output |

**SSLContext or RecursionError** → fix is always `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`.

Test paths relative to `/home/ec2-user/vscode/www/`. Trailing CloudWatch logging error → harmless, ignore.

---

## IPython debug snippets — import order

Same import order as [/debug-api references/debug-snippet-template.md](../debug-api/references/debug-snippet-template.md):

1. `sys.path.insert(0, '/home/ec2-user/vscode/www')`
2. Low-level utils FIRST: `regex_utils`, `list_utils`, `stage_utils`, `ats_config_utils`
3. `user_login` — ALWAYS before profile/apps (modules assume user context during init)
4. Everything else: `from profile import profile as pr` etc.

Each step prints before proceeding — paste incrementally, see where it fails.

### Import rules

Never guess. Grep first. Verified:
- `from profile import profile as pr` — NOT `from profile import pr`
- `from profile import candidate`
- `from profile import stage_transition_utils`
- `from apps.user_profile_actions import get_position_by_id`

### Decode encoded IDs
```python
from profile import profile as pr
profile_id = pr.decode_enc_id('Z5aZwdwjQV')
```

---

## Mode C — Read remote file

Pull right branch before reading:
```bash
ssh -i ~/eightfold/id_rsa -o StrictHostKeyChecking=no ec2-user@172.31.27.248 \
  "cd /home/ec2-user/vscode && git fetch origin && git checkout <branch> && git pull && cat <file_path>"
```
