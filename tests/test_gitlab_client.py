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


async def test_find_agent_note_returns_id_when_marker_present(
    token: str, project_path: str, encoded_project: str
) -> None:
    notes = [
        {"id": 100, "body": "first comment", "author": {"username": "alice"}},
        {"id": 101, "body": "## 🛑 MR Sentinel ...\n<!-- mr-sentinel:v1 -->\nverdict block",
         "author": {"username": "sgharlow"}},
        {"id": 102, "body": "another human reply", "author": {"username": "bob"}},
    ]
    async with respx.mock(base_url="https://gitlab.com/api/v4") as router:
        router.get(f"/projects/{encoded_project}/merge_requests/42/notes").respond(200, json=notes)
        async with GitLabClient() as client:
            note_id = await client.find_agent_note(project_path, 42)
    assert note_id == 101


async def test_find_agent_note_returns_none_when_no_marker(
    token: str, project_path: str, encoded_project: str
) -> None:
    async with respx.mock(base_url="https://gitlab.com/api/v4") as router:
        router.get(f"/projects/{encoded_project}/merge_requests/42/notes").respond(
            200, json=[{"id": 1, "body": "no marker here", "author": {"username": "alice"}}]
        )
        async with GitLabClient() as client:
            note_id = await client.find_agent_note(project_path, 42)
    assert note_id is None


async def test_update_merge_request_note(
    token: str, project_path: str, encoded_project: str
) -> None:
    async with respx.mock(base_url="https://gitlab.com/api/v4") as router:
        router.put(f"/projects/{encoded_project}/merge_requests/42/notes/9001").respond(
            200, json={"id": 9001, "body": "updated"}
        )
        async with GitLabClient() as client:
            note_id = await client.update_merge_request_note(project_path, 42, 9001, "updated body")
    assert note_id == 9001


async def test_upsert_comment_creates_when_no_existing(
    token: str, project_path: str, encoded_project: str
) -> None:
    async with respx.mock(base_url="https://gitlab.com/api/v4") as router:
        router.get(f"/projects/{encoded_project}/merge_requests/42/notes").respond(
            200, json=[{"id": 1, "body": "human note", "author": {"username": "alice"}}]
        )
        router.post(f"/projects/{encoded_project}/merge_requests/42/notes").respond(
            201, json={"id": 555}
        )
        async with GitLabClient() as client:
            note_id, created = await client.upsert_merge_request_comment(project_path, 42, "new body")
    assert note_id == 555
    assert created is True


async def test_upsert_comment_updates_when_marker_found(
    token: str, project_path: str, encoded_project: str
) -> None:
    async with respx.mock(base_url="https://gitlab.com/api/v4") as router:
        router.get(f"/projects/{encoded_project}/merge_requests/42/notes").respond(
            200, json=[{"id": 700, "body": "## MR Sentinel\n<!-- mr-sentinel:v1 -->\nold",
                       "author": {"username": "sgharlow"}}]
        )
        router.put(f"/projects/{encoded_project}/merge_requests/42/notes/700").respond(
            200, json={"id": 700}
        )
        async with GitLabClient() as client:
            note_id, created = await client.upsert_merge_request_comment(project_path, 42, "updated body")
    assert note_id == 700
    assert created is False


async def test_get_latest_pipeline_returns_none_when_empty(
    token: str, project_path: str, encoded_project: str
) -> None:
    async with respx.mock(base_url="https://gitlab.com/api/v4") as router:
        router.get(f"/projects/{encoded_project}/pipelines").respond(200, json=[])
        async with GitLabClient() as client:
            pipeline = await client.get_latest_pipeline_for_sha(project_path, "deadbeef")
    assert pipeline is None


async def test_get_latest_pipeline_returns_first(
    token: str, project_path: str, encoded_project: str
) -> None:
    async with respx.mock(base_url="https://gitlab.com/api/v4") as router:
        router.get(f"/projects/{encoded_project}/pipelines").respond(
            200, json=[{"id": 99, "status": "success", "sha": "deadbeef"}]
        )
        async with GitLabClient() as client:
            pipeline = await client.get_latest_pipeline_for_sha(project_path, "deadbeef")
    assert pipeline is not None
    assert pipeline["id"] == 99


async def test_list_vulnerability_findings_swallows_403(
    token: str, project_path: str, encoded_project: str
) -> None:
    async with respx.mock(base_url="https://gitlab.com/api/v4") as router:
        router.get(f"/projects/{encoded_project}/vulnerability_findings").respond(
            403, json={"message": "Premium tier required"}
        )
        async with GitLabClient() as client:
            findings = await client.list_vulnerability_findings(project_path)
    assert findings == []


async def test_get_file_content_returns_text(
    token: str, project_path: str, encoded_project: str
) -> None:
    encoded_file = ".mr-sentinel.yaml"  # quote(safe="") leaves dots/hyphens alone
    raw_yaml = "version: v1\nrules: []\n"
    async with respx.mock(base_url="https://gitlab.com/api/v4") as router:
        router.get(
            f"/projects/{encoded_project}/repository/files/{encoded_file}/raw"
        ).respond(200, text=raw_yaml)
        async with GitLabClient() as client:
            content = await client.get_file_content(project_path, ".mr-sentinel.yaml")
    assert content == raw_yaml


async def test_get_file_content_returns_none_on_404(
    token: str, project_path: str, encoded_project: str
) -> None:
    async with respx.mock(base_url="https://gitlab.com/api/v4") as router:
        router.get(
            f"/projects/{encoded_project}/repository/files/.mr-sentinel.yaml/raw"
        ).respond(404, json={"message": "404 File Not Found"})
        async with GitLabClient() as client:
            content = await client.get_file_content(project_path, ".mr-sentinel.yaml")
    assert content is None


async def test_get_file_content_raises_on_500(
    token: str, project_path: str, encoded_project: str
) -> None:
    async with respx.mock(base_url="https://gitlab.com/api/v4") as router:
        router.get(
            f"/projects/{encoded_project}/repository/files/.mr-sentinel.yaml/raw"
        ).respond(500, text="boom")
        async with GitLabClient() as client:
            with pytest.raises(GitLabError) as exc_info:
                await client.get_file_content(project_path, ".mr-sentinel.yaml")
    assert exc_info.value.status == 500
    assert exc_info.value.action == "get_file_content"
