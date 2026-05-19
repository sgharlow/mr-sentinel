# MR Sentinel — Hackathon Spec

**Event:** Google Cloud Rapid Agent Hackathon
**Track:** GitLab
**Submission deadline:** June 11, 2026 — 2:00 PM PT
**Author:** sgharlow (personal capacity)
**Repo (planned):** github.com/sgharlow/mr-sentinel
**Demo URL (planned):** mr-sentinel.run.app (Cloud Run)
**License:** MIT

---

## 1. One-line pitch

An AI-powered governance agent for merge requests — applies a configurable engineering rubric to every MR, posts actionable feedback, and surfaces drift trends to engineering leaders.

## 2. The problem

Engineering organizations operating under any meaningful compliance regime — security audits, regulated industries, customer contracts that name specific quality bars — share a common failure pattern. A merge request lands. The author has moved on. Reviewers are stretched. The MR gets a thumbs-up that defers the hard questions: was the rubric actually applied, is the test coverage where it needs to be, did the security gate run, does the change match a known-good pattern, is there a traceable artifact for the audit?

Most teams answer this with a wiki page nobody reads, a checklist nobody fills in, and a quarterly retro that surfaces the failures after they've already happened. The cost shows up as audit findings, security incidents, and rework — not as obvious quality decay, which makes it hard to budget against until it's too late.

The agent class missing from the market is one that **applies a written rubric to every MR with the consistency of a machine and the judgment of a senior reviewer**, in seconds, with a paper trail.

## 3. The target user

An engineering leader running a team of 10–500 developers in an environment where shipping decisions have downstream regulatory, contractual, or safety consequences. Industries: fintech, healthcare SaaS, automotive software, critical infrastructure, regulated data platforms, defense-adjacent commercial. The agent is not for FAANG-style high-velocity consumer engineering where governance is an anti-pattern — it's for environments where the contract names the controls.

## 4. The solution

MR Sentinel is a Gemini-powered agent running on Cloud Run that integrates with GitLab via its REST API. The agent triggers on MR webhooks, executes a multi-step plan against a configurable rubric, and takes real action against the MR: structured comment, labels, linked follow-up issues, label-based merge-block. A separate Cloud Run dashboard surfaces aggregate quality signals to leadership.

**Architectural simplifications taken — deliberate, documented in code:**

- **Gemini via direct Vertex AI SDK, not Agent Builder.** For a 15-rule rubric with one MR per invocation, the orchestration loop is short enough (≤8 deterministic tool calls plus one Gemini call) that the Agent Builder runtime adds latency and operational surface without adding behavior. The plan/reason/act loop lives in `app/main.py::_process_mr_event` as plain Python — every step is visible in Cloud Logging and replayable. If the rubric grows past ~50 rules or per-project planning becomes non-trivial, revisit Agent Builder.
- **Inlined rubric in the Gemini system prompt, not a Vertex AI Data Store.** Fifteen rules at ~3-5K tokens fits comfortably in the prompt and removes a retrieval roundtrip. The same `rubric/v1.yaml` is loaded at module import and rendered into the system prompt. If rules grow past ~50 or per-project customization gets complex, revisit `vertexai.preview.rag` or Discovery Engine.
- **GitLab REST API directly, not the GitLab MCP server.** Eight endpoints suffice for the full agent loop (see `docs/mcp-endpoint-audit.md` for the matrix). REST is documented, stable, and avoids the MCP-transport variance noted in spec §12 risk #1. The endpoint matrix is preserved as a future migration reference.

The rubric is the product's center of gravity. It ships with a v1 derived from the author's published methodologies (the AI Control Framework and the CDPD spec-driven development pattern), and is configurable per project via a `.mr-sentinel.yaml` file at the root of the consumer's repo. Rules map 1:1 to controls a compliance auditor would recognize, which is the deliberate design choice that distinguishes this from a generic "AI code reviewer" — every comment ties back to a named control, every action produces an audit artifact.

## 5. Architecture

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

### Component rationale

- **Vertex AI Gemini 2.5 Flash via direct SDK** — meets the hackathon's "Google Cloud AI" requirement. The 15-rule rubric is inlined in the system prompt, so a Vertex Data Store is not load-bearing. The plan → tool call → reflect → act loop lives in plain Python (`app/main.py::_process_mr_event`), making every step visible in Cloud Logging and replayable from the persisted audit log. See `app/agent_runner.py:4-8` for the architectural simplification note.
- **GitLab REST API (8 tools per MR)** — `get_merge_request`, `get_merge_request_diffs`, `get_latest_pipeline_for_sha`, `list_pipeline_jobs`, `list_vulnerability_findings`, `post_merge_request_comment` / `find_agent_note` / `update_merge_request_note` (upsert pattern), `add_merge_request_labels`, `create_issue`. REST avoids the MCP transport variance flagged in §12 risk #1 while still hitting the 8+ tool-call target in §8 "Technological Implementation."
- **Cloud SQL (PostgreSQL 15, db-f1-micro)** — scoring history, trends, audit log. Schema in `db/migrations/`. PostgreSQL chosen for portability; nothing in the schema is GCP-specific. Connection from Cloud Run is via the Cloud SQL Auth Proxy at the unix socket `/cloudsql/<connection-name>`.
- **Cloud Run** — hosts the webhook handler and the leadership UI as one service (`--cpu-throttling` disabled so background-task evaluation continues after the 202 response). Stateless, scales to zero, max 10 instances.
- **Secret Manager (4 secrets)** — `mr-sentinel-gitlab-webhook-secret` (inbound webhook auth), `mr-sentinel-gitlab-token` (outbound API calls), `mr-sentinel-db-app-password` (Cloud SQL app user), `mr-sentinel-db-password` (Cloud SQL root user, ops-only). Mounted as env vars by Cloud Run at start.
- **Artifact Registry** — Docker images at `us-central1-docker.pkg.dev/aicin-477004/mr-sentinel/webhook:<version>`.

## 6. Core user stories

1. **As an MR author**, when I open an MR, within 30 seconds I see a structured comment from MR Sentinel that scores my change against the project's rubric, with inline suggestions and links to the specific rule each comment ties to.
2. **As a reviewer**, I can trust that the rubric was applied consistently — when I see a 9/10 score from the agent, I can focus my human review on judgment calls, not checklist enforcement.
3. **As an engineering leader**, I can open a dashboard and see this week's MR quality trend, which rules trip most often, which teams are drifting, and which MRs were blocked on a compliance gate.
4. **As a compliance auditor**, I can pull the audit log for any MR and see exactly which controls were checked, when, by which agent version, with what outcome.
5. **As a platform engineer**, I can edit a YAML file in my repo to add a rule, change a threshold, or disable a gate, and the next MR uses the updated rubric.

## 7. The rubric (v1)

Fifteen rules, mapped to controls. Each rule is a Vertex retrieval document with: rule_id, control_mapping, severity, evaluator_prompt, example_pass, example_fail, suggested_remediation.

Categories:
- **Contract & spec gates** (5 rules) — derived from CDPD methodology. Does the change have a contract? Are acceptance criteria testable? Does the implementation match the spec? Are integration boundaries explicit? Is there a kill-switch path?
- **Quality gates** (4 rules) — test coverage on changed methods, mutation-test resilience for critical paths, no skipped tests, no commented-out code in the diff.
- **Security gates** (3 rules) — dependency advisory check, secrets-in-diff scan, authentication-path review for public-facing endpoints.
- **Operational gates** (3 rules) — observability hooks for new endpoints, error-budget impact note for SLO-protected services, rollback documented for migrations.

The rubric ships with the repo; users override per project.

## 8. Track mapping — judging criteria

| Criterion | How MR Sentinel scores |
|---|---|
| **Technological Implementation** | Multi-tool agent (8 GitLab REST endpoints per MR), explicit deterministic plan in Python, Gemini reasoning persisted to Cloud SQL as a replayable audit log, full GCP-native stack (Cloud Run, Cloud SQL, Secret Manager, Artifact Registry, Vertex AI), real production patterns (constant-time auth, sha-based dedup, comment upsert). |
| **Design** | Three surfaces — MR comment (structured, scannable), leadership dashboard (Recharts, dark theme), audit log view (filterable). Each designed for a different persona. |
| **Potential Impact** | Every regulated-industry engineering org has this pain. The control-mapping framing is the differentiator that takes this from "AI code reviewer" to "compliance-grade governance." Productizable. |
| **Quality of the Idea** | The rubric-as-product framing is the moat. Most submissions will be "AI reviews PR." MR Sentinel ships *with* a methodology, and the rubric is configurable per project. |

## 9. Build plan — 26 days (May 16 – June 11)

| Window | Milestone | Done when |
|---|---|---|
| **Days 1–3** (May 16–18) | GCP project setup + bootstrap | ✅ **Closed 2026-05-17.** Project `aicin-477004` reused per existing-credentials policy, 12 APIs enabled, 4 secrets in Secret Manager, Artifact Registry created, $100 credit form pending (deadline June 4). |
| **Days 4–8** (May 19–23) | Core loop: webhook → agent → comment | ✅ **Closed 2026-05-17.** Real MR on `gitlab.com/sgharlow/governance-demo-app` triggers a real comment in ~32s via the live Cloud Run service. |
| **Days 9–14** (May 24–29) | Multi-step actions + rubric | ✅ **Closed 2026-05-17.** Agent uses 8 GitLab REST tools per run, applies the v1 rubric (15 rules), sha-dedups, upserts comments, opens linked remediation issues on block verdicts. |
| **Days 15–19** (May 30 – June 3) | Leadership dashboard | Cloud Run UI live with seeded trend data, drill-down to MR audit log |
| **Days 20–23** (June 4–7) | Polish, edge cases, demo data | Demo repo seeded with 8–12 archetypal MRs, every rule has at least one tripping example, README + LICENSE + architecture doc complete |
| **Days 24–26** (June 8–10) | Demo video, final test, submission | 3-min video locked, hosted demo URL stable, repo public with MIT license detectable in About section |
| **June 11** | Submit by 2pm PT with buffer | Submission complete on Devpost before 12pm PT |

## 10. Demo storyboard (3 minutes)

The demo target is a purpose-built public GitLab repo (`gitlab.com/sgharlow/governance-demo-app`) — a fictional regulated-SaaS reference codebase seeded with realistic MRs. No real customer or employer code appears anywhere in the demo.

**Shot 1 (0:00–0:08)** — cold open on an MR header in GitLab. Cursor hovers a small advisory icon. *"This MR looks clean. Watch what happens in the next ninety seconds."*

**Shot 2 (0:08–0:25)** — author on camera. *"I've spent decades building software for regulated industries. The pattern that ends careers isn't malice — it's a tired senior engineer rubber-stamping an MR at 4:50pm on a Friday. MR Sentinel is the agent I wish I'd had."*

**Shot 3 (0:25–0:40)** — scroll the diff. Three files, eighty lines. Two new dependencies. An auth refactor. *"By the time a reviewer has time for this, the author has shipped two more MRs."*

**Shot 4 (0:40–0:55)** — split-screen: Cloud Run service in GCP console on the left, the open MR in GitLab on the right. *"MR Sentinel runs on Vertex AI Gemini behind a Cloud Run webhook. Fifteen rules, every one mapped to a named control — and the rubric is what ships in this repo."* The `rubric/v1.yaml` file slides in as a brief inset.

**Shot 5 (0:55–1:20)** — Cloud Logging stream alongside the agent loop in source. Eight GitLab API calls fire in sequence: get MR, get diffs, get pipeline, list jobs, list vulnerabilities, Gemini evaluate, upsert comment, label MR. Each log line lights green as it lands.

**Shot 6 (1:20–1:50)** — the persisted evaluation JSON from Cloud SQL, surfaced in the leadership UI's audit-log view. *"New endpoint exposes PII. No test covers the unauthenticated path. Cannot pass compliance gate."* The text quotes the actual `summary` field from the Gemini response, with the failing rule_ids highlighted.

**Shot 7 (1:50–2:15)** — back to the MR. Comment streams in with the rubric scores. Label `blocked-compliance` appears. Linked remediation issue auto-creates with a checklist of the failing rules.

**Shot 8 (2:15–2:35)** — leadership dashboard. This week: 142 MRs scanned, 18 blocked, average score 7.8, drift down 23% WoW. Per-team bar chart. Trend line.

**Shot 9 (2:35–2:55)** — author on camera. *"Eight tool calls, one Gemini evaluation, one rubric, one paper trail. The audit becomes the byproduct of doing the work, not a separate exercise. That's the difference."*

**Shot 10 (2:55–3:00)** — end card: repo URL, demo URL, MIT license, sgharlow handle.

## 11. Submission checklist

- [ ] Public GitHub repo with MIT license file detectable in About
- [ ] README with architecture diagram, setup instructions, rubric customization guide
- [ ] Hosted demo URL on Cloud Run, accessible without auth (or with provided judge credentials)
- [ ] 3-minute demo video uploaded to YouTube (unlisted is OK; public preferred)
- [ ] Devpost submission form complete
- [ ] Track selected: GitLab
- [ ] All AI use restricted to Google Cloud AI tools (Gemini, Vertex) and GitLab's built-in AI features
- [ ] No AWS, no Azure, no third-party LLM APIs

## 12. Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| ~~GitLab MCP server has gaps for required endpoints~~ | ~~Medium~~ | ~~High~~ | **Retired 2026-05-17** — chose GitLab REST as the primary transport during Days 4-8. Eight endpoints cover the full loop; matrix preserved in `docs/mcp-endpoint-audit.md` as a future-migration reference. |
| ~~Cloud Run + Agent Builder integration friction~~ | ~~Medium~~ | ~~Medium~~ | **Retired 2026-05-17** — direct Vertex AI SDK avoids Agent Builder entirely. Orchestration is plain Python; every step is visible in Cloud Logging and replayable from the persisted audit log. |
| Solo bandwidth conflict with other Q2 commitments | High | Medium | Treat the leadership dashboard as the cut line — if days 15–19 slip, ship without it; the agent + comment + audit log is the minimum viable demo |
| GCP credit ($100) insufficient | Low | Low | Free tier covers Cloud Run + Cloud SQL development workloads; budget alerts at $50/$75 to avoid surprise charges |
| 3-min video runs long | Medium | Low | Lock the storyboard at day 20; record by day 24; edit aggressively; cut shot 8 dashboard if needed (story still works) |
| Demo repo not believable as a real project | Low | Medium | Use realistic naming, real OSS dependencies, real-looking commit history (~50 commits over 60 days seeded before the demo) |

## 13. What's explicitly out of scope

- IDE integration — this is a server-side agent, not a copilot
- Slack/Teams bot for chat-based review — deliberately rejected to keep "beyond chat" sharp
- Multi-language rubric translation — English only for hackathon
- SOC2-style audit export — mentioned in the pitch as a future direction, not built for submission
- GitHub support — GitLab track only

## 14. Post-hackathon disposition

The repo stays public under sgharlow. The rubric ships as MIT-licensed reusable IP — engineering organizations that want to adopt it can fork, customize, and run their own instance. No plans to commercialize during the hackathon window; that conversation happens after the submission lands and only if there's external interest.

## 15. Authorship and disclosure

This project is built by sgharlow in personal capacity, outside of any employer relationship. All work occurs on personal time, on personal hardware, using personal GCP credentials. No employer code, customer data, or proprietary information appears in the repo, the demo, or the video. The rubric is derived from publicly published methodologies authored by sgharlow (the AI Control Framework and CDPD pattern). The demo target is a purpose-built fictional codebase.
