from app.agent_runner import evaluation_from_payload, Evaluation
from app.adk_agent import VerdictCollector, make_record_verdict


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
