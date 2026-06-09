---
name: efx
description: Use when running bash, python, or pytest on eightfold EC2 — the us-west-2 dev box or any region-specific prod box (eu-central-1, ca-central-1, …). Symptoms: "run this test on EC2", "ipython snippet on the dev box", "check customer X's data" (regional), "pssh shared-eu", VPN/ssh to 172.31.27.248, code that needs prod DB. Replaces run-on-ec2.
---

# efx — reliable remote execution on eightfold EC2

## Overview
`efx` is a CLI that runs commands/scripts on eightfold EC2 deterministically. It hides every failure mode of raw SSH (VPN drops, interactive-only `pssh`, env bootstrap, quoting across hops, gevent ordering). **Always use `efx`; do not hand-roll `ssh` to 172.31.27.248.**

Engine: `scripts/efx.py` (invoke directly — no wrapper) · cache: `.cache/cache.json` in this skill dir · design: `DESIGN.md`.

## When to use
- Run pytest / a python snippet / a bash command on the **dev box** (us-west-2).
- Run anything against a **region-specific** prod box / customer data (`shared-ca`=ca-central-1, `shared-eu`/`shared-eu-tm`=eu-central-1, …).
- Anything you'd previously SSH to `172.31.27.248` for, or reach with `pssh <cluster>`.

## Quick reference
Invoke the engine directly: `python3 ~/.claude/skills/efx/scripts/efx.py <subcommand>` (shown below as `efx`).
```
efx targets                                   # dev + known regional clusters
efx resolve <cluster> [--refresh]             # resolve+cache instance-id/host
efx exec --target T [--lang sh|py] [--branch B] -- 'CMD'   # sync; or pipe a script via stdin
efx submit --target T [--lang sh|py] [--branch B] -- 'CMD' # detached -> prints job_id
efx poll <T> <job_id> [--tail N]              # status + log tail
efx logs <T> <job_id>                         # full output
efx server start [--branch B] [--force] [--no-wait] [--timeout 420]  # start dev server, block until HTTP 302
efx server status|stop|logs                   # up/down (+exit code) · kill · tail server logs
```
`T` = `dev` or a cluster name. `--lang py` runs the payload as python3 (gevent-safe); default `sh`.

### Sync vs async
- **Short/medium:** `efx exec …`. To avoid blocking the session, run it via the Bash tool with `run_in_background: true`, then read the task output.
- **Long / VPN-flaky:** `efx submit …` → `efx poll …`. Job runs detached on the target (survives VPN drop / session restart).

## Recipes (absorbed from run-on-ec2)
**pytest** (vscode repo, runs on EC2 — never locally; deps are EC2-only):
```
efx exec --target dev -- 'PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest <path> -v --noconftest'
```
`efx` already `cd`s to `/home/ec2-user/vscode/www` and bootstraps the env. `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` + `--noconftest` avoid the boto/SSL/RecursionError boot failures. Trailing CloudWatch log error → harmless.

**python snippet** — pass `--lang py`; write it as a normal script. Import order that works:
```python
import sys; sys.path.insert(0, '/home/ec2-user/vscode/www')
from gevent import monkey; monkey.patch_all()   # FIRST, before any app import
# low-level utils -> user_login -> everything else
from user import user_login
```
Decode enc ids: `pr.decode_enc_id('Z5aZwdwjQV')` (`from profile import profile as pr`).

**Dev server** — start the local dev server reliably and confirm it's actually serving:
```
efx server start          # kills stale gunicorn, runs raw runserver.sh detached, polls to HTTP 302
efx server status         # UP/DOWN + HTTP code + gunicorn proc count (exit 1 if down)
```
`start` no-ops if already up (`--force` to restart), runs `MAX_RSS_SIZE_MB=3500 ./www/apps/runserver.sh` detached, and **blocks until HTTP 302** (or fails with the log tail). No `dev_start.sh` needed — efx's real global-DB env makes its DB-stub patches unnecessary. Run via Bash `run_in_background` if you don't want to wait through the cold start.

**Regional / customer data** — customer data is region-sharded. Pick the cluster in that region:
```
efx exec --target shared-eu-tm --lang py -- "..."   # eu-central-1 TM data
efx exec --target shared-ca   --lang py -- "..."    # ca-central-1
```
The dev box (us-west-2) cannot read another region's shard — use the regional target.

## What efx handles for you (don't re-derive)
- VPN: probes, auto `vpn-connect.sh -y` + retry. Never trust persistence across calls.
- `pssh`/`ssh.py` are interactive-only → efx resolves `pssh_config` itself on dev (global DB).
- Regional hop: dev → jump → regional, with the prod ssh keys + `COM_AWS` creds injected **before** login.
- Env bootstrap: sources `Dockerfile.shared.env` directly (the `.bashrc` interactive guard skips it; `test_env.sh` is the old workaround).
- Quoting: base64s every payload across the 3 ssh layers.
- `python3` (never `python`), venv activated.

## Common mistakes
| Mistake | Fix |
|---|---|
| Raw `ssh 172.31.27.248 "pytest …"` | Use `efx exec` (handles VPN/env/flags) |
| Running vscode pytest locally | EC2-only deps → `efx exec --target dev` |
| Reading regional customer data from `dev` | Use the regional cluster target |
| Long job over flaky VPN with `exec` | Use `submit`/`poll` |
| `python` on the box | efx uses `python3` + venv automatically |

## Details
Full architecture, cache TTLs, and root-cause notes: `DESIGN.md` in this skill dir.
