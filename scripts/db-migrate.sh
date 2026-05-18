#!/usr/bin/env bash
# db-migrate.sh — apply pending SQL migrations using cloud-sql-proxy + asyncpg.
#
# Usage:
#   bash scripts/db-migrate.sh                   # apply pending
#   DRY_RUN=1 bash scripts/db-migrate.sh         # plan only

set -euo pipefail

PROJECT_ID="${PROJECT_ID:-aicin-477004}"
INSTANCE="${INSTANCE:-mr-sentinel-db}"
CONN_NAME="${PROJECT_ID}:us-central1:${INSTANCE}"
DATABASE="${DATABASE:-mrsentinel}"
DB_USER="${DB_USER:-postgres}"
PROXY_PORT="${PROXY_PORT:-5434}"
PROXY_BIN="${PROXY_BIN:-$HOME/.local/bin/cloud-sql-proxy}"
DRY_RUN="${DRY_RUN:-0}"

log() { printf '\033[1;34m[db-migrate]\033[0m %s\n' "$*"; }
err() { printf '\033[1;31m[db-migrate]\033[0m %s\n' "$*" >&2; }

if [[ ! -x "$PROXY_BIN" ]]; then
  log "downloading cloud-sql-proxy v2.13.0"
  mkdir -p "$(dirname "$PROXY_BIN")"
  curl -fsSL -o "$PROXY_BIN" \
    "https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.13.0/cloud-sql-proxy.linux.amd64"
  chmod +x "$PROXY_BIN"
fi

log "fetching $DB_USER password from Secret Manager"
DB_PASSWORD=$(gcloud secrets versions access latest \
  --secret=mr-sentinel-db-password \
  --project="$PROJECT_ID" | tr -d '\n')
[[ -n "$DB_PASSWORD" ]] || { err "missing password"; exit 1; }

log "starting cloud-sql-proxy on 127.0.0.1:$PROXY_PORT"
"$PROXY_BIN" --port="$PROXY_PORT" "$CONN_NAME" >/tmp/cloud-sql-proxy.log 2>&1 &
PROXY_PID=$!
trap 'kill $PROXY_PID 2>/dev/null || true' EXIT

for i in $(seq 1 30); do
  if (echo > /dev/tcp/127.0.0.1/$PROXY_PORT) 2>/dev/null; then break; fi
  sleep 0.5
done
if ! (echo > /dev/tcp/127.0.0.1/$PROXY_PORT) 2>/dev/null; then
  err "proxy not ready after 15s"
  cat /tmp/cloud-sql-proxy.log >&2
  exit 1
fi
log "proxy ready"

# Use the project's venv for asyncpg
VENV_PY="$(dirname "$0")/../.venv/bin/python"
if [[ ! -x "$VENV_PY" ]]; then
  # Windows venv layout (used when run from Git Bash mounting the project)
  VENV_PY="$(dirname "$0")/../.venv/Scripts/python.exe"
fi
if [[ ! -x "$VENV_PY" ]]; then
  err ".venv python not found; create it first: python -m venv .venv && pip install -r requirements-dev.txt"
  exit 1
fi

DRY_FLAG=""
[[ "$DRY_RUN" == "1" ]] && DRY_FLAG="--dry-run"

DB_PASSWORD="$DB_PASSWORD" PROXY_PORT="$PROXY_PORT" DATABASE="$DATABASE" DB_USER="$DB_USER" \
  "$VENV_PY" "$(dirname "$0")/../db/migrate.py" $DRY_FLAG
