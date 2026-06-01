#!/usr/bin/env bash
# cleanup-demo-artifacts.sh — remove the throwaway artifacts that the test/demo
# trigger scripts (verify-tool-logging.sh, demo-capture.sh fire) leave behind:
#   1. duplicate auto-opened "Compliance follow-up" issues (issue creation isn't
#      deduped, so every re-eval of a block MR opens another one), and
#   2. the .mr-sentinel-retest-* / .demo-capture-* marker files on the trigger branch.
#
# Idempotent — safe to run repeatedly. Run from WSL AFTER all recording is done.
#
# KEEP = the legit follow-up issue iids (one per real block verdict, as of the
# 2026-05-31 audit): #1!7 #2!10 #3!9 #4!13 #5!11. Any OTHER open "Compliance
# follow-up" issue is a test artifact and gets closed. Override if the legit set
# changes after a SEED=1 pass:  KEEP="1 2 3 4 5 14 15" bash scripts/cleanup-demo-artifacts.sh
set -uo pipefail

PROJECT="aicin-477004"
PROJ="sgharlow%2Fgovernance-demo-app"
BRANCH="${BRANCH:-test/v030-days-9-14}"
KEEP="${KEEP:-1 2 3 4 5}"

gcloud secrets versions access latest --secret=mr-sentinel-gitlab-token --project="$PROJECT" > /tmp/mrs-pat.txt
GL_PAT="$(tr -d '\r\n' < /tmp/mrs-pat.txt)"; rm -f /tmp/mrs-pat.txt
[ -z "$GL_PAT" ] && { echo "FATAL: empty PAT — run 'gcloud auth login'"; exit 1; }

echo "== closing test-created duplicate 'Compliance follow-up' issues (keeping: $KEEP) =="
KEEPRE=" $KEEP "
curl -fsS -H "PRIVATE-TOKEN: $GL_PAT" \
  "https://gitlab.com/api/v4/projects/$PROJ/issues?state=opened&per_page=100" \
  | jq -r '.[] | select(.title|startswith("Compliance follow-up")) | "\(.iid)\t\(.title)"' \
  | while IFS=$'\t' read -r IID TITLE; do
      if [[ "$KEEPRE" == *" $IID "* ]]; then
        echo "  keep   #$IID  $TITLE"
      else
        curl -fsS -X PUT -H "PRIVATE-TOKEN: $GL_PAT" \
          "https://gitlab.com/api/v4/projects/$PROJ/issues/$IID?state_event=close" >/dev/null \
          && echo "  closed #$IID  $TITLE"
      fi
    done

echo "== deleting throwaway marker files on $BRANCH =="
FILES="$(curl -fsS -H "PRIVATE-TOKEN: $GL_PAT" \
  "https://gitlab.com/api/v4/projects/$PROJ/repository/tree?ref=$BRANCH&per_page=100" \
  | jq -r '.[] | select(.name|test("^\\.(mr-sentinel-retest|demo-capture)-")) | .path')"
if [ -z "$FILES" ]; then
  echo "  none found"
else
  printf '%s\n' "$FILES" | sed 's/^/  delete /'
  ACTIONS="$(printf '%s\n' "$FILES" | jq -R '{action:"delete",file_path:.}' | jq -s .)"
  jq -n --arg b "$BRANCH" --argjson a "$ACTIONS" \
    '{branch:$b,commit_message:"cleanup: remove demo test artifacts",actions:$a}' > /tmp/mrs-cleanup.json
  curl -fsS -X POST -H "PRIVATE-TOKEN: $GL_PAT" -H "Content-Type: application/json" \
    "https://gitlab.com/api/v4/projects/$PROJ/repository/commits" --data @/tmp/mrs-cleanup.json \
    | jq -r '"  committed cleanup " + .short_id'
  rm -f /tmp/mrs-cleanup.json
fi

echo "== done =="
