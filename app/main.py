"""MR Sentinel webhook handler — entry point for GitLab MR events."""

from __future__ import annotations

import hmac
import logging
import os
from typing import Any

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request, status

logger = logging.getLogger("mr_sentinel")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

app = FastAPI(title="MR Sentinel", version="0.1.0")


def _expected_webhook_secret() -> str | None:
    """Return the configured GitLab webhook secret, or None if unset (dev mode)."""
    value = os.environ.get("GITLAB_WEBHOOK_SECRET")
    if value is None:
        return None
    # Cloud Run injects Secret Manager values verbatim, so trailing newlines from
    # `openssl rand | gcloud secrets versions add` survive into the container env.
    return value.strip() or None


def _verify_token(provided: str | None) -> bool:
    """Constant-time compare the inbound X-Gitlab-Token header against config."""
    expected = _expected_webhook_secret()
    if expected is None:
        return True
    if provided is None:
        return False
    return hmac.compare_digest(provided, expected)


async def _process_mr_event(event: dict[str, Any]) -> None:
    """Background handoff. Day 4-8 milestone wires this into Agent Builder."""
    object_kind = event.get("object_kind", "<unknown>")
    object_attrs = event.get("object_attributes", {}) or {}
    mr_iid = object_attrs.get("iid")
    project = (event.get("project") or {}).get("path_with_namespace")
    logger.info(
        "received gitlab event kind=%s project=%s mr_iid=%s action=%s",
        object_kind,
        project,
        mr_iid,
        object_attrs.get("action"),
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/gitlab/webhook", status_code=status.HTTP_202_ACCEPTED)
async def gitlab_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_gitlab_token: str | None = Header(default=None, alias="X-Gitlab-Token"),
    x_gitlab_event: str | None = Header(default=None, alias="X-Gitlab-Event"),
) -> dict[str, str]:
    if not _verify_token(x_gitlab_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid webhook token")

    try:
        payload = await request.json()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid json") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="payload must be an object")

    background_tasks.add_task(_process_mr_event, payload)
    return {"status": "accepted", "event": x_gitlab_event or "unknown"}
