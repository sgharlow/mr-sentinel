# GitLab MCP Endpoint Audit — Migration Reference

**Last updated:** 2026-05-18
**Status:** This matrix is preserved as a future-migration reference. MR Sentinel uses the GitLab REST API directly (right column) for every endpoint listed below. See [decision below](#decision-2026-05-18-rest-as-primary-transport) and the architectural-simplification note at the top of `app/agent_runner.py`.

## Decision — 2026-05-18: REST as primary transport

The spec originally framed the GitLab MCP server as the load-bearing integration with REST as a per-endpoint fallback. After scoping the actual loop (≤8 deterministic calls per MR), we inverted the choice: **REST is the primary transport; MCP is preserved as a future migration target.** Rationale:

1. **Surface size.** Eight stable REST endpoints cover the full agent loop. Adding an MCP transport in front of those endpoints adds operational surface (server process, transport, tool registry, version skew) without changing behavior.
2. **Risk register §12 #1.** The original spec called this risk Medium-likelihood / High-impact. Choosing REST collapses both — REST is documented, stable across GitLab tiers, and behaves consistently between gitlab.com and self-hosted instances.
3. **Trace clarity.** REST calls show up in Cloud Logging as bare HTTP transactions. Judges and compliance reviewers can replay a full evaluation by re-executing the eight calls in order from the persisted `audit_log` rows.
4. **Hackathon judging axis.** The "Technological Implementation" criterion counts tool calls, not the transport in front of them. Eight REST tools per MR meets the multi-tool bar.

Future-MCP migration is a one-file change (`app/gitlab_client.py`) when GitLab's official MCP server reaches feature parity with REST for these endpoints.

## Endpoint matrix

| # | Spec tool name | Actual usage | Production transport | Implementation |
|---|---|---|---|---|
| 1 | `get_merge_request` | Fetch MR metadata (title, description, author, state, labels, sha) | REST | `GitLabClient.get_merge_request()` |
| 2 | `get_merge_request_diff` | Fetch unified diff list for the MR | REST | `GitLabClient.get_merge_request_diffs()` |
| 3 | `list_pipeline_jobs` | Get jobs for the MR's HEAD pipeline | REST | `GitLabClient.list_pipeline_jobs()` (preceded by `get_latest_pipeline_for_sha`) |
| 4 | `list_dependabot_alerts` | Vulnerability findings on the project (`vulnerability_findings`, gracefully empty on Free tier) | REST | `GitLabClient.list_vulnerability_findings()` |
| 5 | `post_merge_request_comment` | Post the agent's structured comment | REST | `GitLabClient.post_merge_request_comment()` |
| 5a | _(upsert pattern)_ | Find prior agent comment via `<!-- mr-sentinel:v1 -->` marker | REST | `GitLabClient.find_agent_note()` |
| 5b | _(upsert pattern)_ | Edit prior agent comment instead of creating a new one | REST | `GitLabClient.update_merge_request_note()` |
| 6 | `add_merge_request_labels` | Add `mr-sentinel-reviewed` and (on block) `blocked-compliance` | REST | `GitLabClient.add_merge_request_labels()` |
| 7 | `create_issue` | Open a remediation issue on block verdict, linked from the MR comment | REST | `GitLabClient.create_issue()` |

**Tool-count summary:** up to 8 GitLab tool calls + 1 Vertex AI Gemini call per evaluation. Skipped automatically when (a) the same `(project, mr_iid, sha, rubric_version)` has already been scored (dedup), (b) the pipeline doesn't exist yet (jobs call skipped), or (c) the project is on Free tier and `vulnerability_findings` returns 403 (silently swallowed).

## Authentication

- `PRIVATE-TOKEN` header with a GitLab personal access token, stored in Secret Manager as `mr-sentinel-gitlab-token` and mounted to the Cloud Run service as `GITLAB_TOKEN`.
- Token scopes: `api`, `read_repository`, `write_repository`.

## When to revisit MCP

Reopen this matrix if any of the following becomes true:

1. The GitLab MCP server gains coverage for all 8 endpoints above with parity (auth, pagination, error semantics).
2. The agent loop grows to >20 distinct tools and the transport boilerplate in `gitlab_client.py` outweighs the cost of an MCP indirection.
3. A consumer of MR Sentinel asks for MCP transport because their security model requires it (e.g., centralized tool-policy enforcement).

Until then, REST.

## Addendum — 2026-06-08: hackathon-required MCP integration (Path B)

The Google Cloud Rapid Agent Hackathon requires the partner's MCP server be imported
and called at runtime. The OFFICIAL GitLab Duo MCP server (`gitlab.com/api/v4/mcp`)
is Premium/Ultimate-only, beta, OAuth-DCR-only, and exposes no tool to post/update an
MR note or set MR labels — so it cannot run MR Sentinel's write-backs and is unusable
on this Free-tier account. Decision: use a community GitLab MCP server
(`@zereight/mcp-gitlab`, stdio) via ADK `MCPToolset` for the agent's evaluation READS
(`get_merge_request`, `get_merge_request_diffs`, `list_merge_request_pipelines`).
Write-backs stay on REST (`app/gitlab_client.py`) to keep comment formatting + upsert +
dedup deterministic. See `docs/superpowers/plans/2026-06-08-adk-gitlab-mcp.md`.
