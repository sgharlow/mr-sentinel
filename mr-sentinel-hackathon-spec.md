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

MR Sentinel is a Gemini-powered agent built on Google Cloud Agent Builder that integrates with GitLab via the official MCP server. The agent triggers on MR events, executes a multi-step plan against a configurable rubric, and takes real action against the MR: structured comment, labels, linked follow-up issues, optional merge-block, optional Slack notification. A separate Cloud Run dashboard surfaces aggregate quality signals to leadership.

The rubric is the product's center of gravity. It ships with a v1 derived from the author's published methodologies (the AI Control Framework and the CDPD spec-driven development pattern), and is configurable per project via a YAML file in the repo. Rules map 1:1 to controls a compliance auditor would recognize, which is the deliberate design choice that distinguishes this from a generic "AI code reviewer" — every comment ties back to a named control, every action produces an audit artifact.

## 5. Architecture

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

### Component rationale

- **Gemini 3 + Agent Builder** — required by hackathon. Agent Builder is the orchestration surface; Gemini is the reasoning engine. Plan → tool call → reflect → act loop visible in the trace pane.
- **GitLab MCP server** — the partner integration; structurally load-bearing. Tools used: `get_merge_request`, `get_merge_request_diff`, `list_pipeline_jobs`, `list_dependabot_alerts` (or equivalent security advisory tool), `post_merge_request_comment`, `add_merge_request_labels`, `create_issue`, `list_project_members`.
- **Vertex AI Data Store** — stores the rubric as searchable retrieval ground. Each rule indexed with control mapping, example pass/fail diffs, suggested remediation.
- **Cloud SQL (PostgreSQL)** — scoring history, trends, audit log. PostgreSQL chosen for portability; nothing in the schema is GCP-specific.
- **Cloud Run** — hosts the webhook handler and the leadership UI. Stateless, scales to zero.
- **Secret Manager** — GitLab tokens, Slack webhooks. No secrets in code or env files.

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
| **Technological Implementation** | Heavy multi-tool agent (8+ GitLab MCP endpoints), explicit multi-step planning, Gemini reasoning surfaced in trace, full GCP-native stack, real production patterns (Secret Manager, Cloud SQL, IAM). |
| **Design** | Three surfaces — MR comment (structured, scannable), leadership dashboard (Recharts, dark theme), audit log view (filterable). Each designed for a different persona. |
| **Potential Impact** | Every regulated-industry engineering org has this pain. The control-mapping framing is the differentiator that takes this from "AI code reviewer" to "compliance-grade governance." Productizable. |
| **Quality of the Idea** | The rubric-as-product framing is the moat. Most submissions will be "AI reviews PR." MR Sentinel ships *with* a methodology, and the rubric is configurable per project. |

## 9. Build plan — 26 days (May 16 – June 11)

| Window | Milestone | Done when |
|---|---|---|
| **Days 1–3** (May 16–18) | GCP credit + project setup | Cloud project created, $100 credit requested (form deadline June 4), Agent Builder enabled, sample MCP call against personal GitLab succeeds end-to-end |
| **Days 4–8** (May 19–23) | Core loop: webhook → agent → comment | A real MR opened on the demo repo triggers a real comment from the agent within 30 seconds |
| **Days 9–14** (May 24–29) | Multi-step actions + rubric | Agent uses 6+ MCP tools per run, applies the v1 rubric, creates linked issues, posts to Slack |
| **Days 15–19** (May 30 – June 3) | Leadership dashboard | Cloud Run UI live with seeded trend data, drill-down to MR audit log |
| **Days 20–23** (June 4–7) | Polish, edge cases, demo data | Demo repo seeded with 8–12 archetypal MRs, every rule has at least one tripping example, README + LICENSE + architecture doc complete |
| **Days 24–26** (June 8–10) | Demo video, final test, submission | 3-min video locked, hosted demo URL stable, repo public with MIT license detectable in About section |
| **June 11** | Submit by 2pm PT with buffer | Submission complete on Devpost before 12pm PT |

## 10. Demo storyboard (3 minutes)

The demo target is a purpose-built public GitLab repo (`gitlab.com/sgharlow/governance-demo-app`) — a fictional regulated-SaaS reference codebase seeded with realistic MRs. No real customer or employer code appears anywhere in the demo.

**Shot 1 (0:00–0:08)** — cold open on an MR header in GitLab. Cursor hovers a small advisory icon. *"This MR looks clean. Watch what happens in the next ninety seconds."*

**Shot 2 (0:08–0:25)** — author on camera. *"I've spent decades building software for regulated industries. The pattern that ends careers isn't malice — it's a tired senior engineer rubber-stamping an MR at 4:50pm on a Friday. MR Sentinel is the agent I wish I'd had."*

**Shot 3 (0:25–0:40)** — scroll the diff. Three files, eighty lines. Two new dependencies. An auth refactor. *"By the time a reviewer has time for this, the author has shipped two more MRs."*

**Shot 4 (0:40–0:55)** — Agent Builder canvas in GCP console. Tool registry visible: GitLab MCP, Vertex retrieval, Slack. *"MR Sentinel runs on Gemini in Agent Builder. The rubric lives in a Vertex data store — fifteen rules, every one mapped to a named control."*

**Shot 5 (0:55–1:20)** — Gemini's plan streams in. Five steps light up green as MCP tools fire below in sequence.

**Shot 6 (1:20–1:50)** — trace view, sanitized chain-of-thought. *"New endpoint exposes PII. No test covers the unauthenticated path. Dependency advisory finds CVE-XXXX in transitive dep. Cannot pass compliance gate."*

**Shot 7 (1:50–2:15)** — back to the MR. Comment streams in with the rubric scores. Label `blocked-compliance` appears. Linked remediation issue auto-creates. Slack notification fires in a side panel.

**Shot 8 (2:15–2:35)** — leadership dashboard. This week: 142 MRs scanned, 18 blocked, average score 7.8, drift down 23% WoW. Per-team bar chart. Trend line.

**Shot 9 (2:35–2:55)** — author on camera. *"Twelve tool calls, one rubric, one paper trail. The audit becomes the byproduct of doing the work, not a separate exercise. That's the difference."*

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
| GitLab MCP server has gaps for required endpoints | Medium | High | Days 1–3 validate every endpoint needed before committing to the full feature set; degrade gracefully to REST API for any endpoint MCP doesn't cover |
| Cloud Run + Agent Builder integration friction | Medium | Medium | Start with the GoogleCloudPlatform/agent-starter-pack template; resist building from scratch |
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
