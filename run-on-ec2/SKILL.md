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

## Pre-entry: project-context contract (mandatory — do not skip)

On entry, MUST invoke `Skill(skill="project-context", args="branch:read")` so the test/debug snippet you write is informed by the branch's prior findings (key files, test env, fixtures). Surface one-line `↳ loaded ...` or `↳ no context yet`.

After running tests or debug snippets, on any material finding (test env detail, fixture path, root cause line, sandbox URL, login), MUST invoke `Skill(skill="project-context", args="branch:update <one-line>")` and surface `↳ saved to branch context: ...`.

Never ask. Save and notify.

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

**Also applies to plain `python3 -c` scripts on wipdp**, not just pytest. If running a debug snippet on a non-dev EC2 (e.g. demo-wipdp) and getting SSL/gevent errors, set the same flag: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -c "..."`.

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

---

## Hopping to other instances (pssh)

`pssh` = shell alias, not binary. Defined in `~/vscode/dotfiles/.bashrc`. Aliases don't load in non-interactive SSH — always fails with `command not found`.

**`ssh.py` is also interactive-only.** Calling it non-interactively (even without a command arg) always fails with `OSError: [Errno 25] Inappropriate ioctl for device`. Do not attempt to pass commands through it.

**Working pattern — three steps:**

**Step 1: Get the prod SSH key path** (stable within a session — do once, reuse)
```bash
ssh -i ~/eightfold/id_rsa -o StrictHostKeyChecking=no ec2-user@172.31.27.248 \
  "source /home/ec2-user/test_env.sh && source /home/ec2-user/py3.13-virt/bin/activate && python3 -c \"
import sys; sys.path.insert(0, '/home/ec2-user/vscode/www')
from gevent import monkey; monkey.patch_all()
import glog as log; log.setLevel(log.ERROR)
from utils import boto_utils; from utils.boto_constants import Secrets
print(boto_utils.secret(Secrets.PROD_SSH_KEY, write_to_file=True))
\" 2>/dev/null"
# → e.g. /tmp/tmp.c3NoL3NlYXJjaC1zZXJ2aWNlLXByb2Q
```

**Step 2: Get the instance hostname** (script prints it before dying — parse stdout)
```bash
ssh -i ~/eightfold/id_rsa -o StrictHostKeyChecking=no ec2-user@172.31.27.248 \
  "source /home/ec2-user/test_env.sh && source /home/ec2-user/py3.13-virt/bin/activate && \
   python3 /home/ec2-user/vscode/scripts/aws/ssh.py <instance-name> 2>&1 | grep 'compute.amazonaws.com' | head -1" \
  | awk '{print $NF}'
# → e.g. ec2-35-85-52-223.us-west-2.compute.amazonaws.com
```

**Step 3: Run commands directly on the target instance**
```bash
ssh -i ~/eightfold/id_rsa -o StrictHostKeyChecking=no ec2-user@172.31.27.248 \
  "ssh -q -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i <key_path> <hostname> '<command>'"
```

Note: use `python3`, not `python` — `python` is not found on the EC2 dev box.

---

## Background processes over SSH

`nohup` alone not enough. Process stays in job table, dies when SSH closes. Use `disown`:

```bash
nohup <command> > /tmp/output.log 2>&1 </dev/null & disown && echo started
```

- `</dev/null` — detach stdin, no blocking
- `& disown` — remove from job table, survives session close
- `&& echo started` — confirm backgrounded

**Pipe chains eat exit codes.** `cmd | tail -30 && echo OK` always prints OK — `tail` always exits 0. Never use to verify success. Check exit code separately.
