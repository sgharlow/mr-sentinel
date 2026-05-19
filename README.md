# MR Sentinel

> An AI-powered governance agent for merge requests — applies a configurable engineering rubric to every MR, posts actionable feedback, and surfaces drift trends to engineering leaders.

**Hackathon:** Google Cloud Rapid Agent Hackathon — GitLab track
**Submission deadline:** June 11, 2026 — 14:00 PT
**License:** [MIT](LICENSE)
**Author:** [sgharlow](https://github.com/sgharlow)

---

## Status

**Day 1–3 milestone closed.** Day 2 of 26. End-to-end loop verified: GitLab MR → webhook fired → Cloud Run 202 Accepted → app logged event. GCP infrastructure bootstrapped on shared `aicin-477004`. See [`mr-sentinel-hackathon-spec.md`](mr-sentinel-hackathon-spec.md) for the full spec and 26-day build plan.

### GCP resources live

| Resource | Identifier |
|---|---|
| Project | `aicin-477004` (region `us-central1`) |
| Cloud Run service | `mr-sentinel-webhook` — https://mr-sentinel-webhook-n6oitfxdra-uc.a.run.app |
| Cloud SQL Postgres 15 | `mr-sentinel-db` (db-f1-micro) · connection `aicin-477004:us-central1:mr-sentinel-db` · db `mrsentinel` · user `app` (unix socket via Cloud SQL Auth Proxy at `/cloudsql/<conn>`) |
| Artifact Registry | `us-central1-docker.pkg.dev/aicin-477004/mr-sentinel` |
| GitLab demo repo | https://gitlab.com/sgharlow/governance-demo-app (webhook id 78485229) |
| Secret: webhook token | `mr-sentinel-gitlab-webhook-secret` — bound to service as `GITLAB_WEBHOOK_SECRET` |
| Secret: GitLab PAT | `mr-sentinel-gitlab-token` (v1) — for outbound GitLab API/MCP calls |
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

Coverage targets: changed-line coverage ≥ 80%, rubric schema validation 100%.

## Repository layout

```
mr-sentinel/
├── app/                  # FastAPI webhook handler
│   ├── __init__.py
│   └── main.py
├── tests/                # pytest suite
│   ├── test_webhook.py
│   └── test_rubric.py
├── rubric/
│   ├── v1.yaml           # the rubric (15 rules)
│   └── schema.json       # JSONSchema for rubric validation
├── docs/
│   └── mcp-endpoint-audit.md   # GitLab MCP coverage matrix (risk #1)
├── Dockerfile            # Cloud Run target
├── Makefile              # local dev shortcuts
├── requirements.txt      # runtime deps
├── requirements-dev.txt  # test/lint deps
├── pyproject.toml        # pytest + tooling config
├── LICENSE               # MIT
├── CODE_OF_CONDUCT.md
└── mr-sentinel-hackathon-spec.md   # the full spec
```

## Contributing

This is a hackathon submission built solo. Post-hackathon the repo stays public under sgharlow and the rubric ships as reusable MIT-licensed IP. Issues welcome; PRs likely won't be merged until after the June 11 deadline.

## Disclosure

Built in personal capacity, outside of any employer relationship. No employer code, customer data, or proprietary information appears in this repo, the demo, or the demo video. The rubric is derived from publicly published methodologies authored by sgharlow (the AI Control Framework and the CDPD spec-driven development pattern).
