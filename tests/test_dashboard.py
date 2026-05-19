"""Dashboard tests — pure-function rendering against synthetic data dicts.

We test the renderer (_render_dashboard, _render_audit) directly with hand-built
data, plus the FastAPI integration through TestClient with persistence patched
to return canned dicts. No real Cloud SQL required.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.dashboard import _render_audit, _render_dashboard
from app.main import app


def _utc(*args) -> datetime:
    return datetime(*args, tzinfo=timezone.utc)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ----- _render_dashboard ----------------------------------------------------


def test_dashboard_empty_renders_no_evaluations() -> None:
    html = _render_dashboard({
        "window_days": 30, "total": 0, "verdicts": [], "top_rules": [], "recent_mrs": [],
    })
    assert "No evaluations recorded in the last 30 days." in html
    assert "<title>" in html
    assert "MR Sentinel" in html


def test_dashboard_populated_shows_counts_and_top_rules() -> None:
    data = {
        "window_days": 30,
        "total": 17,
        "verdicts": [
            {"verdict": "pass", "n": 12},
            {"verdict": "warn", "n": 3},
            {"verdict": "block", "n": 2},
        ],
        "top_rules": [
            {"rule_id": "auth-on-new-public-endpoints", "n": 5},
            {"rule_id": "no-secrets-in-diff", "n": 3},
        ],
        "recent_mrs": [
            {
                "project_path": "sgharlow/governance-demo-app",
                "mr_iid": 8,
                "verdict": "pass",
                "overall_score": 10.0,
                "rubric_version": "v2",
                "scored_at": _utc(2026, 5, 19, 4, 34, 47),
            },
            {
                "project_path": "sgharlow/governance-demo-app",
                "mr_iid": 7,
                "verdict": "block",
                "overall_score": 2.5,
                "rubric_version": "v1",
                "scored_at": _utc(2026, 5, 18, 22, 0, 0),
            },
        ],
    }
    html = _render_dashboard(data)
    assert "MRs scored" in html
    assert ">17<" in html  # total
    assert "auth-on-new-public-endpoints" in html
    assert "sgharlow/governance-demo-app!8" in html
    assert "sgharlow/governance-demo-app!7" in html
    assert "/audit/sgharlow/governance-demo-app/8" in html  # linked
    # Verdict-distribution bars (all three classes)
    assert 'bar pass' in html
    assert 'bar warn' in html
    assert 'bar block' in html
    # Verdict tags present in recent-MR rows (only pass + block in fixture)
    assert "tag pass" in html
    assert "tag block" in html


def test_dashboard_no_failures_shows_empty_rules_panel() -> None:
    data = {
        "window_days": 30,
        "total": 3,
        "verdicts": [{"verdict": "pass", "n": 3}],
        "top_rules": [],
        "recent_mrs": [
            {
                "project_path": "x/y", "mr_iid": 1, "verdict": "pass",
                "overall_score": 9.0, "rubric_version": "v1",
                "scored_at": _utc(2026, 5, 19, 0, 0, 0),
            },
        ],
    }
    html = _render_dashboard(data)
    assert "No rule failures in window." in html


# ----- _render_audit --------------------------------------------------------


def test_audit_renders_score_rules_and_audit_log() -> None:
    data = {
        "project_path": "sgharlow/governance-demo-app",
        "mr_iid": 8,
        "score": {
            "commit_sha": "c08461ff917086414f49fe933f3ad30432814364",
            "rubric_version": "v2",
            "overall_score": 10.0,
            "verdict": "pass",
            "scored_at": _utc(2026, 5, 19, 4, 34, 47),
        },
        "rules": [
            {"rule_id": "auth-on-new-public-endpoints", "category": "security",
             "outcome": "fail", "severity": "blocker",
             "message": "/admin/dump has no auth", "remediation": "add decorator",
             "control_mapping": ["SOC2-CC6.1", "OWASP-ASVS-V1"]},
            {"rule_id": "no-secrets-in-diff", "category": "security",
             "outcome": "pass", "severity": "blocker",
             "message": "no secrets found", "remediation": None,
             "control_mapping": ["SOC2-CC6.1"]},
        ],
        "audit": [
            {"occurred_at": _utc(2026, 5, 19, 4, 34, 47),
             "actor": "mr-sentinel", "action": "evaluate",
             "details": {"score": 10.0, "verdict": "pass", "rubric_source": "project_override"}},
        ],
    }
    html = _render_audit(data)
    assert "sgharlow/governance-demo-app!8" in html
    assert "c08461ff" in html  # sha8
    assert "auth-on-new-public-endpoints" in html
    assert "SOC2-CC6.1" in html
    assert "mr-sentinel" in html
    assert "rubric_source" in html  # audit detail JSON included
    # Failed rule should sort before passing rule in the rendered HTML
    fail_pos = html.find("auth-on-new-public-endpoints")
    pass_pos = html.find("no-secrets-in-diff")
    assert 0 < fail_pos < pass_pos


# ----- FastAPI integration via TestClient + patched persistence -------------


def test_dashboard_route_renders_via_patched_data(client: TestClient) -> None:
    fake = {
        "window_days": 30, "total": 1,
        "verdicts": [{"verdict": "pass", "n": 1}],
        "top_rules": [],
        "recent_mrs": [{
            "project_path": "p/q", "mr_iid": 1, "verdict": "pass",
            "overall_score": 7.0, "rubric_version": "v1",
            "scored_at": _utc(2026, 5, 19, 0, 0, 0),
        }],
    }
    with patch("app.dashboard._dashboard_data", return_value=fake):
        response = client.get("/dashboard")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "p/q!1" in response.text
    assert "MRs scored" in response.text


def test_audit_route_returns_404_when_no_data(client: TestClient) -> None:
    with patch("app.dashboard._audit_data", return_value=None):
        response = client.get("/audit/p/q/99")
    assert response.status_code == 404
    assert "no evaluations recorded" in response.json()["detail"]


def test_audit_route_renders_via_patched_data(client: TestClient) -> None:
    fake = {
        "project_path": "p/q", "mr_iid": 1,
        "score": {
            "commit_sha": "abc12345" + "0" * 32, "rubric_version": "v1",
            "overall_score": 8.0, "verdict": "warn",
            "scored_at": _utc(2026, 5, 19, 0, 0, 0),
        },
        "rules": [], "audit": [],
    }
    with patch("app.dashboard._audit_data", return_value=fake):
        response = client.get("/audit/p/q/1")
    assert response.status_code == 200
    assert "p/q!1" in response.text
    assert "abc12345" in response.text
    assert "warn" in response.text
