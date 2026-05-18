# MR Sentinel

> An AI-powered governance agent for merge requests — applies a configurable engineering rubric to every MR, posts actionable feedback, and surfaces drift trends to engineering leaders.

**Hackathon:** Google Cloud Rapid Agent Hackathon — GitLab track
**Submission deadline:** June 11, 2026 — 14:00 PT
**License:** [MIT](LICENSE)
**Author:** [sgharlow](https://github.com/sgharlow)

---

## Status

Day 2 of 26. Repo initialization complete. Webhook handler scaffolded. Rubric schema v1 in place. **GCP infrastructure bootstrapped** on the shared `aicin-477004` project (previous Google Cloud Run Hackathon, reused per existing-credentials directive). See [`mr-sentinel-hackathon-spec.md`](mr-sentinel-hackathon-spec.md) for the full spec and 26-day build plan.

### GCP resources live

| Resource | Identifier |
|---|---|
| Project | `aicin-477004` (region `us-central1`) |
| Artifact Registry | `us-central1-docker.pkg.dev/aicin-477004/mr-sentinel` |
| Secret: webhook token | `mr-sentinel-gitlab-webhook-secret` (v1 populated — 64 hex chars) |
| Secret: GitLab PAT | `mr-sentinel-gitlab-token` (placeholder — no version yet) |
| APIs enabled | Vertex AI, Agent Builder (Discovery Engine), Cloud Run, Cloud SQL, Secret Manager, Artifact Registry, Cloud Build, IAM, Service Networking, Cloud Resource Manager, Cloud Logging, Cloud Monitoring |

Re-run any time via [`scripts/gcp-bootstrap.sh`](scripts/gcp-bootstrap.sh) — idempotent. Defaults to `PROJECT_ID=aicin-477004`; override with the env var.

## What this is

An agent that watches your GitLab merge requests and applies a written, configurable rubric to each one with the consistency of a machine and the judgment of a senior reviewer — in seconds, with an audit-grade paper trail. Every comment ties back to a named compliance control. The rubric is the product.

The agent class missing from the market is one that **applies a written rubric to every MR with the consistency of a machine and the judgment of a senior reviewer**, in seconds, with a paper trail — without being a generic "AI code reviewer." Every rule maps 1:1 to a control a compliance auditor would recognize.

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                         User's GitLab Project                         │
│             (MR opened / updated → webhook fires)                     │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │
                                 ▼
              ┌──────────────────────────────────────┐
              │       Cloud Run: webhook handler     │
              │       (Python, FastAPI, async)       │
              └──────────────────┬───────────────────┘
                                 │
                                 ▼
              ┌──────────────────────────────────────┐
              │     Google Cloud Agent Builder       │
              │          (Gemini 3, orchestration)   │
              │                                      │
              │   Plan → Tool calls → Reason → Act   │
              └──┬────────────────┬───────────────┬──┘
                 │                │               │
                 ▼                ▼               ▼
         ┌───────────────┐ ┌─────────────┐ ┌────────────────┐
         │ GitLab MCP    │ │ Vertex AI   │ │ Secret Manager │
         │ server        │ │ Data Store  │ │ (tokens, keys) │
         │ (partner)     │ │ (rubric)    │ │                │
         └───────────────┘ └─────────────┘ └────────────────┘
                 │
                 ▼
         ┌────────────────────────────────┐
         │  Cloud SQL (PostgreSQL):       │
         │   – per-MR scoring history     │
         │   – team / project rollups     │
         │   – audit log                  │
         └────────────┬───────────────────┘
                      │
                      ▼
         ┌────────────────────────────────┐
         │  Cloud Run: leadership UI      │
         │   (React + Recharts, served    │
         │    from same Cloud Run service)│
         └────────────────────────────────┘
```

## Cloud

This project is **Google Cloud only**. By hackathon rule and by design choice, no AWS, no Azure, no third-party LLM APIs. AI is Gemini via Agent Builder + Vertex AI Data Store. Compute is Cloud Run. State is Cloud SQL (PostgreSQL). Secrets are Secret Manager.

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
| `GCP_PROJECT_ID` | Used by Agent Builder, Vertex, Cloud SQL bindings |
| `RUBRIC_VERSION` | Defaults to `v1` |

## Rubric customization

The rubric lives in `rubric/v1.yaml`. Schema in `rubric/schema.json`. Fifteen rules across four categories: contract & spec gates, quality gates, security gates, operational gates. Each rule maps to a named control.

To customize per-project: add a `.mr-sentinel.yaml` to the root of your GitLab project that overrides specific rules. Schema-validated on load — invalid configs fail closed.

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
