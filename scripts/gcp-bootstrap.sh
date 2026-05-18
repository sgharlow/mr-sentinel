#!/usr/bin/env bash
# gcp-bootstrap.sh — create the mr-sentinel GCP project, enable required APIs,
# link billing. Idempotent: re-running is safe.
#
# Prereqs: gcloud CLI authenticated (`gcloud auth login` complete and token-refresh
# works — i.e., outside Norton TLS MITM, or in WSL2 on a Norton-affected host).
#
# Usage:
#   ./scripts/gcp-bootstrap.sh                    # uses default project id
#   PROJECT_ID=my-proj ./scripts/gcp-bootstrap.sh # override
#
# Exit codes: 0 ok, 1 auth not fresh, 2 billing link failed, 3 api enable failed.

set -euo pipefail

PROJECT_ID="${PROJECT_ID:-aicin-477004}"
PROJECT_NAME="${PROJECT_NAME:-MR Sentinel}"
REGION="${REGION:-us-central1}"
SKIP_CREATE="${SKIP_CREATE:-0}"  # set to 1 when reusing an existing project

REQUIRED_APIS=(
  aiplatform.googleapis.com
  discoveryengine.googleapis.com
  run.googleapis.com
  sqladmin.googleapis.com
  secretmanager.googleapis.com
  cloudbuild.googleapis.com
  artifactregistry.googleapis.com
  iam.googleapis.com
  servicenetworking.googleapis.com
  cloudresourcemanager.googleapis.com
  logging.googleapis.com
  monitoring.googleapis.com
)

log() { printf '\033[1;34m[gcp-bootstrap]\033[0m %s\n' "$*"; }
err() { printf '\033[1;31m[gcp-bootstrap]\033[0m %s\n' "$*" >&2; }

log "verifying gcloud auth"
if ! gcloud auth print-access-token >/dev/null 2>&1; then
  err "gcloud auth token is not refreshable — run 'gcloud auth login' first"
  err "on Norton-MITM hosts: run this script from inside WSL with Linux-native gcloud"
  exit 1
fi
ACTIVE_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -1)
log "authenticated as $ACTIVE_ACCOUNT"

log "checking if project $PROJECT_ID exists"
if gcloud projects describe "$PROJECT_ID" --quiet >/dev/null 2>&1; then
  log "project $PROJECT_ID already exists — skipping create"
else
  if [[ "$SKIP_CREATE" == "1" ]]; then
    err "SKIP_CREATE=1 but project $PROJECT_ID does not exist"
    exit 1
  fi
  log "creating project $PROJECT_ID"
  gcloud projects create "$PROJECT_ID" --name="$PROJECT_NAME" --quiet
fi

log "setting active project"
gcloud config set project "$PROJECT_ID" --quiet
gcloud config set compute/region "$REGION" --quiet 2>/dev/null || true

log "checking existing billing link on $PROJECT_ID"
EXISTING_BILLING=$(gcloud billing projects describe "$PROJECT_ID" --quiet --format="value(billingAccountName)" 2>/dev/null || true)
if [[ -n "$EXISTING_BILLING" && "$EXISTING_BILLING" != "None" ]]; then
  log "billing already linked: $EXISTING_BILLING — skipping link step"
else
  log "linking billing account"
  BILLING_ACCOUNT=$(gcloud billing accounts list --filter=open=true --format="value(name)" --quiet | head -1)
  if [[ -z "$BILLING_ACCOUNT" ]]; then
    err "no open billing account found"
    exit 2
  fi
  gcloud billing projects link "$PROJECT_ID" --billing-account="$BILLING_ACCOUNT" --quiet || {
    err "billing link failed — possible quota cap on billing account $BILLING_ACCOUNT"
    err "  (Google caps projects per billing account; delete unused projects or reuse an existing one)"
    exit 2
  }
  log "billing linked: $BILLING_ACCOUNT"
fi

log "enabling required APIs (this can take 1–2 minutes)"
gcloud services enable "${REQUIRED_APIS[@]}" --project="$PROJECT_ID" --quiet || {
  err "api enable failed"
  exit 3
}
log "apis enabled:"
for api in "${REQUIRED_APIS[@]}"; do
  printf '  - %s\n' "$api"
done

log "creating Secret Manager placeholders (empty — fill via separate command)"
for secret in mr-sentinel-gitlab-token mr-sentinel-gitlab-webhook-secret; do
  if ! gcloud secrets describe "$secret" --project="$PROJECT_ID" --quiet >/dev/null 2>&1; then
    gcloud secrets create "$secret" --replication-policy=automatic --project="$PROJECT_ID" --quiet
    log "  created secret: $secret (no version yet — add with: echo -n VALUE | gcloud secrets versions add $secret --data-file=-)"
  else
    log "  secret exists: $secret"
  fi
done

log "creating Artifact Registry for Cloud Run images"
REGISTRY_NAME="mr-sentinel"
if ! gcloud artifacts repositories describe "$REGISTRY_NAME" \
      --location="$REGION" --project="$PROJECT_ID" --quiet >/dev/null 2>&1; then
  gcloud artifacts repositories create "$REGISTRY_NAME" \
    --repository-format=docker \
    --location="$REGION" \
    --description="MR Sentinel container images" \
    --project="$PROJECT_ID" \
    --quiet
  log "  registry created: $REGION-docker.pkg.dev/$PROJECT_ID/$REGISTRY_NAME"
else
  log "  registry exists: $REGION-docker.pkg.dev/$PROJECT_ID/$REGISTRY_NAME"
fi

log "bootstrap complete — summary:"
gcloud projects describe "$PROJECT_ID" --format="table(projectId,name,projectNumber,createTime)"
echo
log "next: drop GitLab credentials into the secrets"
echo "  echo -n 'glpat-xxxxx' | gcloud secrets versions add mr-sentinel-gitlab-token --data-file=- --project=$PROJECT_ID"
echo "  openssl rand -hex 32 | gcloud secrets versions add mr-sentinel-gitlab-webhook-secret --data-file=- --project=$PROJECT_ID"
