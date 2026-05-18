"""GitLab client tests — mocked via respx (httpx test layer)."""

from __future__ import annotations

import httpx
import pytest
import respx

from app.gitlab_client import GitLabClient, GitLabError


@pytest.fixture
def token(monkeypatch: pytest.MonkeyPatch) -> str:
    value = "glpat-test-token"
    monkeypatch.setenv("GITLAB_TOKEN", value)
    return value


@pytest.fixture
def project_path() -> str:
    return "sgharlow/governance-demo-app"


@pytest.fixture
def encoded_project() -> str:
    return "sgharlow%2Fgovernance-demo-app"


async def test_get_merge_request_parses_payload(token: str, project_path: str, encoded_project: str) -> None:
    payload = {
        "iid": 42,
        "title": "Refactor auth middleware",
        "description": "Closes #100",
        "author": {"username": "alice"},
        "source_branch": "alice/auth",
        "target_branch": "main",
        "state": "opened",
        "web_url": "https://gitlab.com/sgharlow/governance-demo-app/-/merge_requests/42",
        "sha": "deadbeef",
        "labels": ["needs-review"],
    }
    async with respx.mock(base_url="https://gitlab.com/api/v4") as router:
        router.get(f"/projects/{encoded_project}/merge_requests/42").respond(200, json=payload)
        async with GitLabClient() as client:
            mr = await client.get_merge_request(project_path, 42)
    assert mr.iid == 42
    assert mr.title == "Refactor auth middleware"
    assert mr.author_username == "alice"
    assert mr.labels == ["needs-review"]
    assert mr.sha == "deadbeef"


async def test_get_merge_request_raises_on_404(token: str, project_path: str, encoded_project: str) -> None:
    async with respx.mock(base_url="https://gitlab.com/api/v4") as router:
        router.get(f"/projects/{encoded_project}/merge_requests/99").respond(404, json={"message": "Not Found"})
        async with GitLabClient() as client:
            with pytest.raises(GitLabError) as exc_info:
                await client.get_merge_request(project_path, 99)
    assert exc_info.value.status == 404
    assert exc_info.value.action == "get_merge_request"


async def test_get_merge_request_diffs_returns_entries(token: str, project_path: str, encoded_project: str) -> None:
    diff_payload = [
        {
            "old_path": "app/auth.py",
            "new_path": "app/auth.py",
            "a_mode": "100644",
            "b_mode": "100644",
            "new_file": False,
            "renamed_file": False,
            "deleted_file": False,
            "diff": "@@ -1,3 +1,3 @@\n-old line\n+new line\n",
        },
        {
            "old_path": "tests/test_auth.py",
            "new_path": "tests/test_auth.py",
            "new_file": True,
            "a_mode": "",
            "b_mode": "100644",
            "renamed_file": False,
            "deleted_file": False,
            "diff": "+new test\n",
        },
    ]
    async with respx.mock(base_url="https://gitlab.com/api/v4") as router:
        router.get(f"/projects/{encoded_project}/merge_requests/42/diffs").respond(200, json=diff_payload)
        async with GitLabClient() as client:
            diffs = await client.get_merge_request_diffs(project_path, 42)
    assert len(diffs) == 2
    assert diffs[0].old_path == "app/auth.py"
    assert diffs[1].new_file is True


async def test_post_merge_request_comment_returns_id(token: str, project_path: str, encoded_project: str) -> None:
    async with respx.mock(base_url="https://gitlab.com/api/v4") as router:
        route = router.post(f"/projects/{encoded_project}/merge_requests/42/notes").respond(
            201, json={"id": 9001, "body": "test comment"}
        )
        async with GitLabClient() as client:
            note_id = await client.post_merge_request_comment(project_path, 42, "hello world")
    assert note_id == 9001
    assert route.called
    # httpx form-encodes the body, so 'hello world' arrives as 'body=hello+world'
    assert b"body=hello+world" in route.calls[0].request.content


async def test_add_merge_request_labels_returns_new_set(
    token: str, project_path: str, encoded_project: str
) -> None:
    async with respx.mock(base_url="https://gitlab.com/api/v4") as router:
        router.put(f"/projects/{encoded_project}/merge_requests/42").respond(
            200, json={"labels": ["needs-review", "blocked-compliance"]}
        )
        async with GitLabClient() as client:
            labels = await client.add_merge_request_labels(project_path, 42, ["blocked-compliance"])
    assert labels == ["needs-review", "blocked-compliance"]


async def test_create_issue_returns_payload(token: str, project_path: str, encoded_project: str) -> None:
    issue_payload = {
        "iid": 7,
        "title": "Remediation for MR !42",
        "web_url": "https://gitlab.com/sgharlow/governance-demo-app/-/issues/7",
    }
    async with respx.mock(base_url="https://gitlab.com/api/v4") as router:
        router.post(f"/projects/{encoded_project}/issues").respond(201, json=issue_payload)
        async with GitLabClient() as client:
            issue = await client.create_issue(
                project_path, "Remediation for MR !42", "details", labels=["follow-up"]
            )
    assert issue["iid"] == 7
    assert issue["web_url"].endswith("/issues/7")


async def test_missing_token_raises() -> None:
    import os

    saved = os.environ.pop("GITLAB_TOKEN", None)
    try:
        with pytest.raises(RuntimeError, match="GITLAB_TOKEN"):
            GitLabClient()
    finally:
        if saved is not None:
            os.environ["GITLAB_TOKEN"] = saved
