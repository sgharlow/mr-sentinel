"""MR Sentinel webhook handler — entry point for GitLab MR events."""

from __future__ import annotations

import hmac
import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request, status

logger = logging.getLogger("mr_sentinel")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Open DB pool on startup, close on shutdown (lazy init via persistence module)."""
    yield
    try:
        from app.persistence import close_pool
        await close_pool()
    except Exception as exc:
        logger.warning("error closing DB pool on shutdown: %s", exc)


app = FastAPI(title="MR Sentinel", version="0.2.0", lifespan=lifespan)


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
    """Full agent loop: fetch MR + diffs → evaluate → persist → post comment."""
    object_kind = event.get("object_kind", "<unknown>")
    object_attrs = event.get("object_attributes", {}) or {}
    mr_iid = object_attrs.get("iid")
    project_path = (event.get("project") or {}).get("path_with_namespace")
    action = object_attrs.get("action")

    logger.info("received gitlab event kind=%s project=%s mr_iid=%s action=%s",
                object_kind, project_path, mr_iid, action)

    if object_kind != "merge_request":
        logger.info("ignoring non-MR event")
        return
    if not project_path or not mr_iid:
        logger.warning("event missing project_path or mr_iid; skipping")
        return
    if action not in ("open", "reopen", "update"):
        logger.info("ignoring action=%s (only open/reopen/update trigger evaluation)", action)
        return

    # Lazy imports so this module can be imported without DB/Vertex deps at test time
    from app.agent_runner import AgentRunner, render_comment
    from app.gitlab_client import GitLabClient
    from app.persistence import audit, persist_evaluation

    try:
        async with GitLabClient() as gl:
            mr = await gl.get_merge_request(project_path, mr_iid)
            diffs = await gl.get_merge_request_diffs(project_path, mr_iid)
            logger.info("fetched MR + %d diff entries", len(diffs))

            runner = AgentRunner()
            evaluation = await runner.evaluate(mr, diffs)
            logger.info("evaluation: score=%.1f verdict=%s rules=%d",
                        evaluation.overall_score, evaluation.verdict, len(evaluation.rule_evaluations))

            score_id = await persist_evaluation(mr, evaluation)
            comment_body = render_comment(evaluation, mr)
            note_id = await gl.post_merge_request_comment(project_path, mr_iid, comment_body)
            logger.info("posted comment note_id=%s on MR !%s (score_id=%s)", note_id, mr_iid, score_id)

            if evaluation.verdict == "block":
                await gl.add_merge_request_labels(project_path, mr_iid, ["blocked-compliance", "mr-sentinel-reviewed"])
            else:
                await gl.add_merge_request_labels(project_path, mr_iid, ["mr-sentinel-reviewed"])

            await audit(
                actor="mr-sentinel", action="evaluate",
                project_path=project_path, mr_iid=mr_iid,
                details={"score": evaluation.overall_score, "verdict": evaluation.verdict, "note_id": note_id},
            )
    except Exception as exc:
        logger.exception("agent loop failed for %s!%s: %s", project_path, mr_iid, exc)
        try:
            from app.persistence import audit as _audit
            await _audit(actor="mr-sentinel", action="error",
                         project_path=project_path, mr_iid=mr_iid,
                         details={"error": str(exc)[:500]})
        except Exception:
            pass


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
