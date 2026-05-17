# GitLab MCP Endpoint Audit

**Last updated:** 2026-05-17 (Day 2)
**Purpose:** Mitigate spec risk #1 — "GitLab MCP server has gaps for required endpoints." This document tracks coverage of the 8 endpoints MR Sentinel needs from the GitLab MCP server, with a REST API fallback per endpoint so the build never blocks on MCP gaps.

This is a working document. Each endpoint moves through statuses:

- ❓ **Untested** — listed in spec, not yet verified against live MCP
- ✅ **MCP available** — verified working against live GitLab MCP
- ⚠️ **MCP partial** — endpoint exists but has known limitations (rate limit, missing fields, auth scope mismatch)
- ❌ **MCP missing** — endpoint not exposed; fall back to REST

## Required endpoints (from spec §5 component rationale)

| # | Tool | Purpose | MCP status | Fallback (REST) |
|---|---|---|---|---|
| 1 | `get_merge_request` | Fetch MR metadata (title, description, author, state, labels) | ❓ Untested | `GET /api/v4/projects/:id/merge_requests/:iid` |
| 2 | `get_merge_request_diff` | Fetch the unified diff for the MR | ❓ Untested | `GET /api/v4/projects/:id/merge_requests/:iid/diffs` |
| 3 | `list_pipeline_jobs` | Get pipeline status + job results for the MR's HEAD pipeline | ❓ Untested | `GET /api/v4/projects/:id/pipelines/:pipeline_id/jobs` |
| 4 | `list_dependabot_alerts` | Get vulnerability alerts (or equivalent GitLab security advisory tool) | ❓ Untested | `GET /api/v4/projects/:id/vulnerabilities` (Ultimate) or `GET /api/v4/projects/:id/security/vulnerability_findings` |
| 5 | `post_merge_request_comment` | Post the agent's structured comment to the MR | ❓ Untested | `POST /api/v4/projects/:id/merge_requests/:iid/notes` |
| 6 | `add_merge_request_labels` | Add labels like `blocked-compliance`, `mr-sentinel-reviewed` | ❓ Untested | `PUT /api/v4/projects/:id/merge_requests/:iid` with `add_labels` |
| 7 | `create_issue` | Open a remediation issue linked from the MR comment | ❓ Untested | `POST /api/v4/projects/:id/issues` |
| 8 | `list_project_members` | For tagging the right team in remediation issues | ❓ Untested | `GET /api/v4/projects/:id/members/all` |

## Day 1–3 milestone — "sample MCP call succeeds end-to-end"

The Day 1–3 milestone closes when **one** of these endpoints (`get_merge_request` is the obvious pick) returns a successful payload against the personal demo GitLab project, called through the MCP server from a local Python script.

### Proof-of-life recipe (draft — refine when MCP server is live)

```python
# scripts/mcp_proof_of_life.py — to be filled out Day 3
# Will call get_merge_request via the GitLab MCP server on the demo project
# Success criterion: returns 200 with `iid` field populated for MR #1 on the demo repo
```

### Risk decision tree

```
Is endpoint exposed by MCP server?
├── ✅ Yes → use MCP, log tool name in audit trail
└── ❌ No  → use REST fallback (column 5), log REST endpoint in audit trail
            with a 'mcp_gap' marker so we can revisit after the hackathon
```

The audit trail records which transport was used per call, so any compliance
review can reproduce the agent's decision path even when transports degrade.

## Authentication notes

- **MCP transport:** Bearer token over stdio or HTTP (depends on MCP server build)
- **REST fallback:** `PRIVATE-TOKEN` header with a GitLab personal access token
- Both consume the same `GITLAB_TOKEN` env var (Day 4–8: move to Secret Manager)
- Token scopes required: `api`, `read_repository`, `write_repository`

## Open questions for Day 3 verification

1. Does the GitLab MCP server expose `list_pipeline_jobs` directly, or must we
   reach for the parent pipeline first?
2. Is `list_dependabot_alerts` the correct tool name for GitLab? GitLab's term
   is "vulnerability finding" — verify the MCP server's adapter.
3. Does `post_merge_request_comment` support markdown rendering of tables and
   collapsed sections? The agent's comment design depends on it.
4. Does `add_merge_request_labels` create labels that don't exist yet, or must
   we pre-create them in the project?

## Update protocol

When verifying an endpoint:

1. Run the script under `scripts/mcp_verify_<endpoint>.py`
2. Capture the request/response in `docs/mcp-evidence/<endpoint>.json` (gitignored if it includes tokens)
3. Update the status column above
4. Note any limitations under "MCP partial" with a link to the evidence

When the table reaches **8 ✅** with zero ❌, risk #1 is fully retired.
