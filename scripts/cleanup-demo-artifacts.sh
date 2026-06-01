#!/usr/bin/env bash
# cleanup-demo-artifacts.sh — remove the throwaway artifacts that the test/demo
# trigger scripts (verify-tool-logging.sh, demo-capture.sh fire) leave behind:
#   1. DUPLICATE auto-opened "Compliance follow-up for !N" issues — issue creation
#      isn't deduped, so every re-eval of a block MR opens another one. We keep the
#      LOWEST issue iid per MR (the original) and close the rest. This is robust
#      against the SEED pass adding new legit issues — no manual keep-list needed.
#   2. the .mr-sentinel-retest-* / .demo-capture-* marker files on the trigger branch.
#
# Idempotent — safe to run repeatedly. Run from WSL AFTER all recording is done.
# Optional: FORCE_KEEP="6" never-close these iids (escape hatch).  DRY=1 = preview only.
set -uo pipefail

PROJECT="aicin-477004"
PROJ="sgharlow%2Fgovernance-demo-app"
BRANCH="${BRANCH:-test/v030-days-9-14}"
FORCE_KEEP=" ${FORCE_KEEP:-} "
DRY="${DRY:-0}"

gcloud secrets versions access latest --secret=mr-sentinel-gitlab-token --project="$PROJECT" > /tmp/mrs-pat.txt
GL_PAT="$(tr -d '\r\n' < /tmp/mrs-pat.txt)"; rm -f /tmp/mrs-pat.txt
[ -z "$GL_PAT" ] && { echo "FATAL: empty PAT — run 'gcloud auth login'"; exit 1; }

echo "== de-duplicating 'Compliance follow-up' issues (keep lowest iid per MR) =="
# emit: <iid>\t<mr_number>\t<title>, sorted by iid ascending so the first seen per MR is the keeper
declare -A SEEN
curl -fsS -H "PRIVATE-TOKEN: $GL_PAT" \
  "https://gitlab.com/api/v4/projects/$PROJ/issues?state=opened&per_page=100" \
  | jq -r 'sort_by(.iid) | .[] | select(.title|test("Compliance follow-up for !")) | "\(.iid)\t\(.title|capture("for !(?<n>[0-9]+)").n)\t\(.title)"' \
  > /tmp/mrs-issues.tsv
while IFS=$'\t' read -r IID N TITLE; do
  if [[ "$FORCE_KEEP" == *" $IID "* ]]; then
    echo "  keep    #$IID (force)  $TITLE"
  elif [[ -z "${SEEN[$N]:-}" ]]; then
    SEEN[$N]="$IID"
    echo "  keep    #$IID (MR !$N original)  $TITLE"
  elif [[ "$DRY" == "1" ]]; then
    echo "  WOULD CLOSE #$IID (dup of MR !$N -> kept #${SEEN[$N]})"
  else
    curl -fsS -X PUT -H "PRIVATE-TOKEN: $GL_PAT" \
      "https://gitlab.com/api/v4/projects/$PROJ/issues/$IID?state_event=close" >/dev/null \
      && echo "  closed  #$IID (dup of MR !$N -> kept #${SEEN[$N]})"
  fi
done < /tmp/mrs-issues.tsv
rm -f /tmp/mrs-issues.tsv

echo "== deleting throwaway marker files on $BRANCH =="
FILES="$(curl -fsS -H "PRIVATE-TOKEN: $GL_PAT" \
  "https://gitlab.com/api/v4/projects/$PROJ/repository/tree?ref=$BRANCH&per_page=100" \
  | jq -r '.[] | select(.name|test("^\\.(mr-sentinel-retest|demo-capture)-")) | .path')"
if [ -z "$FILES" ]; then
  echo "  none found"
elif [ "$DRY" == "1" ]; then
  printf '%s\n' "$FILES" | sed 's/^/  WOULD DELETE /'
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
