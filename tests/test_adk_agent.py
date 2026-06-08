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
