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
from app.agent_runner import build_system_prompt, evaluation_from_payload, Evaluation

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


# ---------------------------------------------------------------------------
# Agent runner — builds an LlmAgent (Gemini + GitLab MCP + record_verdict) and
# drives it to completion. Imported at module top (no cycle: agent_runner does
# not import adk_agent).
# ---------------------------------------------------------------------------

EVAL_USER_PROMPT = (
    "Evaluate merge request {project}!{iid}.\n"
    "1. Call get_merge_request, get_merge_request_diffs, and list_merge_request_pipelines "
    "to gather the MR title, description, diff, and pipeline status.\n"
    "2. Apply EVERY rule in the rubric (in your system instruction) to the diff.\n"
    "3. Then call record_verdict exactly once with your structured scoring. "
    "Do not write any prose response — record_verdict is your only output."
)


class _AdkRunner:
    """Real runner: assembles the LlmAgent (Gemini + GitLab MCP + record_verdict) and runs it."""

    def __init__(self, record_verdict, *, rubric: dict[str, Any]):
        from google.adk.agents import LlmAgent
        from google.adk.tools import FunctionTool
        from google.adk.runners import InMemoryRunner

        self._InMemoryRunner = InMemoryRunner
        toolset = build_gitlab_mcp_toolset()
        self._agent = LlmAgent(
            name="mr_sentinel_evaluator",
            model=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
            instruction=build_system_prompt(rubric),
            tools=[toolset, FunctionTool(record_verdict)],
        )

    async def run_and_collect(self, *, project_path: str, mr_iid: int) -> None:
        from google.genai import types

        runner = self._InMemoryRunner(self._agent, app_name="mr-sentinel")
        session = await runner.session_service.create_session(
            app_name="mr-sentinel", user_id="mr-sentinel"
        )
        message = types.Content(
            role="user",
            parts=[types.Part(text=EVAL_USER_PROMPT.format(project=project_path, iid=mr_iid))],
        )
        async for event in runner.run_async(
            user_id="mr-sentinel", session_id=session.id, new_message=message
        ):
            # record_verdict side-effects into the collector; drain events, but
            # surface any model-side error so a "no verdict" failure is debuggable.
            if getattr(event, "error_code", None) or getattr(event, "error_message", None):
                logger.warning("ADK agent error event: code=%s msg=%s",
                               getattr(event, "error_code", None),
                               getattr(event, "error_message", None))


class AdkAgentRunner:
    """Evaluate an MR via an ADK agent that reads context through the GitLab MCP server."""

    def __init__(
        self,
        *,
        rubric: dict[str, Any] | None = None,
        runner_factory: Any = None,
    ) -> None:
        if rubric is None:
            from app.agent_runner import load_rubric
            rubric = load_rubric()
        self.rubric = rubric
        self._runner_factory = runner_factory or _AdkRunner

    async def evaluate(self, project_path: str, mr_iid: int) -> Evaluation:
        collector = VerdictCollector()
        record_verdict = make_record_verdict(collector)
        runner = self._runner_factory(record_verdict, rubric=self.rubric)
        logger.info("ADK evaluate %s!%s via GitLab MCP", project_path, mr_iid)
        await runner.run_and_collect(project_path=project_path, mr_iid=mr_iid)
        if collector.payload is None:
            raise RuntimeError(f"agent did not record a verdict for {project_path}!{mr_iid}")
        return evaluation_from_payload(
            collector.payload, rubric_version=self.rubric.get("version", "")
        )
