# MR Sentinel — recording master (script → capture → audio)

**The single turnkey doc for the re-record.** Three phases, in order:
1. **THE SCRIPT** — beat-by-beat SCREEN / DO / SAY, the 20·90·30·20 arc (below).
2. **CAPTURE** — record the silent screen sequences (phase 2).
3. **AUDIO** — record the voiceover against this teleprompter, then sync (phase 3).

Analysis behind every choice: `docs/video-winning-profile-2026-06-09.md`.

---

## North star — what makes THIS video win

Four judging axes, **equal weight (25% each)**: Technological Implementation · Design · Potential Impact · Quality of the Idea. We're in the **GitLab track** — judged against other GitLab-MCP agents, by Google Cloud + GitLab engineers. So the video must, in under 3:00:

- **Make the GitLab MCP server LOAD-BEARING and VISIBLE at runtime** — the one shot the whole eligibility leans on (Shot D). Judges want to *see* the partner's MCP server actually used, not named.
- **Show it ACCOMPLISH A TASK, not chat** — it posts a verdict, labels the MR, opens a remediation issue. Real side effects in GitLab.
- **Lead with the moat idea** — *the rubric is the product*: every rule maps 1:1 to a named compliance control. That reframes "AI reviews a PR" (crowded) into "compliance-grade governance with an audit trail" (novel = Quality of the Idea).
- **Show real UX, live data — never slides** (Design): three surfaces, three personas.
- **Name a fundable pain** (Impact): a tired reviewer rubber-stamps a secret on a Friday; an auditor finds it six months later.

**Three upgrades vs the prior cut** (the reasons this version scores higher):
1. **Timing rebalanced to the real arc.** The prior cut starved the "deliberate architecture choice" beat (~12s, impossible word count). Expert judges reward an *intentional* tech choice — the analog of "why this database." It now gets **~30s** (Shot H) to actually make the case.
2. **The MCP-trace shot is the spine of the 90s "app in action,"** narrated to the lines that are *actually on screen* (`ADK evaluate … via GitLab MCP`, `Starting GitLab MCP Server`) — honest, not claims.
3. **Hero MR `!10` stays pristine** (block / 0.0, untouched). The live agent loop is captured on a *working* MR (`!9`) and framed as the mechanism; `!10` is the showcase verdict. Two real MRs by one agent = breadth, not a seam.

---

## Layout (one 1920×1080 canvas)
**Browser**, dark mode, bookmarks bar hidden. Tabs, left→right:
1. **GitLab MR `!10`** — `https://gitlab.com/sgharlow/governance-demo-app/-/merge_requests/10`
2. **Dashboard** — `https://mr-sentinel-webhook-n6oitfxdra-uc.a.run.app/dashboard`
3. **Audit** — `https://mr-sentinel-webhook-n6oitfxdra-uc.a.run.app/audit/sgharlow/governance-demo-app/10`
4. **Rubric** — `https://github.com/sgharlow/mr-sentinel/blob/main/rubric/v1.yaml`

**Terminal** (dark, large font ≥16pt) for the Shot D MCP trace.

## Pre-flight — BEFORE you record
- **P1.** `curl -s …/health` → `{"status":"ok"}`; dashboard + audit `!10` (block / 0.0) render. *(Verified live 2026-06-10 on rev `00016-45d`.)*
- **P2.** Stage the trace (WSL): `bash scripts/demo-capture.sh fire 9` → wait ~40s → then print the trace into the terminal:
  ```bash
  gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="mr-sentinel-webhook" AND timestamp>="'$(date -u -d '4 minutes ago' +%Y-%m-%dT%H:%M:%SZ)'"' \
    --project=aicin-477004 --format='value(timestamp,textPayload)' --order=asc --limit=120 \
    | grep -Ei 'ADK evaluate|via GitLab MCP|Starting GitLab MCP|MCPToolset|evaluation: score|tool='
  ```
  You want, on screen: `ADK evaluate sgharlow/governance-demo-app!9 via GitLab MCP` → `Starting GitLab MCP Server with stdio transport` → `… MCPToolset` → `evaluation: score=… verdict=block rules=15 mr_iid=9`. **Leave it on screen — it IS the Shot D visual.** (Optional booster — ask Claude to add per-MCP-tool INFO logging so each `get_merge_request_diffs` call prints; not required, the lines above already prove MCP runs.)
- **P3.** Note the **measured loop latency** (~25–30s observed) — you say it in Shot D.
- **P4.** Hard-refresh all four tabs. **Do NOT say a Gemini version number** — say "Gemini, on Vertex AI" (banner says "3", we run 2.5 Flash; rules say "Gemini models").

---

## THE SCRIPT — 20·90·30·20 (~2:40)

Legend: **[SCREEN]** what's visible · **[DO]** the action · **[SAY]** narration · **[CAPTURE]** how to record it.

### ── PROBLEM · 0:00–0:20 ──

**Shot A · 0:00–0:09 · Cold open**
- **[SCREEN]** MR `!10`, Changes tab, `.env.production` diff visible.
- **[SAY]** "Friday, four-fifty PM. A merge request lands — 'add the production env file.' The reviewer's tired, with eight more in the queue."
- **[CAPTURE]** Screen-record the MR `!10` Changes tab, diff already expanded.

**Shot B · 0:09–0:20 · The stakes**
- **[DO]** Cursor down the diff, pause on the `AWS_ACCESS_KEY_ID` line.
- **[SAY]** "Inside this diff: a database password, a JWT secret, a live Stripe key, an AWS access key — everything policy says must never hit the repo. This is how secrets ship. MR Sentinel is the reviewer that never gets tired."

### ── APP IN ACTION · 0:20–1:50 ──

**Shot C · 0:20–0:30 · Hand off to the agent**
- **[SCREEN]** Hold on the `!10` diff a beat, begin moving toward the terminal.
- **[SAY]** "The moment an MR opens, MR Sentinel — a Google Agent Development Kit agent on Cloud Run — wakes up. Watch it actually run."

**Shot D · 0:30–1:02 · The agent loop — GitLab MCP trace ⭐ (load-bearing)**
- **[DO]** Cut to the **terminal** trace. Cursor-highlight, in order: `via GitLab MCP` → `Starting GitLab MCP Server` → `evaluation: score=`.
- **[SAY]** "Read the log. 'ADK evaluate, via GitLab MCP' — it spins up **GitLab's own MCP server** and pulls the merge request, its diff, and its pipeline *through* it. It hands all that to **Gemini, on Vertex AI**, which judges the diff against fifteen rules at once and emits a structured verdict by calling record-verdict. Every step logged and replayable — the whole loop runs in about [LATENCY ~30] seconds."
- **[CAPTURE]** Record the terminal with the staged trace; slow cursor pass over the MCP lines.
- ⚠️ If the trace lacks `Starting GitLab MCP Server` / `via GitLab MCP`, re-fire (P2) before recording — this is the eligibility proof.

**Shot E · 1:02–1:28 · The verdict lands**
- **[DO]** Cut to **MR `!10`** → the MR Sentinel comment. Cursor: verdict badge → the cited evidence line → linked remediation issue → `blocked-compliance` label in the sidebar.
- **[SAY]** "And here's what it leaves on the merge request that started this. Verdict: block. Score: zero out of ten. It cites no-secrets-in-diff by rule ID — mapped to SOC 2, ISO 27001, OWASP — quotes the exact lines, opens a remediation issue with a checklist, and labels it blocked-compliance so the merge button is one step further away. Every action ties back to a named control."

**Shot F · 1:28–1:42 · Leadership dashboard**
- **[DO]** Cut to **Dashboard**, full screen; cursor down the verdict distribution + top failing rules.
- **[SAY]** "That's one MR. Here's the portfolio — the last thirty days, every MR scored, most blocked on compliance, the top failing rules, each one a control mapped to an audit framework."

**Shot G · 1:42–1:50 · Audit drill-down**
- **[DO]** Cut to **Audit** (`/audit/.../10`); hover the rule outcomes + control_mapping column + timeline.
- **[SAY]** "Click any one and you're in the audit log — every outcome, every control mapping, the timeline. At year-end, that's just… there."

### ── DELIBERATE ARCHITECTURE CHOICE · 1:50–2:20 ──

**Shot H · 1:50–2:20 · Why this build** *(the beat expert judges score)*
- **[DO]** Cut to the **Rubric** tab; scroll to the `no-secrets-in-diff` rule so its `control_mapping` array is on screen.
- **[SAY]** "Three deliberate choices. **GitLab's MCP server** for the reads — because it's a portable tool surface: the same agent points at gitlab.com or a self-hosted instance with no rewiring. **ADK**, because governance needs a real tool-calling loop and a *structured* verdict, not a chat reply. And **Gemini on Vertex**, so no diff ever leaves Google Cloud. One honest seam: the reads run through MCP, the write-backs use GitLab's REST API — because the official Duo MCP server can't post a comment yet. I built that hybrid on purpose, and documented exactly why."

### ── SO WHAT · 2:20–2:40 ──

**Shot I · 2:20–2:40 · Close**
- **[SCREEN]** Stay on the rubric (control_mapping visible) → cut to end card in edit.
- **[SAY]** "Every regulated engineering org has this exact pain — and most ship the secret anyway. One ADK agent, Gemini for the judgment, GitLab's MCP server for reach, and one rubric where every rule is a named compliance control. It ships MIT — fork it, drop a YAML, run your own. The audit trail is just the byproduct. MR Sentinel."

**Stop recording.**

### Word budget (~150 wpm)
| Shot | Beat | Sec | ~Words |
|---|---|---|---|
| A+B | problem | 20 | 50 |
| C | app·handoff | 10 | 26 |
| D | app·MCP trace | 32 | 78 |
| E | app·verdict | 26 | 70 |
| F | app·dashboard | 14 | 38 |
| G | app·audit | 8 | 24 |
| H | architecture | 30 | 74 |
| I | so-what | 20 | 52 |
| **Total** | | **~160 (2:40)** | **~412** |

If long, trim Shot H's "or a self-hosted instance" clause and Shot E's label sentence. **Never cut Shot D or the `!10` verdict.** Hard cap 3:00.

---

## PHASE 2 — CAPTURE (record the screen, silent)

Record **silent** screen clips first; narrate separately in Phase 3 (far more forgiving than a live one-take). Tool: **OBS Studio** (free), 1920×1080, 60fps, capture the browser/terminal window, dark theme.

Capture these clips (order doesn't matter; each a few seconds longer than its shot for trim slack):
1. **Terminal trace** (Shot D) — stage per pre-flight P2, then record a slow cursor pass over the MCP lines. *Capture this FIRST while the trace is fresh.*
2. **MR `!10`** (Shots A, B, E) — the `.env.production` diff (expanded, cursor on the AWS key), then scroll to the MR Sentinel verdict comment (badge → evidence → linked issue → label).
3. **Dashboard** (Shot F) — full-screen, slow scroll over verdict distribution + top failing rules.
4. **Audit `!10`** (Shot G) — hover rule outcomes + control_mapping + timeline.
5. **Rubric** (Shot H) — scroll to `no-secrets-in-diff`, control_mapping array on screen.

Also re-grab the **5 gallery screenshots** from these same tabs (`docs/screenshots/CAPTURE-GUIDE.md`) — **especially `05-agent-loop`, which must now show the GitLab MCP trace**, not the old REST `tool=` ×8 loop.

---

## PHASE 3 — AUDIO (voiceover against this teleprompter)

Record the narration separately, reading the **[SAY]** lines top to bottom. Two clean options:
- **Your voice:** a decent mic + Audacity/your DAW. Quiet room, ~15 cm off-axis, record a 10s room-tone pad. Read each shot's line; leave a beat between shots.
- **AI voiceover (allowed, often cleaner):** paste the [SAY] lines into **ElevenLabs** or **Descript**; pick one consistent voice; export the track. The rules permit this.

Either way: target **~-16 LUFS**, no clipping. **Check audio before anything else** — judges tolerate a rough picture, not inaudible sound.

**Assemble:** lay the VO over the silent clips in order (A→I); trim each clip to the narration; add light captions (also satisfies the English-subtitles rule and helps muted viewers). Keep **under 3:00**.

---

## End card (still, ~3–5s, pulled into the edit)
```
MR Sentinel
github.com/sgharlow/mr-sentinel  ·  gitlab.com/sgharlow/governance-demo-app
Google ADK + Gemini (Vertex AI) + GitLab MCP server  ·  Cloud Run · Cloud SQL
MIT licensed · Google Cloud Rapid Agent Hackathon · GitLab track
```

## Upload & propagate
- YouTube, **Public** (rules require "publicly visible" — not Unlisted). Title/description/tags/chapters from `docs/youtube-metadata.md`.
- Put the new URL into: the **Devpost form**, `README.md`, and `docs/devpost-submission.md` (Links table + asset checklist).
