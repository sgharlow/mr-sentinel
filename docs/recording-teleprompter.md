# Recording teleprompter — ADK + GitLab MCP cut — one continuous take (~2:50)

> ⚠️ **Record only AFTER the ADK + GitLab MCP build is deployed and validated** (see
> `docs/adk-mcp-deploy-runbook.md` §2 deploy, §4 MCP tool-trace, §6 hero-MR regression).
> Recording before deploy would film the old REST/direct-Vertex behavior. If the §6 hero-MR
> check shows `!10` drifted from block/0.0, fix that BEFORE recording — the script below
> assumes `!10` still lands block, 0.0/10, `no-secrets-in-diff`.
>
> **This cut is restructured to the 20/90/30/20 arc** (problem → app running → deliberate
> architecture choice → so-what). Rationale + the criteria map are in
> `docs/video-winning-profile-2026-06-09.md`. The biggest change from the prior version: the
> architecture explanation moves **after** the judge has SEEN the agent work, not before.

Read top to bottom while recording. **Voiceover-only, single screen capture.** Numbers in
[brackets] are placeholders to fill from your live state before/while recording.

Legend: **[SCREEN]** what's visible · **[DO]** the click/scroll · **[SAY]** narration.

---

## Layout (one 1920×1080 screen capture)
- **Browser**, dark mode, bookmarks bar hidden. Open these tabs left→right:
  1. GitLab MR `!10` — `https://gitlab.com/sgharlow/governance-demo-app/-/merge_requests/10`
  2. Dashboard — `https://mr-sentinel-webhook-n6oitfxdra-uc.a.run.app/dashboard`
  3. Audit — `https://mr-sentinel-webhook-n6oitfxdra-uc.a.run.app/audit/sgharlow/governance-demo-app/10`
  4. Rubric — `https://github.com/sgharlow/mr-sentinel/blob/main/rubric/v1.yaml`
- **Terminal window** (for the agent-loop / MCP-trace shot) — see pre-flight P3.

## Pre-flight — do ALL of this BEFORE you hit record
- **P1.** Deploy + validate per the runbook (§2/§4/§6). Confirm `/health` is 200 and the dashboard renders.
- **P2.** `bash scripts/demo-capture.sh` → all three surfaces green.
- **P3.** In the terminal: `bash scripts/demo-capture.sh fire 9` → wait until the agent runs.
  The log MUST show the **GitLab MCP read-tool calls** the ADK agent makes
  (`get_merge_request`, `get_merge_request_diffs`, `list_merge_request_pipelines`) followed by
  the `evaluation: score=…` line, the `record_verdict` emit, and the posted comment. **Leave
  that output on screen** — it IS your Shot 4 visual and your runtime-eligibility proof.
  **If the three MCP tool lines don't appear, STOP and fix per runbook §4a before recording —
  this is the shot the whole submission's eligibility leans on.**
- **P4.** Open the four tabs in order; hard-refresh each. Mic: record a 10-second pad and do one
  silent practice Alt-Tab pass.
- **P5.** Note your **measured latency** from the runbook §8 re-capture — you'll say it in Shot 4.
- **P6.** Do NOT say a Gemini version number aloud. Say "Gemini, on Vertex AI." (See
  `video-winning-profile-2026-06-09.md` §1 — the overview banner says "Gemini 3," we run 2.5
  Flash; the rules say "Gemini models," which we satisfy. Don't hand a judge a number mismatch.)

> Window switching: Shots A/B/C/E (verdict) = MR tab · Shot D = Terminal · Shot F = Dashboard ·
> Shot G = Audit · Shot H (architecture) = Rubric tab · Shot I = close (audit or end card).

---

## THE TAKE (hit record, then go)

> Arc markers in the headers tell you which beat you're in. Keep the energy up through the
> 90-second "app in action" stretch (Shots C–G) — that's where eligibility and Design are won.

### ── PROBLEM (≈0:00–0:24) ──

### Shot A · 0:00–0:10 · Cold open
- **[SCREEN]** MR `!10`, Changes tab, `.env.production` file visible.
- **[SAY]** "Friday, four-fifty PM. An MR lands — 'add the production env file.' The reviewer is tired, and has eight more in the queue."

### Shot B · 0:10–0:24 · The stakes + the diff
- **[DO]** Expand the `.env.production` diff; cursor over the `AWS_ACCESS_KEY_ID` line.
- **[SAY]** "I've spent two decades shipping software in regulated industries. The pattern that ends careers isn't malice — it's that tired engineer rubber-stamping this. And inside this diff: a database password, a JWT secret, a live Stripe key, an AWS access key — everything the policy says must never enter the repo. MR Sentinel is the agent I wish I'd had."

### ── APP IN ACTION (≈0:24–1:52) ──

### Shot C · 0:24–0:40 · Hand off to the agent
- **[SCREEN]** Stay on the MR `!10` diff a beat, then start Alt-Tabbing toward the terminal.
- **[SAY]** "So when this MR opens, MR Sentinel — a Google Agent Development Kit agent running on Cloud Run — wakes up and goes to work. Watch it actually run."

### Shot D · 0:40–1:18 · The agent loop — GitLab MCP trace (THE load-bearing shot)
- **[DO]** Alt-Tab to the **Terminal** (the `fire 9` output). Scroll slowly: the three MCP
  read-tool calls → the evaluation line → `record_verdict` → posted comment. Pause the cursor
  on the MCP tool lines for ~1 second so they're legible.
- **[SAY]** "It reaches into GitLab through **GitLab's own MCP server** — calling get-merge-request, get-merge-request-diffs, and list-pipelines to pull the context. It hands all of that to **Gemini, on Vertex AI**, which judges the diff against fifteen rules at once and emits a structured verdict by calling record-verdict. Every MCP call, every decision — logged and replayable. The whole evaluation runs in about [STATE MEASURED LATENCY, e.g. 'thirty seconds']."

> If the captured trace is missing the MCP tool lines, you cannot record this shot honestly —
> re-fire (non-determinism) or add the per-tool INFO logs first (runbook §4/§4a). This shot is
> the proof that all three required technologies run at runtime.

### Shot E · 1:18–1:52 · The verdict lands
- **[DO]** Alt-Tab to the **MR `!10`** tab; scroll to the MR Sentinel comment. Cursor: badge → evidence quote → linked issue → `blocked-compliance` label in the sidebar.
- **[SAY]** "And here's what it leaves behind. Verdict: block. Score: zero out of ten. It cites `no-secrets-in-diff` by exact rule ID — mapped to SOC 2 CC6.1, ISO 27001 A.9.4.3, OWASP-ASVS V2 — quotes the exact lines that tripped it, auto-opens a remediation issue with a checklist, and labels the MR blocked-compliance so the merge button is one step further away. Every action ties back to a named control."

### Shot F · 1:52–2:14 · Leadership dashboard
- **[DO]** Alt-Tab to the **Dashboard** tab. Full screen. Cursor down the list.
- **[SAY]** "That's one MR. Here's the portfolio. An engineering leader opens the dashboard: the last thirty days — [STATE LIVE COUNT, e.g. 'thirteen'] MRs scored, most blocked on compliance, the top failing rules, every one a control mapped to an audit framework. Click any MR…"

### Shot G · 2:14–2:30 · Audit drill-down
- **[DO]** Alt-Tab to the **Audit** tab (`/audit/.../10`). Hover the failing rules + the control_mapping column + the timeline.
- **[SAY]** "…and you're in the audit log. Every rule outcome, every control mapping, the exact prompt the agent used, the timeline of every action. This is what a compliance auditor asks for at year-end — and here it's just the byproduct of doing the work."

### ── DELIBERATE ARCHITECTURE CHOICE (≈2:30–2:42) ──

### Shot H · 2:30–2:42 · Why this build
- **[DO]** Alt-Tab to the **Rubric** tab; scroll to the `no-secrets-in-diff` rule so the control_mapping array is on screen.
- **[SAY]** "Three deliberate choices. The MCP server, because it's a portable tool surface — the same agent points at gitlab.com or a self-hosted instance without rewiring. ADK, because governance needs a real tool-calling loop and a structured verdict, not a chat reply. And Vertex, so no diff ever leaves Google Cloud. Reads go through MCP; the write-backs use GitLab's REST API — because the official Duo MCP server can't post a comment yet. Honest hybrid, by design."

### ── SO WHAT (≈2:42–2:50) ──

### Shot I · 2:42–2:50 · Close
- **[SCREEN]** Stay on the rubric (control_mapping visible), or cut to an end card in edit.
- **[SAY]** "Every regulated engineering org has this exact pain. One ADK agent, Gemini for judgment, GitLab's MCP server for reach — and one rubric where every rule is a named control. The rubric ships open-source. MR Sentinel."

**Stop recording.**

---

## End card (still, pulled into the edit — ≈3–5s after the cut)

```
MR Sentinel
github.com/sgharlow/mr-sentinel  ·  gitlab.com/sgharlow/governance-demo-app
Google ADK + Gemini (Vertex AI) + GitLab MCP server  ·  Cloud Run · Cloud SQL
MIT licensed · Google Cloud Rapid Agent Hackathon · GitLab track
```

---

## Word-count budget (≈150 wpm)

| Shot | Beat | Seconds | ~Words |
|---|---|---|---|
| A | problem | 10 | 26 |
| B | problem | 14 | 60 |
| C | app | 16 | 38 |
| D | app (MCP trace) | 38 | 75 |
| E | app (verdict) | 34 | 78 |
| F | app (dashboard) | 22 | 55 |
| G | app (audit) | 16 | 50 |
| H | architecture | 12 | 78 |
| I | so-what | 8 | 40 |
| **Total** | | **170** | **500** |

Shot H is dense — if it feels rushed, drop the "self-hosted instance" clause first. If the whole
take runs long, trim per `video-winning-profile-2026-06-09.md` §5 (protect Shots D and E).

---

## After the take
- **Edit:** trim the first/last second; burn in captions (rules allow English subtitles in lieu
  of English audio — captions also help muted-on-transit judges); loudness ~-16 LUFS. Keep it
  **under 3:00** (hard rules cap).
- **Screenshots:** re-grab the 5 gallery shots (`screenshots/CAPTURE-GUIDE.md`) from the same
  tabs — **especially `05-agent-loop`, which must now show the three GitLab MCP read-tool
  calls** (`get_merge_request` / `get_merge_request_diffs` / `list_merge_request_pipelines`),
  not the old eight-REST-call loop.
- **Upload:** **public** (rules require publicly visible on YouTube/Vimeo — not Unlisted as the
  safest reading of "publicly visible"); paste title + description + tags + chapters from
  `docs/youtube-metadata.md`. Then put the new URL into the Devpost form and into `README.md` +
  `docs/devpost-submission.md`.

## What changed from the prior cut (so you know what to re-narrate)
- **Arc reordered** to 20/90/30/20: architecture moved from ~0:42 (before the payoff) to ~2:30
  (after the judge has seen it work). Per `video-winning-profile-2026-06-09.md`.
- **Shot D is now the load-bearing MCP-trace shot** — narration names the three MCP read tools
  explicitly and ties them to the Gemini eval + `record_verdict`. This is the runtime-
  eligibility proof; it sits inside the 90s "app in action" stretch on purpose.
- **Shot H volunteers the honest hybrid** (MCP reads + REST write-backs, and *why*) in one
  sentence — a net positive with expert judges.
- **No Gemini version number is spoken** ("Gemini, on Vertex AI") — avoids the banner-says-3 /
  we-run-2.5 mismatch.
- **Latency** — say your re-measured agentic-loop number, not the old "~twenty seconds."
