# ADK + GitLab MCP Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make MR Sentinel genuinely use all three hackathon-required technologies at runtime — Gemini, Google Cloud Agent Builder (ADK), and the GitLab (partner) MCP server — by replacing the hand-coded Gemini evaluation step with an ADK `LlmAgent` that fetches MR context through a GitLab MCP server.

**Architecture:** The deterministic control flow in `app/main.py` (webhook parse, rubric override, sha-dedup, persistence, audit) is preserved. Only the *evaluation* step changes: instead of pre-fetching diffs over REST and calling Vertex `generate_content` directly, an ADK agent (Gemini 2.5 Flash) calls GitLab MCP read tools (`get_merge_request`, `get_merge_request_diffs`, `list_merge_request_pipelines`) to gather context, applies the rubric, and returns a structured verdict via a final `record_verdict` function-tool. Write-backs (comment upsert, labels, remediation issue) stay on the existing REST `GitLabClient` so the demo output and the Cloud SQL / dashboard `Evaluation` contract remain byte-identical. This is a deliberate hybrid: the partner MCP server is load-bearing for evaluation reads, REST handles the formatting-sensitive writes.

**Tech Stack:** Python 3.11, FastAPI, `google-adk==2.2.0`, `mcp`, ADK `MCPToolset` (stdio) → `@zereight/mcp-gitlab` (Node) GitLab MCP server, Vertex AI Gemini 2.5 Flash, Cloud Run, Cloud SQL.

**Out of scope (deliberately, for this tier):** Vertex AI Agent Engine deployment (additive later); routing write-backs through MCP; the official GitLab Duo MCP server (Premium/Ultimate-only, OAuth-only, lacks MR-note/label tools — see `docs/mcp-endpoint-audit.md` addendum).

**Environment note:** Unit tests (Tasks 1-5) run anywhere with the project venv. Build + deploy + live verification (Task 7) MUST run from **WSL** (Norton blocks gcloud on Git Bash per portfolio convention). Claude cannot run gcloud/Docker here; Task 7 is a Steve-run runbook.

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `app/agent_runner.py` | Rubric load, prompts, `Evaluation`/`RuleEvaluation` dataclasses, comment/issue rendering, payload→Evaluation mapping | Modify: extract `evaluation_from_payload()` helper (DRY: shared by old + new path) |
| `app/adk_agent.py` | **NEW.** Build the ADK agent + GitLab MCP toolset + `record_verdict` tool; `AdkAgentRunner.evaluate(project_path, mr_iid) -> Evaluation` | Create |
| `app/main.py` | Webhook orchestration | Modify: swap the evaluation step to `AdkAgentRunner`; drop the diffs pre-fetch (agent fetches via MCP); keep MR fetch (dedup) + pipeline fetch (comment status) + all write-backs on REST |
| `requirements.txt` | Runtime deps | Modify: add `google-adk==2.2.0`, `mcp` |
| `Dockerfile` | Container image | Modify: install Node.js + `npm install -g @zereight/mcp-gitlab`; default `GITLAB_API_URL` |
| `tests/test_adk_agent.py` | **NEW.** Unit tests for the ADK runner, record_verdict tool, payload mapping, toolset config — all without real Gemini/MCP/network | Create |
| `docs/adk-mcp-deploy-runbook.md` | **NEW.** WSL deploy + live-verify + re-seed + re-record checklist | Create |
| `docs/mcp-endpoint-audit.md` | Existing migration-reference doc | Modify: add a dated addendum recording the 2026-06-08 official-vs-community findings and the hybrid decision |

---

### Task 1: Safety checkpoint (rollback anchor)

**Files:** none (git only)

- [ ] **Step 1: Confirm green baseline**

Run: `PYTHONPATH=. .venv/Scripts/python.exe -m pytest -q`
Expected: `52 passed`

- [ ] **Step 2: Commit the plan + branch checkpoint**

```bash
git add docs/superpowers/plans/2026-06-08-adk-gitlab-mcp.md
git commit -m "docs: ADK + GitLab MCP integration plan (Path B, hybrid)"
```

This commit is the rollback anchor — `git checkout main` restores the working REST loop in <1 min at any point.

---

### Task 2: Extract `evaluation_from_payload()` (DRY mapping helper)

**Files:**
- Modify: `app/agent_runner.py` (factor mapping out of `AgentRunner._parse_response`)
- Test: `tests/test_adk_agent.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_adk_agent.py`:

```python
from app.agent_runner import evaluation_from_payload, Evaluation


def test_evaluation_from_payload_maps_all_fields():
    payload = {
        "overall_score": 0.0,
        "verdict": "block",
        "summary": "secrets in diff",
        "rule_evaluations": [
            {"rule_id": "no-secrets-in-diff", "outcome": "fail",
             "evidence": "AWS key on line 3", "remediation": "remove it"},
            {"rule_id": "contract-has-spec-link", "outcome": "pass", "evidence": "ok"},
        ],
    }
    ev = evaluation_from_payload(payload, rubric_version="v1")
    assert isinstance(ev, Evaluation)
    assert ev.overall_score == 0.0
    assert ev.verdict == "block"
    assert ev.rubric_version == "v1"
    assert len(ev.rule_evaluations) == 2
    assert ev.rule_evaluations[0].rule_id == "no-secrets-in-diff"
    assert ev.rule_evaluations[0].remediation == "remove it"
    assert ev.rule_evaluations[1].remediation is None


def test_evaluation_from_payload_derives_missing_verdict_and_summary():
    payload = {"overall_score": 2.0, "rule_evaluations": [
        {"rule_id": "r1", "outcome": "fail", "evidence": "bad"}]}
    ev = evaluation_from_payload(payload, rubric_version="v2")
    assert ev.verdict == "block"          # fail + score<=3 -> block
    assert "r1" in ev.summary
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. .venv/Scripts/python.exe -m pytest tests/test_adk_agent.py -q`
Expected: FAIL — `ImportError: cannot import name 'evaluation_from_payload'`

- [ ] **Step 3: Implement the helper and refactor `_parse_response` to use it**

In `app/agent_runner.py`, add this module-level function (place it just above `class AgentRunner`):

```python
def evaluation_from_payload(data: dict[str, Any], *, rubric_version: str) -> Evaluation:
    """Map a structured-score dict (Gemini JSON or record_verdict args) to an Evaluation.

    Shared by the legacy direct-Gemini path (AgentRunner._parse_response) and the
    new ADK path (AdkAgentRunner). Defensive: derives verdict/summary if omitted.
    """
    rule_evals = [
        RuleEvaluation(
            rule_id=r.get("rule_id", "unknown"),
            outcome=r.get("outcome", "skip"),
            evidence=r.get("evidence", ""),
            remediation=r.get("remediation"),
        )
        for r in (data.get("rule_evaluations") or [])
    ]
    overall_score = float(data.get("overall_score", 5.0))
    verdict = data.get("verdict") or _derive_verdict(rule_evals, overall_score)
    summary = data.get("summary") or _derive_summary(rule_evals)
    return Evaluation(
        overall_score=overall_score,
        verdict=verdict,
        summary=summary,
        rule_evaluations=rule_evals,
        rubric_version=rubric_version,
        raw_response=data,
    )
```

Then replace the body of `AgentRunner._parse_response` (everything after the `json.loads`/`isinstance` guards that produce `data`) with:

```python
        return evaluation_from_payload(data, rubric_version=self.rubric.get("version", ""))
```

(Keep the existing `text = response.text` extraction and the JSON-decode / non-object guards above it unchanged.)

- [ ] **Step 4: Run tests to verify pass + no regression**

Run: `PYTHONPATH=. .venv/Scripts/python.exe -m pytest tests/test_adk_agent.py tests/test_agent_runner.py -q`
Expected: PASS (new tests pass; existing `test_agent_runner.py` still green — mapping unchanged)

- [ ] **Step 5: Commit**

```bash
git add app/agent_runner.py tests/test_adk_agent.py
git commit -m "refactor: extract evaluation_from_payload mapping helper (DRY)"
```

---

### Task 3: `record_verdict` function-tool + verdict collector

**Files:**
- Create: `app/adk_agent.py`
- Test: `tests/test_adk_agent.py`

ADK's `LlmAgent.output_schema` disables tool use, so structured output is captured via a final tool the agent must call. The collector holds the payload across the run.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_adk_agent.py`:

```python
from app.adk_agent import VerdictCollector, make_record_verdict


def test_record_verdict_stores_payload_and_acks():
    collector = VerdictCollector()
    record = make_record_verdict(collector)
    out = record(
        overall_score=0.0, verdict="block", summary="secrets",
        rule_evaluations=[{"rule_id": "no-secrets-in-diff", "outcome": "fail", "evidence": "x"}],
    )
    assert out["status"] == "recorded"
    assert collector.payload is not None
    assert collector.payload["verdict"] == "block"
    assert collector.payload["rule_evaluations"][0]["rule_id"] == "no-secrets-in-diff"


def test_collector_starts_empty():
    assert VerdictCollector().payload is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. .venv/Scripts/python.exe -m pytest tests/test_adk_agent.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.adk_agent'`

- [ ] **Step 3: Create `app/adk_agent.py` with the collector + tool factory**

```python
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
```

- [ ] **Step 4: Run tests to verify pass**

Run: `PYTHONPATH=. .venv/Scripts/python.exe -m pytest tests/test_adk_agent.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/adk_agent.py tests/test_adk_agent.py
git commit -m "feat: record_verdict tool + verdict collector for ADK agent"
```

---

### Task 4: GitLab MCP toolset builder

**Files:**
- Modify: `app/adk_agent.py`
- Test: `tests/test_adk_agent.py`

- [ ] **Step 1: Write the failing test**

The test asserts the stdio server params are wired from env (command, token, api url) and the tool filter is applied — without launching Node.

Append to `tests/test_adk_agent.py`:

```python
import app.adk_agent as adk


def test_build_gitlab_mcp_toolset_wires_env(monkeypatch):
    captured = {}

    class FakeMCPToolset:
        def __init__(self, *, connection_params, tool_filter=None):
            captured["connection_params"] = connection_params
            captured["tool_filter"] = tool_filter

    class FakeStdioServerParameters:
        def __init__(self, *, command, args=None, env=None):
            captured["command"] = command
            captured["args"] = args
            captured["env"] = env

    class FakeStdioConnectionParams:
        def __init__(self, *, server_params, timeout=5.0):
            captured["server_params"] = server_params
            captured["timeout"] = timeout

    monkeypatch.setattr(adk, "MCPToolset", FakeMCPToolset)
    monkeypatch.setattr(adk, "StdioServerParameters", FakeStdioServerParameters)
    monkeypatch.setattr(adk, "StdioConnectionParams", FakeStdioConnectionParams)
    monkeypatch.setenv("GITLAB_TOKEN", "glpat-test")
    monkeypatch.setenv("GITLAB_BASE_URL", "https://gitlab.com")

    ts = adk.build_gitlab_mcp_toolset()
    assert isinstance(ts, FakeMCPToolset)
    assert captured["command"] == adk.GITLAB_MCP_COMMAND
    assert captured["env"]["GITLAB_PERSONAL_ACCESS_TOKEN"] == "glpat-test"
    assert captured["env"]["GITLAB_API_URL"] == "https://gitlab.com/api/v4"
    assert captured["tool_filter"] == adk.GITLAB_MCP_TOOL_FILTER


def test_build_gitlab_mcp_toolset_requires_token(monkeypatch):
    monkeypatch.delenv("GITLAB_TOKEN", raising=False)
    monkeypatch.setattr(adk, "MCPToolset", object)
    import pytest
    with pytest.raises(RuntimeError, match="GITLAB_TOKEN"):
        adk.build_gitlab_mcp_toolset()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. .venv/Scripts/python.exe -m pytest tests/test_adk_agent.py -k toolset -q`
Expected: FAIL — `AttributeError: module 'app.adk_agent' has no attribute 'MCPToolset'`

- [ ] **Step 3: Implement the toolset builder**

Add to the imports / body of `app/adk_agent.py`:

```python
# Imported at module top so tests can monkeypatch these names on the module.
# NOTE (verified against google-adk 2.2.0): MCPToolset + StdioConnectionParams are
# exported from google.adk.tools.mcp_tool, but StdioServerParameters comes from `mcp`.
from google.adk.tools.mcp_tool import MCPToolset, StdioConnectionParams  # noqa: E402
from mcp import StdioServerParameters  # noqa: E402

# `npm install -g @zereight/mcp-gitlab` installs this binary on PATH (see Dockerfile).
GITLAB_MCP_COMMAND = os.environ.get("GITLAB_MCP_COMMAND", "mcp-gitlab")


def build_gitlab_mcp_toolset() -> "MCPToolset":
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
```

- [ ] **Step 4: Run tests to verify pass**

Run: `PYTHONPATH=. .venv/Scripts/python.exe -m pytest tests/test_adk_agent.py -k toolset -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/adk_agent.py tests/test_adk_agent.py
git commit -m "feat: GitLab MCP toolset builder (zereight stdio, read-only filter)"
```

---

### Task 5: `AdkAgentRunner.evaluate()` — build agent, run, map result

**Files:**
- Modify: `app/adk_agent.py`
- Test: `tests/test_adk_agent.py`

The runner is injectable: a `runner_factory` lets tests drive a fake run that "calls" record_verdict, with zero Gemini/MCP/network.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_adk_agent.py`:

```python
import asyncio
from app.agent_runner import Evaluation


def test_adk_runner_evaluate_maps_collector_payload():
    rubric = {"version": "v1", "rules": [{"id": "no-secrets-in-diff"}]}

    # Fake runner that, when run, simulates the agent calling record_verdict.
    class FakeRunner:
        def __init__(self, record_verdict, **_):
            self._record = record_verdict

        async def run_and_collect(self, *, project_path, mr_iid):
            # Simulate the agent's terminal tool call.
            self._record(
                overall_score=0.0, verdict="block", summary="secrets in diff",
                rule_evaluations=[{"rule_id": "no-secrets-in-diff", "outcome": "fail",
                                   "evidence": "AWS key", "remediation": "rotate"}],
            )

    runner = adk.AdkAgentRunner(rubric=rubric, runner_factory=FakeRunner)
    ev = asyncio.get_event_loop().run_until_complete(
        runner.evaluate("sgharlow/governance-demo-app", 10)
    )
    assert isinstance(ev, Evaluation)
    assert ev.verdict == "block"
    assert ev.overall_score == 0.0
    assert ev.rubric_version == "v1"
    assert ev.rule_evaluations[0].rule_id == "no-secrets-in-diff"


def test_adk_runner_raises_if_no_verdict_recorded():
    class SilentRunner:
        def __init__(self, record_verdict, **_):
            pass

        async def run_and_collect(self, *, project_path, mr_iid):
            pass  # agent never called record_verdict

    runner = adk.AdkAgentRunner(rubric={"version": "v1"}, runner_factory=SilentRunner)
    import pytest
    with pytest.raises(RuntimeError, match="did not record a verdict"):
        asyncio.get_event_loop().run_until_complete(
            runner.evaluate("p/x", 1)
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. .venv/Scripts/python.exe -m pytest tests/test_adk_agent.py -k adk_runner -q`
Expected: FAIL — `AttributeError: module 'app.adk_agent' has no attribute 'AdkAgentRunner'`

- [ ] **Step 3: Implement `AdkAgentRunner` + the real runner**

Add to `app/adk_agent.py`. The real `_AdkRunner` wraps ADK's `InMemoryRunner`; the `runner_factory` seam swaps it out in tests.

```python
from app.agent_runner import build_system_prompt, evaluation_from_payload  # noqa: E402

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
        async for _event in runner.run_async(
            user_id="mr-sentinel", session_id=session.id, new_message=message
        ):
            pass  # record_verdict side-effects into the collector; we just drain events.


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

    async def evaluate(self, project_path: str, mr_iid: int) -> "Evaluation":
        from app.agent_runner import Evaluation  # noqa: F401  (return type)

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
```

- [ ] **Step 4: Run tests to verify pass**

Run: `PYTHONPATH=. .venv/Scripts/python.exe -m pytest tests/test_adk_agent.py -q`
Expected: PASS (all adk_agent tests)

- [ ] **Step 5: Full suite — confirm no regression**

Run: `PYTHONPATH=. .venv/Scripts/python.exe -m pytest -q`
Expected: PASS — `>= 60 passed` (52 baseline + new), 0 failed

- [ ] **Step 6: Commit**

```bash
git add app/adk_agent.py tests/test_adk_agent.py
git commit -m "feat: AdkAgentRunner evaluates MRs via Gemini + GitLab MCP (ADK)"
```

---

### Task 6: Wire `main.py` to the ADK runner + deps + Dockerfile

**Files:**
- Modify: `app/main.py:80-149` (evaluation step only)
- Modify: `requirements.txt`, `Dockerfile`
- Modify: `docs/mcp-endpoint-audit.md` (addendum)
- Test: `tests/test_webhook.py` (existing — confirm still green with the runner mocked)

- [ ] **Step 1: Inspect how `test_webhook.py` patches the evaluation**

Run: `PYTHONPATH=. .venv/Scripts/python.exe -m pytest tests/test_webhook.py -q`
Expected: PASS (baseline). Read the test to see how it injects a fake evaluation (it patches `AgentRunner` / `GitLabClient`). The wiring change below must keep those seams working; update the patch target to `AdkAgentRunner` if the test patches the runner class by name.

- [ ] **Step 2: Swap the evaluation step in `app/main.py`**

In `_process_mr_event`, change the import block (around line 80) to also import the ADK runner:

```python
    from app.adk_agent import AdkAgentRunner
```

Delete the diffs pre-fetch used only for evaluation (the `# Tool 3: fetch diffs` block) and replace the evaluation call (around lines 148-149):

```python
            runner = AgentRunner(rubric=override_rubric)
            evaluation = await runner.evaluate(mr, diffs)
```

with:

```python
            runner = AdkAgentRunner(rubric=override_rubric)
            evaluation = await runner.evaluate(project_path, mr_iid)
```

Keep everything else (MR fetch for dedup, `get_latest_pipeline_for_sha` for `pipeline_status`, comment upsert, labels, issue, audit) UNCHANGED. Note: `diffs` is no longer available for the `len(diffs)` log line — change that log to drop the diff count or fetch `len` from the audit details. Minimal: change the line
`"fetched MR + %d diffs, pipeline=%s, jobs=%d, advisories=%d, rubric=%s"` to omit diffs, or keep one REST diffs fetch if you want the count. Prefer omitting to avoid a redundant REST call.

- [ ] **Step 3: Add runtime deps**

Append to `requirements.txt`:

```
google-adk==2.2.0
mcp==1.13.1
```

(Pin `mcp` to the version resolved in the venv — run `.venv/Scripts/python.exe -m pip show mcp` and use that exact version.)

**Verified 2026-06-08:** `google-adk==2.2.0` requires `httpx>=0.27,<1`, so it is compatible with the existing `httpx==0.27.2` pin — do NOT bump httpx (a bump to 0.28 breaks `respx==0.21.1` in the GitLab tests). Keep httpx + respx pins unchanged; `pip install -r requirements.txt` resolves cleanly with httpx held at 0.27.2. The full 52-test baseline was confirmed green with google-adk + mcp installed alongside httpx 0.27.2.

- [ ] **Step 4: Add Node + the MCP server to the image**

In `Dockerfile`, after `FROM python:3.11-slim AS base` and before `pip install`, add Node.js and the GitLab MCP server:

```dockerfile
# Node.js + GitLab MCP server (zereight/gitlab-mcp) for the ADK agent's tool transport.
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g @zereight/mcp-gitlab \
    && apt-get purge -y curl gnupg && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

ENV GITLAB_API_URL=https://gitlab.com/api/v4
```

Verify the installed binary name after install: `npm ls -g @zereight/mcp-gitlab` and `which mcp-gitlab`. If the bin is not `mcp-gitlab`, set `GITLAB_MCP_COMMAND` env in the Cloud Run deploy to the actual bin name (Task 7).

- [ ] **Step 5: Add the audit-doc addendum**

Append to `docs/mcp-endpoint-audit.md`:

```markdown
## Addendum — 2026-06-08: hackathon-required MCP integration (Path B)

The Google Cloud Rapid Agent Hackathon requires the partner's MCP server be imported
and called at runtime. The OFFICIAL GitLab Duo MCP server (`gitlab.com/api/v4/mcp`)
is Premium/Ultimate-only, beta, OAuth-DCR-only, and exposes no tool to post/update an
MR note or set MR labels — so it cannot run MR Sentinel's write-backs and is unusable
on this Free-tier account. Decision: use a community GitLab MCP server
(`@zereight/mcp-gitlab`, stdio) via ADK `MCPToolset` for the agent's evaluation READS
(`get_merge_request`, `get_merge_request_diffs`, `list_merge_request_pipelines`).
Write-backs stay on REST (`app/gitlab_client.py`) to keep comment formatting + upsert +
dedup deterministic. See `docs/superpowers/plans/2026-06-08-adk-gitlab-mcp.md`.
```

- [ ] **Step 6: Run the full suite**

Run: `PYTHONPATH=. .venv/Scripts/python.exe -m pytest -q`
Expected: PASS — 0 failed. If `test_webhook.py` patched `AgentRunner` by name, update the patch to `app.adk_agent.AdkAgentRunner` and re-run.

- [ ] **Step 7: Lint**

Run: `.venv/Scripts/python.exe -m ruff check app/ tests/` (if ruff installed; else skip)
Expected: clean

- [ ] **Step 8: Commit**

```bash
git add app/main.py requirements.txt Dockerfile docs/mcp-endpoint-audit.md tests/test_webhook.py
git commit -m "feat: route MR evaluation through ADK + GitLab MCP; add Node+MCP to image"
```

---

### Task 7: WSL deploy + live verification (STEVE-RUN — not Claude)

**Files:** Create `docs/adk-mcp-deploy-runbook.md` (Claude writes the runbook; Steve executes it in WSL)

This task CANNOT run in the Claude session (needs gcloud + Docker + WSL). Claude produces the runbook; Steve runs it and reports back.

- [ ] **Step 1: Claude writes `docs/adk-mcp-deploy-runbook.md`** containing, in order:
  1. Pre-flight: `gcloud auth list` (expect `sgharlow@gmail.com`), `gcloud config get project` (expect `aicin-477004`).
  2. Confirm the PAT secret is readable and exposed to the agent: the Cloud Run service already mounts `GITLAB_TOKEN`; the MCP server reuses it. No new secret needed.
  3. Build + deploy: `bash scripts/cloud-run-deploy.sh` (same script; the new Dockerfile installs Node + MCP server). Watch for npm-install failures in Cloud Build logs.
  4. If the MCP bin name differs, redeploy adding `--set-env-vars GITLAB_MCP_COMMAND=<bin>`.
  5. `curl $SERVICE/health` → `{"status":"ok"}`.
  6. **Tool-trace proof:** trigger a non-hero MR (`bash scripts/verify-tool-logging.sh` or `bash scripts/demo-capture.sh fire 9`) and grep Cloud Logging for the MCP tool calls (`get_merge_request`, `get_merge_request_diffs`, `list_merge_request_pipelines`) AND the `evaluation: score=...` line — proving Gemini + MCP ran at runtime.
  7. **Hero MR `!10` regression check:** confirm verdict still `block`, score `0.0`, sha8 `1fb25ad2`, the `no-secrets-in-diff` failure + SOC2/ISO/OWASP mapping unchanged. If the verdict drifted, the demo storyboard + screenshots need a re-shoot — STOP and decide before recording.
  8. Latency re-capture (`docs/latency-capture.md`) — expect higher p50/p95 than REST (agentic multi-turn); update README Status if materially changed.
  9. Re-seed if needed (`SEED=1 bash scripts/closeout-all.sh`), then re-record demo per `docs/recording-teleprompter.md`.

- [ ] **Step 2: Commit the runbook**

```bash
git add docs/adk-mcp-deploy-runbook.md
git commit -m "docs: WSL deploy + live-verify runbook for ADK + GitLab MCP"
```

- [ ] **Step 3: Steve runs the runbook in WSL and reports tool-trace + hero-MR results.**

- [ ] **Step 4: Merge decision.** Only after live tool-trace proof + hero-MR regression pass: open PR `feat/adk-gitlab-mcp` → `main`, or fast-forward merge. Keep `main`'s prior HEAD noted as the rollback point.

---

## Self-Review

**Spec coverage:**
- "Gemini imported + called at runtime" → Task 5 (`LlmAgent(model=gemini-2.5-flash)`) + Task 7 step 6 (live trace). ✓
- "Agent Builder (ADK) at runtime" → Tasks 3-5 (`google-adk` LlmAgent/Runner/MCPToolset/FunctionTool). ✓
- "Partner (GitLab) MCP server at runtime" → Task 4 (toolset) + Task 5 (agent calls it) + Task 7 (trace proof). ✓
- "No competing AI/cloud" → unchanged; only google-adk + Vertex Gemini added. ✓
- "Preserve demo + dashboard contract" → write-backs unchanged (Task 6 keeps REST writes); `Evaluation` shape preserved via `evaluation_from_payload` (Task 2); hero-MR regression gate (Task 7 step 7). ✓

**Placeholder scan:** No TBD/TODO; every code step has concrete code. Two flagged runtime unknowns (exact MCP bin name; exact `mcp` pin version) have explicit verification steps (Task 6 step 3/4), not placeholders.

**Type consistency:** `VerdictCollector.payload` (dict|None), `make_record_verdict`→callable, `evaluation_from_payload(data, *, rubric_version)`→`Evaluation`, `AdkAgentRunner.evaluate(project_path, mr_iid)`→`Evaluation`, `runner_factory(record_verdict, *, rubric)` with `.run_and_collect(*, project_path, mr_iid)` — consistent across Tasks 3-6 and the tests.

**Risk register:**
1. Agentic non-determinism may drift the hero verdict → Task 7 step 7 gate + write-backs kept deterministic.
2. Cold-start: spawning the Node MCP server per invocation adds latency → acceptable for demo QPS; HTTP-sidecar is the optimization if needed.
3. `mcp`/`google-adk` version skew between venv and image → pin both exactly (Task 6 step 3).
4. Interpretation risk (community vs official MCP server) → documented in audit addendum; accepted by Steve (Path B).
