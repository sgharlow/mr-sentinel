#!/usr/bin/env bash
# cloud-run-deploy.sh — build via Cloud Build, deploy to Cloud Run with secret
# bindings, print the live URL. Idempotent.
#
# Prereqs: gcp-bootstrap.sh has already run (so the project, registry, and
# webhook secret exist).

set -euo pipefail

PROJECT_ID="${PROJECT_ID:-aicin-477004}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-mr-sentinel-webhook}"
# Default IMAGE_TAG to the current git short SHA so every deploy gets a unique,
# traceable tag. Override via `IMAGE_TAG=x.y.z bash scripts/cloud-run-deploy.sh`
# when shipping a marketing-readable version. Falls back to `dev` when not in a
# git checkout (e.g., running from a tarball).
IMAGE_TAG="${IMAGE_TAG:-$(git rev-parse --short HEAD 2>/dev/null || echo dev)}"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/mr-sentinel/webhook:${IMAGE_TAG}"

log() { printf '\033[1;34m[cloud-run-deploy]\033[0m %s\n' "$*"; }
err() { printf '\033[1;31m[cloud-run-deploy]\033[0m %s\n' "$*" >&2; }

log "project = $PROJECT_ID  region = $REGION  service = $SERVICE_NAME"

PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
log "default compute SA: $COMPUTE_SA"

log "granting Secret Manager access to compute SA (idempotent)"
gcloud secrets add-iam-policy-binding mr-sentinel-gitlab-webhook-secret \
  --member="serviceAccount:${COMPUTE_SA}" \
  --role='roles/secretmanager.secretAccessor' \
  --project="$PROJECT_ID" --quiet >/dev/null

log "building image via Cloud Build (1-2 min)"
gcloud builds submit \
  --tag "$IMAGE" \
  --project="$PROJECT_ID" \
  --quiet \
  .

log "deploying to Cloud Run"
gcloud run deploy "$SERVICE_NAME" \
  --image="$IMAGE" \
  --region="$REGION" \
  --platform=managed \
  --allow-unauthenticated \
  --set-secrets='GITLAB_WEBHOOK_SECRET=mr-sentinel-gitlab-webhook-secret:latest,GITLAB_TOKEN=mr-sentinel-gitlab-token:latest,DB_PASSWORD=mr-sentinel-db-app-password:latest' \
  --set-env-vars="GCP_PROJECT_ID=$PROJECT_ID,DB_HOST=/cloudsql/$PROJECT_ID:$REGION:mr-sentinel-db,DB_NAME=mrsentinel,DB_USER=app" \
  --add-cloudsql-instances="$PROJECT_ID:$REGION:mr-sentinel-db" \
  --memory=1Gi \
  --cpu=1 \
  --no-cpu-throttling \
  --max-instances=10 \
  --min-instances=0 \
  --concurrency=20 \
  --timeout=120 \
  --project="$PROJECT_ID" \
  --quiet

SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
  --region="$REGION" --project="$PROJECT_ID" \
  --format='value(status.url)')

log "deployed: $SERVICE_URL"
log "smoke test: curl $SERVICE_URL/health"
curl -sS -w '\nhttp_code=%{http_code}\n' "$SERVICE_URL/health"
