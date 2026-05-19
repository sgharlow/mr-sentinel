#!/usr/bin/env bash
# cleanup-override-verification.sh — close the verification MR and delete the
# verification branch(es) created by scripts/test-override-live.sh.
#
# Idempotent: safe to re-run. Leaves the .mr-sentinel.yaml on main alone
# (the user decides whether to keep it as a demo example or remove it).
#
# Usage: gcloud must be authed and able to pull mr-sentinel-gitlab-token.

set -euo pipefail

PROJ_ID="${PROJ_ID:-82289558}"   # sgharlow/governance-demo-app
GCP_PROJECT="${GCP_PROJECT:-aicin-477004}"
MR_IID="${MR_IID:-8}"

log() { printf '\033[1;34m[cleanup]\033[0m %s\n' "$*"; }

TOKEN=$(gcloud secrets versions access latest \
  --secret=mr-sentinel-gitlab-token \
  --project="$GCP_PROJECT" | tr -d '\n')

log "close MR !$MR_IID"
curl -sS -X PUT -H "PRIVATE-TOKEN: $TOKEN" \
  -d "state_event=close" \
  "https://gitlab.com/api/v4/projects/$PROJ_ID/merge_requests/$MR_IID" \
  -o /tmp/close-resp.json -w "  http=%{http_code}\n"
python3 -c "
import json
d = json.load(open('/tmp/close-resp.json'))
print(f'  state={d.get(\"state\")} title={d.get(\"title\", \"\")[:60]}')
"

log "list verification branches (test/override-verification-*)"
curl -sS -H "PRIVATE-TOKEN: $TOKEN" \
  "https://gitlab.com/api/v4/projects/$PROJ_ID/repository/branches?search=test/override-verification" \
  -o /tmp/verif-branches.json
python3 -c "
import json
branches = json.load(open('/tmp/verif-branches.json'))
print(f'  found {len(branches)} branches')
with open('/tmp/verif-branch-names.txt', 'w') as f:
    for b in branches:
        print(f'    {b[\"name\"]}')
        f.write(b['name'] + '\n')
"

log "delete each verification branch"
while read -r BRANCH; do
  [ -z "$BRANCH" ] && continue
  ENCODED=$(python3 -c "import urllib.parse, sys; print(urllib.parse.quote(sys.argv[1], safe=''))" "$BRANCH")
  HTTP=$(curl -sS -X DELETE -H "PRIVATE-TOKEN: $TOKEN" -w '%{http_code}' \
    -o /dev/null \
    "https://gitlab.com/api/v4/projects/$PROJ_ID/repository/branches/$ENCODED")
  printf '    %s -> http=%s\n' "$BRANCH" "$HTTP"
done < /tmp/verif-branch-names.txt

log "done. .mr-sentinel.yaml on main is preserved (user decision)."
