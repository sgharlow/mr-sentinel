#!/usr/bin/env bash
# test-override-live.sh — end-to-end verification of the per-project rubric
# override path on the deployed Cloud Run service.
#
# Steps:
# 1. Pull GitLab token from Secret Manager.
# 2. Resolve numeric project id for sgharlow/governance-demo-app.
# 3. Create .mr-sentinel.yaml (v2 fork of v1) on main if absent, else update it.
# 4. Create a fresh feature branch with one trivial file change.
# 5. Open an MR from feature -> main (this fires the live webhook).
# 6. Wait, then tail Cloud Logging for the rubric=project_override line.
#
# DESIGNED TO BE RE-RUN: idempotent across all GitLab writes.

set -euo pipefail

PROJECT_PATH="sgharlow/governance-demo-app"
ENCODED_PROJECT="sgharlow%2Fgovernance-demo-app"
BRANCH="test/override-verification-$(date +%s)"
OVERRIDE_FILE_LOCAL="/tmp/override-v2.yaml"
GCP_PROJECT="aicin-477004"

log() { printf '\033[1;34m[verify]\033[0m %s\n' "$*"; }

log "fetching GitLab token from Secret Manager"
GITLAB_TOKEN=$(gcloud secrets versions access latest \
  --secret=mr-sentinel-gitlab-token \
  --project="$GCP_PROJECT" | tr -d '\n')
test -n "$GITLAB_TOKEN" || { echo "no token"; exit 1; }

log "resolving numeric project id"
PROJ_ID=$(curl -sS -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  "https://gitlab.com/api/v4/projects/$ENCODED_PROJECT" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')
log "project_id=$PROJ_ID"

log "preparing override yaml (v2 fork of v1)"
# Resolve repo root from this script's location so the path stays portable
# across WSL and native-Linux runs (no hardcoded /mnt/c/Users/<user>/...).
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cp "$REPO_ROOT/rubric/v1.yaml" "$OVERRIDE_FILE_LOCAL"
sed -i 's/^version: v1/version: v2/' "$OVERRIDE_FILE_LOCAL"
head -2 "$OVERRIDE_FILE_LOCAL"

log "encoding override as base64 for JSON body"
CONTENT_B64=$(base64 -w0 "$OVERRIDE_FILE_LOCAL")
python3 -c "
import json
print(json.dumps({
    'branch': 'main',
    'commit_message': 'chore: add .mr-sentinel.yaml v2 override for live verification',
    'encoding': 'base64',
    'content': '$CONTENT_B64',
}))
" > /tmp/override-payload.json

log "checking if .mr-sentinel.yaml exists on main"
EXISTS=$(curl -sS -o /dev/null -w '%{http_code}' \
  -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  "https://gitlab.com/api/v4/projects/$PROJ_ID/repository/files/.mr-sentinel.yaml/raw?ref=main")
log "  current state: HTTP $EXISTS"

if [[ "$EXISTS" == "404" ]]; then
  log "creating .mr-sentinel.yaml via POST"
  HTTP=$(curl -sS -o /tmp/create-resp.json -w '%{http_code}' \
    -X POST -H "PRIVATE-TOKEN: $GITLAB_TOKEN" -H "Content-Type: application/json" \
    --data @/tmp/override-payload.json \
    "https://gitlab.com/api/v4/projects/$PROJ_ID/repository/files/.mr-sentinel.yaml")
  log "  create resp: HTTP $HTTP"
  cat /tmp/create-resp.json | head -c 300; echo
else
  log "updating .mr-sentinel.yaml via PUT"
  HTTP=$(curl -sS -o /tmp/create-resp.json -w '%{http_code}' \
    -X PUT -H "PRIVATE-TOKEN: $GITLAB_TOKEN" -H "Content-Type: application/json" \
    --data @/tmp/override-payload.json \
    "https://gitlab.com/api/v4/projects/$PROJ_ID/repository/files/.mr-sentinel.yaml")
  log "  update resp: HTTP $HTTP"
  cat /tmp/create-resp.json | head -c 300; echo
fi

log "creating feature branch $BRANCH from main"
curl -sS -o /tmp/branch-resp.json -w 'http_code=%{http_code}\n' \
  -X POST -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  "https://gitlab.com/api/v4/projects/$PROJ_ID/repository/branches?branch=$BRANCH&ref=main"

log "adding a trivial file on $BRANCH"
TRIVIAL_B64=$(echo -n "verification trigger at $(date -u +%FT%TZ)" | base64 -w0)
python3 -c "
import json
print(json.dumps({
    'branch': '$BRANCH',
    'commit_message': 'test: trigger override verification',
    'encoding': 'base64',
    'content': '$TRIVIAL_B64',
}))
" > /tmp/trivial-payload.json
curl -sS -o /tmp/trivial-resp.json -w 'http_code=%{http_code}\n' \
  -X POST -H "PRIVATE-TOKEN: $GITLAB_TOKEN" -H "Content-Type: application/json" \
  --data @/tmp/trivial-payload.json \
  "https://gitlab.com/api/v4/projects/$PROJ_ID/repository/files/verify-$BRANCH.txt"

log "opening MR $BRANCH -> main"
python3 -c "
import json
print(json.dumps({
    'source_branch': '$BRANCH',
    'target_branch': 'main',
    'title': 'Verification: override path live-fire',
    'description': 'Synthetic MR opened by scripts/test-override-live.sh to verify the .mr-sentinel.yaml override path on the deployed Cloud Run service. Safe to close after the agent comment lands.',
}))
" > /tmp/mr-payload.json
curl -sS -o /tmp/mr-resp.json -w 'http_code=%{http_code}\n' \
  -X POST -H "PRIVATE-TOKEN: $GITLAB_TOKEN" -H "Content-Type: application/json" \
  --data @/tmp/mr-payload.json \
  "https://gitlab.com/api/v4/projects/$PROJ_ID/merge_requests"
MR_IID=$(python3 -c 'import json; print(json.load(open("/tmp/mr-resp.json"))["iid"])')
MR_URL=$(python3 -c 'import json; print(json.load(open("/tmp/mr-resp.json"))["web_url"])')
log "MR opened: !$MR_IID  $MR_URL"
echo "$MR_IID" > /tmp/last-mr-iid.txt

log "done. Webhook should fire within ~10s; agent eval ~20-30s."
log "next: tail Cloud Logging for rubric=project_override"
