# MR Sentinel — share copy variants

Ready-to-paste social and outreach text. Voice mirrors the foreign-mind.com book launch tone (per MEMORY: "no hashtags, ≤3 emojis, one link per post, no employer references"). All variants link to the GitHub repo as the canonical entry point — Steve's personal capacity, not any employer.

**Author profile:** sgharlow personal (NOT the business page).
**One link per post.** Default: `github.com/sgharlow/mr-sentinel`.
**Demo video URL:** _[fill in after recording]_

---

## LinkedIn — long form (1 post, ~1500-2000 chars)

```
A common pattern that ends careers in regulated industries isn't malice. It's a tired senior engineer rubber-stamping a merge request at 4:50 on a Friday.

Six months later, the audit finds it. The MR introduced a new public endpoint with no authentication. Or it committed a production env file with a live API key. Or it shipped a database migration with no rollback path. The author has long since moved on. The reviewer doesn't remember reviewing it.

The agent class I wanted to build for this hackathon is the one that's missing from the market: an MR governance agent that applies a written rubric to every merge request with the consistency of a machine and the judgment of a senior reviewer — in seconds, with an audit-grade paper trail.

So I built it. MR Sentinel runs on Google Cloud Run with Vertex AI Gemini, fires on GitLab webhook, evaluates against a 15-rule rubric, posts a structured Markdown comment with the verdict and the failing rules cited by ID, opens a linked remediation issue on blocking failures, and writes everything to a Postgres audit log that's replayable end-to-end.

The differentiator isn't the AI. Most submissions to this hackathon will be "AI reviews PR." MR Sentinel ships with a written methodology — every rule in the rubric maps 1:1 to a named control auditors recognize. SOC 2 CC6.1. ISO 27001 A.14.2.5. OWASP ASVS V1. NIST SA-11. When a comment says the MR is blocked on `auth-on-new-public-endpoints`, that's a control number a compliance team can cite in a finding.

The rubric is the product. It ships in the repo, MIT-licensed. Consumers override per project via a single YAML file. Engineering organizations that adopt the framing can fork it, customize the YAML to match their controls, and run their own instance — no vendor relationship required.

Built in personal capacity for the Google Cloud Rapid Agent Hackathon, GitLab track. Submission deadline June 11.

Code: github.com/sgharlow/mr-sentinel
```

---

## LinkedIn — short form (1 post, ~500-800 chars)

```
The pattern that ends careers in regulated industries isn't malice. It's a tired engineer rubber-stamping an MR at 4:50 on a Friday.

I built an AI governance agent for that exact moment. MR Sentinel runs on Google Cloud Run, fires on GitLab webhook, evaluates against a 15-rule rubric where every rule maps to a named compliance control (SOC 2, ISO 27001, OWASP, NIST). Structured comment in ~30 seconds. Linked remediation issue. Replayable audit log.

The rubric ships open-source. Engineering teams fork it, customize the YAML, run their own instance.

Personal capacity. Google Cloud Rapid Agent Hackathon, GitLab track.

github.com/sgharlow/mr-sentinel
```

---

## Twitter / X — 280-char version

```
The pattern that ends careers in regulated SaaS isn't malice. It's a tired senior engineer rubber-stamping an MR Friday afternoon.

I built MR Sentinel for that exact moment. Vertex AI + Cloud Run + GitLab. Every rule maps to a named compliance control.

github.com/sgharlow/mr-sentinel
```

(266 chars.)

---

## Twitter / X — thread (3 posts)

**Post 1 (250 chars):**
```
The pattern that ends careers in regulated industries isn't malice. It's a tired senior engineer rubber-stamping a merge request at 4:50 on a Friday afternoon.

I built MR Sentinel for that exact moment. 🧵
```

**Post 2 (270 chars):**
```
Runs on Google Cloud Run. Vertex AI Gemini evaluates each MR against 15 rules. Every rule maps 1:1 to a named compliance control — SOC 2, ISO 27001, OWASP, NIST.

Structured comment in ~30s. Linked remediation issue. Postgres audit log that's replayable end-to-end.
```

**Post 3 (250 chars):**
```
The rubric is the product. It ships open-source, MIT-licensed. Engineering teams fork it, customize the YAML, run their own instance.

Built in personal capacity. Google Cloud Rapid Agent Hackathon, GitLab track.

Code: github.com/sgharlow/mr-sentinel
```

---

## Bluesky / Mastodon (300-char native limit)

```
The pattern that ends careers in regulated industries isn't malice. It's a tired senior engineer rubber-stamping an MR Friday afternoon.

I built MR Sentinel for that moment. Vertex AI + Cloud Run + GitLab. Every rule maps to a named compliance control.

github.com/sgharlow/mr-sentinel
```

(293 chars.)

---

## GitHub README sticky-pin (top of `sgharlow` profile)

```
**MR Sentinel** — An AI governance agent for merge requests. Built for the Google Cloud Rapid Agent Hackathon, GitLab track. The rubric is the product: 15 rules, every one mapped to a named compliance control. Live demo + open-source under MIT. → github.com/sgharlow/mr-sentinel
```

---

## "Reply-to-comment" snippets (canned replies for the next 72 hours after the share)

| Trigger | Reply |
|---|---|
| "What's the differentiator from CodeRabbit / Greptile / etc.?" | "Those are AI code reviewers. MR Sentinel is a compliance-grade governance agent — every rule maps to a named control (SOC 2, ISO 27001, OWASP, NIST), and the rubric ships open-source so consumers customize per project. Different product class." |
| "Can it work with GitHub?" | "GitLab track for this hackathon, GitLab REST API for the integration. The webhook handler + Gemini call + rubric apply to any MR/PR source — porting is a single-file change in `gitlab_client.py`. Post-hackathon backlog." |
| "Why not Agent Builder?" | "For 15 rules and 8 deterministic tool calls, the orchestration is the agent. Plain Python in `app/main.py::_process_mr_event`, visible in Cloud Logging, replayable from the audit log. Documented in `agent_runner.py:4-8`." |
| "Open to PRs?" | "After June 11 (submission deadline). Issues welcome anytime — please flag use cases or rule additions you'd like to see." |
| "Pricing model?" | "MIT-licensed open source. No commercial plans during the hackathon. Conversations about a managed offering happen after submission, only if there's external interest." |
| "How accurate is Gemini at this?" | "Tracks the rubric well — see the demo MRs at gitlab.com/sgharlow/governance-demo-app/merge_requests. Each one trips its target rule with cited evidence. Edge cases get a 'skip' outcome with an explanation rather than a false fail." |

---

## Email outreach template (for engineering leaders in personal network)

```
Subject: Built something for the audit-finding problem

Hi [name],

Built this for the Google Cloud Rapid Agent Hackathon and wanted to send it your way before the submission deadline next week.

MR Sentinel is an AI governance agent that watches GitLab merge requests and applies a written rubric to every one — 15 rules, each mapped 1:1 to a named compliance control. The rubric is the product. It ships open-source under MIT so engineering teams fork it, customize the YAML per project, and run their own instance.

Live: github.com/sgharlow/mr-sentinel
Demo MRs: gitlab.com/sgharlow/governance-demo-app/merge_requests
Architecture: a 3-min walkthrough on YouTube — [link after upload]

The differentiator from AI code reviewers (CodeRabbit, Greptile, etc.) is the control-mapping framing. When you ship this in a regulated environment, every blocking comment cites a control number an auditor recognizes, and the full evaluation is persisted to Postgres for the audit trail.

Built in personal capacity, not via any employer relationship.

Would value a 15-minute reaction if you have time before June 11. No pitch, just curious what an actual engineering leader sees that I missed.

Steve
```

---

## Notes on tone (from MEMORY constraints + project context)

- **No employer references.** Never name "Opus Inspection," "Virginia," or use exact report counts (memory: `feedback_no_employer_references`).
- **No hashtags.** Personal-capacity voice, not marketing-channel voice.
- **≤3 emojis per post.** The 🧵 thread marker is OK; otherwise lean on text.
- **One link per post.** Default to the GitHub repo.
- **Steve's PERSONAL LinkedIn profile.** Not the business page.
- **No "we" — use "I."** Built solo.
- **Don't claim "production-ready."** This is a hackathon submission and demo.
- **The "rubric is the product" framing is the load-bearing differentiator.** Every variant returns to it.
