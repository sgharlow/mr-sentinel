# Recording teleprompter — one continuous 1-pass take (~2:50)

Read top to bottom while recording. **Voiceover-only, single screen capture** — no
mid-take decisions, no "record this part separately." (Optional on-camera intro/outro
noted at the end; splice later if you want one.) Numbers below are the live
post-SEED state (verified 2026-06-01).

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
- **P1.** `bash scripts/demo-capture.sh` → all three green (dashboard shows **13 MRs**).
- **P2.** Open the four tabs above, in order. Hard-refresh each.
- **P3.** In the terminal: `bash scripts/demo-capture.sh fire 9` → wait ~25 s until it
  prints the **AGENT LOOP** block (`received → tool= … → evaluation … → comment`).
  **Leave that output on screen** — it IS your Shot 5 visual (no waiting on camera).
- **P4.** Mic: record a 10-second pad. Do one silent practice Alt-Tab pass through
  the sequence so window switches are muscle-memory.

> Window switching: Shots 1/3/6 = MR tab · Shot 4 = Rubric tab · Shot 5 = Terminal ·
> Shot 7 = Dashboard tab · Shot 8 = Audit tab. Alt-Tab/Ctrl-number, no hunting.

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

### 0:42–0:58 · The rubric / where it runs
- **[DO]** Alt-Tab to the **Rubric** tab; scroll to the `no-secrets-in-diff` rule.
- **[SAY]** "MR Sentinel runs on Cloud Run with Vertex AI Gemini behind a webhook. Fifteen rules in one YAML file — every rule mapped to a named compliance control: SOC 2, ISO 27001, OWASP, NIST. The rubric is the product."

### 0:58–1:22 · The agent loop (pre-baked terminal)
- **[DO]** Alt-Tab to the **Terminal** (the `fire 9` AGENT LOOP block). Scroll slowly down it.
- **[SAY]** "When the webhook fires, the agent runs a deterministic plan: pull the MR, the diff, the pipeline, the vulnerability scan, check for a project rubric override, then hand it to Gemini. Eight tool calls, one Gemini evaluation — about twenty seconds end to end. Every call is logged and replayable."

### 1:22–1:52 · The verdict lands
- **[DO]** Alt-Tab to the **MR `!10`** tab; scroll to the MR Sentinel comment. Cursor: badge → evidence → linked issue → `blocked-compliance` label.
- **[SAY]** "Here's the comment. Verdict: block. Score: zero out of ten. It cites `no-secrets-in-diff` by exact rule ID — mapped to SOC 2 CC6.1, ISO 27001 A.9.4.3, OWASP-ASVS V2 — quotes the lines that tripped it, auto-opens a remediation issue, and labels the MR blocked-compliance. Every action ties back to a named control."

### 1:52–2:20 · Leadership dashboard
- **[DO]** Alt-Tab to the **Dashboard** tab. Full screen. Cursor down the list.
- **[SAY]** "An engineering leader opens the dashboard. The last thirty days: thirteen MRs scored, eight blocked on compliance. The top failing rules — every one a control mapped to an audit framework. Drift, by rule, by window. Click any MR…"

### 2:20–2:38 · Audit drill-down
- **[DO]** Alt-Tab to the **Audit** tab (`/audit/.../10`). Hover the failing rules + the timeline.
- **[SAY]** "…and you're in the audit log. Every rule outcome, every control mapping, the exact prompt the agent used, the timeline of every action. This is what a compliance auditor asks for at year-end — and here it's the byproduct of doing the work."

### 2:38–2:50 · Close
- **[SCREEN]** Stay on the audit page (or cut to an end card in edit).
- **[SAY]** "Eight tool calls. One Gemini evaluation. One rubric. One paper trail — on Cloud Run, Cloud SQL, Secret Manager, and Vertex AI. The rubric ships open-source. MR Sentinel."

**Stop recording.**

---

## After the take
- **Edit:** trim the first/last second; burn in captions; loudness ~-16 LUFS. Keep it under 3:00.
- **Screenshots:** grab the 5 in [`screenshots/CAPTURE-GUIDE.md`](screenshots/CAPTURE-GUIDE.md) from the same tabs while they're open.
- **Cleanup:** `DRY=1 bash scripts/cleanup-demo-artifacts.sh` then run it for real (closes the `fire`/retest dup issues, deletes marker files).
- **Upload:** DONE — published at https://youtu.be/0IlB2KJsJ4A (in `devpost-submission.md` Links table + `devpost-submit-cheatsheet.md`).

## Optional on-camera (only if you want a talking head)
Record two short webcam clips separately and splice: the **0:10–0:24 stakes** line and
the **2:38–2:50 close** line. Everything else stays screen-only. Skip these for a pure
1-pass; the voiceover carries the story fine.
