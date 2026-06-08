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
from dataclasses import dataclass
from typing import Any

# Imported at module top so tests can monkeypatch these names on the module.
# (verified google-adk 2.2.0): MCPToolset + StdioConnectionParams come from
# google.adk.tools.mcp_tool; StdioServerParameters comes from `mcp`.
from google.adk.tools.mcp_tool import MCPToolset, StdioConnectionParams
from mcp import StdioServerParameters

logger = logging.getLogger("mr_sentinel.adk")

# GitLab MCP tools the agent is allowed to call (read-only context gathering).
GITLAB_MCP_TOOL_FILTER = [
    "get_merge_request",
    "get_merge_request_diffs",
    "list_merge_request_pipelines",
]

# `npm install -g @zereight/mcp-gitlab` installs this binary on PATH (see Dockerfile).
GITLAB_MCP_COMMAND = os.environ.get("GITLAB_MCP_COMMAND", "mcp-gitlab")


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


def build_gitlab_mcp_toolset() -> MCPToolset:
    """Construct an ADK MCPToolset backed by the zereight GitLab MCP server (stdio).

    Reuses the same PAT the REST client uses (GITLAB_TOKEN) and the same base URL
    (GITLAB_BASE_URL), translated to the env names the zereight server expects.
    """
    token = (os.environ.get("GITLAB_TOKEN") or "").strip()
    if not token:
        raise RuntimeError("GITLAB_TOKEN is required to launch the GitLab MCP server")
    base_url = (os.environ.get("GITLAB_BASE_URL") or "https://gitlab.com").rstrip("/")
    server_params = StdioServerParameters(
        command=GITLAB_MCP_COMMAND,
        args=[],
        env={
            "GITLAB_PERSONAL_ACCESS_TOKEN": token,
            "GITLAB_API_URL": f"{base_url}/api/v4",
            # Read-only posture for the evaluation agent; write tools stay on REST.
            "GITLAB_READ_ONLY_MODE": "true",
            "PATH": os.environ.get("PATH", ""),
        },
    )
    return MCPToolset(
        connection_params=StdioConnectionParams(server_params=server_params, timeout=30.0),
        tool_filter=GITLAB_MCP_TOOL_FILTER,
    )
