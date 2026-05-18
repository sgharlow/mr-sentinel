#!/usr/bin/env bash
# gitlab-bootstrap.sh — create the governance-demo-app target repo on GitLab using
# the REST API. Idempotent.
#
# Prereqs: GITLAB_TOKEN env var set to a personal access token with `api`,
# `read_repository`, `write_repository` scopes.
#
# Usage:
#   GITLAB_TOKEN=glpat-xxxxx ./scripts/gitlab-bootstrap.sh
#
# Or source from .env.local:
#   set -a; source .env.local; set +a; ./scripts/gitlab-bootstrap.sh

set -euo pipefail

GITLAB_BASE_URL="${GITLAB_BASE_URL:-https://gitlab.com}"
REPO_NAME="${REPO_NAME:-governance-demo-app}"
REPO_VISIBILITY="${REPO_VISIBILITY:-public}"
REPO_DESCRIPTION="${REPO_DESCRIPTION:-Reference repository for MR Sentinel demos — fictional regulated-SaaS codebase}"

log() { printf '\033[1;34m[gitlab-bootstrap]\033[0m %s\n' "$*"; }
err() { printf '\033[1;31m[gitlab-bootstrap]\033[0m %s\n' "$*" >&2; }

if [[ -z "${GITLAB_TOKEN:-}" ]]; then
  err "GITLAB_TOKEN env var is unset"
  err "issue one at: $GITLAB_BASE_URL/-/user_settings/personal_access_tokens"
  err "scopes required: api, read_repository, write_repository"
  exit 1
fi

log "verifying token"
USERNAME=$(curl -sf -H "PRIVATE-TOKEN: $GITLAB_TOKEN" "$GITLAB_BASE_URL/api/v4/user" \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['username'])" 2>/dev/null) || {
    err "token rejected by $GITLAB_BASE_URL/api/v4/user — invalid or scope-missing"
    exit 1
  }
log "authenticated as: $USERNAME"

log "checking if repo $USERNAME/$REPO_NAME already exists"
PROJECT_PATH="$USERNAME/$REPO_NAME"
ENCODED_PATH=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$PROJECT_PATH', safe=''))")

if curl -sf -o /dev/null -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
      "$GITLAB_BASE_URL/api/v4/projects/$ENCODED_PATH"; then
  log "repo $PROJECT_PATH already exists — skipping create"
  WEB_URL="$GITLAB_BASE_URL/$PROJECT_PATH"
else
  log "creating $PROJECT_PATH (visibility=$REPO_VISIBILITY)"
  RESPONSE=$(curl -sf -X POST -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
    --data-urlencode "name=$REPO_NAME" \
    --data-urlencode "visibility=$REPO_VISIBILITY" \
    --data-urlencode "description=$REPO_DESCRIPTION" \
    --data-urlencode "initialize_with_readme=true" \
    "$GITLAB_BASE_URL/api/v4/projects") || {
      err "repo create failed"
      exit 2
    }
  WEB_URL=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['web_url'])")
  log "created: $WEB_URL"
fi

log "configuring webhook will be done in a separate step once Cloud Run URL is live"
log "  manual cmd template:"
cat <<EOF
  curl -X POST -H "PRIVATE-TOKEN: \$GITLAB_TOKEN" \\
    --data-urlencode "url=https://<cloud-run-url>/gitlab/webhook" \\
    --data-urlencode "merge_requests_events=true" \\
    --data-urlencode "token=\$GITLAB_WEBHOOK_SECRET" \\
    --data-urlencode "enable_ssl_verification=true" \\
    "$GITLAB_BASE_URL/api/v4/projects/$ENCODED_PATH/hooks"
EOF

log "done. demo repo: $WEB_URL"
