# MR Sentinel — winning-video profile & criteria map (2026-06-09)

This is the ultrathink analysis behind the re-cut teleprompter. It answers one question:
**what does a winning submission look like for THIS hackathon, and how does our 2:50 video
hit every judging axis on purpose?** Read this before recording so every shot earns its seconds.

---

## 1. The judging criteria (quoted verbatim from the rules)

Source: `https://rapid-agent.devpost.com/rules` (Stage Two judging). **All four criteria are
equal-weighted** — there is no "Technological Implementation counts double." That changes
strategy: you cannot win on stack depth alone; Design, Impact, and Idea each carry 25%.

> 1. **Technological Implementation** — "Does the interaction with Google Cloud and Partner
>    services demonstrate quality software development?"
> 2. **Design** — "Is the user experience and design of the project well thought out?"
> 3. **Potential Impact** — "How big of an impact could the project have on the target
>    communities?"
> 4. **Quality of the Idea** — "How creative and unique is the project?"

**Prize structure (our track = GitLab):** 1st $5,000, 2nd $3,000, 3rd $2,000. Six partner
buckets (Arize, Elastic, Fivetran, **GitLab**, MongoDB, Dynatrace), $60K total. We compete
only against other GitLab-track entries — so the bar is "best agent that meaningfully uses
GitLab's MCP server," not "best agent overall."

**Required tech (eligibility gate, from the rules):**
- Functional agent powered by **Gemini** on **Google Cloud Agent Builder**.
- **Integrates a Partner Entity's MCP server** ("integrates a Partner Entity's MCP server").
- "All other artificial intelligence tools are not permitted" — inference must be Google only.
- Public open-source repo with a detectable license; project newly created in the contest period.

**Video requirements (from the rules):**
- "Should include footage that shows the Project functioning on the platform(s)."
- "It should not be longer than 3 minutes."
- "must be uploaded to and made publicly visible on YouTube or Vimeo."
- "must be in English or include English subtitles."

> ⚠️ **Gemini-version watch-out.** The Devpost *overview* page currently phrases the model
> requirement as "powered by **Gemini 3**," while the *rules* page says "Gemini models on
> Agent Platform" / "powered by Gemini and Google Cloud Agent Builder." Our agent runs
> **Gemini 2.5 Flash** on Vertex AI. The rules text (the legally controlling document) says
> "Gemini models," which 2.5 Flash satisfies. **Action: do not put a Gemini version number
> in the video narration** — say "Gemini, on Vertex AI." Keep the exact model id (2.5 Flash)
> in the repo/Devpost text where it's accurate and defensible, but don't hand a judge a
> "they said 2.5, the banner said 3" mismatch in the 30-second architecture beat. (Flagged
> again in the risks section of the final report.)

---

## 2. The winning project profile for THIS hackathon

Synthesizing the equal-weighted criteria + the "deliberate architecture choice" lens, the
GitLab-track winner is almost certainly the entry that:

1. **Makes the partner MCP server load-bearing, visibly, at runtime** — not a checkbox.
   The hackathon is *literally about* agents reaching into a partner's platform through MCP.
   The judges (GitLab + Google engineers) will look for the MCP read tools actually firing.
   A submission where MCP is bolted on but the real work happens elsewhere reads as
   box-ticking and loses Technological Implementation.
2. **"Accomplishes a task," not "chats"** — the org copy says move "beyond chatbot
   functionality to accomplish tasks" and handle "complex goals through multi-step planning."
   Our agent doesn't answer questions; it *acts*: posts a verdict, labels the MR, opens a
   remediation issue. That's a task with a side effect in the partner's system. Strong fit.
3. **Has a non-obvious, defensible idea** (Quality of the Idea). "AI reviews a PR" is the
   crowded, predictable entry. Our wedge: **the rubric is the product** — every rule maps 1:1
   to a *named compliance control* (SOC 2 / ISO 27001 / OWASP-ASVS / NIST). That reframes the
   project from "code reviewer" to "compliance-grade governance with an audit trail." It is
   the thing a judge has not seen ten times already.
4. **Shows real UX, not slides** (Design). Three server-rendered surfaces for three personas
   (author comment, leadership dashboard, auditor drill-down). We must SHOW them running with
   live data, clicking through, not narrate over a static architecture diagram.
5. **Names a real, fundable pain** (Potential Impact). Regulated-industry engineering orgs
   ship a secret in a diff, a human rubber-stamps it Friday afternoon, an auditor finds it six
   months later. Every CTO in fintech/health/regulated-SaaS recognizes this. That's the
   "who uses it / why pay / scale" close.

### Why ADK + GitLab MCP + Gemini-on-Vertex was the *right* call (the deliberate-choice beat)

This is the analog of "why this database." The judges are domain experts; they reward a tech
choice that is intentional. State the reasoning, not the checkbox:

- **GitLab MCP server (reads):** MCP gives a **portable, governed tool surface**. The same
  agent can point at gitlab.com or a self-hosted GitLab without re-coding the integration —
  the tool contract (`get_merge_request`, `get_merge_request_diffs`,
  `list_merge_request_pipelines`) is the same. For a governance product that has to run across
  customer GitLab tiers, a stable MCP tool surface is the integration you *want* to standardize
  on. This is the hackathon's whole thesis, and it's genuinely the right primitive here.
- **Google ADK / Agent Builder (the loop):** governance needs a **multi-turn tool-calling
  loop** (gather context across several reads, then reason), and a **structured** result the
  three UIs and Cloud SQL can consume. ADK gives both: `LlmAgent` + `Runner` drive the
  tool-calling turns, and a final `record_verdict` function-tool yields a typed `Evaluation`.
  We didn't hand-roll an agent loop; we used the platform's.
- **Gemini 2.5 Flash on Vertex AI (the judgment):** the reasoning that maps a diff to fifteen
  rubric rules at once needs a capable model, and keeping inference **inside Google Cloud on
  Vertex** is both a rules requirement ("no other AI tools") and a compliance posture (no diff
  leaves Google Cloud). Flash keeps the per-MR latency and cost low enough to run on every MR.
- **The honest hybrid (MCP reads + REST write-backs):** the official GitLab **Duo** MCP server
  is Premium/Ultimate-only, OAuth-DCR-only, and exposes **no tool to post an MR note or set a
  label** — so it physically cannot carry the write path on a free-tier project. We use a
  community GitLab MCP server (`@zereight/mcp-gitlab`) for the reads and keep the
  formatting-sensitive writes on GitLab REST so the comment is byte-stable and the demo is
  reproducible. **Say this out loud in the video** (one sentence). Volunteering the seam reads
  as senior engineering judgment; hiding it and getting caught reads as box-ticking. It is a
  net *positive* with expert judges.

### The one-line thesis to land

> "One ADK agent. Gemini for the judgment. GitLab's MCP server for reach. One rubric where
> every rule is a named compliance control — and the audit log is the byproduct."

---

## 3. The 20 / 90 / 30 / 20 arc, mapped to the criteria

The sister-hackathon craft guidance: ~20s problem → ~90s app actually running → ~30s the
deliberate architectural choice → ~20s "so what." Our 2:50 budget maps cleanly:

| Beat | Time | What's on screen | Primary criterion it serves |
|---|---|---|---|
| **Problem** | 0:00–0:24 | Hero MR `!10`, `.env.production` with live-looking secrets; the tired-reviewer story | **Potential Impact** (names the pain a real org pays to avoid) + hook |
| **App in action** | 0:24–1:52 | The three required techs FIRING (agent-loop/MCP-trace pane) → the verdict comment lands on `!10` → dashboard → audit drill-down | **Technological Implementation** (MCP+ADK+Gemini visibly run) + **Design** (three real surfaces, live data) |
| **Deliberate choice** | 1:52–2:32 | Architecture: why MCP reads + ADK loop + Gemini-on-Vertex, and the honest hybrid | **Technological Implementation** + **Quality of the Idea** (rubric-as-product moat) |
| **So what** | 2:32–2:50 | Who uses it, why it scales, MIT rubric ships open-source | **Potential Impact** + **Quality of the Idea** |

> Note the deliberate sequencing change vs. the old cut: in the rework the **architecture/
> deliberate-choice beat moves LATER** (after the judge has already SEEN it work), per the
> craft guidance — show it running first, *then* explain why the build is smart. The old cut
> front-loaded the architecture at 0:42 before the payoff landed.

### Where the three required techs must be SEEN (eligibility-critical)

Eligibility hinges on the judge *seeing* Gemini + ADK + the GitLab MCP server run at runtime.
This MUST happen inside the 90s "app in action" beat, concretely:

- **The agent-loop / MCP-trace pane (≈1:00–1:24).** This is the load-bearing shot. On screen,
  a terminal/log pane (the `demo-capture.sh fire 9` output, or a Cloud Logging tail) shows, in
  order: the **GitLab MCP read-tool calls** (`get_merge_request`, `get_merge_request_diffs`,
  `list_merge_request_pipelines`) → the **Gemini evaluation** line (`evaluation: score=…`) →
  the **`record_verdict`** structured emit → the posted comment. If those MCP tool lines are
  not visibly in the captured trace, the eligibility proof is weak — **re-fire until they
  appear, or add one INFO log per MCP tool call before recording** (runbook §4 / §4a).
- **Reinforced in the architecture beat (≈1:52–2:32)** by naming each tech to its role, but
  the *proof* is the trace pane, not the narration.

**Pre-record gate:** the runbook's §4 MCP-trace check and §6 hero-MR regression check both pass
*before* the camera rolls. If `!10` has drifted off block/0.0/`no-secrets-in-diff`, fix that
first — a video that contradicts the live audit page is worse than no re-record.

---

## 4. Per-criterion scorecard (how the cut earns each 25%)

- **Technological Implementation (25%).** Agent-loop trace shows all three required techs at
  runtime; architecture beat explains the portable MCP tool surface + ADK structured output +
  Vertex-only inference; the honest hybrid is volunteered. Production patterns mentioned:
  constant-time webhook auth, sha-based dedup, replayable audit log.
- **Design (25%).** Three personas, three real server-rendered surfaces, shown live with real
  counts (13 MRs scored, distribution, top-5 failing rules), dark-theme consistency,
  cursor-led drill-down from dashboard → audit. No slideware.
- **Potential Impact (25%).** Cold-open names the exact regulated-industry pain; close names
  who adopts it (any compliance-bound eng org), why it scales (Cloud Run scale-to-zero,
  MIT rubric forkable per-project), and the audit-as-byproduct value to a year-end auditor.
- **Quality of the Idea (25%).** The rubric-as-product / control-mapping framing is the moat
  and is repeated as the spine of the narration ("the rubric is the product"). Differentiates
  from the predictable "AI reviews a PR" field.

---

## 5. What to cut if timing slips

Budget is tight at 2:50. If over 3:00, cut in this order (protect the trace beat and the
verdict climax at all costs):
1. Trim the second sentence of the dashboard beat (2:10–2:32) — the visual carries it.
2. Trim one clause from the audit drill-down.
3. NEVER cut: the agent-loop/MCP-trace pane, the `!10` verdict landing, or the one-sentence
   honest-hybrid disclosure.
