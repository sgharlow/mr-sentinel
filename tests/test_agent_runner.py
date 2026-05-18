"""Agent runner tests — model factory is injectable so we don't call Vertex AI."""

from __future__ import annotations

import json
from typing import Any

import pytest

from app.agent_runner import (
    AgentRunner,
    Evaluation,
    RuleEvaluation,
    build_system_prompt,
    build_user_prompt,
    load_rubric,
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
        web_url="", sha="", labels=[],
    )
    md = render_comment(eval_, mr)
    assert "🛑" in md
    assert "verdict: **block**" in md
    assert "score 4.0/10" in md
    assert "auth-on-new-public-endpoints" in md
    assert "Add decorator." in md
    # Passes go in a collapsed section
    assert "<details>" in md
    assert "no-secrets-in-diff" in md
