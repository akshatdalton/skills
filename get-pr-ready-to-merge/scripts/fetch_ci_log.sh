#!/usr/bin/env bash
# fetch_ci_log.sh <stage.eightfold.ai/internal/s3viewer URL>
# Streams the log to stdout. Loads AWS creds from ~/eightfold/wipdp/.env.
set -euo pipefail

url="${1:?usage: fetch_ci_log.sh <s3viewer-url>}"
env_file="${WIPDP_ENV:-$HOME/eightfold/wipdp/.env}"

[[ -f "$env_file" ]] || { echo "missing $env_file" >&2; exit 2; }

# shellcheck disable=SC1090
set -a; source "$env_file"; set +a

bucket=$(python3 -c "import urllib.parse as u,sys; q=u.parse_qs(u.urlparse(sys.argv[1]).query); print(q['bucket'][0])" "$url")
key=$(python3 -c "import urllib.parse as u,sys; q=u.parse_qs(u.urlparse(sys.argv[1]).query); print(q['key'][0])" "$url")

aws s3 cp "s3://${bucket}/${key}" - 2>/dev/null
