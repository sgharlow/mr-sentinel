# YouTube upload metadata — MR Sentinel demo

Paste-ready metadata for the demo video. ⚠️ **RE-RECORD PENDING** — the published cut at
**https://youtu.be/0IlB2KJsJ4A** (2:49) describes the pre-ADK architecture. The copy below is
updated for the ADK + GitLab MCP loop; re-upload after recording from
`docs/recording-teleprompter.md`. Chapter timestamps are approximate until the new cut exists.

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
An AI governance agent for GitLab merge requests. When an MR opens, a Google ADK agent — Gemini 2.5 Flash as its model — reads the MR, its diff, and its pipeline through GitLab's MCP server, judges them against a 15-rule rubric, and acts: a structured verdict comment with each failing rule cited by ID, a linked remediation issue, and a replayable Postgres audit log.

The differentiator isn't the AI — it's the rubric. Every rule maps 1:1 to a named compliance control: SOC 2, ISO 27001, OWASP ASVS, NIST. When a comment says an MR is blocked, that's a control number a compliance team can cite in a finding. The rubric ships MIT-licensed; teams fork it and override per-project via one YAML file.

Built on Google Cloud, end to end: a Google Agent Development Kit agent, Vertex AI (Gemini 2.5 Flash), GitLab's MCP server for the agent's reads, Cloud Run, Cloud SQL (Postgres), Secret Manager, Artifact Registry, Cloud Build.

— Links —
Code (MIT):        https://github.com/sgharlow/mr-sentinel
Live dashboard:    https://mr-sentinel-webhook-n6oitfxdra-uc.a.run.app/dashboard
Sample audit page: https://mr-sentinel-webhook-n6oitfxdra-uc.a.run.app/audit/sgharlow/governance-demo-app/10
Demo GitLab repo:  https://gitlab.com/sgharlow/governance-demo-app

— Chapters —
0:00  Intro — the Friday-afternoon MR
0:24  Inside the diff: hard-coded secrets
0:42  The agent: Google ADK + Gemini + GitLab's MCP server
1:00  The agent loop — MCP tool calls -> Gemini verdict
1:24  The verdict: block, 0/10, controls cited
1:52  Leadership dashboard
2:20  Audit drill-down
2:38  Recap + stack
(timestamps approximate — re-align to the new cut)

— Stack —
Google ADK (Agent Builder) · Vertex AI Gemini 2.5 Flash · GitLab MCP server (@zereight/mcp-gitlab) · Cloud Run · Cloud SQL Postgres · Secret Manager · Artifact Registry · Cloud Build · FastAPI · GitLab REST API (write-backs)

Built in personal capacity for the Google Cloud Rapid Agent Hackathon (GitLab track).
```

---

## Tags (paste into the Tags field — 478 chars)

```
mr sentinel, ai code review, merge request review, pull request review, compliance automation, compliance as code, devsecops, code governance, ai agent, ai governance, google adk, agent development kit, agent builder, model context protocol, mcp, gitlab, google cloud, vertex ai, gemini, cloud run, cloud sql, secret manager, postgres, fastapi, soc 2, iso 27001, owasp, nist, audit log, hackathon, google cloud rapid agent
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
