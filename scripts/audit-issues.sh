#!/usr/bin/env bash
# audit-issues.sh — list every issue on the demo repo with its labels, so we can
# see which label the agent's auto-opened remediation issues actually carry (the
# dashboard/audit "linked issue" view assumed `mr-sentinel`). Keeps the PAT in a
# variable and NEVER echoes it.
#
# RUN FROM WSL:  bash scripts/audit-issues.sh
set -uo pipefail

PROJECT="aicin-477004"
PROJ="sgharlow%2Fgovernance-demo-app"

gcloud secrets versions access latest --secret=mr-sentinel-gitlab-token --project="$PROJECT" > /tmp/mrs-pat.txt
GL_PAT="$(tr -d '\r\n' < /tmp/mrs-pat.txt)"; rm -f /tmp/mrs-pat.txt
if [ -z "$GL_PAT" ]; then echo "FATAL: empty PAT — run 'gcloud auth login' and retry"; exit 1; fi

echo "== all issues on $PROJ (iid / labels / state / title) =="
curl -fsS -H "PRIVATE-TOKEN: $GL_PAT" \
  "https://gitlab.com/api/v4/projects/$PROJ/issues?per_page=100&order_by=created_at&sort=asc" \
  | jq -r '.[] | "#\(.iid)  [\(.labels|join(","))]  \(.state)  \(.title)"'

echo
echo "Looking for: the auto-opened 'Compliance follow-up for !N' issues and what label they carry."
