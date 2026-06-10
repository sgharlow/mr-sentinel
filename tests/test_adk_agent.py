import asyncio

import pytest

import app.adk_agent as adk
from app.agent_runner import evaluation_from_payload, Evaluation
from app.adk_agent import VerdictCollector, make_record_verdict


def test_adk_module_selects_vertex_ai_backend():
    """Importing adk_agent must route google-genai to Vertex AI, not the
    Developer API. If this regresses, the live agent dies with 'No API key was
    provided' and inference would (if a key were present) run outside Google
    Cloud — both rule violations. See the os.environ.setdefault block."""
    import os

    assert os.environ.get("GOOGLE_GENAI_USE_VERTEXAI") == "TRUE"
    # location always defaulted; project only when GCP_PROJECT_ID is present.
    assert os.environ.get("GOOGLE_CLOUD_LOCATION")


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
    assert captured["env"]["GITLAB_READ_ONLY_MODE"] == "true"
    assert captured["timeout"] == 30.0


def test_build_gitlab_mcp_toolset_requires_token(monkeypatch):
    monkeypatch.delenv("GITLAB_TOKEN", raising=False)
    monkeypatch.setattr(adk, "MCPToolset", object)
    with pytest.raises(RuntimeError, match="GITLAB_TOKEN"):
        adk.build_gitlab_mcp_toolset()


def test_build_gitlab_mcp_toolset_strips_trailing_slash(monkeypatch):
    captured = {}

    class FakeStdioServerParameters:
        def __init__(self, *, command, args=None, env=None):
            captured["env"] = env

    class FakeStdioConnectionParams:
        def __init__(self, *, server_params, timeout=5.0):
            pass

    class FakeMCPToolset:
        def __init__(self, *, connection_params, tool_filter=None):
            pass

    monkeypatch.setattr(adk, "MCPToolset", FakeMCPToolset)
    monkeypatch.setattr(adk, "StdioServerParameters", FakeStdioServerParameters)
    monkeypatch.setattr(adk, "StdioConnectionParams", FakeStdioConnectionParams)
    monkeypatch.setenv("GITLAB_TOKEN", "glpat-test")
    monkeypatch.setenv("GITLAB_BASE_URL", "https://gitlab.com/")

    adk.build_gitlab_mcp_toolset()
    assert captured["env"]["GITLAB_API_URL"] == "https://gitlab.com/api/v4"


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
    with pytest.raises(RuntimeError, match="did not record a verdict"):
        asyncio.get_event_loop().run_until_complete(
            runner.evaluate("p/x", 1)
        )
