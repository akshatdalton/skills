#!/usr/bin/env python3
"""
efx — reliable remote execution on eightfold EC2 (dev box + regional prod boxes).

Hides every gotcha root-caused in the run-on-ec2 investigation:
  - VPN dropping across calls            -> probe + auto vpn-connect.sh -y + retry
  - interactive-only pssh / ssh.py       -> resolve pssh_config ourselves on dev
  - .bashrc interactive guard skips env  -> source Dockerfile.shared.env explicitly
  - source | sed loses exports (subshell)-> never pipe source
  - creds must be in env BEFORE login    -> COM_AWS_*=... bash ...  (prefix, not pipe)
  - 3 nested quoting layers              -> base64 every payload across hops
  - python vs python3 / venv missing     -> activate py3.13-virt, call python3

Targets:
  dev                      -> the us-west-2 dev box
  <cluster> (shared-ca...) -> regional prod box, hopped dev->jump->regional

State/cache: ~/.claude/efx/cache.json
"""
import argparse
import base64
import json
import os
import subprocess
import sys
import time

# ---------------------------------------------------------------------------
# Constants (stable infra coordinates)
# ---------------------------------------------------------------------------
DEV_HOST = "ec2-user@172.31.27.248"
DEV_KEY = os.path.expanduser("~/eightfold/id_rsa")
JUMP = "ip-172-31-27-97.us-west-2.compute.internal"          # HOSTNAME_ADMIN['airflow']
INNER_KEY = "/home/ec2-user/.ssh/search-service-prod.pem"     # on jump box
VPN_CONNECT = os.path.expanduser("~/eightfold/vpn-connect.sh")

WWWDIR = "/home/ec2-user/vscode/www"
VENV = "/home/ec2-user/py3.13-virt/bin/activate"
TEST_ENV = "/home/ec2-user/test_env.sh"
SHARED_ENV = "/home/ec2-user/vscode/production/docker_configs/Dockerfile.shared.env"

# Cache lives inside the skill dir (parent of scripts/), in a .cache subdir.
_SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(_SKILL_DIR, ".cache")
CACHE_FILE = os.path.join(CACHE_DIR, "cache.json")
CLUSTER_TTL = 24 * 3600
HOST_TTL = 3600

SSH_OPTS = [
    "-o", "ConnectTimeout=15",
    "-o", "ServerAliveInterval=10",
    "-o", "ServerAliveCountMax=30",
    "-o", "StrictHostKeyChecking=no",
]
SSH_QUIET = ["-q", "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null"]


def log(*a):
    print("[efx]", *a, file=sys.stderr)


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------
def _load_cache():
    try:
        with open(CACHE_FILE) as f:
            return json.load(f)
    except Exception:
        return {"clusters": {}, "hosts": {}}


def _save_cache(c):
    os.makedirs(CACHE_DIR, exist_ok=True)
    tmp = CACHE_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(c, f, indent=2)
    os.replace(tmp, CACHE_FILE)


def _fresh(entry, ttl):
    return entry and (time.time() - entry.get("ts", 0)) < ttl


# ---------------------------------------------------------------------------
# Low-level SSH to the dev box (with VPN auto-recovery)
# ---------------------------------------------------------------------------
def _ssh_dev(remote_cmd, capture=True, _retried=False):
    """Run a command string on the dev box. Auto-connects VPN on timeout."""
    cmd = ["ssh", *SSH_OPTS, "-i", DEV_KEY, DEV_HOST, remote_cmd]
    r = subprocess.run(cmd, capture_output=capture, text=True)
    if (r.returncode == 255 and not _retried
            and r.stderr and ("Operation timed out" in r.stderr
                              or "Connection timed out" in r.stderr
                              or "No route to host" in r.stderr)):
        log("dev unreachable — bringing up VPN…")
        _vpn_connect()
        return _ssh_dev(remote_cmd, capture=capture, _retried=True)
    return r


def _vpn_connect():
    if not os.path.exists(VPN_CONNECT):
        log(f"WARNING: {VPN_CONNECT} not found; cannot auto-connect VPN")
        return
    subprocess.run([VPN_CONNECT, "-y"], capture_output=True, text=True)
    time.sleep(2)


def _b64(s: str) -> str:
    return base64.b64encode(s.encode()).decode()


# ---------------------------------------------------------------------------
# Dev-side bootstrap snippets
# ---------------------------------------------------------------------------
def _dev_bootstrap():
    # test_env.sh = AWS creds; Dockerfile.shared.env = region + global DB + config.
    # source directly (never pipe), redirect noise.
    return (
        f"source {TEST_ENV} >/dev/null 2>&1; "
        f"source {VENV} 2>/dev/null; "
        f"export WWWDIR={WWWDIR} AZURE_DEFAULT_REGION=westus2; "
        f"source {SHARED_ENV} >/dev/null 2>&1; "
        f"cd {WWWDIR}; "
    )


# Regional bootstrap, parameterised by nothing (region from IMDSv2 on the box).
REGIONAL_BOOTSTRAP = r"""
export AWS_ACCESS_KEY_ID="${COM_AWS_ACCESS_KEY_ID}"
export AWS_SECRET_ACCESS_KEY="${COM_AWS_SECRET_ACCESS_KEY}"
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 60" 2>/dev/null)
export AWS_DEFAULT_REGION=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/placement/region 2>/dev/null)
export AZURE_DEFAULT_REGION=westus2
export WWWDIR=/home/ec2-user/vscode/www
export PYTHON_VERSION=python3.13 PYTHON3_ENV_VERSION=3.13
source ~/py3.13-virt/bin/activate 2>/dev/null
export PYTHONPATH="${VIRTUAL_ENV}/lib/python3.13/dist-packages/:${VIRTUAL_ENV}/lib/python3.13/site-packages/:.:${HOME}/vscode/www:${HOME}/vscode/spark:${HOME}/vscode/production/lambda"
source /home/ec2-user/vscode/production/docker_configs/Dockerfile.shared.env >/dev/null 2>&1
cd /home/ec2-user/vscode/www
"""


def _payload_cmd(lang, payload_b64):
    """Bash that decodes the user payload and runs it (sh or py)."""
    if lang == "py":
        return (f'echo {payload_b64} | base64 -d > /tmp/efx_payload.py; '
                f'PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 /tmp/efx_payload.py')
    return (f'echo {payload_b64} | base64 -d > /tmp/efx_payload.sh; '
            f'bash /tmp/efx_payload.sh')


# ---------------------------------------------------------------------------
# Resolution (cluster -> instance-id -> hostname), done on the dev box
# ---------------------------------------------------------------------------
RESOLVER_PY = r"""
import sys, json
sys.path.insert(0, '/home/ec2-user/vscode/www')
from gevent import monkey; monkey.patch_all()
try:
    import glog as log; log.setLevel(log.ERROR)
except Exception: pass
cluster = sys.argv[1]
out = {}
try:
    from config import config
    from utils import ec2_utils
    pc = config.get('pssh_config') or {}
    hd = pc.get('HOSTNAME_DEV', {}) if isinstance(pc, dict) else {}
    iid = hd.get(cluster)
    out['instance_id'] = iid
    if iid and iid.startswith('i-'):
        # instance lives in its own region — iterate all regions like ssh.py
        try:
            from utils import os_constants
            regions = os_constants.EF_SUPPORTED_REGIONS.split()
        except Exception:
            import os as _os
            regions = (_os.getenv('AWS_ALL_REGIONS') or
                       'us-west-2 eu-central-1 ca-central-1 us-gov-west-1 ap-southeast-2').split()
        host = None
        for r in regions:
            try:
                host = ec2_utils.get_dns_from_instance_id(iid, region=r)
                if host:
                    out['region'] = r
                    break
            except Exception:
                continue
        out['hostname'] = host
        if not host:
            out['error'] = 'instance %s not found in regions %s' % (iid, regions)
    else:
        out['hostname'] = iid
except Exception as e:
    out['error'] = repr(e)[:300]
print('EFX_RESOLVE=' + json.dumps(out))
"""


def _resolve_on_dev(cluster):
    snippet = RESOLVER_PY.replace("sys.argv[1]", repr(cluster))
    b = _b64(snippet)
    cmd = (_dev_bootstrap()
           + f'echo {b} | base64 -d > /tmp/efx_resolve.py; '
           + 'PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 /tmp/efx_resolve.py 2>/dev/null')
    r = _ssh_dev(cmd)
    for line in (r.stdout or "").splitlines():
        if line.startswith("EFX_RESOLVE="):
            return json.loads(line[len("EFX_RESOLVE="):])
    raise SystemExit(f"resolve failed for {cluster}: {(r.stdout or '')[-400:]}\n{(r.stderr or '')[-400:]}")


def resolve(cluster, refresh=False):
    """Return {instance_id, hostname}, using/refreshing the local cache."""
    cache = _load_cache()
    cl = cache["clusters"].get(cluster)
    if not refresh and _fresh(cl, CLUSTER_TTL):
        iid = cl["instance_id"]
        h = cache["hosts"].get(iid)
        if _fresh(h, HOST_TTL):
            return {"instance_id": iid, "hostname": h["hostname"], "cached": True}

    info = _resolve_on_dev(cluster)
    if info.get("error") or not info.get("instance_id"):
        raise SystemExit(f"resolve error for {cluster}: {info.get('error', 'no instance-id')}")
    now = time.time()
    cache["clusters"][cluster] = {"instance_id": info["instance_id"], "ts": now}
    cache["hosts"][info["instance_id"]] = {"hostname": info["hostname"], "ts": now}
    _save_cache(cache)
    return {"instance_id": info["instance_id"], "hostname": info["hostname"], "cached": False}


# ---------------------------------------------------------------------------
# Build the remote command for a payload on a given target
# ---------------------------------------------------------------------------
def _git_sync(branch):
    """Foreground checkout+pull of a branch on the box before running the payload."""
    if not branch:
        return ""
    return (f"cd /home/ec2-user/vscode && git fetch origin >/dev/null 2>&1 && "
            f"git checkout {branch} 2>&1 | tail -1 && git pull 2>&1 | tail -1; ")


def _dev_command(lang, payload_b64, detached=None, branch=None):
    inner = _git_sync(branch) + _payload_cmd(lang, payload_b64)
    if detached:
        job, logf = detached["job"], detached["log"]
        envf = f"/tmp/efx_env_{job}.sh"
        # Bootstrap FOREGROUND (Dockerfile.shared.env hangs if its process group
        # is backgrounded), dump the resolved env, then detach a payload that
        # only sources the cheap env dump — no Dockerfile.shared.env in the
        # backgrounded group, so no hang.
        body = (f"{_dev_bootstrap()}"
                f"export -p > {envf} 2>/dev/null; "
                f"rm -f {logf}; "
                f"nohup bash -c 'source {envf} 2>/dev/null; {inner}; echo EFX_EXIT=$?' "
                f"> {logf} 2>&1 </dev/null & disown; echo {job}")
        return body
    return _dev_bootstrap() + inner


def _regional_command(hostname, lang, payload_b64, detached=None, branch=None):
    """Full dev-side string that hops to the regional box and runs the payload."""
    inner = _git_sync(branch) + _payload_cmd(lang, payload_b64)
    if detached:
        job, logf = detached["job"], detached["log"]
        envf = f"/tmp/efx_env_{job}.sh"
        # Bootstrap FOREGROUND on the regional box, dump env, then detach a
        # payload sourcing only the cheap dump (Dockerfile.shared.env hangs if
        # its process group is backgrounded — same fix as dev).
        regional_script = (
            REGIONAL_BOOTSTRAP + "\n"
            + f"export -p > {envf} 2>/dev/null\n"
            + f"rm -f {logf}\n"
            + f"nohup bash -c 'source {envf} 2>/dev/null; {inner}; echo EFX_EXIT=$?' "
              f"> {logf} 2>&1 </dev/null & disown\n"
            + f"echo {job}\n"
        )
    else:
        regional_script = REGIONAL_BOOTSTRAP + "\n" + inner + "\n"
    rs_b64 = _b64(regional_script)

    # Wrapper on the regional box: decode script, run FOREGROUND with COM creds
    # in env at start.  (For detached jobs the script self-detaches the payload.)
    regional_wrap = (
        f"echo {rs_b64} | base64 -d > /tmp/efx_regional.sh; "
        f"COM_AWS_ACCESS_KEY_ID=$COM_AWS_ACCESS_KEY_ID "
        f"COM_AWS_SECRET_ACCESS_KEY=$COM_AWS_SECRET_ACCESS_KEY bash /tmp/efx_regional.sh"
    )
    rw_b64 = _b64(regional_wrap)

    # Dev-side script: source test_env (creds), get DEVKEY, hop to jump->regional.
    # COM creds are the dev box's AWS creds; export them so the regional shell
    # inherits them through the nested ssh env.  We push them on the inner ssh
    # via a creds-prefixed remote command (decoded from base64 on regional).
    dev_side = f"""
source {TEST_ENV} >/dev/null 2>&1
source {VENV} 2>/dev/null
export WWWDIR={WWWDIR}
DEVKEY=$(PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -c "
import sys; sys.path.insert(0,'{WWWDIR}')
from gevent import monkey; monkey.patch_all()
from utils import boto_utils
from utils.boto_constants import Secrets
print(boto_utils.secret(Secrets.PROD_SSH_KEY, write_to_file=True))
" 2>/dev/null)
ssh {' '.join(SSH_QUIET)} -i "$DEVKEY" ec2-user@{JUMP} \
  "ssh {' '.join(SSH_QUIET)} -i {INNER_KEY} {hostname} \
  'COM_AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID COM_AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY bash -c \\"echo {rw_b64} | base64 -d | bash\\"'"
"""
    return dev_side


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
def _read_payload(args):
    if args.cmd:
        body = " ".join(args.cmd)
        if args.lang == "py":
            return body  # treat as python source line(s)
        return body
    data = sys.stdin.read()
    if not data:
        raise SystemExit("no command given (-- CMD) and stdin empty")
    return data


def cmd_targets(args):
    cache = _load_cache()
    print("dev")
    known = ["shared-ca", "shared-eu", "shared-eu-tm"]
    for k in known:
        print(k)
    extra = [c for c in cache.get("clusters", {}) if c not in known]
    for c in sorted(extra):
        print(c)
    print("\n(any pssh_config HOSTNAME_DEV cluster key is a valid --target)", file=sys.stderr)


def cmd_resolve(args):
    info = resolve(args.target, refresh=args.refresh)
    print(json.dumps(info, indent=2))


def cmd_exec(args):
    payload = _read_payload(args)
    pb = _b64(payload)
    branch = getattr(args, "branch", None)
    if args.target == "dev":
        remote = _dev_command(args.lang, pb, branch=branch)
    else:
        info = resolve(args.target)
        remote = _regional_command(info["hostname"], args.lang, pb, branch=branch)
    r = _ssh_dev(remote, capture=True)
    sys.stdout.write(r.stdout or "")
    if r.stderr:
        sys.stderr.write(r.stderr)
    sys.exit(r.returncode)


def _job_id():
    # deterministic-ish unique id without Date.now/random restrictions
    return "job_" + base64.b32encode(os.urandom(5)).decode().lower().rstrip("=")


def cmd_submit(args):
    payload = _read_payload(args)
    pb = _b64(payload)
    job = _job_id()
    logf = f"/tmp/efx_{job}.log"
    det = {"job": job, "log": logf}
    branch = getattr(args, "branch", None)
    if args.target == "dev":
        remote = _dev_command(args.lang, pb, detached=det, branch=branch)
        r = _ssh_dev(remote, capture=True)
    else:
        info = resolve(args.target)
        remote = _regional_command(info["hostname"], args.lang, pb, detached=det, branch=branch)
        r = _ssh_dev(remote, capture=True)
    out = (r.stdout or "").strip()
    if job not in out:
        sys.stderr.write(out + "\n" + (r.stderr or ""))
        raise SystemExit("submit failed")
    print(job)
    print(f"poll with: efx poll {args.target} {job}", file=sys.stderr)


def _poll_remote_cmd(target, job, tail):
    logf = f"/tmp/efx_{job}.log"
    inner = (f"if [ -f {logf} ]; then tail -{tail} {logf}; echo '---EFX---'; "
             f"grep -q EFX_EXIT= {logf} && echo STATUS=DONE || echo STATUS=RUNNING; "
             f"else echo STATUS=NOLOG; fi")
    if target == "dev":
        return inner
    # regional: the log lives on the regional box -> need to hop to read it
    info = resolve(target)
    rb = _b64(inner)
    return f"""
source {TEST_ENV} >/dev/null 2>&1
source {VENV} 2>/dev/null
DEVKEY=$(PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -c "
import sys; sys.path.insert(0,'{WWWDIR}')
from gevent import monkey; monkey.patch_all()
from utils import boto_utils
from utils.boto_constants import Secrets
print(boto_utils.secret(Secrets.PROD_SSH_KEY, write_to_file=True))
" 2>/dev/null)
ssh {' '.join(SSH_QUIET)} -i "$DEVKEY" ec2-user@{JUMP} \
  "ssh {' '.join(SSH_QUIET)} -i {INNER_KEY} {info['hostname']} 'echo {rb} | base64 -d | bash'"
"""


def cmd_poll(args):
    remote = _poll_remote_cmd(args.target, args.job, tail=args.tail)
    r = _ssh_dev(remote, capture=True)
    sys.stdout.write(r.stdout or "")
    if r.stderr:
        sys.stderr.write(r.stderr)


def cmd_logs(args):
    args.tail = 100000
    cmd_poll(args)


# ---------------------------------------------------------------------------
# Dev server mode (us-west-2 dev box)
# ---------------------------------------------------------------------------
SERVER_PORT = 8000
SERVER_LOG = "/tmp/efx_server.log"   # efx-captured runserver output
APP_LOGS = "/tmp/runserver.log /tmp/apps.logs"  # runserver's own logs


def _curl_code(port=SERVER_PORT):
    r = _ssh_dev(
        f"curl -s -o /dev/null -w '%{{http_code}}' --max-time 6 http://localhost:{port}/ 2>/dev/null"
    )
    return ((r.stdout or "").strip()[-3:]) or "000"


def _server_payload(branch=None, react_hot=None):
    parts = ["cd /home/ec2-user/vscode"]
    if branch:
        parts.append(f"git fetch origin >/dev/null 2>&1; git checkout {branch} 2>&1 | tail -1; git pull 2>&1 | tail -1")
    # runserver.sh kills its own old gunicorn, but be explicit/idempotent:
    parts.append("pkill -9 -f gunicorn 2>/dev/null; pkill -9 -f runserver.sh 2>/dev/null; sleep 1")
    rs = "MAX_RSS_SIZE_MB=3500 ./www/apps/runserver.sh"
    if react_hot:
        rs += f" --react_hot_url {react_hot}"
    parts.append(rs)
    return " ; ".join(parts)


def cmd_server(args):
    if args.action == "status":
        code = _curl_code()
        r = _ssh_dev("pgrep -fc gunicorn || echo 0")
        workers = (r.stdout or "0").strip()
        up = code in ("302", "200")
        print(f"{'UP' if up else 'DOWN'}  HTTP={code}  gunicorn_procs={workers}")
        sys.exit(0 if up else 1)

    if args.action == "stop":
        r = _ssh_dev("pkill -9 -f gunicorn 2>/dev/null; pkill -9 -f runserver.sh 2>/dev/null; "
                     "sleep 1; pgrep -fc gunicorn || echo 0")
        print("stopped (gunicorn procs left:", (r.stdout or "?").strip() + ")")
        return

    if args.action == "logs":
        r = _ssh_dev(f"tail -n {args.tail} {SERVER_LOG} {APP_LOGS} 2>/dev/null")
        sys.stdout.write(r.stdout or "")
        return

    # action == "start"
    code = _curl_code()
    if code in ("302", "200") and not args.force:
        print(f"already UP  HTTP={code}  (use --force to restart)")
        return
    payload = _server_payload(args.branch, args.react_hot_url)
    job = _job_id()
    det = {"job": job, "log": SERVER_LOG}
    remote = _dev_command("sh", _b64(payload), detached=det)
    r = _ssh_dev(remote, capture=True)
    if job not in (r.stdout or ""):
        sys.stderr.write((r.stdout or "") + "\n" + (r.stderr or ""))
        raise SystemExit("server launch failed")
    log(f"runserver launched (job {job}); polling http://localhost:{SERVER_PORT}/ up to {args.timeout}s…")
    if args.no_wait:
        print(job)
        return
    deadline = time.time() + args.timeout
    while time.time() < deadline:
        code = _curl_code()
        if code in ("302", "200"):
            wk = (_ssh_dev("pgrep -fc gunicorn || echo 0").stdout or "?").strip()
            print(f"SERVER UP  HTTP={code}  gunicorn_procs={wk}  log={SERVER_LOG}")
            return
        log(f"warming… HTTP={code}")
        time.sleep(10)
    # timed out — surface tail of logs for diagnosis
    tail = _ssh_dev(f"tail -n 25 {SERVER_LOG} {APP_LOGS} 2>/dev/null").stdout or ""
    sys.stderr.write(tail)
    raise SystemExit(f"server did not reach 302 within {args.timeout}s (last HTTP={code})")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    p = argparse.ArgumentParser(prog="efx", description="reliable remote execution on eightfold EC2")
    sub = p.add_subparsers(dest="sub", required=True)

    sp = sub.add_parser("targets", help="list targets")
    sp.set_defaults(func=cmd_targets)

    sp = sub.add_parser("resolve", help="resolve+cache a target's chain")
    sp.add_argument("target")
    sp.add_argument("--refresh", action="store_true")
    sp.set_defaults(func=cmd_resolve)

    for name, fn, helptxt in [("exec", cmd_exec, "run sync"),
                              ("submit", cmd_submit, "run detached, print job id")]:
        sp = sub.add_parser(name, help=helptxt)
        sp.add_argument("--target", required=True)
        sp.add_argument("--lang", choices=["sh", "py"], default="sh")
        sp.add_argument("--branch", help="git fetch+checkout+pull this branch on the box first")
        sp.add_argument("cmd", nargs="*", help="command/source; or pipe via stdin")
        sp.set_defaults(func=fn)

    sp = sub.add_parser("poll", help="poll a submitted job")
    sp.add_argument("target")
    sp.add_argument("job")
    sp.add_argument("--tail", type=int, default=30)
    sp.set_defaults(func=cmd_poll)

    sp = sub.add_parser("logs", help="full job output")
    sp.add_argument("target")
    sp.add_argument("job")
    sp.set_defaults(func=cmd_logs)

    sp = sub.add_parser("server", help="dev server: start (poll to 302) / status / stop / logs")
    sp.add_argument("action", choices=["start", "status", "stop", "logs"])
    sp.add_argument("--branch", help="git checkout this branch first (default: leave current)")
    sp.add_argument("--react-hot-url", dest="react_hot_url", default=None,
                    help="pass --react_hot_url to runserver.sh (default: omit)")
    sp.add_argument("--timeout", type=int, default=420, help="seconds to wait for 302 (start)")
    sp.add_argument("--no-wait", action="store_true", help="launch and return immediately (start)")
    sp.add_argument("--force", action="store_true", help="restart even if already up (start)")
    sp.add_argument("--tail", type=int, default=40, help="lines for logs")
    sp.set_defaults(func=cmd_server)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
