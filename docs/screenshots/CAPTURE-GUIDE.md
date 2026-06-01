# Gallery screenshot capture guide

Five images for the Devpost gallery. Capture during the same browser session as the
video (Phase C of [`../recording-runbook.md`](../recording-runbook.md)), so state is
consistent. Each must show the **proof elements** listed — that's what makes a judge
believe it's real, not a mockup.

**Format:** PNG, **1920×1080**. Save into this folder with the exact filenames below.
The Devpost *thumbnail* (1280×720) is separate and already done (`../assets/devpost-thumbnail.png`).

## Pre-capture prep (once)
- OS + browser in **dark mode** (the dashboard/audit pages are dark-themed).
- Hide the bookmarks bar and any extension chrome (clean frame).
- Browser window ≈ 1920×1080, or capture larger and crop/resize to 1920×1080 after.
  On a HiDPI/Retina display screenshots come out 2× — resize down to 1920×1080.
- Hit `/dashboard` once before capturing so Cloud Run is warm (no cold-start blank).

---

## 01-dashboard.png — the leadership view *(lead image)*
- **Surface:** `https://mr-sentinel-webhook-n6oitfxdra-uc.a.run.app/dashboard`
- **Must be in frame:**
  - the "last 30d" header + the **MRs-scored count** (higher after the SEED pass)
  - the **verdict distribution** bars (block / warn / pass)
  - the **top-5 failing rules** list — with the control-mapping text visible
  - the **recent-MRs table** with verdict pills
- **Framing:** full page, top-aligned. If it scrolls, capture the top fold (distribution + top-5).
- **Caption:** "Leadership dashboard — verdict distribution, top failing rules, and drill-down across the last 30 days."

## 02-mr-comment.png — the agent verdict on the hero MR *(money shot)*
- **Surface:** `https://gitlab.com/sgharlow/governance-demo-app/-/merge_requests/10`, scrolled to the MR Sentinel comment.
- **Must be in frame:**
  - the 🛑 verdict badge: **block (score 0.0/10)** and "Applied rubric `v2` … 15 rules"
  - the **Failures** section citing **`no-secrets-in-diff`** with its control mapping
    (**SOC 2 CC6.1 · ISO 27001 A.9.4.3 · OWASP-ASVS V2**) and the evidence quote
  - the **linked remediation issue**
  - the **`blocked-compliance`** label in the right sidebar
- **Framing:** the comment card + the sidebar label both visible (zoom out slightly if needed).
- **Caption:** "Every blocked MR gets a structured comment — verdict, the exact failing rule, and the named compliance control it maps to."

## 03-audit.png — the auditor view
- **Surface:** `https://mr-sentinel-webhook-n6oitfxdra-uc.a.run.app/audit/sgharlow/governance-demo-app/10`
- **Must be in frame:**
  - verdict badge + **score 0.0** + sha8 + rubric version
  - the **rule-outcomes table** (failures first) with the **control_mapping column populated**
  - the **audit_log timeline** rows with timestamps
- **Framing:** top fold showing the header + the first several rule rows incl. the control column.
- **Caption:** "The audit page: every rule outcome, its control mapping, and the timeline — the audit is the byproduct of doing the work."

## 04-rubric.png — the rubric is the product
- **Surface:** `rubric/v1.yaml` (GitHub web at `github.com/sgharlow/mr-sentinel`, or a local editor with a dark theme).
- **Must be in frame:** one full rule object showing `rule_id`, `category`, `control_mapping`,
  `severity`, `evaluator_prompt`. Prefer the **`no-secrets-in-diff`** rule so it ties to the hero MR.
- **Framing:** ~20–30 lines, enough to see the rule's shape and the control_mapping array.
- **Caption:** "15 rules, each mapped 1:1 to a named control. MIT-licensed; override per-project via `.mr-sentinel.yaml`."

## 05-agent-loop.png — it really runs on Google Cloud
- **Surface:** Cloud Logging for `mr-sentinel-webhook`, showing one evaluation's trace. Easiest:
  run `bash scripts/demo-capture.sh fire 9` and screenshot its printed **AGENT LOOP** block,
  or the GCP console Logs Explorer filtered to the service.
- **Must be in frame:** the ordered loop —
  `received gitlab event` → `using project override rubric (v2)` → the run of **`tool=…`** lines
  (get_merge_request, get_merge_request_diffs, get_latest_pipeline_for_sha, list_vulnerability_findings, …)
  → `evaluation: score=… rules=15 mr_iid=9` → `created followup issue` → `posted comment`.
- **Caption:** "Eight deterministic GitLab tool calls and one Gemini evaluation per MR — fully traced and replayable in Cloud Logging."

---

## Two extra frames for the demo player (`../demo-player.html`)
- `mr-header.png` — MR `!10` top: title "chore: add .env.production…", Changes tab visible (Shots 1–2).
- `mr-diff.png` — the expanded `.env.production` diff with the secret lines visible (Shot 3).

## Quick checklist
- [ ] mr-header.png      (MR !10 header / changes tab)
- [ ] mr-diff.png        (.env.production secrets in the diff)
- [ ] 01-dashboard.png   (1920×1080, distribution + top-5 + count visible)
- [ ] 02-mr-comment.png  (badge + no-secrets-in-diff + control mappings + label)
- [ ] 03-audit.png       (rule table + control_mapping column + timeline)
- [ ] 04-rubric.png      (a rule with control_mapping; prefer no-secrets-in-diff)
- [ ] 05-agent-loop.png  (received → tool= ×8 → evaluation mr_iid → issue → comment)
- [ ] all 1920×1080 PNG in `docs/screenshots/` (these feed both the Devpost gallery AND `demo-player.html`)
