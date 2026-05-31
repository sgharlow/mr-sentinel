"""Outbound GitLab REST API client.

Used by the agent to read MR diffs and to post results back (comments, labels,
issues). All calls are async (httpx). Project paths are URL-encoded automatically.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx

logger = logging.getLogger("mr_sentinel.gitlab")


class GitLabError(Exception):
    """Raised when the GitLab API returns an unexpected status."""

    def __init__(self, status: int, body: str, *, action: str) -> None:
        super().__init__(f"GitLab {action} failed: HTTP {status}: {body[:300]}")
        self.status = status
        self.body = body
        self.action = action


@dataclass(frozen=True)
class MergeRequest:
    iid: int
    project_path: str
    title: str
    description: str
    author_username: str
    source_branch: str
    target_branch: str
    state: str
    web_url: str
    sha: str
    labels: list[str]


@dataclass(frozen=True)
class DiffEntry:
    old_path: str
    new_path: str
    a_mode: str
    b_mode: str
    new_file: bool
    renamed_file: bool
    deleted_file: bool
    diff: str


class GitLabClient:
    def __init__(
        self,
        token: str | None = None,
        base_url: str | None = None,
        *,
        timeout: float = 15.0,
    ) -> None:
        self._token = (token or os.environ.get("GITLAB_TOKEN", "")).strip()
        self._base_url = (base_url or os.environ.get("GITLAB_BASE_URL", "https://gitlab.com")).rstrip("/")
        if not self._token:
            raise RuntimeError("GITLAB_TOKEN is required (env var or constructor arg)")
        self._client = httpx.AsyncClient(
            base_url=f"{self._base_url}/api/v4",
            headers={"PRIVATE-TOKEN": self._token},
            timeout=timeout,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "GitLabClient":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()

    @staticmethod
    def _encode_project(project_path: str) -> str:
        return quote(project_path, safe="")

    async def _request(
        self, method: str, path: str, *, action: str | None = None, **kwargs: Any
    ) -> httpx.Response:
        response = await self._client.request(method, path, **kwargs)
        # One INFO line per tool call. Passing `action=<name>` makes each GitLab
        # REST call legible in Cloud Logging (and on screen in the demo's Shot 5
        # agent-loop trace) as `tool=<name> ...` instead of only the URL-encoded
        # path. Falls back to the bare form when no action is supplied.
        if action:
            logger.info("tool=%s %s %s -> %d", action, method, path, response.status_code)
        else:
            logger.info("gitlab %s %s -> %d", method, path, response.status_code)
        return response

    async def get_merge_request(self, project_path: str, mr_iid: int) -> MergeRequest:
        encoded = self._encode_project(project_path)
        response = await self._request(
            "GET", f"/projects/{encoded}/merge_requests/{mr_iid}", action="get_merge_request"
        )
        if response.status_code != 200:
            raise GitLabError(response.status_code, response.text, action="get_merge_request")
        data = response.json()
        return MergeRequest(
            iid=data["iid"],
            project_path=project_path,
            title=data["title"],
            description=data.get("description") or "",
            author_username=data["author"]["username"],
            source_branch=data["source_branch"],
            target_branch=data["target_branch"],
            state=data["state"],
            web_url=data["web_url"],
            sha=data["sha"],
            labels=data.get("labels", []),
        )

    async def get_merge_request_diffs(self, project_path: str, mr_iid: int) -> list[DiffEntry]:
        encoded = self._encode_project(project_path)
        response = await self._request(
            "GET", f"/projects/{encoded}/merge_requests/{mr_iid}/diffs",
            action="get_merge_request_diffs",
        )
        if response.status_code != 200:
            raise GitLabError(response.status_code, response.text, action="get_merge_request_diffs")
        diffs = response.json()
        return [
            DiffEntry(
                old_path=d["old_path"],
                new_path=d["new_path"],
                a_mode=d.get("a_mode", ""),
                b_mode=d.get("b_mode", ""),
                new_file=d.get("new_file", False),
                renamed_file=d.get("renamed_file", False),
                deleted_file=d.get("deleted_file", False),
                diff=d.get("diff", ""),
            )
            for d in diffs
        ]

    async def post_merge_request_comment(
        self, project_path: str, mr_iid: int, body: str
    ) -> int:
        """Post a note (comment) on the MR. Returns the note id."""
        encoded = self._encode_project(project_path)
        response = await self._request(
            "POST",
            f"/projects/{encoded}/merge_requests/{mr_iid}/notes",
            action="post_merge_request_comment",
            data={"body": body},
        )
        if response.status_code not in (200, 201):
            raise GitLabError(response.status_code, response.text, action="post_merge_request_comment")
        return response.json()["id"]

    async def add_merge_request_labels(
        self, project_path: str, mr_iid: int, labels: list[str]
    ) -> list[str]:
        """Add labels to the MR (additive — existing labels stay). Returns the new label list."""
        encoded = self._encode_project(project_path)
        response = await self._request(
            "PUT",
            f"/projects/{encoded}/merge_requests/{mr_iid}",
            action="add_merge_request_labels",
            data={"add_labels": ",".join(labels)},
        )
        if response.status_code != 200:
            raise GitLabError(response.status_code, response.text, action="add_merge_request_labels")
        return response.json().get("labels", [])

    async def create_issue(
        self, project_path: str, title: str, description: str, labels: list[str] | None = None
    ) -> dict[str, Any]:
        """Open a new issue. Returns the created issue payload (iid, web_url, ...)."""
        encoded = self._encode_project(project_path)
        payload: dict[str, Any] = {"title": title, "description": description}
        if labels:
            payload["labels"] = ",".join(labels)
        response = await self._request(
            "POST", f"/projects/{encoded}/issues", action="create_issue", data=payload
        )
        if response.status_code not in (200, 201):
            raise GitLabError(response.status_code, response.text, action="create_issue")
        return response.json()

    async def list_merge_request_notes(self, project_path: str, mr_iid: int) -> list[dict[str, Any]]:
        """List all notes/comments on the MR. Used to find the agent's prior comment."""
        encoded = self._encode_project(project_path)
        response = await self._request("GET", f"/projects/{encoded}/merge_requests/{mr_iid}/notes",
                                       action="list_merge_request_notes",
                                       params={"per_page": 100})
        if response.status_code != 200:
            raise GitLabError(response.status_code, response.text, action="list_merge_request_notes")
        return response.json()

    async def find_agent_note(
        self, project_path: str, mr_iid: int, marker: str = "<!-- mr-sentinel:v1 -->"
    ) -> int | None:
        """Return the note_id of the prior agent comment, or None."""
        notes = await self.list_merge_request_notes(project_path, mr_iid)
        # Latest first — GitLab returns chronological; reverse so we pick the most recent
        for note in reversed(notes):
            if marker in (note.get("body") or ""):
                return note["id"]
        return None

    async def update_merge_request_note(
        self, project_path: str, mr_iid: int, note_id: int, body: str
    ) -> int:
        """Edit an existing note. Returns the note id (unchanged on success)."""
        encoded = self._encode_project(project_path)
        response = await self._request(
            "PUT",
            f"/projects/{encoded}/merge_requests/{mr_iid}/notes/{note_id}",
            action="update_merge_request_note",
            data={"body": body},
        )
        if response.status_code not in (200, 201):
            raise GitLabError(response.status_code, response.text, action="update_merge_request_note")
        return response.json()["id"]

    async def upsert_merge_request_comment(
        self, project_path: str, mr_iid: int, body: str, *,
        marker: str = "<!-- mr-sentinel:v1 -->",
    ) -> tuple[int, bool]:
        """Post comment if none exists, otherwise update the existing one.

        Returns (note_id, created) where created=True means new note, False means edited.
        """
        existing_id = await self.find_agent_note(project_path, mr_iid, marker=marker)
        if existing_id is not None:
            return (await self.update_merge_request_note(project_path, mr_iid, existing_id, body), False)
        return (await self.post_merge_request_comment(project_path, mr_iid, body), True)

    async def get_latest_pipeline_for_sha(
        self, project_path: str, sha: str
    ) -> dict[str, Any] | None:
        """Return the most-recent pipeline run against the given commit sha, or None."""
        encoded = self._encode_project(project_path)
        response = await self._request(
            "GET",
            f"/projects/{encoded}/pipelines",
            action="get_latest_pipeline_for_sha",
            params={"sha": sha, "order_by": "updated_at", "sort": "desc", "per_page": 1},
        )
        if response.status_code != 200:
            raise GitLabError(response.status_code, response.text, action="get_latest_pipeline_for_sha")
        pipelines = response.json()
        return pipelines[0] if pipelines else None

    async def list_pipeline_jobs(
        self, project_path: str, pipeline_id: int
    ) -> list[dict[str, Any]]:
        """Return jobs for the given pipeline run."""
        encoded = self._encode_project(project_path)
        response = await self._request(
            "GET", f"/projects/{encoded}/pipelines/{pipeline_id}/jobs",
            action="list_pipeline_jobs",
            params={"per_page": 100},
        )
        if response.status_code != 200:
            raise GitLabError(response.status_code, response.text, action="list_pipeline_jobs")
        return response.json()

    async def get_file_content(
        self, project_path: str, file_path: str, ref: str = "HEAD"
    ) -> str | None:
        """Fetch a single file's raw bytes from the project's repository.

        Returns the file content as a string, or None if the file does not
        exist (404). Used by the per-project `.mr-sentinel.yaml` override
        path. `ref` defaults to `HEAD` which GitLab resolves to the project's
        default branch.
        """
        encoded_project = self._encode_project(project_path)
        encoded_path = quote(file_path, safe="")
        response = await self._request(
            "GET",
            f"/projects/{encoded_project}/repository/files/{encoded_path}/raw",
            action="get_file_content",
            params={"ref": ref},
        )
        if response.status_code == 200:
            return response.text
        if response.status_code == 404:
            return None
        raise GitLabError(response.status_code, response.text, action="get_file_content")

    async def list_vulnerability_findings(
        self, project_path: str
    ) -> list[dict[str, Any]]:
        """Return security vulnerability findings if the project + tier exposes them.

        Many GitLab Free / Premium projects return 403 here — caller should treat
        that as 'no data available' and skip the dep-advisory rule.
        """
        encoded = self._encode_project(project_path)
        response = await self._request(
            "GET",
            f"/projects/{encoded}/vulnerability_findings",
            action="list_vulnerability_findings",
            params={"per_page": 50},
        )
        if response.status_code == 200:
            return response.json()
        if response.status_code in (403, 404):
            logger.info("vulnerability_findings not accessible (status=%d, likely free tier)", response.status_code)
            return []
        raise GitLabError(response.status_code, response.text, action="list_vulnerability_findings")
