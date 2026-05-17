"""Webhook handler tests — auth, payload validation, healthz."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("GITLAB_WEBHOOK_SECRET", "test-secret")
    return TestClient(app)


@pytest.fixture
def client_no_secret(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.delenv("GITLAB_WEBHOOK_SECRET", raising=False)
    return TestClient(app)


def test_healthz_returns_ok(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_webhook_rejects_missing_token(client: TestClient) -> None:
    response = client.post("/gitlab/webhook", json={"object_kind": "merge_request"})
    assert response.status_code == 401


def test_webhook_rejects_wrong_token(client: TestClient) -> None:
    response = client.post(
        "/gitlab/webhook",
        json={"object_kind": "merge_request"},
        headers={"X-Gitlab-Token": "wrong"},
    )
    assert response.status_code == 401


def test_webhook_accepts_valid_token(client: TestClient) -> None:
    response = client.post(
        "/gitlab/webhook",
        json={
            "object_kind": "merge_request",
            "object_attributes": {"iid": 42, "action": "open"},
            "project": {"path_with_namespace": "sgharlow/governance-demo-app"},
        },
        headers={"X-Gitlab-Token": "test-secret", "X-Gitlab-Event": "Merge Request Hook"},
    )
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "accepted"
    assert body["event"] == "Merge Request Hook"


def test_webhook_rejects_non_object_payload(client: TestClient) -> None:
    response = client.post(
        "/gitlab/webhook",
        json=["not", "an", "object"],
        headers={"X-Gitlab-Token": "test-secret"},
    )
    assert response.status_code == 400


def test_webhook_dev_mode_accepts_without_secret(client_no_secret: TestClient) -> None:
    response = client_no_secret.post("/gitlab/webhook", json={"object_kind": "ping"})
    assert response.status_code == 202
