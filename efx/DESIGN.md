# efx — reliable remote execution for Claude Code

**Status:** spec → build · **Date:** 2026-06-10 · **Owner:** akshat.v

## Problem
Claude Code must run bash / python / pytest on eightfold EC2 boxes reliably and deterministically:
- the **dev box** (us-west-2, `ec2-user@172.31.27.248`), and
- **region-specific prod boxes** (eu-central-1, ca-central-1, …) reached by hopping dev → jump → regional.

Prior attempts (see `run-on-ec2` skill + history) failed on: VPN dropping across calls, interactive-only `pssh`/`ssh.py`, iTerm quote-stripping & races, gevent import deadlocks, `python` vs `python3`, the `.bashrc` interactive guard skipping env bootstrap, and `source | sed` subshell loss. All root-caused and fixed this session.

## Goal
One CLI, `efx`, that hides every gotcha behind deterministic subcommands, with a local TTL cache and an async submit/poll path that survives VPN drops. A companion skill makes it discoverable to Claude and replaces `run-on-ec2`.

## Form factor
- **CLI engine:** `~/.claude/efx/efx.py` (python3, single file) + PATH wrapper `~/.claude/bin/efx`.
- **Skill:** `~/.claude/skills/efx/SKILL.md` — when/how to use efx + the absorbed run-on-ec2 recipes. Retires `run-on-ec2`.
- **State:** `~/.claude/efx/cache.json`.

## Command surface
```
efx targets                                 # dev + known regional clusters (+ cached)
efx resolve <target> [--refresh]            # resolve & cache the chain; print it
efx exec --target T [--lang sh|py] [-- CMD] # sync exec; or script on stdin
efx submit --target T [--lang sh|py] [-- CMD]  # remote-detached -> prints job_id
efx poll <target> <job_id>                  # status + log tail (+ exit code when done)
efx logs <target> <job_id>                  # full captured output
```
- **Non-blocking short/medium:** Claude runs `efx exec …` via its own Bash `run_in_background`.
- **Robust long jobs:** `submit` → `poll` — job runs detached on the target (`nohup … & disown`), survives VPN drop / session restart.

## Targets
- `dev` — the us-west-2 dev box. No hop.
- any `pssh_config.HOSTNAME_DEV` cluster key (`shared-ca`, `shared-eu`, `shared-eu-tm`, …) — regional, hopped.

## Execution layers (all proven 2026-06-09/10)
**dev:** `local → dev`. Bootstrap: `source test_env.sh` (AWS creds) + `source Dockerfile.shared.env` (region, global DB, config). Then venv + payload.

**regional:** `local → dev → JUMP(ip-172-31-27-97.us-west-2.compute.internal) → regional`.
1. On dev, bootstrap → read `config.get('pssh_config')['HOSTNAME_DEV'][cluster]` → instance-id.
2. `ec2_utils.get_dns_from_instance_id(id)` → live hostname (iterates regions).
3. `boto_utils.secret(PROD_SSH_KEY, write_to_file=True)` → DEVKEY `/tmp/tmp.xxx`.
4. Hop: `ssh -i DEVKEY ec2-user@JUMP "ssh -i /home/ec2-user/.ssh/search-service-prod.pem REGIONAL '<payload>'"`.
5. On regional: `COM_AWS_*` creds in env **before** login; map → standard AWS creds; `AWS_DEFAULT_REGION` from IMDSv2; `WWWDIR`; activate `py3.13-virt`; `source Dockerfile.shared.env`; run payload.
6. **base64** every payload across the 3 quoting layers. **Never pipe `source`.**

## Cache (`~/.claude/efx/cache.json`)
| key | TTL | bust |
|---|---|---|
| cluster → instance-id | 24h | `--refresh` |
| instance-id → hostname | 1h | ssh fail → auto re-resolve once |
| DEVKEY | regenerated per regional run (cheap boto call); not cached |

VPN state never cached — always probe, auto `~/eightfold/vpn-connect.sh -y` on failure, retry.

## Error handling (auto-recover)
- SSH timeout / VPN down → connect + retry once.
- Stale hostname (ssh to regional fails) → `resolve --refresh` + retry once.
- DEVKEY missing on dev → regenerate.
- Standard pytest/py: always `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` (+ `--noconftest` for pytest).

## Pytest / ipython conventions (absorbed from run-on-ec2)
- pytest base `cd ~/vscode/www`; flags `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 --noconftest -v`.
- py snippet import order: `sys.path.insert(0,'…/www')` → `gevent.monkey.patch_all()` → low-level utils → `user_login` → rest.
- regional customer data: pick the cluster in that region (`shared-eu-tm` = eu-central-1 TM data).

## Non-goals (v1)
- Interactive REPL passthrough (iTerm). efx is for non-interactive exec.
- Auto-notify via harness background tasks (use Bash `run_in_background` + `poll`).
- Windows/azure targets.

## Verification plan
1. `efx targets`
2. `efx resolve shared-ca` → instance-id + host, cache written
3. `efx exec --target dev -- 'echo OK; hostname'`
4. `efx exec --target dev --lang py` (career-navigator probe) → DB read
5. `efx exec --target shared-ca --lang py` (region probe) → EF region ca-central-1 + DB_OK
6. `efx submit` + `efx poll` round-trip
7. second `resolve`/`exec` hits cache (fast, no re-resolution)
