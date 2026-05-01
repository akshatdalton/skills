---
name: test-live-api
description: Test HTTP endpoints against the live dev server on akshat-v.dev.eightfold.ai. Covers server startup, Bearer token auth + CSRF seeding, executing API sequences with assertions, and producing a tabular test report. Use when you need HTTP-level integration testing of new or changed endpoints — distinct from /run-on-ec2 (pytest, no live server) and /debug-api (Python code tracing).
---

# Test Live API

Tests HTTP endpoints against `https://akshat-v.dev.eightfold.ai`. Produces a tabular test report.

**Distinct from:**
- `/run-on-ec2` — runs pytest on EC2; no live server required
- `/debug-api` — traces failing Python code; no HTTP calls

---

## Quick start: given a curl from DevTools

If the user provides a curl command (e.g. copied from browser Network tab), **skip the phase flow and go directly to Option C**. Parse the curl first:

```
curl 'https://<host>/api/<path>?domain=<group>' \
  -H 'x-ef-group-id: <group_id>' \
  --data-raw '{"data": {...}}'
```

Extract:
- **endpoint path**: everything after the host — e.g. `/api/career_hub/v1/action/position/12345/favorite`
- **group_id / DOMAIN**: from `?domain=` param OR `x-ef-group-id` header, whichever is present
- **request body**: from `--data-raw` or `-d`
- **user email**: ask the user — "Which email should I use for `<group_id>`?" if not obvious from context

Then build the Option C script with those values. **Do not attempt curl-to-curl translation** — always convert to the Python requests pattern.

**⚠️ Option C requires NO running server** — it runs Python directly on EC2, hitting `localhost:8000` from within the EC2 process. Skip Phase 0 entirely when using Option C.

---

## Pre-entry: project-context contract (mandatory)

On entry, invoke `Skill(skill="project-context", args="branch:read")` first. Surface one-line `↳ loaded ...` or `↳ no context yet`.

After any material finding (auth detail, endpoint behaviour, bug), invoke `Skill(skill="project-context", args="branch:update <one-liner>")`.

---

## Phase 0 — Start the Live Server (if not running)

Check first:
```bash
ssh -i ~/eightfold/id_rsa -o ConnectTimeout=5 ec2-user@172.31.27.248 \
  "curl -s http://localhost:8000/api/tether/v1/agents/ | head -c 50"
```
If connection refused → server is down. If redirect to /login → server is up, skip to Phase 1.

### Pull branch and kill stale processes
```bash
ssh -i ~/eightfold/id_rsa ec2-user@172.31.27.248 \
  "cd /home/ec2-user/vscode && \
   git fetch origin && git checkout <branch> && git pull && \
   pkill -9 -f runserver; pkill -9 -f gunicorn; echo killed"
```

### Required EC2 temp patches (apply before starting)

These patches are NOT committed — apply to the live EC2 files each time after pulling a fresh branch. They fix dev-environment-specific failures that don't affect production.

**1. `test_env.sh` — add missing env vars:**
```bash
ssh -i ~/eightfold/id_rsa ec2-user@172.31.27.248 "cat >> /home/ec2-user/test_env.sh << 'EOF'
export REDIS_CLUSTER_DEV_URI=red1k2ybk2jy5de0.lspxxu.clustercfg.usw2.cache.amazonaws.com
export VS_STATIC_CDN=https://static.vscdn.net
EOF"
```
- `REDIS_CLUSTER_DEV_URI` — without it, `runserver.sh:110` zeroes out `REDIS_CLUSTER_URI` → empty Redis host → worker crash
- `VS_STATIC_CDN` — `before_request` calls `os.getenv('VS_STATIC_CDN').strip('/')` → AttributeError if unset. Interactive shell gets this from `dotfiles/.bashrc` sourcing `Dockerfile.shared.env`; `test_env.sh` does not.

**2. `runserver.sh` — remove `--reload` flag:**
```bash
ssh -i ~/eightfold/id_rsa ec2-user@172.31.27.248 \
  "sed -i 's/--reload --worker-class/--worker-class/' /home/ec2-user/vscode/www/apps/runserver.sh"
```
`--reload` watches Python files. Any file change (including our other patches) triggers worker restarts → restart loop.

**3. `config/config.py` — patch `cannot_edit_config` and `_get_config`:**
```bash
ssh -i ~/eightfold/id_rsa ec2-user@172.31.27.248 "cat > /tmp/patch_config.py << 'PYEOF'
import re

path = '/home/ec2-user/vscode/www/config/config.py'
src = open(path).read()

# Patch 1: cannot_edit_config — skip global DB reentrancy check
old = '''def cannot_edit_config(namespace='', json_data=None):'''
# Find the function and replace its body to return False
src = re.sub(
    r\"(def cannot_edit_config\\([^)]*\\):[\\s\\S]*?)\\n(\\s*def )\",
    lambda m: 'def cannot_edit_config(namespace=\\'\\', json_data=None):\\n    return False  # dev patch\\n\\n\\g<2>',
    src, count=1
)

# Patch 2: _get_config — return default when global DB unavailable (in except block near end)
src = src.replace(
    \"            raise\\n\",
    \"            return default  # dev patch: global DB unavailable\\n\",
    1
)

open(path, 'w').write(src)
print('config.py patched')
PYEOF
python3 /tmp/patch_config.py"
```

Alternatively, apply manually:
- `cannot_edit_config` body → `return False  # dev patch`
- In `_get_config` except block (near line 585), change `raise` → `return default  # dev patch`

**4. `utils/flask_utils.py` — fix `subdomain_mapping = None` crash:**
```bash
ssh -i ~/eightfold/id_rsa ec2-user@172.31.27.248 \
  "sed -i 's/subdomain_mapping = config.get(.subdomain_mapping.)/subdomain_mapping = config.get(\"subdomain_mapping\") or {}/' \
   /home/ec2-user/vscode/www/utils/flask_utils.py"
```
`config.get('subdomain_mapping')` returns None when the global DB is patched to return defaults. `subdomain in None` → TypeError. `or {}` makes it safe. Without this, `?domain=` param is ignored and group_id falls back to `volkscience.com`.

**5. `utils/redis_utils.py` + `utils/counters.py` — break recursive crash on first start:**

These are only needed if workers crash on first start with a Redis recursion error. Check `/tmp/apps.logs` first; if no recursion errors, skip.

```bash
ssh -i ~/eightfold/id_rsa ec2-user@172.31.27.248<< 'EOF'
# redis_utils.py: wrap counters.add in _handle_error
python3 -c "
p='/home/ec2-user/vscode/www/utils/redis_utils.py'
s=open(p).read()
s=s.replace('counters.add(', 'try:\n        counters.add(', 1)
# only patch the first occurrence in _handle_error
open(p,'w').write(s)
print('redis_utils patched')
"

# counters.py: set whitelist defaults before Redis lookup
python3 -c "
p='/home/ec2-user/vscode/www/utils/counters.py'
s=open(p).read()
# Patch at class/module level near top of get_breakdown_config
open(p,'w').write(s)
print('counters patched')
"
EOF
```

### Start server

For API-only testing (no browser, Bearer token auth): **omit `--react_hot_url`**. That flag points gunicorn at a local webpack hot server on the Mac; it's only needed when also running FE locally. Since Bearer token + CSRF seeding works without a browser, skip it.

```bash
ssh -i ~/eightfold/id_rsa ec2-user@172.31.27.248 \
  "nohup bash -c 'source /home/ec2-user/test_env.sh && \
    source /home/ec2-user/py3.13-virt/bin/activate && \
    cd /home/ec2-user/vscode && \
    MAX_RSS_SIZE_MB=3500 ./www/apps/runserver.sh' \
    > /tmp/runserver.log 2>&1 </dev/null & disown && echo started"
```

**Key flags:**
- `MAX_RSS_SIZE_MB=3500` — caps memory so a single worker doesn't OOM a t2.large
- `</dev/null` + `& disown` — survives SSH session close

**Monitor startup:**
```bash
ssh -i ~/eightfold/id_rsa ec2-user@172.31.27.248 "tail -50 /tmp/runserver.log"
```

Watch for these lines — they appear together and signal gunicorn is about to bind:
```
Starting server..
Starting with num workers: 2
Running gunicorn -c /home/ec2-user/vscode/production/docker_configs/gunicorn_config.py --reuse-port ...
```
**APIs are available ~20 seconds after these lines appear.** No need to wait for individual worker PIDs.

**If server loops with exit code 3** (app import failure — gunicorn hides the traceback):
```bash
ssh -i ~/eightfold/id_rsa ec2-user@172.31.27.248 \
  "source /home/ec2-user/test_env.sh && \
   source /home/ec2-user/py3.13-virt/bin/activate && \
   cd /home/ec2-user/vscode/www && \
   python3 -c 'from apps.runserver import app; print(\"app boot OK\")' 2>&1 | tail -20"
```
This prints the exact traceback that gunicorn hides.

---

## Phase 1 — Auth Setup

**⚠️ ALWAYS notify the user before running live server tests:**
> "Running live tests on `https://akshat-v.dev.eightfold.ai` as `<user>@<group>.com`. Continue?"

Three options — prefer Option A (scriptable) or Option C (Python requests, most direct for localhost).

### Option A — Bearer token + curl (against public URL)

Generate from EC2 using `auth_utils`:

```bash
TOKEN=$(ssh -i ~/eightfold/id_rsa ec2-user@172.31.27.248 \
  "source /home/ec2-user/test_env.sh && \
   source /home/ec2-user/py3.13-virt/bin/activate && \
   cd /home/ec2-user/vscode/www && python3 << 'EOF'
import sys; sys.path.insert(0, '/home/ec2-user/vscode/www')
from gevent import monkey; monkey.patch_all()
import glog as log; log.setLevel(log.ERROR)
import config.config as config_module
_orig_get_config = config_module._get_config
def _safe_get_config(config_name, field_name=None, default=None, skip_cache=False):
    try:
        return _orig_get_config(config_name, field_name=field_name, default=default, skip_cache=skip_cache)
    except Exception:
        return default
config_module._get_config = _safe_get_config
import utils.auth_utils as auth_utils
auth_utils._get_session_max_length = lambda g: 7 * 86400
from user.user_login import get_by_email
u = get_by_email('USER@GROUP.com', group_id='GROUP.com')
print(auth_utils.generate_auth_token(u))
EOF
2>/dev/null")
echo "TOKEN: ${TOKEN:0:20}..."
```

**Why two patches are needed:**
- `_get_session_max_length` patch: `generate_auth_token` reads token TTL from global DB. Patching returns 7 days directly.
- `config._get_config` patch: `get_by_email` calls lookups that hit the global DB. Patching returns default on failure.

If `get_by_email` returns None after patching: retry up to 3×.

Token TTL: 7 days. Regenerate if server redirects to /login.

**Seed session + capture CSRF (required for POST/PATCH, even with Bearer):**

```bash
BASE="https://akshat-v.dev.eightfold.ai"
COOKIEJAR=/tmp/ef_test_cookies.txt

CSRF=$(curl -si "${BASE}/api/tether/v1/agents/" \
  -H "Authorization: Bearer ${TOKEN}" \
  -c "${COOKIEJAR}" -b "${COOKIEJAR}" \
  | grep -i 'x-csrf-token:' | awk '{print $2}' | tr -d '\r')
echo "CSRF: ${CSRF}"
```

CSRF tokens are bound to the `_vs` session cookie. **Refresh CSRF before every POST/PATCH.**

### Option B — Browser session

1. Open `https://akshat-v.dev.eightfold.ai` and log in
2. DevTools → Network → any XHR → copy `Cookie` header + `x-csrf-token` response header
3. Use `-H "Cookie: ${COOKIE}"` instead of Bearer + cookie jar in all curl calls

### Option C — Python requests on EC2 (recommended for localhost direct testing)

This approach runs Python on EC2, imports the user directly (same as `/debug-api`), and uses `requests.Session()` to hit `localhost:8000`. Avoids CloudFront routing issues entirely.

**Does NOT require a running server** — Python accesses the DB and generates auth tokens directly. The only thing that must be running is the gunicorn server to receive the HTTP requests on port 8000.

**Deriving user + group from a curl:**
- `group_id` / `DOMAIN`: use `x-ef-group-id` header or `?domain=` param from the curl
- `email`: ask the user if not stated — e.g. "Which email for `volkscience.com`?" Common: `akshat.v@eightfold.ai` for `volkscience.com`, `demo@eightfolddemo-samyak4.com` for `eightfolddemo-samyak4.com`

**Verify EC2 patches before running** (quick check — takes 5 seconds):
```bash
ssh -i ~/eightfold/id_rsa ec2-user@172.31.27.248 \
  "grep -c 'dev patch' /home/ec2-user/vscode/www/config/config.py && \
   grep -c 'or {}' /home/ec2-user/vscode/www/utils/flask_utils.py && \
   grep -c 'REDIS_CLUSTER_DEV_URI' /home/ec2-user/test_env.sh && \
   grep -c 'VS_STATIC_CDN' /home/ec2-user/test_env.sh"
```
Expected: `2`, `1`, `1`, `1`. Any `0` → apply the corresponding patch from Phase 0 before proceeding.

**Critical: `_vs` Secure cookie fix.** The server sets the `_vs` session cookie with `Secure=True`. Python's `requests` library correctly withholds secure cookies over plain HTTP (`localhost:8000`). If not fixed, every POST gets a fresh vs_cookie → CSRF `sha1(old_vs) ≠ sha1(new_vs)` → "Please reload" 400.

**How CSRF works in Eightfold** (see `index_view.py:593-620`):
- CSRF = `URLSafeTimedSerializer(PROD_CSRF_key, PROD_CSRF_salt).dumps(sha1(vs_cookie))`
- Validation: decode CSRF token → compare decoded sha1 with `sha1(g.vs_cookie)` for the current request
- `g.vs_cookie` comes from the `_vs` cookie sent in the request (or freshly generated if absent)
- If `_vs` not sent → fresh vs_cookie ≠ old vs_cookie → CSRF always invalid

**Template script** (`/tmp/test_endpoints.py` on EC2):

```python
import sys, re
sys.path.insert(0, '/home/ec2-user/vscode/www')

# Patch config before any other import — avoids global DB failures
import config.config as config_module
_orig = config_module._get_config
def _safe(n, field_name=None, default=None, skip_cache=False):
    try:
        return _orig(n, field_name=field_name, default=default, skip_cache=skip_cache)
    except Exception:
        return default
config_module._get_config = _safe

from gevent import monkey; monkey.patch_all()
import glog as log; log.setLevel(log.ERROR)
from utils import regex_utils, list_utils
from user import user_login
import utils.auth_utils as auth_utils
auth_utils._get_session_max_length = lambda g: 7 * 86400

ul = user_login.get_by_email('USER@GROUP.com', group_id='GROUP.com')
if ul is None:
    print('ERROR: user not found'); sys.exit(1)
token = auth_utils.generate_auth_token(ul)

import requests
BASE = 'http://localhost:8000'
DOMAIN = 'GROUP.com'
H = {'Authorization': 'Bearer ' + token}

def get_fresh_csrf():
    """Return (session, csrf) with _vs cookie properly set."""
    s = requests.Session()
    # Any endpoint works for seeding — 404s are fine, just need before_request to run
    r = s.get(BASE + '/api/career_hub/v1/user_profile', params={'domain': DOMAIN}, headers=H)

    # Extract _vs from Set-Cookie header (secure=True blocks automatic re-sending over HTTP)
    vs_val = None
    for cookie in r.cookies:
        if cookie.name == '_vs':
            vs_val = cookie.value; break
    if not vs_val:
        m = re.search(r'_vs=([^;]+)', r.headers.get('Set-Cookie', ''))
        if m:
            vs_val = m.group(1)

    if vs_val:
        s.cookies['_vs'] = vs_val  # force-add without Secure restriction

    # Second GET: session now sends _vs → server returns a CSRF that matches
    r2 = s.get(BASE + '/api/career_hub/v1/user_profile', params={'domain': DOMAIN}, headers=H)
    csrf = r2.headers.get('x-csrf-token', '') or r.headers.get('x-csrf-token', '')
    return s, csrf

# Example: POST mutation
s, csrf = get_fresh_csrf()
post_h = {**H, 'x-csrf-token': csrf, 'Content-Type': 'application/json'}
resp = s.post(
    BASE + '/api/career_hub/v1/action/project/39106647/favorite',
    params={'domain': DOMAIN},
    headers=post_h,
    json={'data': {'is_favorited': False}}
)
print(resp.status_code, resp.text[:300])
```

**Run on EC2:**
```bash
scp -i ~/eightfold/id_rsa /tmp/test_endpoints.py ec2-user@172.31.27.248:/tmp/test_endpoints.py
ssh -i ~/eightfold/id_rsa ec2-user@172.31.27.248 \
  "source /home/ec2-user/test_env.sh && \
   source /home/ec2-user/py3.13-virt/bin/activate && \
   cd /home/ec2-user/vscode/www && \
   python3 /tmp/test_endpoints.py 2>/tmp/test_endpoints_err.log"
```

**Why the seed endpoint can be 404:** `before_request` runs for all routes (including 404) and sets the session. Any endpoint is sufficient to seed the `_vs` cookie. Use a 404 path to avoid triggering application errors that might regenerate the session in the error handler.

**⚠️ Avoid seed endpoints that return 500:** A 500 error handler may regenerate the session (new vs_cookie), making the CSRF generated at `before_request` time inconsistent with the Set-Cookie sent in the error response. 404 is safe; 500 is not.

---

## Phase 2 — Pre-test State Capture

Before running mutations:

1. **List current state** — GET the relevant resource listing endpoints; note what currently exists and what is active/enabled.
2. **Check exclusivity constraints** — if the resource type has an only-one-active rule (e.g., only one `manager_agent` enabled at a time), identify which entities are currently enabled.
3. **Disable conflicting entities** — PATCH each conflicting entity to its inactive/disabled state. Verify via GET that state is clean before proceeding.
4. **Note pre-test baseline** — record entity counts and states so you can verify they change as expected and restore them in Phase 6.

---

## Phase 3 — Execute API Sequence

Run calls in order. Log method, path, key request fields, status code, key response fields after each call.

**Rules:**
- **Request bodies use snake_case** — `agent_type`, `doc_info_list`, `connector_name`. The `@apischema(to_camel_case=True)` decorator only camelizes responses, not inbound parsing.
- **Responses use camelCase** — `agentId`, `docInfoList`.
- **CSRF header**: `x-csrf-token` (all lowercase) — required for POST/PATCH; GET doesn't need it.
- **Cookie jar must be shared** — pass `-c ${COOKIEJAR} -b ${COOKIEJAR}` on every call (curl), or reuse the same `requests.Session()` (Python).
- **S3 presigned URLs expire ~15 min** — PUT the file immediately after receiving the URL.
- **Async operations** — if a mutation triggers background processing (ingestion, indexing), `sleep 60` before asserting on the result.

---

## Phase 4 — Assertions

After each call:
- Verify status code matches expected (200, 201, etc.)
- Verify expected fields are present and non-null (IDs, timestamps)
- Verify state changes took effect (re-GET to confirm)

**Knowledge isolation check** (if applicable): send a query that is outside the test data's domain → expect empty results / `sources: []`.

---

## Phase 5 — Test Report

Output a table:

```
| # | Method | Endpoint | Key Request Fields | Status | Key Response Fields | Pass? |
|---|--------|----------|--------------------|--------|---------------------|-------|
| 1 | GET    | /api/... | —                  | 200    | items: [...], total: N | ✅ |
| 2 | POST   | /api/... | filename, connector | 200   | url: ..., docId: ... | ✅ |
```

---

## Phase 6 — Cleanup

1. PATCH all test entities back to their pre-test state (disable entities that were disabled before, delete test data if possible)
2. Remove cookie jar: `rm -f ${COOKIEJAR}`
3. Save findings: `Skill(skill="project-context", args="branch:update <test summary>")`

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `x-csrf-invalid: 1` (400) | CSRF missing or stale | GET any endpoint, extract `x-csrf-token`, resend |
| "Please reload the page" (400) | `_vs` cookie not sent → vs_cookie mismatch | Use Option C: extract `_vs` from Set-Cookie, `s.cookies['_vs'] = val` |
| CSRF valid but POST returns 400 "Please reload" | Seed endpoint returned 500, session regenerated | Use a 404 seed (not 500) — 500 error handler regenerates session |
| 302 redirect to /login | Bearer token expired | Regenerate via Phase 1; token TTL is 7 days |
| Server won't accept Bearer for POST | Bearer alone is not enough for mutations | CSRF + session cookie always required for mutations |
| Camelcase request body returns validation error | Pydantic expects snake_case on input | Use `agent_type` not `agentType`, `doc_info_list` not `docInfoList` |
| `get_by_email` returns None | Global DB intermittent failure | Retry Phase 1 token generation up to 3× |
| `group_id` becomes `volkscience.com` | `subdomain_mapping = None` in `flask_utils.py` | Apply patch 4 (flask_utils.py `or {}` fix) |
| Server loops with exit code 3 | App import failure | Run `python3 -c 'from apps.runserver import app'` to see real traceback |
| Worker restart loop after startup | `--reload` flag in runserver.sh watching patched files | Apply patch 2: remove `--reload` from runserver.sh |
| `AttributeError: 'NoneType' has no attribute 'strip'` on startup | `VS_STATIC_CDN` not set | Apply patch 1: add `export VS_STATIC_CDN=https://static.vscdn.net` to test_env.sh |
| `ValueError: Reentrant function call not allowed config._get` | `db_client.safe_execute` calls `cannot_edit_config` while `_get_config` is running | Apply patch 3: `cannot_edit_config` → `return False` |
| `DBClientException`: global DB not configured | `_get_config` re-raises when global DB unavailable | Apply patch 3: `_get_config` except → `return default` |
| Gate `<name>_gate` not found — ValueError | Gate doesn't exist in tenant config DB | Patch 3 also needed; gate lookups fail via _get_config |
| Async operation returns empty result | Ingestion/indexing not complete | `sleep 60` after enabling the entity, then retry |
| S3 PUT returns 403 | Presigned URL expired | Re-fetch upload URL, upload immediately |
| `ValueError: This endpoint (X) is already set` | Flask-RESTX endpoint name collision | Prefix endpoint param with namespace: `endpoint='ns_resource'` |
| `get_check_runs` green but server fails | Missing env var in `test_env.sh` | `printenv | grep <VAR>` on running instance, add missing vars |

---

## EC2 Details

| Item | Value |
|------|-------|
| Dev server | `https://akshat-v.dev.eightfold.ai` |
| EC2 host | `ec2-user@172.31.27.248` |
| SSH key | `~/eightfold/id_rsa` |
| Test users | `akshat.v@eightfold.ai` (group_id=`volkscience.com`) — dev instance owner account; `valerie.cote@eightfolddemo-samyak4.com` (group_id=`eightfolddemo-samyak4.com`) — demo tenant candidate |
| Server log | `/tmp/runserver.log` |
| App request log | `/tmp/apps.logs` (Flask request-level errors go here, NOT runserver.log) |
| Server port | `8000` (local on EC2) |

---

## Unit Tests on EC2 (quick reference)

To run pytest for the changed endpoints (not the live server):

```bash
ssh -i ~/eightfold/id_rsa ec2-user@172.31.27.248 \
  "source /home/ec2-user/test_env.sh && \
   source /home/ec2-user/py3.13-virt/bin/activate && \
   cd /home/ec2-user/vscode/www && \
   git fetch origin && git checkout <branch> && git pull && \
   PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest <test_path> -v --noconftest"
```

Required flags (same as `/run-on-ec2`):
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` — prevents boto3 SSL init crash
- `--noconftest` — prevents conftest from hitting real AWS on import

Use `/run-on-ec2` directly for this step.
