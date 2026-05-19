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


app = FastAPI(title="MR Sentinel", version="0.4.0", lifespan=lifespan)

from app.dashboard import router as dashboard_router  # noqa: E402
app.include_router(dashboard_router)


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
    """Full agent loop. Days 9-14 additions:
    - sha-based dedup (skip if commit_sha already scored)
    - upsert comment (edit existing instead of posting new)
    - linked remediation issue on verdict=block
    - pipeline + vulnerability tool calls (6+ tools per run)
    """
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

    from app.agent_runner import (
        AgentRunner,
        PROJECT_OVERRIDE_PATH,
        RubricValidationError,
        parse_rubric,
        render_comment,
        render_followup_issue_body,
    )
    from app.gitlab_client import GitLabClient
    from app.persistence import already_evaluated, audit, persist_evaluation

    try:
        async with GitLabClient() as gl:
            # Tool 1: fetch MR (gives us the commit sha for dedup)
            mr = await gl.get_merge_request(project_path, mr_iid)

            # Tool 2: per-project rubric override (`.mr-sentinel.yaml` at repo root).
            # Resolved BEFORE the dedup check so the dedup key includes the
            # actually-active rubric version (not a hardcoded "v1"). Fail-closed
            # semantics: if present but invalid, audit, fall back to bundled v1.
            override_yaml = await gl.get_file_content(project_path, PROJECT_OVERRIDE_PATH)
            override_rubric = None
            override_source = "bundled"
            if override_yaml is not None:
                try:
                    override_rubric = parse_rubric(override_yaml)
                    override_source = "project_override"
                    logger.info("using project override rubric (%s)", override_rubric.get("version"))
                except RubricValidationError as exc:
                    logger.warning("invalid .mr-sentinel.yaml — falling back to bundled: %s", exc)
                    await audit(actor="mr-sentinel", action="override_invalid",
                                project_path=project_path, mr_iid=mr_iid,
                                details={"error": str(exc)[:300]})
                    override_source = "bundled_after_invalid_override"

            # Active version for dedup: override's version if valid, else "v1" (bundled).
            active_rubric_version = (override_rubric or {}).get("version") or "v1"

            # Dedup check: skip if same commit already scored under the active rubric
            if await already_evaluated(project_path, mr_iid, mr.sha, active_rubric_version):
                logger.info("skipping re-evaluation — sha %s already scored under %s",
                            mr.sha[:8], active_rubric_version)
                await audit(actor="mr-sentinel", action="skip_duplicate",
                            project_path=project_path, mr_iid=mr_iid,
                            details={"sha": mr.sha[:8], "reason": "already_evaluated",
                                     "rubric_version": active_rubric_version})
                return

            # Tool 3: fetch diffs
            diffs = await gl.get_merge_request_diffs(project_path, mr_iid)

            # Tool 4: latest pipeline for this commit
            pipeline = await gl.get_latest_pipeline_for_sha(project_path, mr.sha)
            pipeline_status = pipeline["status"] if pipeline else None

            # Tool 5: pipeline jobs (only when pipeline exists; saves a noop call otherwise)
            pipeline_jobs = []
            if pipeline:
                pipeline_jobs = await gl.list_pipeline_jobs(project_path, pipeline["id"])

            # Tool 6: vulnerability findings (gracefully empty on Free tier)
            advisories = await gl.list_vulnerability_findings(project_path)

            logger.info(
                "fetched MR + %d diffs, pipeline=%s, jobs=%d, advisories=%d, rubric=%s",
                len(diffs), pipeline_status, len(pipeline_jobs), len(advisories), override_source,
            )

            runner = AgentRunner(rubric=override_rubric)
            evaluation = await runner.evaluate(mr, diffs)
            logger.info("evaluation: score=%.1f verdict=%s rules=%d",
                        evaluation.overall_score, evaluation.verdict, len(evaluation.rule_evaluations))

            score_id = await persist_evaluation(mr, evaluation)

            # Tool 7: linked remediation issue on block
            followup_issue_url = None
            if evaluation.verdict == "block":
                issue = await gl.create_issue(
                    project_path,
                    title=f"Compliance follow-up for !{mr_iid}: {mr.title[:60]}",
                    description=render_followup_issue_body(evaluation, mr),
                    labels=["mr-sentinel-followup", "blocker"],
                )
                followup_issue_url = issue.get("web_url")
                logger.info("created followup issue !%s — %s", issue.get("iid"), followup_issue_url)

            # Tool 8: upsert comment (find existing, update; else create)
            comment_body = render_comment(
                evaluation, mr,
                followup_issue_url=followup_issue_url,
                pipeline_status=pipeline_status,
            )
            note_id, created = await gl.upsert_merge_request_comment(project_path, mr_iid, comment_body)
            logger.info("%s comment note_id=%s on MR !%s (score_id=%s)",
                        "posted" if created else "updated", note_id, mr_iid, score_id)

            # Tool 9: labels
            labels_to_add = ["mr-sentinel-reviewed"]
            if evaluation.verdict == "block":
                labels_to_add.append("blocked-compliance")
            await gl.add_merge_request_labels(project_path, mr_iid, labels_to_add)

            await audit(
                actor="mr-sentinel", action="evaluate",
                project_path=project_path, mr_iid=mr_iid,
                details={
                    "score": evaluation.overall_score, "verdict": evaluation.verdict,
                    "note_id": note_id, "comment_created": created,
                    "followup_issue_url": followup_issue_url,
                    "pipeline_status": pipeline_status,
                    "rubric_source": override_source,
                    # Count of distinct MR-affecting GitLab actions used (max 8 per
                    # spec §4). The override-fetch is a config read, not an MR
                    # action — it's recorded via rubric_source above.
                    "mr_action_calls": 8 - (0 if pipeline else 1) - (1 if evaluation.verdict != "block" else 0),
                },
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
