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

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        response = await self._client.request(method, path, **kwargs)
        logger.info("gitlab %s %s -> %d", method, path, response.status_code)
        return response

    async def get_merge_request(self, project_path: str, mr_iid: int) -> MergeRequest:
        encoded = self._encode_project(project_path)
        response = await self._request("GET", f"/projects/{encoded}/merge_requests/{mr_iid}")
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
        response = await self._request("GET", f"/projects/{encoded}/merge_requests/{mr_iid}/diffs")
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
        response = await self._request("POST", f"/projects/{encoded}/issues", data=payload)
        if response.status_code not in (200, 201):
            raise GitLabError(response.status_code, response.text, action="create_issue")
        return response.json()
