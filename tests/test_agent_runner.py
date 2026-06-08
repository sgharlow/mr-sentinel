"""Agent runner tests — model factory is injectable so we don't call Vertex AI."""

from __future__ import annotations

import json
from typing import Any

import pytest

from app.agent_runner import (
    AgentRunner,
    Evaluation,
    RubricValidationError,
    RuleEvaluation,
    build_system_prompt,
    build_user_prompt,
    load_rubric,
    parse_rubric,
    render_comment,
)
from app.gitlab_client import DiffEntry, MergeRequest


@pytest.fixture
def sample_mr() -> MergeRequest:
    return MergeRequest(
        iid=1,
        project_path="sgharlow/governance-demo-app",
        title="Add /admin/dump endpoint",
        description="Closes #1 — quick admin dump endpoint",
        author_username="alice",
        source_branch="alice/admin-dump",
        target_branch="main",
        state="opened",
        web_url="https://gitlab.com/sgharlow/governance-demo-app/-/merge_requests/1",
        sha="deadbeef",
        labels=[],
    )


@pytest.fixture
def sample_diffs() -> list[DiffEntry]:
    return [
        DiffEntry(
            old_path="app/admin.py",
            new_path="app/admin.py",
            a_mode="100644", b_mode="100644",
            new_file=False, renamed_file=False, deleted_file=False,
            diff="@@ -1 +1,3 @@\n+@app.route('/admin/dump')\n+def dump(): return get_all_users()\n",
        ),
    ]


class FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text


class FakeModel:
    def __init__(self, response_text: str) -> None:
        self._response_text = response_text

    def generate_content(self, prompt: str, generation_config: Any = None) -> FakeResponse:
        self.last_prompt = prompt
        self.last_config = generation_config
        return FakeResponse(self._response_text)


def fake_factory(response_text: str):
    def factory(model_name: str):
        return FakeModel(response_text)
    return factory


def test_load_rubric_returns_15_rules() -> None:
    rubric = load_rubric()
    assert rubric["version"] == "v1"
    assert len(rubric["rules"]) == 15


def test_system_prompt_includes_rubric_version() -> None:
    rubric = load_rubric()
    prompt = build_system_prompt(rubric)
    assert "v1" in prompt
    assert "rule_id" in prompt
    assert "MR Sentinel" in prompt


def test_user_prompt_includes_mr_metadata_and_diff(sample_mr: MergeRequest, sample_diffs: list[DiffEntry]) -> None:
    prompt = build_user_prompt(sample_mr, sample_diffs)
    assert "sgharlow/governance-demo-app!1" in prompt
    assert "alice/admin-dump → main" in prompt
    assert "@alice" in prompt
    assert "@app.route('/admin/dump')" in prompt


async def test_agent_runner_parses_canned_response(
    sample_mr: MergeRequest, sample_diffs: list[DiffEntry]
) -> None:
    canned = json.dumps({
        "overall_score": 4.0,
        "verdict": "block",
        "summary": "New public endpoint with no auth check.",
        "rule_evaluations": [
            {"rule_id": "auth-on-new-public-endpoints", "outcome": "fail",
             "evidence": "/admin/dump has no @require_role decorator",
             "remediation": "Add @require_role('admin')."},
            {"rule_id": "no-skipped-tests-introduced", "outcome": "pass",
             "evidence": "no test skips in diff"},
        ],
    })
    runner = AgentRunner(project_id="test-project", model_factory=fake_factory(canned))
    result = await runner.evaluate(sample_mr, sample_diffs)
    assert isinstance(result, Evaluation)
    assert result.overall_score == 4.0
    assert result.verdict == "block"
    assert len(result.rule_evaluations) == 2
    assert result.rule_evaluations[0].outcome == "fail"
    assert result.rule_evaluations[0].remediation is not None
    assert result.rubric_version == "v1"


async def test_agent_runner_rejects_invalid_json(
    sample_mr: MergeRequest, sample_diffs: list[DiffEntry]
) -> None:
    runner = AgentRunner(project_id="test-project", model_factory=fake_factory("not json"))
    with pytest.raises(RuntimeError, match="not valid JSON"):
        await runner.evaluate(sample_mr, sample_diffs)


def test_render_comment_shows_verdict_score_and_failures() -> None:
    eval_ = Evaluation(
        overall_score=4.0,
        verdict="block",
        summary="Auth-path missing.",
        rule_evaluations=[
            RuleEvaluation(rule_id="auth-on-new-public-endpoints", outcome="fail",
                           evidence="/admin/dump", remediation="Add decorator."),
            RuleEvaluation(rule_id="no-secrets-in-diff", outcome="pass",
                           evidence="no secrets found"),
        ],
        rubric_version="v1",
    )
    mr = MergeRequest(
        iid=1, project_path="sgharlow/governance-demo-app",
        title="t", description="d", author_username="a",
        source_branch="s", target_branch="t", state="opened",
        web_url="", sha="abc12345", labels=[],
    )
    md = render_comment(eval_, mr)
    assert "<!-- mr-sentinel:v1 -->" in md  # marker for upsert
    assert "🛑" in md
    assert "verdict: **block**" in md
    assert "score 4.0/10" in md
    assert "auth-on-new-public-endpoints" in md
    assert "Add decorator." in md
    assert "abc12345" in md  # sha shown in comment
    # Passes go in a collapsed section
    assert "<details>" in md
    assert "no-secrets-in-diff" in md


def test_render_comment_includes_followup_issue_url_and_pipeline() -> None:
    from app.agent_runner import render_comment
    eval_ = Evaluation(
        overall_score=2.0, verdict="block", summary="bad",
        rule_evaluations=[
            RuleEvaluation(rule_id="auth-on-new-public-endpoints", outcome="fail",
                           evidence="x", remediation="y"),
        ],
        rubric_version="v1",
    )
    mr = MergeRequest(iid=1, project_path="p/q", title="t", description="d",
                     author_username="a", source_branch="s", target_branch="t",
                     state="opened", web_url="", sha="deadbeef", labels=[])
    md = render_comment(eval_, mr,
                       followup_issue_url="https://gitlab.com/p/q/-/issues/9",
                       pipeline_status="failed")
    assert "https://gitlab.com/p/q/-/issues/9" in md
    assert "Follow-up issue" in md
    assert "pipeline `failed`" in md


def test_parse_rubric_accepts_valid_bundled_rubric() -> None:
    """The shipped rubric/v1.yaml is the canonical valid example."""
    from pathlib import Path
    text = (Path(__file__).resolve().parent.parent / "rubric" / "v1.yaml").read_text(encoding="utf-8")
    result = parse_rubric(text)
    assert result["version"] == "v1"
    assert len(result["rules"]) == 15


def test_parse_rubric_rejects_invalid_yaml() -> None:
    with pytest.raises(RubricValidationError, match="invalid YAML"):
        parse_rubric("version: v1\n  bad: indent:\n - this is broken")


def test_parse_rubric_rejects_non_mapping_root() -> None:
    with pytest.raises(RubricValidationError, match="mapping"):
        parse_rubric("- just\n- a\n- list")


def test_parse_rubric_rejects_schema_violation() -> None:
    """Rubric must have exactly 15 rules — 14 is invalid per schema."""
    text = "version: v1\nrules:\n"
    # Build 14 minimal valid rules
    for i in range(14):
        text += (
            f"  - rule_id: rule-{i:02d}\n"
            f"    category: quality\n"
            f"    control_mapping: [\"CTRL-{i}\"]\n"
            f"    severity: info\n"
            f"    evaluator_prompt: \"prompt long enough to pass schema\"\n"
            f"    example_pass: \"yes\"\n"
            f"    example_fail: \"no\"\n"
            f"    suggested_remediation: \"fix it\"\n"
        )
    with pytest.raises(RubricValidationError, match="schema validation failed"):
        parse_rubric(text)


def test_agent_runner_accepts_override_rubric_dict() -> None:
    """When a `rubric` arg is provided, AgentRunner uses it instead of loading from disk."""
    custom = {
        "version": "v1",
        "rules": [
            {"rule_id": f"custom-{i:02d}", "category": "quality",
             "control_mapping": [f"CTRL-{i}"], "severity": "info",
             "evaluator_prompt": "some prompt long enough", "example_pass": "y",
             "example_fail": "n", "suggested_remediation": "fix"}
            for i in range(15)
        ],
    }
    runner = AgentRunner(project_id="test-project", rubric=custom, model_factory=fake_factory("{}"))
    assert runner.rubric["rules"][0]["rule_id"] == "custom-00"
    assert runner.rubric["version"] == "v1"


def test_render_followup_issue_body_lists_failures_as_checklist() -> None:
    from app.agent_runner import render_followup_issue_body
    eval_ = Evaluation(
        overall_score=2.0, verdict="block", summary="bad",
        rule_evaluations=[
            RuleEvaluation(rule_id="auth-on-new-public-endpoints", outcome="fail",
                           evidence="route /admin/dump has no auth",
                           remediation="add decorator"),
            RuleEvaluation(rule_id="no-secrets-in-diff", outcome="fail",
                           evidence="SSN found", remediation="remove SSN"),
            RuleEvaluation(rule_id="quality-01", outcome="pass", evidence="ok"),
        ],
        rubric_version="v1",
    )
    mr = MergeRequest(iid=42, project_path="sgharlow/governance-demo-app",
                     title="Add /admin/dump", description="",
                     author_username="alice", source_branch="alice/admin",
                     target_branch="main", state="opened",
                     web_url="https://gitlab.com/sgharlow/governance-demo-app/-/merge_requests/42",
                     sha="abc12345", labels=[])
    body = render_followup_issue_body(eval_, mr)
    assert "sgharlow/governance-demo-app!42" in body
    assert "Failing rules (2)" in body
    assert "[ ] **`auth-on-new-public-endpoints`**" in body
    assert "route /admin/dump has no auth" in body
    assert "add decorator" in body
    # Passes should not appear
    assert "quality-01" not in body


def test_build_system_prompt_default_asks_for_json():
    from app.agent_runner import build_system_prompt
    p = build_system_prompt({"version": "v1", "rules": []})
    assert "JSON" in p  # legacy direct-Gemini path returns a JSON text response


def test_build_system_prompt_tool_use_variant_instructs_record_verdict():
    from app.agent_runner import build_system_prompt
    p = build_system_prompt({"version": "v1", "rules": []}, for_tool_use=True)
    assert "record_verdict" in p
    # the tool-use variant must NOT order the model to return a JSON blob
    assert "valid JSON matching this shape" not in p
    assert "Output structured JSON matching the schema" not in p
