#!/usr/bin/env bash
# Quick diagnostic — print service status and test both URL formats.
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-aicin-477004}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-mr-sentinel-webhook}"
PROJECT_NUMBER="${PROJECT_NUMBER:-239116109469}"

echo "=== service describe (selected fields) ==="
gcloud run services describe "$SERVICE_NAME" \
  --region="$REGION" --project="$PROJECT_ID" \
  --format='value(status.url,status.address.url,status.conditions[0].status,status.conditions[0].message,status.latestReadyRevisionName)'

echo
echo "=== try project-number URL (new format) ==="
URL_NEW="https://${SERVICE_NAME}-${PROJECT_NUMBER}.${REGION}.run.app"
echo "URL: $URL_NEW/healthz"
curl -sS -w '\nhttp_code=%{http_code}\n' "$URL_NEW/healthz"

echo
echo "=== try status.url (whatever gcloud returns) ==="
URL_STATUS=$(gcloud run services describe "$SERVICE_NAME" \
  --region="$REGION" --project="$PROJECT_ID" --format='value(status.url)')
echo "URL: $URL_STATUS/healthz"
curl -sS -w '\nhttp_code=%{http_code}\n' "$URL_STATUS/healthz"

echo
echo "=== recent service logs (last 20 lines) ==="
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=${SERVICE_NAME}" \
  --project="$PROJECT_ID" \
  --limit=20 \
  --format='value(timestamp,textPayload,jsonPayload.message)' 2>&1 | head -40
