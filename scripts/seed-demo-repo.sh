#!/usr/bin/env bash
# seed-demo-repo.sh — push the Medbill scaffold to gitlab.com/sgharlow/governance-demo-app.
#
# Reads files from <repo-root>/scratch/medbill/ and pushes them as ONE
# commit to main via the GitLab commits API. Skips .mr-sentinel.yaml on
# the target so the override demo stays intact.
#
# Idempotent: if a file already exists on the target, uses action:update
# instead of action:create.

set -euo pipefail

PROJ_ID="${PROJ_ID:-82289558}"
GCP_PROJECT="${GCP_PROJECT:-aicin-477004}"
SCRATCH="${SCRATCH:-$(cd "$(dirname "$0")/.." && pwd)/scratch/medbill}"
BRANCH="${BRANCH:-main}"
COMMIT_MESSAGE="${COMMIT_MESSAGE:-feat: initial Medbill scaffold — FastAPI app for the MR Sentinel governance demo}"

log() { printf '\033[1;34m[seed-demo]\033[0m %s\n' "$*"; }

TOKEN=$(gcloud secrets versions access latest \
  --secret=mr-sentinel-gitlab-token \
  --project="$GCP_PROJECT" | tr -d '\n')

log "scratch dir: $SCRATCH"
log "target: gitlab.com project $PROJ_ID branch $BRANCH"

# Build list of {path,action,base64} tuples — one per file under scratch/medbill/
log "scanning scratch for files"
export SCRATCH PROJ_ID TOKEN BRANCH COMMIT_MESSAGE
python3 << EOF > /tmp/seed-actions.json
import base64
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

scratch = Path(os.environ["SCRATCH"])
proj_id = os.environ["PROJ_ID"]
token = os.environ["TOKEN"]
branch = os.environ["BRANCH"]

actions = []
for f in sorted(scratch.rglob("*")):
    if not f.is_file():
        continue
    rel = f.relative_to(scratch).as_posix()
    if rel == ".mr-sentinel.yaml":
        # Don't touch the override file
        continue

    # Does the file already exist on the target branch?
    encoded_path = urllib.parse.quote(rel, safe="")
    url = f"https://gitlab.com/api/v4/projects/{proj_id}/repository/files/{encoded_path}/raw?ref={branch}"
    req = urllib.request.Request(url, headers={"PRIVATE-TOKEN": token})
    try:
        with urllib.request.urlopen(req) as resp:
            exists = resp.status == 200
    except urllib.error.HTTPError as e:
        exists = (e.code != 404)
        if e.code not in (200, 404):
            # any other error — still try create
            exists = False

    content = f.read_bytes()
    action = {
        "action": "update" if exists else "create",
        "file_path": rel,
        "encoding": "base64",
        "content": base64.b64encode(content).decode("ascii"),
    }
    actions.append(action)
    print(f"  {action['action']:6s} {rel}  ({len(content)} bytes)", file=sys.stderr)

payload = {
    "branch": branch,
    "commit_message": os.environ["COMMIT_MESSAGE"],
    "actions": actions,
}
print(json.dumps(payload))
EOF

ACTION_COUNT=$(python3 -c "import json; print(len(json.load(open('/tmp/seed-actions.json'))['actions']))")
log "prepared $ACTION_COUNT file actions"

log "POSTing commit"
TOKEN="$TOKEN" SCRATCH="$SCRATCH" PROJ_ID="$PROJ_ID" BRANCH="$BRANCH" \
  curl -sS -X POST -H "PRIVATE-TOKEN: $TOKEN" -H "Content-Type: application/json" \
  --data @/tmp/seed-actions.json \
  "https://gitlab.com/api/v4/projects/$PROJ_ID/repository/commits" \
  -o /tmp/seed-resp.json -w "  http=%{http_code}\n"

python3 -c "
import json
d = json.load(open('/tmp/seed-resp.json'))
if 'id' in d:
    print(f'  commit_id={d[\"id\"][:10]}  short_id={d.get(\"short_id\", \"\")}')
    print(f'  message={d.get(\"message\", \"\")[:80]}')
    print(f'  stats={d.get(\"stats\")}')
else:
    print(json.dumps(d, indent=2))
"
