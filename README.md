<p align="center">
  <img src="docs/assets/logo-256.png" alt="MR Sentinel logo" width="160" height="160">
</p>

<h1 align="center">MR Sentinel</h1>

> An AI governance agent for merge requests — a Google ADK agent that reads each MR through GitLab's MCP server, judges it with Gemini against a written compliance rubric, and leaves an audit-grade paper trail.

**▶ Watch the 3-minute demo:** [youtu.be/S93xnolHRe0](https://youtu.be/S93xnolHRe0)

**Try it now:** [live dashboard](https://mr-sentinel-webhook-n6oitfxdra-uc.a.run.app/dashboard) · [sample audit page](https://mr-sentinel-webhook-n6oitfxdra-uc.a.run.app/audit/sgharlow/governance-demo-app/10) · [demo MR](https://gitlab.com/sgharlow/governance-demo-app/-/merge_requests/10)

**Hackathon:** Google Cloud Rapid Agent Hackathon — GitLab track
**Submission deadline:** June 11, 2026 — 14:00 PT (target submit by 12:00 PT for safety buffer)
**License:** [MIT](LICENSE)
**Author:** [sgharlow](https://github.com/sgharlow)

---

## 👋 Judges — start here

A 60-second guided tour. Every link is live and needs no auth:

1. **Watch a verdict land** → [demo MR `!10`](https://gitlab.com/sgharlow/governance-demo-app/-/merge_requests/10) — a `chore: add .env.production` MR carrying live-looking secrets. The agent's comment scores it **0.0/10 · block**, cites `no-secrets-in-diff` mapped to **SOC 2 CC6.1 / ISO 27001 A.9.4.3 / OWASP-ASVS V2**, applies a `blocked-compliance` label, and auto-opens a remediation issue.
2. **The leadership view** → [`/dashboard`](https://mr-sentinel-webhook-n6oitfxdra-uc.a.run.app/dashboard) — verdict distribution (last 30 days), top-5 failing rules, recent-MR drill-down.
3. **The auditor view** → [`/audit/sgharlow/governance-demo-app/10`](https://mr-sentinel-webhook-n6oitfxdra-uc.a.run.app/audit/sgharlow/governance-demo-app/10) — every rule outcome, its control mapping, and the audit-log timeline. The audit *is* the byproduct of doing the work, not a separate exercise.
4. **The product's center of gravity** → [`rubric/v1.yaml`](rubric/v1.yaml) — 15 rules, each mapped 1:1 to a named compliance control. MIT-licensed; consumers override per-project by dropping a `.mr-sentinel.yaml` at their repo root.

**What to notice:** every action ties back to a control an auditor recognizes — that's what makes this *compliance-grade governance* rather than "AI reviews a PR." The agent runs on Cloud Run scale-to-zero and is fully replayable from the `audit_log`.

**Judging-criteria map** — *Technological implementation:* a Google ADK agent (Gemini 2.5 Flash) that reads each MR through **GitLab's MCP server** (`@zereight/mcp-gitlab`, attached via ADK `MCPToolset`) and records a structured verdict via a tool call — all three required technologies (Gemini, Agent Builder/ADK, the partner MCP server) invoked at runtime — on a full GCP-native stack (Cloud Run, Cloud SQL, Secret Manager, Artifact Registry, Vertex AI, Cloud Build, Cloud Logging), with a replayable audit log. *Design:* three surfaces / three personas (above). *Potential impact:* every regulated-industry engineering org has this exact pain. *Quality of idea:* the rubric-as-product moat. Full write-up in [`docs/devpost-submission.md`](docs/devpost-submission.md).

---

## Status

> ✅ **SUBMITTED to the Google Cloud Rapid Agent Hackathon (GitLab track) on 2026-05-31.** Demo video: https://youtu.be/S93xnolHRe0. Project edits remain open until the June 11, 2026 — 17:00 EDT deadline.

**End-to-end loop on Cloud Run:** GitLab MR webhook → a **Google ADK agent** (Gemini 2.5 Flash) reads the MR, its diff, and its pipeline **through GitLab's MCP server**, resolves an optional `.mr-sentinel.yaml` per-project rubric override, evaluates against the 15 rubric rules, and records a structured verdict via a `record_verdict` tool → MR Sentinel upserts the structured comment + labels on the MR, opens a linked remediation issue on block verdicts, and persists score + child rule outcomes + audit row to Cloud SQL (write-backs over the GitLab REST API). Leadership dashboard at `/dashboard` + `/audit/{project}/{mr_iid}` (server-rendered, dark theme). **64 tests green, CI green.** End-to-end latency for the agentic ADK loop runs ~25–30s per evaluation (observed live; the prior single-call REST path measured p50 ~20s — the multi-turn MCP tool-calling loop is expectedly longer). GCP infrastructure on shared `aicin-477004`. See [`mr-sentinel-hackathon-spec.md`](mr-sentinel-hackathon-spec.md) for the full spec.

### GCP resources live

| Resource | Identifier |
|---|---|
| Project | `aicin-477004` (region `us-central1`) |
| Cloud Run service | `mr-sentinel-webhook` — https://mr-sentinel-webhook-n6oitfxdra-uc.a.run.app |
| Cloud SQL Postgres 15 | `mr-sentinel-db` (db-f1-micro) · connection `aicin-477004:us-central1:mr-sentinel-db` · db `mrsentinel` · user `app` (unix socket via Cloud SQL Auth Proxy at `/cloudsql/<conn>`) |
| Artifact Registry | `us-central1-docker.pkg.dev/aicin-477004/mr-sentinel` |
| GitLab demo repo | https://gitlab.com/sgharlow/governance-demo-app (webhook id 78485229) |
| Secret: webhook token | `mr-sentinel-gitlab-webhook-secret` — bound to service as `GITLAB_WEBHOOK_SECRET` |
| Secret: GitLab PAT | `mr-sentinel-gitlab-token` (v1) — outbound GitLab calls: the MCP server (agent reads) + the REST client (write-backs) |
| Secret: DB app password | `mr-sentinel-db-app-password` — bound to service as `DB_PASSWORD` |
| Secret: DB root password | `mr-sentinel-db-password` — postgres user; held for ops only |
| APIs enabled | Vertex AI (Gemini, via the Google ADK agent), Cloud Run, Cloud SQL, Secret Manager, Artifact Registry, Cloud Build, IAM, Service Networking, Cloud Resource Manager, Cloud Logging, Cloud Monitoring. (Vertex AI Search / Discovery Engine is *not* used — here "Agent Builder" means the Google Agent Development Kit; see `docs/mcp-endpoint-audit.md`.) |

Service endpoints:
- `GET /health` — liveness check (not `/healthz` — Cloud Run intercepts that path)
- `GET /docs` — FastAPI Swagger UI
- `POST /gitlab/webhook` — webhook handler, requires `X-Gitlab-Token` header

Re-run any time:

```bash
bash scripts/gcp-bootstrap.sh         # project, APIs, secrets, registry (idempotent)
bash scripts/cloud-run-deploy.sh      # Cloud Build + Cloud Run deploy
bash scripts/smoke-test.sh            # 4-test health + auth check
bash scripts/diag.sh                  # service status + recent logs
```

## What this is

An agent that watches your GitLab merge requests and applies a written, configurable rubric to each one with the consistency of a machine and the judgment of a senior reviewer — in seconds, with an audit-grade paper trail. Every comment ties back to a named compliance control. The rubric is the product.

The agent class missing from the market is one that **applies a written rubric to every MR with the consistency of a machine and the judgment of a senior reviewer**, in seconds, with a paper trail — without being a generic "AI code reviewer." Every rule maps 1:1 to a control a compliance auditor would recognize.

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                         User's GitLab Project                         │
│             (MR opened / updated → webhook fires)                     │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │  POST /gitlab/webhook
                                 │  X-Gitlab-Token: <secret>
                                 ▼
              ┌──────────────────────────────────────┐
              │   Cloud Run: webhook handler         │
              │   (Python 3.11, FastAPI, uvicorn)    │
              │   202 Accepted → BackgroundTask      │
              └──────────────────┬───────────────────┘
                                 │
                                 ▼
              ┌──────────────────────────────────────┐
              │   Orchestration (app/main.py)        │
              │   1. dedup (sha + rubric_version)    │
              │   2. resolve per-project rubric      │
              │   3. run the ADK evaluation agent ───┼────────┐
              │   4. write verdict back + persist    │        │
              └──────────────┬───────────────────────┘        │
   write-backs (comment/     │                                │ evaluation
   labels/issue) via REST     │                               ▼
                 ┌────────────┴───┬───────────────┐  ┌─────────────────────────────────────┐
                 ▼                ▼               ▼  │ ADK evaluation agent                │
         ┌───────────────┐ ┌─────────────┐ ┌──────┐ │ (app/adk_agent.py = Agent Builder)  │
         │ GitLab REST   │ │ Cloud SQL   │ │Secret│ │  • model: Vertex AI Gemini 2.5 Flash│
         │ (write-backs) │ │ mr_scores / │ │ Mgr  │ │  • tools: GitLab MCP server (reads) │
         └───────────────┘ │ rule_outcomes│ └──────┘ │    @zereight/mcp-gitlab (stdio):    │
                           │ / audit_log │           │    get_merge_request / _diffs /     │
                           └──────┬──────┘           │    _pipelines                       │
                                  │                  │  • record_verdict (structured out)  │
                                  ▼                  └─────────────────────────────────────┘
                    ┌────────────────────────────┐
                    │ Cloud Run: leadership UI   │
                    │  /dashboard · /audit       │
                    │  (server-rendered HTML)    │
                    └────────────────────────────┘
```

## Cloud

This project is **Google Cloud only**. By hackathon rule and by design choice, no AWS, no Azure, no third-party LLM APIs. The evaluation is a **Google Agent Development Kit (ADK) agent** — the hackathon's "Agent Builder" surface — whose model is **Vertex AI Gemini 2.5 Flash** and whose context-gathering tools come from **GitLab's MCP server** (`@zereight/mcp-gitlab`, attached via ADK `MCPToolset` over stdio). Compute is Cloud Run (one service hosting both webhook and dashboard). State is Cloud SQL PostgreSQL 15. Secrets are Secret Manager.

**The three required technologies, at runtime:** *Gemini* is the ADK agent's model; *Agent Builder* is the ADK agent itself (`LlmAgent` + `Runner` in `app/adk_agent.py`); the *GitLab MCP server* supplies the agent's read tools (`get_merge_request`, `get_merge_request_diffs`, `list_merge_request_pipelines`), which the agent calls on every evaluation. This is a deliberate **hybrid**: the agent *reads* the MR through the MCP server, but the *write-backs* (comment, labels, remediation issue) stay on the GitLab REST API — because the official GitLab Duo MCP server is Premium/Ultimate-only, OAuth-only, and exposes no tool to post an MR note or set MR labels. So a community GitLab MCP server (`@zereight/mcp-gitlab`) carries the reads while REST keeps the formatting-sensitive writes deterministic. The full decision is documented in [`docs/mcp-endpoint-audit.md`](docs/mcp-endpoint-audit.md).

## Setup (local development)

Prerequisites:

- Python 3.11+
- Docker (for Cloud Run parity local builds)
- `gcloud` CLI authenticated to your GCP project
- A GitLab personal access token with `api`, `read_repository`, `write_repository` scopes

```bash
# install
make install

# run the webhook handler locally on :8080
make run-local

# verify
curl http://localhost:8080/healthz
```

Environment variables (do not commit values — use `.env.local` for dev, Secret Manager for production):

| Variable | Purpose |
|---|---|
| `GITLAB_WEBHOOK_SECRET` | Token expected in `X-Gitlab-Token` header on inbound webhooks |
| `GITLAB_BASE_URL` | Defaults to `https://gitlab.com` |
| `GITLAB_TOKEN` | Personal access token for outbound GitLab API/MCP calls |
| `GCP_PROJECT_ID` | Used by Vertex AI (Gemini) and Cloud SQL connector bindings |
| `RUBRIC_VERSION` | Defaults to `v1` |

## Rubric customization

The default rubric lives in `rubric/v1.yaml`. Schema in `rubric/schema.json`. Fifteen rules across four categories: contract & spec gates, quality gates, security gates, operational gates. Each rule maps to a named control.

To customize per-project: drop a `.mr-sentinel.yaml` at the root of your GitLab repo (on the default branch). On every webhook fire, MR Sentinel fetches the file via `GET /repository/files/.mr-sentinel.yaml/raw`, validates it against `rubric/schema.json`, and uses it in place of the bundled v1 for that evaluation.

Override semantics:

- The override is a **full rubric replacement** — same shape as `rubric/v1.yaml`, exactly 15 rules (enforced by schema), valid `version` field. Copy `rubric/v1.yaml` as a starting point and edit.
- **Fail-closed:** if the file is present but invalid (bad YAML, schema violation), the agent falls back to the bundled v1 and writes an `override_invalid` row to the `audit_log` table with the validation error.
- **No file → bundled v1.** A 404 is treated as "no override, use defaults."
- The `audit_log.details.rubric_source` field records which rubric was used per evaluation: `bundled`, `project_override`, or `bundled_after_invalid_override`.

## Tests

```bash
make test
```

CI runs the full pytest suite plus a separate rubric-schema-validation step on every push (see `.github/workflows/ci.yml`). Line coverage is aspirational — not gated in CI yet; a `pytest-cov` gate is on the post-hackathon backlog.

## Repository layout

```
mr-sentinel/
├── app/                              # FastAPI service + agent orchestration
│   ├── __init__.py
│   ├── main.py                       # webhook handler + _process_mr_event loop
│   ├── adk_agent.py                  # ADK agent: Gemini + GitLab MCP toolset + record_verdict
│   ├── agent_runner.py               # rubric load + prompts + Evaluation mapping + comment render
│   ├── gitlab_client.py              # async GitLab REST client (write-backs: comment/label/issue)
│   └── persistence.py                # asyncpg pool + mr_scores/rule_outcomes/audit_log writes
├── tests/                            # pytest — 64 tests
│   ├── test_webhook.py               # /health + webhook auth + payload validation
│   ├── test_adk_agent.py             # ADK runner + MCP toolset wiring + record_verdict + Vertex-backend (mocked)
│   ├── test_agent_runner.py          # rubric load/parse + prompt assembly + comment render
│   ├── test_gitlab_client.py         # REST write-back endpoints + override fetch + upsert pattern
│   ├── test_dashboard.py             # /dashboard + /audit rendering (TestClient, patched data)
│   └── test_rubric.py                # schema validation + rule counts + id uniqueness
├── rubric/
│   ├── v1.yaml                       # bundled rubric (15 rules, 4 categories)
│   └── schema.json                   # JSONSchema for rubric validation
├── db/
│   ├── migrate.py                    # asyncpg-based migration runner
│   └── migrations/
│       ├── 001_initial.sql           # mr_scores + rule_outcomes + audit_log + schema_migrations
│       └── 002_app_grants.sql        # GRANT to `app` user + default privileges
├── scripts/
│   ├── gcp-bootstrap.sh              # project + APIs + secrets + Artifact Registry (idempotent)
│   ├── gitlab-bootstrap.sh           # create the governance-demo-app target repo
│   ├── cloud-run-deploy.sh           # Cloud Build + Cloud Run deploy
│   ├── db-migrate.sh                 # cloud-sql-proxy + db/migrate.py
│   ├── smoke-test.sh                 # 4-test health + auth check on deployed service
│   ├── diag.sh                       # service status + recent logs
│   ├── test-override-live.sh         # live-fire the `.mr-sentinel.yaml` override path
│   └── cleanup-override-verification.sh   # teardown for the live-fire test
├── docs/
│   ├── mcp-endpoint-audit.md         # REST endpoint matrix + future-MCP migration reference
│   ├── devpost-submission.md         # paste-ready Devpost form text
│   ├── demo-script.md                # 3-minute video script with shot-by-shot direction
│   ├── days-20-23-demo-coverage.md   # rubric coverage gap analysis (11/15 → 14/15)
│   ├── live-fire-2026-05-21.md       # latest end-to-end verification + dashboard scrape
│   └── share-copy.md                 # social/blog launch copy
├── .github/workflows/
│   └── ci.yml                        # pytest + rubric schema validation on push/PR
├── Dockerfile                        # Python 3.11-slim → uvicorn → :8080
├── Makefile                          # install / test / run-local / lint shortcuts
├── requirements.txt                  # runtime deps (FastAPI, asyncpg, vertexai, google-adk, mcp, ...)
├── requirements-dev.txt              # test/lint deps (pytest, respx, jsonschema, ...)
├── pyproject.toml                    # pytest + ruff config
├── .env.example                      # local-dev env vars template
├── .gcloudignore                     # Cloud Build context excludes
├── LICENSE                           # MIT
├── CODE_OF_CONDUCT.md                # Contributor Covenant 2.1
└── mr-sentinel-hackathon-spec.md     # the full spec (15 sections)
```

## Contributing

This is a hackathon submission built solo. Post-hackathon the repo stays public under sgharlow and the rubric ships as reusable MIT-licensed IP. Issues welcome; PRs likely won't be merged until after the June 11 deadline.

## Disclosure

Built in personal capacity, outside of any employer relationship. No employer code, customer data, or proprietary information appears in this repo, the demo, or the demo video. The rubric is derived from publicly published methodologies authored by sgharlow (the AI Control Framework and the CDPD spec-driven development pattern).
