"""ADK agent that evaluates an MR using the GitLab MCP server + Gemini.

Replaces the legacy direct-Vertex evaluation (app.agent_runner.AgentRunner) with a
Google ADK LlmAgent (Gemini 2.5 Flash) whose context-gathering tools come from a
GitLab MCP server (zereight/gitlab-mcp over stdio). The agent fetches the MR, its
diffs, and pipelines THROUGH the MCP server, applies the rubric, then calls the
local record_verdict tool to emit the structured score.

Write-backs (comment/labels/issue) remain on app.gitlab_client (REST) — see
docs/superpowers/plans/2026-06-08-adk-gitlab-mcp.md.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("mr_sentinel.adk")

# GitLab MCP tools the agent is allowed to call (read-only context gathering).
GITLAB_MCP_TOOL_FILTER = [
    "get_merge_request",
    "get_merge_request_diffs",
    "list_merge_request_pipelines",
]


@dataclass
class VerdictCollector:
    """Mutable holder the record_verdict tool writes the final structured score into."""

    payload: dict[str, Any] | None = None


def make_record_verdict(collector: VerdictCollector):
    """Build the record_verdict callable bound to a collector.

    The agent MUST call this exactly once with its final structured evaluation.
    Returned function has an explicit signature + docstring so ADK can derive the
    tool schema from it.
    """

    def record_verdict(
        overall_score: float,
        verdict: str,
        summary: str,
        rule_evaluations: list[dict],
    ) -> dict:
        """Record the final MR evaluation. Call once, last, after applying the rubric.

        Args:
            overall_score: 0-10. Failing blockers => <= 3.
            verdict: one of "pass", "warn", "block".
            summary: one or two sentences explaining the verdict.
            rule_evaluations: list of {rule_id, outcome(pass|fail|skip), evidence, remediation?}.
        """
        collector.payload = {
            "overall_score": overall_score,
            "verdict": verdict,
            "summary": summary,
            "rule_evaluations": rule_evaluations,
        }
        return {"status": "recorded"}

    return record_verdict
