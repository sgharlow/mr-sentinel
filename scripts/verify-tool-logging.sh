#!/usr/bin/env bash
# verify-tool-logging.sh — confirm the tool=<action> + mr_iid= logging (commit
# 79b5fee, Cloud Run rev 00013+) is live. Retriggers a NON-hero MR by pushing a
# fresh commit via the GitLab API (new sha -> bypasses dedup -> full eval), waits,
# then reads the new Cloud Logging lines.
#
# RUN FROM WSL (gcloud is Norton-blocked in Git Bash):  bash scripts/verify-tool-logging.sh
# Override the MR with:  MR=6 bash scripts/verify-tool-logging.sh
set -uo pipefail

PROJECT="aicin-477004"
PROJ="sgharlow%2Fgovernance-demo-app"
MR="${MR:-7}"   # non-hero MR; keeps hero !10 sha (1fb25ad2) pinned for the demo

echo "== [1/4] reading GitLab PAT from Secret Manager =="
# File-redirect (not \$(gcloud ...)) to avoid the wsl/gcloud subshell-capture quirk.
gcloud secrets versions access latest --secret=mr-sentinel-gitlab-token --project="$PROJECT" > /tmp/mrs-pat.txt
GL_PAT="$(tr -d '\r\n' < /tmp/mrs-pat.txt)"; rm -f /tmp/mrs-pat.txt
if [ -z "$GL_PAT" ]; then echo "FATAL: empty PAT — run 'gcloud auth login' and retry"; exit 1; fi

echo "== [2/4] resolving MR !$MR source branch =="
BRANCH="$(curl -fsS -H "PRIVATE-TOKEN: $GL_PAT" "https://gitlab.com/api/v4/projects/$PROJ/merge_requests/$MR" | jq -r .source_branch)"
echo "source branch: $BRANCH"

echo "== [3/4] creating a fresh commit on $BRANCH (new sha -> fresh eval) =="
STAMP="$(date -u +%s)"
cat > /tmp/mrs-commit.json <<JSON
{"branch":"$BRANCH","commit_message":"retest tool= logging $STAMP","actions":[{"action":"create","file_path":".mr-sentinel-retest-$STAMP","content":"$STAMP"}]}
JSON
curl -fsS -X POST -H "PRIVATE-TOKEN: $GL_PAT" -H "Content-Type: application/json" \
  "https://gitlab.com/api/v4/projects/$PROJ/repository/commits" \
  --data @/tmp/mrs-commit.json | jq -r '"committed " + .short_id + " on " + .title'
rm -f /tmp/mrs-commit.json

echo "== [4/4] waiting 50s for webhook + background eval, then reading logs =="
sleep 50
gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"mr-sentinel-webhook\" AND (textPayload:\"tool=\" OR textPayload:\"evaluation: score=\") AND timestamp>=\"$(date -u -d '4 minutes ago' +%Y-%m-%dT%H:%M:%SZ)\"" \
  --project="$PROJECT" --format="value(timestamp,textPayload)" --limit=40

echo
echo "PASS if you see a run of tool=get_merge_request / tool=get_merge_request_diffs / ..."
echo "followed by 'evaluation: score=... rules=15 mr_iid=$MR'."
