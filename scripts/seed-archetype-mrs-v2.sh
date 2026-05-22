#!/usr/bin/env bash
# seed-archetype-mrs-v2.sh — open 4 NEW archetypal MRs against governance-demo-app.
#
# This is the Days 20-23 expansion seeded by docs/days-20-23-demo-coverage.md.
# v1 (scripts/seed-archetype-mrs.sh) opened MRs !9-!13. This v2 opens four more
# to lift rubric-rule coverage from 10/15 → 14/15 and bring the demo into the
# spec §9 target band of 8-12 archetype MRs.
#
# New archetypes:
#   6 — feat(refunds): admin refund-all per #220   → spec-implementation-match (E)
#                                                  + auth-on-new-public-endpoints (B)
#   7 — fix(billing): skip flaky Stripe tests      → no-skipped-tests-introduced (E)
#                                                  + no-commented-out-code (I)
#   8 — refactor(auth): simplify token validation  → no-commented-out-code (I)
#   9 — feat(slo): adopt SLO + rewrite hot path    → error-budget-impact-declared (W)
#
# Pre-req for archetype 9: an `slo.yaml` must exist on `main`. The script
# commits it first as a single non-MR chore commit.
#
# Run from WSL (gcloud SSL is blocked by Norton MITM on the Windows side).
# Idempotent re-runs will fail on branch creation if the branch already exists;
# delete the stale branches first or change the names.

set -euo pipefail

PROJ_ID="${PROJ_ID:-82289558}"
GCP_PROJECT="${GCP_PROJECT:-aicin-477004}"

log() { printf '\033[1;34m[v2-archetype]\033[0m %s\n' "$*"; }

TOKEN=$(gcloud secrets versions access latest \
  --secret=mr-sentinel-gitlab-token \
  --project="$GCP_PROJECT" | tr -d '\n')
export TOKEN PROJ_ID

# --- Helpers (identical to v1; copied here to keep the script self-contained) -

create_branch() {
  local branch="$1"
  curl -sS -X POST -H "PRIVATE-TOKEN: $TOKEN" \
    -o /tmp/branch-resp.json -w '%{http_code}' \
    "https://gitlab.com/api/v4/projects/$PROJ_ID/repository/branches?branch=$branch&ref=main"
}

commit_actions_file() {
  curl -sS -X POST -H "PRIVATE-TOKEN: $TOKEN" -H "Content-Type: application/json" \
    --data @/tmp/commit-payload.json \
    -o /tmp/commit-resp.json -w '%{http_code}' \
    "https://gitlab.com/api/v4/projects/$PROJ_ID/repository/commits"
}

build_payload() {
  python3 -c "
import json, sys
print(json.dumps({
    'branch': sys.argv[1],
    'commit_message': sys.argv[2],
    'actions': json.loads(sys.argv[3]),
}))
" "$1" "$2" "$3" > /tmp/commit-payload.json
}

open_mr_with() {
  python3 -c "
import json, sys
print(json.dumps({
    'source_branch': sys.argv[1],
    'target_branch': 'main',
    'title': sys.argv[2],
    'description': sys.argv[3],
    'remove_source_branch': False,
}))
" "$1" "$2" "$3" > /tmp/mr-payload.json

  curl -sS -X POST -H "PRIVATE-TOKEN: $TOKEN" -H "Content-Type: application/json" \
    --data @/tmp/mr-payload.json \
    -o /tmp/mr-resp.json -w '  http=%{http_code}\n' \
    "https://gitlab.com/api/v4/projects/$PROJ_ID/merge_requests"

  python3 -c "
import json
d = json.load(open('/tmp/mr-resp.json'))
if d.get('iid'):
    print(f'  !{d[\"iid\"]}  {d[\"web_url\"]}')
else:
    print(f'  ERROR: {d}')
"
}

b64() { printf '%s' "$1" | base64 -w0; }

single_file_commit() {
  local branch="$1" msg="$2" action="$3" path="$4" content="$5"
  local b64content
  b64content=$(printf '%s' "$content" | base64 -w0)
  local actions
  actions=$(python3 -c "
import json, sys
print(json.dumps([{
    'action': sys.argv[1],
    'file_path': sys.argv[2],
    'encoding': 'base64',
    'content': sys.argv[3],
}]))" "$action" "$path" "$b64content")
  build_payload "$branch" "$msg" "$actions"
  commit_actions_file
  echo
}

# Direct-to-main commit (no MR) — for the slo.yaml preamble before archetype 9.
commit_to_main() {
  local msg="$1" path="$2" content="$3"
  local b64content actions
  b64content=$(printf '%s' "$content" | base64 -w0)
  actions=$(python3 -c "
import json, sys
print(json.dumps([{
    'action': sys.argv[1],
    'file_path': sys.argv[2],
    'encoding': 'base64',
    'content': sys.argv[3],
}]))" "create" "$path" "$b64content")
  build_payload "main" "$msg" "$actions"
  commit_actions_file
  echo
}

# ===========================================================================
# Archetype 6 — out-of-scope feature creep + missing auth
# ===========================================================================
log "1/4 — feat(refunds): admin refund-all per #220 (out-of-scope + auth-missing)"
BRANCH="feature/admin-refund-all"
log "  branch http=$(create_branch "$BRANCH")"

# The MR description references a spec issue #220 that says "audit-only" but
# the diff adds a destructive endpoint, so spec-implementation-match should
# fire. Plus the new route has no auth decoration — auth-on-new-public-endpoints.
read -r -d '' REFUNDS_PY << 'PYEOF' || true
"""Refund endpoints — per spec #220 (audit-only read access to refund records)."""
from __future__ import annotations
from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Invoice

router = APIRouter()


@router.get("/refunds")
async def list_refunds(session: Annotated[AsyncSession, Depends(get_session)]) -> list[dict]:
    """Read-only refund audit log per spec #220."""
    result = await session.execute(
        select(Invoice).where(Invoice.refunded_at.is_not(None))
    )
    return [{"invoice_id": str(i.id), "refunded_at": i.refunded_at.isoformat()} for i in result.scalars()]


@router.post("/refund-all")
async def refund_all(session: Annotated[AsyncSession, Depends(get_session)]) -> dict:
    """Mass refund — useful for ops when a batch goes wrong. Returns count."""
    result = await session.execute(
        select(Invoice).where(Invoice.paid_at.is_not(None), Invoice.refunded_at.is_(None))
    )
    invoices = list(result.scalars())
    for inv in invoices:
        inv.refunded_at = sa.func.now()
    await session.commit()
    return {"refunded_count": len(invoices)}
PYEOF

read -r -d '' MAIN_PY_WITH_REFUNDS << 'PYEOF' || true
"""Medbill FastAPI app — service entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.db import engine
from app.routes import admin, auth, invoices, patients, refunds

logger = logging.getLogger("medbill")
logging.basicConfig(level=settings.LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("medbill starting — env=%s", settings.ENVIRONMENT)
    yield
    await engine.dispose()
    logger.info("medbill shut down cleanly")


app = FastAPI(
    title="Medbill",
    description="Medical billing and invoicing platform for outpatient clinics",
    version="0.5.0",
    lifespan=lifespan,
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(patients.router, prefix="/patients", tags=["patients"])
app.include_router(invoices.router, prefix="/invoices", tags=["invoices"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(refunds.router, prefix="/refunds", tags=["refunds"])


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "medbill", "version": app.version}
PYEOF

ACTIONS=$(python3 -c "
import json, sys
print(json.dumps([
    {'action': 'create', 'file_path': 'app/routes/refunds.py',
     'encoding': 'base64', 'content': sys.argv[1]},
    {'action': 'update', 'file_path': 'app/main.py',
     'encoding': 'base64', 'content': sys.argv[2]},
]))" "$(b64 "$REFUNDS_PY")" "$(b64 "$MAIN_PY_WITH_REFUNDS")")

build_payload "$BRANCH" "feat(refunds): admin refund-all per #220" "$ACTIONS"
log "  commit http=$(commit_actions_file)"
echo
log "  MR:"
open_mr_with "$BRANCH" \
  "feat(refunds): admin refund-all per #220" \
  "Closes #220 (audit-only access to refund records). Adds GET /refunds/refunds for the audit log + POST /refunds/refund-all for ops mass-refund. Both routes registered under /refunds prefix."

# ===========================================================================
# Archetype 7 — no-skipped-tests-introduced
# ===========================================================================
log "2/4 — fix(billing): skip flaky Stripe retry tests"
BRANCH="fix/skip-stripe-retry-tests"
log "  branch http=$(create_branch "$BRANCH")"

read -r -d '' TEST_BILLING_PY << 'PYEOF' || true
"""Billing service tests."""
from __future__ import annotations

import pytest
import stripe

from app.services import charge_invoice, _build_charge_metadata


def test_build_charge_metadata_returns_invoice_id():
    meta = _build_charge_metadata("inv-123")
    assert meta["invoice_id"] == "inv-123"
    assert meta["source"] == "medbill"


@pytest.mark.skip
async def test_charge_invoice_creates_stripe_charge():
    """Disabled — Stripe test mode is flaky in CI lately."""
    charge = await charge_invoice("inv-999", 1500, "usd")
    assert charge["amount"] == 1500


@pytest.mark.skip
async def test_charge_invoice_retries_on_rate_limit():
    """Disabled."""
    # Old version:
    # charge = await charge_invoice_with_retry("inv-999", 1500, "usd", max_retries=3)
    # assert charge["amount"] == 1500
    pass


def test_charge_invoice_uses_lowercase_currency():
    # Smoke-only — does not actually call Stripe, just verifies the kwarg path.
    pass
PYEOF

single_file_commit "$BRANCH" \
  "fix(billing): skip flaky Stripe retry tests in CI" \
  "create" "tests/test_billing.py" "$TEST_BILLING_PY"
log "  MR:"
open_mr_with "$BRANCH" \
  "fix(billing): skip flaky Stripe retry tests in CI" \
  "Stripe test mode has been flaky in CI for the last week. Skipping the two retry tests until the upstream stabilizes. Will re-enable in a follow-up."

# ===========================================================================
# Archetype 8 — no-commented-out-code
# ===========================================================================
log "3/4 — refactor(auth): simplify token validation"
BRANCH="refactor/auth-token-simplify"
log "  branch http=$(create_branch "$BRANCH")"

read -r -d '' AUTH_PY << 'PYEOF' || true
"""JWT validation helpers — Medbill auth layer."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import jwt

from app.config import settings

logger = logging.getLogger("medbill.auth")


def validate_token(token: str) -> dict:
    """Decode and validate a JWT. Returns the payload dict on success."""
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])


# def validate_token_old(token: str) -> dict | None:
#     """Old validator — pre-refactor. Kept in comments for reference until we
#     confirm the new one handles all the edge cases observed in production
#     during Q1. Specifically the clock-skew issue from incident INC-2148 and
#     the audience claim mismatch from INC-2203."""
#     try:
#         payload = jwt.decode(
#             token,
#             settings.JWT_SECRET,
#             algorithms=[settings.JWT_ALGORITHM],
#             options={"verify_aud": False},
#         )
#     except jwt.ExpiredSignatureError:
#         logger.warning("token expired")
#         return None
#     except jwt.InvalidTokenError as e:
#         logger.warning("invalid token: %s", e)
#         return None
#
#     exp = payload.get("exp")
#     if exp:
#         exp_dt = datetime.fromtimestamp(exp, tz=timezone.utc)
#         if exp_dt < datetime.now(tz=timezone.utc):
#             logger.warning("token explicitly past exp")
#             return None
#
#     iss = payload.get("iss")
#     if iss and iss != settings.JWT_ISSUER:
#         logger.warning("token iss mismatch: %s vs %s", iss, settings.JWT_ISSUER)
#         return None
#
#     return payload
PYEOF

single_file_commit "$BRANCH" \
  "refactor(auth): simplify validate_token" \
  "create" "app/auth.py" "$AUTH_PY"
log "  MR:"
open_mr_with "$BRANCH" \
  "refactor(auth): simplify validate_token" \
  "Simplifies the validator. The new version delegates the edge-case handling to PyJWT defaults. Old version preserved as a comment for reference until QA signs off."

# ===========================================================================
# Preamble for Archetype 9 — commit slo.yaml directly to main
# ===========================================================================
log "preamble — commit slo.yaml directly to main (no MR)"

read -r -d '' SLO_YAML << 'YAMLEOF' || true
# Medbill service-level objectives.
# Sentinel reads this file to know which services have an SLO; MRs touching
# files listed under `hot_paths` should include an error-budget impact note
# in the description.

services:
  billing:
    availability_slo: 99.9
    latency_slo_p95_ms: 800
    error_budget_window_days: 30
    hot_paths:
      - app/services.py
      - app/routes/invoices.py
  patients:
    availability_slo: 99.5
    latency_slo_p95_ms: 1200
    error_budget_window_days: 30
    hot_paths:
      - app/routes/patients.py
YAMLEOF

commit_to_main \
  "chore(slo): adopt explicit SLO definitions" \
  "slo.yaml" "$SLO_YAML"

# ===========================================================================
# Archetype 9 — error-budget-impact-declared
# ===========================================================================
log "4/4 — feat(slo): rewrite invoice hot path"
BRANCH="feature/invoices-hot-path-rewrite"
log "  branch http=$(create_branch "$BRANCH")"

read -r -d '' SERVICES_PY_NEW << 'PYEOF' || true
"""Billing service + Stripe client wrapper — rewritten hot path."""

from __future__ import annotations

import asyncio
import logging

import stripe

from app.config import settings

logger = logging.getLogger("medbill.services")

stripe.api_key = settings.STRIPE_API_KEY


def _build_charge_metadata(invoice_id: str) -> dict[str, str]:
    return {"invoice_id": invoice_id, "source": "medbill"}


async def charge_invoice(invoice_id: str, amount_cents: int, currency: str = "USD") -> dict:
    """Hot path — rewrite uses gather() to parallelize the metadata lookup with
    the Stripe call. Net latency improvement target: ~40% on p95."""
    logger.info("charging invoice %s for %s %d", invoice_id, currency, amount_cents)

    # Parallelize metadata + charge intent.
    async def _meta() -> dict[str, str]:
        return _build_charge_metadata(invoice_id)

    async def _charge() -> dict:
        return stripe.Charge.create(
            amount=amount_cents,
            currency=currency.lower(),
            description=f"Medbill invoice {invoice_id}",
        )

    metadata, charge = await asyncio.gather(_meta(), _charge())
    charge["metadata"] = metadata
    return charge
PYEOF

single_file_commit "$BRANCH" \
  "perf(billing): parallelize metadata + charge call" \
  "update" "app/services.py" "$SERVICES_PY_NEW"
log "  MR:"
open_mr_with "$BRANCH" \
  "perf(billing): parallelize metadata + charge call" \
  "Rewrites the charge_invoice hot path to gather() the metadata lookup with the Stripe call. Net latency improvement target ~40% on p95. Closes #305."

log "v2 done — 4 new archetypes opened. webhook → agent eval should start within seconds."
log "expected coverage uplift: 10/15 rules → 14/15 rules. See docs/days-20-23-demo-coverage.md."
