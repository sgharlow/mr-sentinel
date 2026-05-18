#!/usr/bin/env bash
# smoke-test.sh — verify a deployed Cloud Run service is reachable and authenticated.
# Exits 0 on success, 1 on healthz failure, 2 on auth failure.

set -euo pipefail

PROJECT_ID="${PROJECT_ID:-aicin-477004}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-mr-sentinel-webhook}"

log() { printf '\033[1;34m[smoke]\033[0m %s\n' "$*"; }
err() { printf '\033[1;31m[smoke]\033[0m %s\n' "$*" >&2; }

SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
  --region="$REGION" --project="$PROJECT_ID" \
  --format='value(status.url)' 2>/dev/null) || {
    err "service $SERVICE_NAME not found in $PROJECT_ID/$REGION"
    exit 1
  }
log "service URL: $SERVICE_URL"

log "test 1: /health returns 200"
H_RESP=$(curl -sS -w '\n%{http_code}' "$SERVICE_URL/health")
H_BODY=$(echo "$H_RESP" | head -n -1)
H_CODE=$(echo "$H_RESP" | tail -n 1)
echo "  body: $H_BODY"
echo "  code: $H_CODE"
[[ "$H_CODE" == "200" ]] || { err "/health failed (Cloud Run intercepts /healthz — use /health)"; exit 1; }

log "test 2: webhook rejects missing token with 401"
NOTOKEN=$(curl -sS -o /dev/null -w '%{http_code}' -X POST "$SERVICE_URL/gitlab/webhook" \
  -H 'Content-Type: application/json' \
  -d '{"object_kind":"merge_request"}')
echo "  no-token response: $NOTOKEN"
[[ "$NOTOKEN" == "401" ]] || { err "expected 401 for missing token, got $NOTOKEN"; exit 2; }

log "test 3: webhook rejects wrong token with 401"
BADTOKEN=$(curl -sS -o /dev/null -w '%{http_code}' -X POST "$SERVICE_URL/gitlab/webhook" \
  -H 'Content-Type: application/json' \
  -H 'X-Gitlab-Token: definitely-wrong' \
  -d '{"object_kind":"merge_request"}')
echo "  bad-token response: $BADTOKEN"
[[ "$BADTOKEN" == "401" ]] || { err "expected 401 for bad token, got $BADTOKEN"; exit 2; }

log "test 4: webhook accepts correct token with 202"
# Pull the actual secret value to verify e2e
WEBHOOK_SECRET=$(gcloud secrets versions access latest \
  --secret=mr-sentinel-gitlab-webhook-secret \
  --project="$PROJECT_ID" 2>/dev/null)
OK=$(curl -sS -o /dev/null -w '%{http_code}' -X POST "$SERVICE_URL/gitlab/webhook" \
  -H 'Content-Type: application/json' \
  -H "X-Gitlab-Token: $WEBHOOK_SECRET" \
  -H 'X-Gitlab-Event: Merge Request Hook' \
  -d '{"object_kind":"merge_request","object_attributes":{"iid":1,"action":"open"},"project":{"path_with_namespace":"sgharlow/governance-demo-app"}}')
echo "  good-token response: $OK"
[[ "$OK" == "202" ]] || { err "expected 202 for valid token, got $OK"; exit 2; }

log "all 4 checks passed."
echo
log "service URL for GitLab webhook config: $SERVICE_URL/gitlab/webhook"
