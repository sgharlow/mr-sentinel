# YouTube upload metadata — MR Sentinel demo

Paste-ready metadata for the **new 2:46 cut** (`docs/demo/demo-final.mp4`): ADK + GitLab MCP loop,
intro/outro cards, voiceover. **Upload PUBLIC** (the rules require "publicly visible on YouTube
or Vimeo"). Chapter timestamps below match the final 166-second cut.

> Only Google (Gemini, ADK/Agent Builder, Vertex, Cloud Run…) and GitLab (MCP) tech is named —
> keep it that way (no other AI tools in the title/description/tags).

---

## Title (≤100 chars — paste one)

```
MR Sentinel — a Google ADK agent that governs GitLab MRs through GitLab's MCP server
```

Alternates:
```
MR Sentinel — Gemini + Google ADK + GitLab MCP: compliance governance for every merge request
```
```
MR Sentinel — the rubric is the product | Google Cloud Rapid Agent Hackathon (GitLab track)
```

---

## Description (paste into the YouTube description field)

```
An AI governance agent that doesn't chat — it acts. When a GitLab merge request opens, a Google Agent Development Kit (ADK) agent reaches into GitLab through GitLab's MCP server to read the MR, its diff, and its pipeline, hands them to Gemini on Vertex AI, judges them against a 15-rule rubric, and takes action: a structured verdict comment with each failing rule cited by ID, a blocked-compliance label, an auto-opened remediation issue, and a replayable Postgres audit log.

The differentiator isn't the AI — it's the rubric. Every rule maps 1:1 to a named compliance control: SOC 2, ISO 27001, OWASP ASVS, NIST. When a comment says an MR is blocked, that's a control number a compliance team can cite in a finding. The rubric ships MIT-licensed; teams fork it and override per-project via one YAML file.

Built on Google Cloud, end to end: a Google Agent Development Kit agent, Vertex AI (Gemini 2.5 Flash), GitLab's MCP server for the agent's reads, Cloud Run, Cloud SQL (Postgres), Secret Manager, Artifact Registry, Cloud Build. Write-backs (comment, labels, issue) use the GitLab REST API.

— Links —
Code (MIT):        https://github.com/sgharlow/mr-sentinel
Live dashboard:    https://mr-sentinel-webhook-n6oitfxdra-uc.a.run.app/dashboard
Sample audit page: https://mr-sentinel-webhook-n6oitfxdra-uc.a.run.app/audit/sgharlow/governance-demo-app/10
Demo GitLab repo:  https://gitlab.com/sgharlow/governance-demo-app

— Chapters —
0:00  The problem: a secret in the Friday-afternoon merge request
0:29  The agent runs: GitLab MCP read tools + Gemini on Vertex
1:06  The verdict: block, near-zero, every control cited
1:33  Leadership dashboard + the audit log
1:56  Why ADK + GitLab MCP + Vertex (and who uses it)

— Stack —
Google ADK (Agent Builder) · Vertex AI Gemini 2.5 Flash · GitLab MCP server (@zereight/mcp-gitlab) · Cloud Run · Cloud SQL Postgres · Secret Manager · Artifact Registry · Cloud Build · FastAPI · GitLab REST API (write-backs)

Built in personal capacity for the Google Cloud Rapid Agent Hackathon (GitLab track).
```

---

## Tags (paste into the Tags field)

```
mr sentinel, ai code review, merge request review, pull request review, compliance automation, compliance as code, devsecops, code governance, ai agent, ai governance, google adk, agent development kit, agent builder, model context protocol, mcp, gitlab, google cloud, vertex ai, gemini, cloud run, cloud sql, secret manager, postgres, fastapi, soc 2, iso 27001, owasp, nist, audit log, hackathon, google cloud rapid agent
```

---

## Upload settings

| Field | Value |
|-------|-------|
| Visibility | **Public** (the rules require "publicly visible" — not Unlisted, never Private) |
| Category | Science & Technology |
| Language | English (the video has an English voiceover) |
| Captions | Optional — the video has English audio. To add a sidecar `.srt`, re-time `docs/demo/captions.srt` to the 2:46 cut first, then upload via Subtitles ▸ Upload. None are burned in. |
| Audience | "No, it's not made for kids" |
| License | Standard YouTube License |
| Comments | On |

---

## Pinned comment (optional)

```
The rubric is open-source under MIT — fork it and customize the YAML to your own controls: https://github.com/sgharlow/mr-sentinel
```

---

## After upload
Put the new URL into: the **Devpost submission form**, `README.md` (top banner), and
`docs/devpost-submission.md` (Links table). Optional above-title hashtags: `#GoogleCloud #Gemini #DevSecOps`.
