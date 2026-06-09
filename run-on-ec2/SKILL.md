---
name: run-on-ec2
description: >
  DEPRECATED — use the `efx` skill instead. Execute code, pytest, or IPython on the
  remote EC2 dev instance (vscode deps are EC2-only). Trigger for any EC2 code
  execution, pytest, or debug snippet; also the execution backend for /debug-api.
  efx supersedes this with deterministic exec + regional targets + async submit/poll.
---

> # ⚠️ DEPRECATED — use `efx` instead
> This skill is superseded by **`efx`** (`~/.claude/skills/efx/`), which does the same
> job deterministically and also handles regional prod boxes, async submit/poll, VPN
> auto-recovery, and the env-bootstrap gotchas this skill hand-rolls.
>
> **Migrate your call:**
> | run-on-ec2 (old) | efx (new) |
> |---|---|
> | `ssh … "… pytest <p> -v --noconftest"` | `python3 ~/.claude/skills/efx/scripts/efx.py exec --target dev -- 'PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest <p> -v --noconftest'` |
> | ipython snippet via SSH | `… efx exec --target dev --lang py < snippet.py` |
> | `pssh shared-eu` regional data | `… efx exec --target shared-eu-tm --lang py -- '…'` |
> | long job over flaky VPN | `… efx submit …` then `… efx poll …` |
>
> Prefer `efx`. The content below remains only as reference for the underlying mechanics.

**Scope:** vscode/ repo only. wipdp/ → run locally, no SSH.

> For all per-ticket state mutations, see [shared progress policy](/Users/akshat.v/.claude/skills/_shared/progress-policy.md).

# Run on EC2

All code execution happens on EC2. Packages not installed locally.

## Pre-entry: progress.md contract (mandatory — do not skip)

On entry, MUST invoke `python3 ~/.claude/scripts/progress_fm.py get <TICKET_ID>` so the test/debug snippet you write is informed by the branch's prior findings (key files, test env, fixtures). Surface one-line `↳ loaded ...` or `↳ no context yet`.

After running tests or debug snippets, on any material finding (test env detail, fixture path, root cause line, sandbox URL, login), MUST invoke `python3 ~/.claude/scripts/progress_fm.py append-section <TICKET_ID> --section "Decisions" --line "<one-line>"` and surface `↳ saved to progress.md: ...`.

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
Fails → connect via:
```bash
~/eightfold/vpn-connect.sh -y     # -y auto-kills any stale connection; ~5–10s
```
Then re-run the VPN check. Disconnect with `~/eightfold/vpn-disconnect.sh`. Full automation details (Keychain pass, TOTP, sudoers) in `~/opensource/vault/wiki/projects/vscode/learnings.md` → "VPN automation".

**Note:** the openvpn process backgrounded by `vpn-connect.sh` does NOT survive across Bash tool invocations (harness reaps it after each shell exits). Re-run `vpn-connect.sh -y` immediately before each SSH if the prior connection dropped.

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

## Region-specific (VPC) execution — customer data lives in the customer's region

Customer/prod data is **region-sharded** (e.g. `se.com` → eu-central-1; us customers → us-west-2). The dev box (172.31.27.248, us-west-2) has **no prod-DB creds** and **cannot resolve a non-us-west-2 group's shard** (`No secret or cluster URI for db_type global` → `DBConnectionErrorException`). To run code against a specific region's prod data, hop to a box **in that region** first.

**Interactive hop via `pssh <regional-cluster>`** (verified 2026-06-01): from an interactive SSH session on the dev box, `pssh shared-eu-tm` lands you on an eu-central-1 prod box with the right region context + prod creds:
```
$ pssh shared-eu-tm
i-0e... -> ec2-3-67-194-168.eu-central-1.compute.amazonaws.com
...
EF REGION IS: eu-central-1   AWS DEFAULT REGION: eu-central-1   AWS ACCOUNT ID: 948299231917
(py3.13-virt) ec2-user@shared-eu-tm:~/vscode$ ipython   # now db_utils / get_custom_field_by_name see EU prod data
```
Known regional clusters: `shared-eu-tm` (eu-central-1). `pssh` is interactive-only (shell alias) — drive it in an interactive shell / iTerm, then run `ipython` there. This is the path for "who/what in customer X's data" when X is not a us-west-2 tenant.

> gevent note on the EU box: harmless `_ThreadHandle._set_done() takes no keyword arguments` fork warnings may print after `monkey.patch_all()` — ignore, output still returns.

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

---

## Long pytest under flaky VPN — detach + poll

When the VPN is unstable, a single synchronous `ssh ec2 "<long pytest>"` will die if VPN drops mid-run. Detach the work from the SSH session so reconnects don't kill it:

**1. Kick off detached** (the SSH command itself can disconnect after `echo backgrounded` — the work is already running):
```bash
ssh -o ConnectTimeout=10 -i ~/eightfold/id_rsa -o StrictHostKeyChecking=no ec2-user@172.31.27.248 \
  "rm -f /tmp/pytest-<TICKET>.log && \
   nohup bash -c 'source /home/ec2-user/test_env.sh && \
     source /home/ec2-user/py3.13-virt/bin/activate && \
     cd /home/ec2-user/vscode/www && \
     PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest <test_paths> -v --noconftest; \
     echo PYTEST_DONE_EXIT=\$?' > /tmp/pytest-<TICKET>.log 2>&1 </dev/null & disown && echo backgrounded"
```

**2. Poll** (reconnect VPN if needed first via `~/eightfold/vpn-connect.sh -y`):
```bash
ssh -o ConnectTimeout=10 -i ~/eightfold/id_rsa -o StrictHostKeyChecking=no ec2-user@172.31.27.248 \
  "tail -30 /tmp/pytest-<TICKET>.log ; echo '---' ; pgrep -fa 'pytest.*<keyword>' || echo done"
```

**Completion signals:**
- `PYTEST_DONE_EXIT=N` line in the log → pytest finished, N = exit code
- `pgrep` returns no hits → process is gone

The `\$?` (escaped) captures pytest's exit code inside the inner bash -c. The bash escaping is critical — `$?` unescaped would expand in the outer shell, always to 0. Trailing `echo done` on the pgrep line ensures non-zero pgrep exit doesn't mask intent.
