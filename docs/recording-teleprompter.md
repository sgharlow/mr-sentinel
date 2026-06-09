# Recording teleprompter — ADK + GitLab MCP cut — one continuous take (~2:50)

> ⚠️ **Record only AFTER the ADK + GitLab MCP build is deployed and validated** (see
> `docs/adk-mcp-deploy-runbook.md` §2 deploy, §4 MCP tool-trace, §6 hero-MR regression).
> Recording before deploy would film the old REST/direct-Vertex behavior. If the §6 hero-MR
> check shows `!10` drifted from block/0.0, fix that BEFORE recording — the script below
> assumes `!10` still lands block, 0.0/10, `no-secrets-in-diff`.

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
- **Terminal window** (for Shot 5) — see pre-flight P3.

## Pre-flight — do ALL of this BEFORE you hit record
- **P1.** Deploy + validate per the runbook (§2/§4/§6). Confirm `/health` is 200 and the dashboard renders.
- **P2.** `bash scripts/demo-capture.sh` → all three surfaces green.
- **P3.** In the terminal: `bash scripts/demo-capture.sh fire 9` → wait until the agent runs.
  The log should show the **GitLab MCP tool calls** the ADK agent makes
  (`get_merge_request`, `get_merge_request_diffs`, `list_merge_request_pipelines`) followed by
  the `evaluation: score=…` line and the comment. **Leave that output on screen** — it IS your
  Shot 5 visual. (If the MCP tool lines don't appear, see runbook §4a before recording.)
- **P4.** Open the four tabs in order; hard-refresh each. Mic: record a 10-second pad and do one
  silent practice Alt-Tab pass.
- **P5.** Note your **measured latency** from the runbook §8 re-capture — you'll say it in Shot 5.

> Window switching: Shots 1/3/6 = MR tab · Shot 4 = Rubric tab · Shot 5 = Terminal ·
> Shot 7 = Dashboard tab · Shot 8 = Audit tab.

---

## THE TAKE (hit record, then go)

### 0:00–0:10 · Cold open
- **[SCREEN]** MR `!10`, Changes tab, `.env.production` file visible.
- **[SAY]** "Friday afternoon. An MR lands — 'add the production env file.' The reviewer is tired, and has eight more in the queue."

### 0:10–0:24 · The stakes
- **[SCREEN]** Stay on the MR.
- **[SAY]** "I've spent two decades shipping software in regulated industries. The pattern that ends careers isn't malice — it's a tired senior engineer rubber-stamping an MR at four-fifty on a Friday. MR Sentinel is the agent I wish I'd had, built on Google Cloud."

### 0:24–0:42 · The diff
- **[DO]** Expand the `.env.production` diff; cursor over the `AWS_ACCESS_KEY_ID` line.
- **[SAY]** "Inside the diff: a database password, a JWT secret, a live Stripe key, an AWS access key — everything the policy says must never enter the repo."

### 0:42–1:00 · What it is (the architecture beat) — CHANGED
- **[DO]** Alt-Tab to the **Rubric** tab; scroll to the `no-secrets-in-diff` rule.
- **[SAY]** "MR Sentinel is a **Google ADK agent**. Its model is **Gemini 2.5 Flash**, and it reaches into GitLab through **GitLab's MCP server** to read the merge request, the diff, and the pipeline. Then it judges them against fifteen rules — every rule mapped to a named compliance control: SOC 2, ISO 27001, OWASP, NIST. The rubric is the product."

### 1:00–1:24 · The agent loop (pre-baked terminal) — CHANGED
- **[DO]** Alt-Tab to the **Terminal** (the `fire 9` output). Scroll slowly down the MCP tool calls → the evaluation line.
- **[SAY]** "When the webhook fires, the ADK agent calls GitLab's MCP tools to gather context — the merge request, its diff, its pipeline — reasons over them with Gemini against the rubric, and records a structured verdict. The whole evaluation runs in about [STATE MEASURED LATENCY, e.g. 'thirty seconds'], and every call is logged and replayable."

### 1:24–1:52 · The verdict lands
- **[DO]** Alt-Tab to the **MR `!10`** tab; scroll to the MR Sentinel comment. Cursor: badge → evidence → linked issue → `blocked-compliance` label.
- **[SAY]** "Here's the comment. Verdict: block. Score: zero out of ten. It cites `no-secrets-in-diff` by exact rule ID — mapped to SOC 2 CC6.1, ISO 27001 A.9.4.3, OWASP-ASVS V2 — quotes the lines that tripped it, auto-opens a remediation issue, and labels the MR blocked-compliance. Every action ties back to a named control."

### 1:52–2:20 · Leadership dashboard
- **[DO]** Alt-Tab to the **Dashboard** tab. Full screen. Cursor down the list.
- **[SAY]** "An engineering leader opens the dashboard. The last thirty days: [STATE LIVE COUNT] MRs scored, most blocked on compliance. The top failing rules — every one a control mapped to an audit framework. Drift, by rule, by window. Click any MR…"

### 2:20–2:38 · Audit drill-down
- **[DO]** Alt-Tab to the **Audit** tab (`/audit/.../10`). Hover the failing rules + the timeline.
- **[SAY]** "…and you're in the audit log. Every rule outcome, every control mapping, the exact prompt the agent used, the timeline of every action. This is what a compliance auditor asks for at year-end — and here it's the byproduct of doing the work."

### 2:38–2:50 · Close — CHANGED
- **[SCREEN]** Stay on the audit page (or cut to an end card in edit).
- **[SAY]** "One ADK agent. Gemini for judgment. GitLab's MCP server for reach. One rubric, one paper trail — on Cloud Run, Cloud SQL, and Vertex AI. The rubric ships open-source. MR Sentinel."

**Stop recording.**

---

## After the take
- **Edit:** trim the first/last second; burn in captions; loudness ~-16 LUFS. Keep it under 3:00.
- **Screenshots:** re-grab the 5 gallery shots (`screenshots/CAPTURE-GUIDE.md`) from the same tabs — **especially `05-agent-loop`, which must now show the GitLab MCP tool calls**, not the old REST loop.
- **Upload:** unlisted/public; paste title + description + tags + chapters from `docs/youtube-metadata.md` (already updated for this cut). Then put the new URL into the Devpost form and into `README.md` + `docs/devpost-submission.md`.

## What changed from the pre-ADK cut (so you know what to re-narrate)
- **Shot 0:42** — now "a Google ADK agent … reads through GitLab's MCP server" (was "runs on Cloud Run with Vertex AI Gemini behind a webhook").
- **Shot 1:00** — now "calls GitLab's MCP tools … reasons with Gemini … records a verdict" (was "deterministic plan … eight tool calls, one Gemini evaluation").
- **Shot 2:38** — now names ADK + Gemini + GitLab MCP (was "eight tool calls, one Gemini evaluation").
- **Latency** — say your re-measured number, not the old "~twenty seconds."
- Everything else (stakes, diff, verdict, dashboard, audit) carries over unchanged.
