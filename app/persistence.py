"""Cloud SQL persistence — asyncpg pool + score/audit writes."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import asyncpg

from app.agent_runner import Evaluation
from app.gitlab_client import MergeRequest

logger = logging.getLogger("mr_sentinel.persistence")

_pool: asyncpg.Pool | None = None


def _connection_kwargs() -> dict[str, Any]:
    """Build asyncpg connection kwargs from env (Cloud Run unix socket aware)."""
    host = os.environ.get("DB_HOST", "127.0.0.1")
    name = os.environ.get("DB_NAME", "mrsentinel")
    user = os.environ.get("DB_USER", "app")
    password = os.environ.get("DB_PASSWORD", "")

    kwargs: dict[str, Any] = {"database": name, "user": user, "password": password}
    if host.startswith("/cloudsql/"):
        # Unix socket path on Cloud Run; asyncpg uses `host` for socket dir.
        kwargs["host"] = host
    else:
        kwargs["host"] = host
        kwargs["port"] = int(os.environ.get("DB_PORT", "5432"))
    return kwargs


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        kwargs = _connection_kwargs()
        logger.info("creating asyncpg pool host=%s database=%s user=%s",
                    kwargs.get("host"), kwargs.get("database"), kwargs.get("user"))
        _pool = await asyncpg.create_pool(min_size=1, max_size=4, **kwargs)
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def persist_evaluation(mr: MergeRequest, evaluation: Evaluation) -> int:
    """Insert mr_scores row + rule_outcomes children. Returns mr_scores.id."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            score_id = await conn.fetchval(
                """
                INSERT INTO mr_scores
                    (project_path, mr_iid, commit_sha, rubric_version, overall_score, verdict, raw_evaluation)
                VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb)
                ON CONFLICT (project_path, mr_iid, commit_sha, rubric_version)
                DO UPDATE SET
                    overall_score = EXCLUDED.overall_score,
                    verdict = EXCLUDED.verdict,
                    raw_evaluation = EXCLUDED.raw_evaluation,
                    scored_at = NOW()
                RETURNING id
                """,
                mr.project_path, mr.iid, mr.sha, evaluation.rubric_version,
                evaluation.overall_score, evaluation.verdict,
                json.dumps(evaluation.raw_response),
            )

            # Replace child rows (idempotent for re-evaluations)
            await conn.execute("DELETE FROM rule_outcomes WHERE mr_score_id = $1", score_id)

            rubric_by_id = {r["rule_id"]: r for r in _load_rubric_rules()}

            for r in evaluation.rule_evaluations:
                rule_meta = rubric_by_id.get(r.rule_id, {})
                await conn.execute(
                    """
                    INSERT INTO rule_outcomes
                        (mr_score_id, rule_id, category, outcome, severity, message, remediation, control_mapping)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    """,
                    score_id, r.rule_id,
                    rule_meta.get("category", "unknown"),
                    r.outcome,
                    rule_meta.get("severity", "info"),
                    r.evidence,
                    r.remediation,
                    rule_meta.get("control_mapping", []),
                )

            logger.info("persisted mr_score id=%s rules=%d", score_id, len(evaluation.rule_evaluations))
    return int(score_id)


async def already_evaluated(
    project_path: str, mr_iid: int, commit_sha: str, rubric_version: str
) -> bool:
    """Return True if (project, mr_iid, sha, rubric_version) was already scored.

    Used to short-circuit re-evaluation when GitLab fires an update event that
    didn't change the diff (label change, description edit, etc.).
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        return bool(await conn.fetchval(
            """
            SELECT EXISTS(
                SELECT 1 FROM mr_scores
                WHERE project_path = $1 AND mr_iid = $2
                  AND commit_sha = $3 AND rubric_version = $4
            )
            """,
            project_path, mr_iid, commit_sha, rubric_version,
        ))


async def audit(actor: str, action: str, project_path: str | None = None,
                mr_iid: int | None = None, details: dict[str, Any] | None = None) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO audit_log (actor, action, project_path, mr_iid, details)
            VALUES ($1, $2, $3, $4, $5::jsonb)
            """,
            actor, action, project_path, mr_iid, json.dumps(details or {}),
        )


def _load_rubric_rules() -> list[dict[str, Any]]:
    from app.agent_runner import load_rubric
    return load_rubric().get("rules", [])
