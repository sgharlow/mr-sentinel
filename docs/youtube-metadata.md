# YouTube upload metadata — MR Sentinel demo

Paste-ready metadata for the demo video. Published at **https://youtu.be/0IlB2KJsJ4A**
(runtime 2:49, under the Devpost 3:00 cap). Chapter timestamps are anchored to the
actual slide transitions in the final cut.

---

## Title (published)

```
MR Sentinel — the rubric is the product | Google Cloud Rapid Agent Hackathon demo
```

Alternates (if re-titling):
```
MR Sentinel — AI Compliance Governance for GitLab Merge Requests | Cloud Run + Gemini
```
```
MR Sentinel: an AI agent that applies a compliance rubric to every merge request
```

---

## Description (paste into the YouTube description field)

```
An AI governance agent for GitLab merge requests. When an MR opens, MR Sentinel runs a deterministic plan across eight GitLab REST endpoints, hands the diff to Vertex AI Gemini 2.5 Flash against a 15-rule rubric, and acts: a structured verdict comment with each failing rule cited by ID, a linked remediation issue, and a replayable Postgres audit log.

The differentiator isn't the AI — it's the rubric. Every rule maps 1:1 to a named compliance control: SOC 2, ISO 27001, OWASP ASVS, NIST. When a comment says an MR is blocked, that's a control number a compliance team can cite in a finding. The rubric ships MIT-licensed; teams fork it and override per-project via one YAML file.

Built on Google Cloud, end to end: Cloud Run, Vertex AI (Gemini 2.5 Flash), Cloud SQL (Postgres), Secret Manager, Artifact Registry, Cloud Build.

— Links —
Code (MIT):        https://github.com/sgharlow/mr-sentinel
Live dashboard:    https://mr-sentinel-webhook-n6oitfxdra-uc.a.run.app/dashboard
Sample audit page: https://mr-sentinel-webhook-n6oitfxdra-uc.a.run.app/audit/sgharlow/governance-demo-app/10
Demo GitLab repo:  https://gitlab.com/sgharlow/governance-demo-app

— Chapters —
0:00  Intro — the Friday-afternoon MR
0:31  Inside the diff: hard-coded secrets
0:46  The rubric — 15 rules, named controls
1:01  The agent loop on Cloud Run + Gemini
1:22  The verdict: block, 0/10, controls cited
1:49  Leadership dashboard
2:12  Audit drill-down
2:29  Recap
2:45  Outro

— Stack —
Cloud Run · Vertex AI Gemini 2.5 Flash · Cloud SQL Postgres · Secret Manager · Artifact Registry · Cloud Build · FastAPI · GitLab REST API

Built in personal capacity for the Google Cloud Rapid Agent Hackathon (GitLab track).
```

---

## Tags (paste into the Tags field — 478 chars)

```
mr sentinel, ai code review, merge request review, pull request review, compliance automation, compliance as code, devsecops, code governance, ai agent, ai governance, gitlab, google cloud, vertex ai, gemini, cloud run, cloud sql, secret manager, postgres, fastapi, soc 2, iso 27001, owasp, nist, audit log, hackathon, google cloud rapid agent
```

---

## Upload settings

| Field | Value |
|-------|-------|
| Visibility | **Unlisted** or **Public** (never Private — judges must be able to open it) |
| Category | Science & Technology |
| Language / Captions | English. Captions are burned in; no separate caption file needed |
| Audience | "No, it's not made for kids" |
| License | Standard YouTube License |
| Comments | On |

---

## Pinned comment (optional)

```
The rubric is open-source under MIT — fork it and customize the YAML to your own controls: https://github.com/sgharlow/mr-sentinel
```

---

## Notes

- Description is intentionally hashtag-free to match the personal-brand voice. To use the
  3 above-title hashtags YouTube supports, append `#GoogleCloud #Gemini #DevSecOps`.
- Chapter marks are verified against 7 of 8 detected scene transitions in the final cut;
  the 1:22 mark (verdict) is interpolated from the surrounding exact matches.
