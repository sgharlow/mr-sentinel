# MR Sentinel

> An AI-powered governance agent for merge requests — applies a configurable engineering rubric to every MR, posts actionable feedback, and surfaces drift trends to engineering leaders.

**Hackathon:** Google Cloud Rapid Agent Hackathon — GitLab track
**Submission deadline:** June 11, 2026 — 14:00 PT
**License:** [MIT](LICENSE)
**Author:** [sgharlow](https://github.com/sgharlow)

---

## Status

**Days 1-3, 4-8, 9-14 milestones closed (3 of 6).** Day 4 of 26. End-to-end loop verified live on Cloud Run: GitLab MR webhook → fetch MR + diffs + pipeline + vulnerabilities → fetch optional `.mr-sentinel.yaml` per-project rubric override → Vertex AI Gemini 2.5 Flash evaluation against 15 rubric rules → upsert structured comment + labels on the MR → open linked remediation issue on block verdicts → persist score + child rule outcomes + audit row to Cloud SQL. Latency ~30s p50. 44/44 tests green, CI green. GCP infrastructure on shared `aicin-477004`. See [`mr-sentinel-hackathon-spec.md`](mr-sentinel-hackathon-spec.md) for the full spec and 26-day build plan.

### GCP resources live

| Resource | Identifier |
|---|---|
| Project | `aicin-477004` (region `us-central1`) |
| Cloud Run service | `mr-sentinel-webhook` — https://mr-sentinel-webhook-n6oitfxdra-uc.a.run.app |
| Cloud SQL Postgres 15 | `mr-sentinel-db` (db-f1-micro) · connection `aicin-477004:us-central1:mr-sentinel-db` · db `mrsentinel` · user `app` (unix socket via Cloud SQL Auth Proxy at `/cloudsql/<conn>`) |
| Artifact Registry | `us-central1-docker.pkg.dev/aicin-477004/mr-sentinel` |
| GitLab demo repo | https://gitlab.com/sgharlow/governance-demo-app (webhook id 78485229) |
| Secret: webhook token | `mr-sentinel-gitlab-webhook-secret` — bound to service as `GITLAB_WEBHOOK_SECRET` |
| Secret: GitLab PAT | `mr-sentinel-gitlab-token` (v1) — for outbound GitLab REST API calls |
| Secret: DB app password | `mr-sentinel-db-app-password` — bound to service as `DB_PASSWORD` |
| Secret: DB root password | `mr-sentinel-db-password` — postgres user; held for ops only |
| APIs enabled | Vertex AI, Cloud Run, Cloud SQL, Secret Manager, Artifact Registry, Cloud Build, IAM, Service Networking, Cloud Resource Manager, Cloud Logging, Cloud Monitoring (Discovery Engine enabled by bootstrap but not in use — see `docs/mcp-endpoint-audit.md`) |

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
              │   Agent loop (app/main.py)           │
              │                                      │
              │   1. dedup check (sha + rubric_ver)  │
              │   2-5. fetch MR/diffs/pipeline/jobs/ │
              │        vulnerability findings        │
              │   6. Gemini evaluate vs. rubric      │
              │   7-9. persist · upsert comment ·    │
              │        labels · followup issue       │
              └──┬────────────────┬───────────────┬──┘
                 │                │               │
                 ▼                ▼               ▼
         ┌───────────────┐ ┌─────────────┐ ┌────────────────┐
         │ GitLab REST   │ │ Vertex AI   │ │ Secret Manager │
         │ API (8 tools) │ │ Gemini 2.5  │ │ (4 secrets)    │
         │               │ │ Flash       │ │                │
         └───────────────┘ └─────────────┘ └────────────────┘
                 │
                 ▼
         ┌────────────────────────────────┐
         │  Cloud SQL (PostgreSQL 15):    │
         │   – mr_scores                  │
         │   – rule_outcomes              │
         │   – audit_log                  │
         │   – schema_migrations          │
         └────────────┬───────────────────┘
                      │
                      ▼
         ┌────────────────────────────────┐
         │  Cloud Run: leadership UI      │
         │   (server-rendered HTML,       │
         │    same Cloud Run service)     │
         └────────────────────────────────┘
```

## Cloud

This project is **Google Cloud only**. By hackathon rule and by design choice, no AWS, no Azure, no third-party LLM APIs. AI is Vertex AI Gemini 2.5 Flash via the direct Vertex SDK. Compute is Cloud Run (one service hosting both webhook and dashboard). State is Cloud SQL PostgreSQL 15. Secrets are Secret Manager. GitLab integration is the REST API (8 endpoints per MR — `docs/mcp-endpoint-audit.md` holds the matrix as a future-migration reference for the MCP transport).

The architectural simplifications taken — direct Vertex SDK instead of Agent Builder, inlined rubric instead of a Vertex Data Store, GitLab REST instead of MCP — are documented at the top of `app/agent_runner.py`. They keep the orchestration loop visible in plain Python, the audit trail replayable from Cloud SQL, and the deployment surface small.

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
│   ├── agent_runner.py               # rubric load + Gemini call + parse + comment render
│   ├── gitlab_client.py              # async GitLab REST client (8 endpoints)
│   └── persistence.py                # asyncpg pool + mr_scores/rule_outcomes/audit_log writes
├── tests/                            # pytest — 44 tests
│   ├── test_webhook.py               # /health + webhook auth + payload validation
│   ├── test_agent_runner.py          # rubric load/parse + prompt assembly + comment render
│   ├── test_gitlab_client.py         # 8 REST endpoints + override fetch + upsert pattern
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
│   └── mcp-endpoint-audit.md         # REST endpoint matrix + future-MCP migration reference
├── .github/workflows/
│   └── ci.yml                        # pytest + rubric schema validation on push/PR
├── Dockerfile                        # Python 3.11-slim → uvicorn → :8080
├── Makefile                          # install / test / run-local / lint shortcuts
├── requirements.txt                  # runtime deps (FastAPI, asyncpg, jsonschema, vertexai, ...)
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
