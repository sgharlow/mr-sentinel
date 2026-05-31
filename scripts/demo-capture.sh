#!/usr/bin/env bash
# demo-capture.sh — the executable companion to docs/demo-script.md. Two jobs:
#
#   check  (default)  Read-only recording-readiness check. Verifies all four
#                     on-camera surfaces respond and prints the exact tabs to
#                     open, in shot order. Uses curl only (no gcloud) so it runs
#                     anywhere; run it from WSL for parity with `fire`.
#
#   fire [MR]         LIVE Shot-5 trigger. Pushes a fresh commit to a NON-hero MR
#                     (default !7, so hero !10's sha 1fb25ad2 stays pinned), waits
#                     for the agent loop, then prints the FULL ordered loop
#                     (received -> tool= x8 -> evaluation -> issue -> comment) in
#                     chronological order — film this block for Shot 5. Needs
#                     gcloud, so run it from WSL (Norton blocks gcloud elsewhere).
#
# USAGE (from WSL):
#   bash scripts/demo-capture.sh            # readiness check
#   bash scripts/demo-capture.sh fire       # live loop on !7, ready to film
#   bash scripts/demo-capture.sh fire 9     # ...on !9 (the /admin/dump-patients block)
#
# NOTE on the hero MR: re-firing !10 would change its sha8 (1fb25ad2) that Shot 6
# narration pins. Default fires a non-hero MR. Pass `fire 10` ONLY if you've
# already decided to recapture the sha (e.g. after the SEED=1 pass).
set -uo pipefail

PROJECT="aicin-477004"
BASE_URL="https://mr-sentinel-webhook-n6oitfxdra-uc.a.run.app"
PROJ="sgharlow%2Fgovernance-demo-app"
GL_WEB="https://gitlab.com/sgharlow/governance-demo-app"
HERO=10
MODE="${1:-check}"

hr()  { printf '\n========== %s ==========\n' "$1"; }
ok()  { printf '  [OK]   %s\n' "$1"; }
bad() { printf '  [FAIL] %s\n' "$1"; }

# ---------------------------------------------------------------------------
demo_check() {
  hr "RECORDING-READINESS CHECK"

  if curl -fsS -m 20 "$BASE_URL/health" | grep -q '"status":"ok"'; then
    ok "/health -> ok"
  else
    bad "/health not ok — service may be cold or down"
  fi

  DASH="$(curl -fsS -m 20 "$BASE_URL/dashboard" || true)"
  if [ -n "$DASH" ]; then
    # crude count of MR rows by the verdict pills the dashboard renders
    N="$(printf '%s' "$DASH" | grep -oiE 'verdict|block|warn|pass' | wc -l)"
    ok "/dashboard renders (verdict/score markers seen: $N) — eyeball the MR count + top-5 rules"
  else
    bad "/dashboard empty/unreachable"
  fi

  HERO_HTML="$(curl -fsS -m 20 "$BASE_URL/audit/sgharlow/governance-demo-app/$HERO" || true)"
  if printf '%s' "$HERO_HTML" | grep -qiE 'block'; then
    ok "/audit/.../$HERO renders and shows a block verdict (hero MR intact)"
  else
    bad "/audit/.../$HERO missing or not a block — re-check hero MR state"
  fi

  hr "OPEN THESE TABS, IN SHOT ORDER (see docs/demo-script.md)"
  cat <<TABS
  Shot 1/3/6 — hero MR:    $GL_WEB/-/merge_requests/$HERO
  Shot 4     — Cloud Run:  https://console.cloud.google.com/run/detail/us-central1/mr-sentinel-webhook?project=$PROJECT
  Shot 4     — rubric:     $GL_WEB/-/blob/main/rubric/v1.yaml   (or local rubric/v1.yaml)
  Shot 5     — live logs:  run  'bash scripts/demo-capture.sh fire'  in a side pane
  Shot 7     — dashboard:  $BASE_URL/dashboard
  Shot 8     — audit page: $BASE_URL/audit/sgharlow/governance-demo-app/$HERO
TABS
  echo
  echo "  Then: dark mode on, mic pad recorded, narration in docs/demo-script.md."
}

# ---------------------------------------------------------------------------
demo_fire() {
  local MR="${1:-7}"
  if [ "$MR" = "$HERO" ]; then
    echo "WARNING: firing the HERO MR !$HERO will change its sha8 (1fb25ad2 in Shot 6)."
    echo "         Ctrl-C now unless you've decided to recapture the sha. Continuing in 5s..."
    sleep 5
  fi

  hr "FIRE — live Shot-5 loop on MR !$MR"
  gcloud secrets versions access latest --secret=mr-sentinel-gitlab-token --project="$PROJECT" > /tmp/mrs-pat.txt
  local GL_PAT; GL_PAT="$(tr -d '\r\n' < /tmp/mrs-pat.txt)"; rm -f /tmp/mrs-pat.txt
  [ -z "$GL_PAT" ] && { bad "empty PAT — run 'gcloud auth login'"; return 1; }

  local BRANCH; BRANCH="$(curl -fsS -H "PRIVATE-TOKEN: $GL_PAT" "https://gitlab.com/api/v4/projects/$PROJ/merge_requests/$MR" | jq -r .source_branch)"
  echo "  source branch: $BRANCH"

  local STAMP; STAMP="$(date -u +%s)"
  cat > /tmp/mrs-commit.json <<JSON
{"branch":"$BRANCH","commit_message":"demo capture $STAMP","actions":[{"action":"create","file_path":".demo-capture-$STAMP","content":"$STAMP"}]}
JSON
  curl -fsS -X POST -H "PRIVATE-TOKEN: $GL_PAT" -H "Content-Type: application/json" \
    "https://gitlab.com/api/v4/projects/$PROJ/repository/commits" --data @/tmp/mrs-commit.json \
    | jq -r '"  committed " + .short_id'
  rm -f /tmp/mrs-commit.json

  echo "  waiting 20s for the agent loop to complete..."
  sleep 20

  hr "AGENT LOOP (chronological — film this)"
  gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"mr-sentinel-webhook\" AND (textPayload:\"received gitlab event\" OR textPayload:\"using project override\" OR textPayload:\"tool=\" OR textPayload:\"evaluation: score=\" OR textPayload:\"created followup issue\" OR textPayload:\"comment note_id=\") AND timestamp>=\"$(date -u -d '3 minutes ago' +%Y-%m-%dT%H:%M:%SZ)\"" \
    --project="$PROJECT" --order=asc --format="value(timestamp,textPayload)" --limit=40
  echo
  echo "  ^ expect: received event -> using override (v2) -> tool= x8 -> evaluation: score=...mr_iid=$MR -> created issue -> posted/updated comment"
}

case "$MODE" in
  check) demo_check ;;
  fire)  demo_fire "${2:-7}" ;;
  *)     echo "usage: bash scripts/demo-capture.sh [check|fire [MR]]"; exit 2 ;;
esac
