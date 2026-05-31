# MR Sentinel — 3-minute demo video script

**Total runtime:** 3:00
**Format:** 1080p screen capture with picture-in-picture for on-camera shots
**Hero MR:** `gitlab.com/sgharlow/governance-demo-app/-/merge_requests/10` — the secret-in-diff archetype. Most visually striking verdict (0.0/10, block, `no-secrets-in-diff` blocker mapped to SOC 2 + ISO 27001 + OWASP-ASVS, automated remediation issue). Live audit confirms 2 fail rows (`contract-has-spec-link` warning + `no-secrets-in-diff` blocker), commit sha8 `1fb25ad2`.

This script is the verbatim narration plus shot-level camera direction. Total spoken-word count budgets for ~150 wpm delivery, leaving breathing room for cuts.

---

## Scriptable runner — `scripts/demo-capture.sh`

This script is the executable companion to the storyboard below. Run both from WSL:

- **`bash scripts/demo-capture.sh`** — read-only recording-readiness check: pings `/health`, `/dashboard`, and the hero audit page, then prints every tab to open in shot order. Run it right before recording; all three must pass.
- **`bash scripts/demo-capture.sh fire`** — the live **Shot 5** moment: pushes a fresh commit to a non-hero MR (`!7` by default, so hero `!10`'s sha8 `1fb25ad2` stays pinned), waits for the agent loop, and prints the full ordered trace (`received → using override (v2) → tool= ×8 → evaluation: score=… mr_iid=7 → created issue → posted comment`) — film that block. Pass `fire 9` to use the `/admin/dump-patients` block instead; pass `fire 10` ONLY after you've decided to recapture the hero sha (e.g. post-`SEED=1`).

## Pre-recording checklist (15 min before record)

0. **Run `bash scripts/demo-capture.sh`** — green on all three surfaces before doing anything else.
1. **Demo repo state.** Verify on `gitlab.com/sgharlow/governance-demo-app`:
   - `.mr-sentinel.yaml` exists on `main` (the v2 override, identical content to bundled v1 — fine for the demo)
   - MR `!10` is OPEN with verdict `block`, score `0.0/10`, posted comment, label `blocked-compliance`, linked follow-up issue
   - If `!10` is closed: re-run `bash scripts/seed-archetype-mrs.sh` from WSL to regenerate
2. **Cloud Run service.** `curl https://mr-sentinel-webhook-n6oitfxdra-uc.a.run.app/health` → `{"status":"ok"}`.
3. **Dashboard data.** Visit `/dashboard` — confirm 8+ MRs scored, top-5 rules populated, recent MRs table shows `!10` near the top.
4. **Audit page.** Visit `/audit/sgharlow/governance-demo-app/10` — confirm 15 rule rows, audit_log timeline, score 0.0.
5. **Browser theme.** Switch OS + browser to dark mode so the dashboard's intentional dark palette matches the surrounding chrome.
6. **Window setup.** Two 1080p windows side-by-side: left = GCP console / Cloud Run logs, right = GitLab MR. Plus full-screen mode for the dashboard shots.
7. **Mic.** Same level as the foreign-mind.com book launch videos; record a 10-second pad before the take.

---

## Shot-by-shot script

### Shot 1 — Cold open (0:00–0:08, 8s)

**Visual:** Full-screen GitLab MR view. MR `!10` header visible: title "chore: add .env.production for prod deploy", description "Drops the production env file into the repo...", commits tab showing 1 commit.

**Camera:** No on-camera. Cursor hovers near the `.env.production` file in the changes tab — viewer can see the file pending review.

**Narration (8s):**
> "Friday afternoon. An MR lands. The title says 'production env file.' The reviewer is tired."

**Verified 2026-05-21:** MR `!10` exists, title and description match seeding script v1 line 232-234.

### Shot 2 — On-camera open (0:08–0:25, 17s)

**Visual:** Picture-in-picture, lower right, on-camera. MR still visible on screen.

**Narration (17s):**
> "I've spent two decades shipping software for regulated industries — fintech, healthcare, regulated SaaS. The pattern that ends careers isn't malice. It's a tired senior engineer rubber-stamping an MR at four-fifty PM on a Friday. MR Sentinel is the agent I wish I'd had — and it's built on Google Cloud."

### Shot 3 — Diff inspection (0:25–0:40, 15s)

**Visual:** Click into MR `!10` changes tab. The `.env.production` file expands. The viewer can see: `STRIPE_API_KEY=sk_live_...`, `AWS_ACCESS_KEY_ID=AKIA...`, database password in URL form.

**Camera:** No on-camera. Cursor highlights the `AWS_ACCESS_KEY_ID` line.

**Narration (15s):**
> "Inside the diff: a production env file. Database password. JWT secret. Live Stripe key. AWS access key. Every single thing the policy says should never enter the repo. And the reviewer has eight more MRs in the queue."

**Verified 2026-05-21:** `.env.production` diff contains all 6 named secret types (`DATABASE_URL`, `JWT_SECRET`, `STRIPE_API_KEY`, `STRIPE_WEBHOOK_SECRET`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`). Per seeding script v1 lines 212-226. Live audit page `/audit/.../10` quotes all six verbatim.

### Shot 4 — Architecture orientation (0:40–0:55, 15s)

**Visual:** Split screen. Left half: Cloud Run service page in GCP console showing `mr-sentinel-webhook` with traffic at 100% on the latest revision. Right half: the MR page from before. A small slide-in shows `rubric/v1.yaml` — top of file with the v1 version + 15 rule count visible.

**Camera:** Voiceover only.

**Narration (15s):**
> "MR Sentinel runs on Cloud Run. Vertex AI Gemini behind a webhook. Fifteen rules in a YAML file — every one mapped to a named compliance control. SOC 2. ISO 27001. OWASP. NIST. The rubric is the product."

**Verified 2026-05-21:** Service `mr-sentinel-webhook` live on Cloud Run. `rubric/v1.yaml` has 15 rules. `control_mapping` covers CDPD, SOC2, ISO-27001, OWASP-ASVS, NIST (all four named families present). Vertex AI Gemini 2.5 Flash per `app/main.py`.

### Shot 5 — Agent loop trace (0:55–1:20, 25s)

**Visual:** Cloud Logging tail filtered to `mr-sentinel-webhook`. Logs scroll showing the agent loop firing in real time for MR `!10`:
- `received gitlab event kind=merge_request mr_iid=10 action=update`
- `using project override rubric (v2)`
- 8 GitLab REST calls (get_merge_request, get_file_content for override, get_merge_request_diffs, get_latest_pipeline_for_sha, list_vulnerability_findings, etc.)
- `evaluation: score=0.0 verdict=block rules=15`
- `created followup issue !3 — https://gitlab.com/.../issues/3`
- `posted comment note_id=... on MR !10`

**Camera:** No on-camera. Cursor traces down the log lines as they fire.

**Narration (25s):**
> "When the webhook fires, the agent runs a deterministic plan. It pulls the merge request, the diff, the pipeline, the vulnerability scan. It checks for a project-specific rubric override — Medbill ships one. It hands the diff to Gemini. Gemini scores against all fifteen rules at once and returns a structured verdict. Eight tool calls. One Gemini call. About twenty seconds end to end."

**VERIFIED 2026-05-31 (WSL closeout, `docs/closeout-20260531/`):** Log strings pulled from live Cloud Logging. Corrections applied to the visual cues above:

- **Real log lines that ARE emitted** (use these as the on-screen cues): `received gitlab event kind=merge_request project=sgharlow/governance-demo-app mr_iid=10 action=update` → `using project override rubric (v2)` → `evaluation: score=0.0 verdict=block rules=15` → `created followup issue !3 — https://gitlab.com/sgharlow/governance-demo-app/-/work_items/3` → `posted comment note_id=3361770482 on MR !10`. (Note: issue URL is `/-/work_items/N`, **not** `/-/issues/N`; older runs logged a `(vv2)` typo, now corrected to `(v2)`.)
- **⚠️ The eight individual tool-call lines do NOT exist in the logs.** A grep for `get_merge_request`, `get_file_content`, `get_merge_request_diffs`, `get_latest_pipeline`, `list_vulnerability` returned zero matches — the agent does not log each REST call at INFO. So the imagined "eight API calls fire in sequence, each lights green" visual is not backed by logs. **Two options before record:** (a) narrate "eight tool calls" over the five real log lines above (cut the per-call zoom), or (b) add one INFO log per tool call in `app/gitlab_client.py` and redeploy so the visual is real. Option (a) is zero-risk; (b) makes Shot 5 markedly stronger if there's deploy headroom.
- **Latency MEASURED:** full webhook→comment loop **p50 19.5s, p95 30.0s, p99 33.4s** (n=17, last 30 days). The old "~30s" was effectively the p95; median is ~20s. Narration updated to "about twenty seconds." (The gemini-leg p95/p99 in `03-latency-results.txt` are a pairing artifact — `evaluation: score=` carries no `mr_iid` — ignore that tail.)

### Shot 6 — Verdict comment lands (1:20–1:50, 30s)

**Visual:** Back to MR `!10`. The agent's structured Markdown comment renders. Viewer sees:
- `🛑 MR Sentinel — verdict: block (score 0.0/10)`
- "Applied rubric `v2` to 15 rules. Commit `1fb25ad2` · pipeline `failed`"
- **Failures (2)** block with `no-secrets-in-diff` cited specifically — quote the evidence: *"DATABASE_URL, JWT_SECRET, STRIPE_API_KEY, STRIPE_WEBHOOK_SECRET, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY are all present in .env.production"*
- Linked remediation issue
- Label `blocked-compliance` visible on the right sidebar

**Camera:** Cursor traces from the verdict badge → to the evidence → to the linked issue → to the label.

**Narration (30s):**
> "Here's the comment. Verdict: block. Score: zero out of ten. The agent cites — by exact rule ID — `no-secrets-in-diff`, mapped to SOC 2 CC6.1, ISO 27001 A.9.4.3, and OWASP ASVS V2. It quotes the lines that tripped it. It auto-opens a remediation issue with a checklist. It labels the MR `blocked-compliance` so the merge button is one step further away. Every action ties back to a named control. Every action is logged to Postgres."

**Verified + corrected 2026-05-21:** Live audit at `/audit/.../10` shows verdict=block, score=0.0/10, rubric=v2. Commit sha8 corrected from `5d2e7a14` → **`1fb25ad2`** (per live audit page). Failure count corrected: live shows **2 fails** (`contract-has-spec-link` warning + `no-secrets-in-diff` blocker), not 4. The hero quote on `no-secrets-in-diff` matches the live audit page verbatim — the demo's punchline still lands. Control mappings on `no-secrets-in-diff` verified as `SOC2-CC6.1, ISO-27001-A.9.4.3, OWASP-ASVS-V2` (matches narration). **After v2 archetypes seed, recapture sha8 (if the demo runs against the updated `!10`).** Narration "every action is logged to Postgres" — verified: Cloud SQL audit table per `app/main.py`.

### Shot 7 — Leadership dashboard (1:50–2:20, 30s)

**Visual:** Navigate to `https://mr-sentinel-webhook-n6oitfxdra-uc.a.run.app/dashboard`. Full screen. Dark theme. Viewer sees:
- "Leadership dashboard · last 30d"
- "MRs scored: 8"
- Verdict distribution bars: 6 block, 1 warn, 1 pass
- Top-5 failing rules: `contract-has-spec-link (5)`, `integration-boundaries-explicit (3)`, `auth-on-new-public-endpoints (3)`, `no-secrets-in-diff (3)`, `changed-method-coverage (3)`
- Recent MRs table — cursor hovers MR `!10` row

**Camera:** Voiceover only. Cursor moves down the list.

**Narration (30s):**
> "An engineering leader opens the dashboard. The last thirty days: eight MRs scored. Six blocked on compliance. The top-five failing rules — every one a control mapped to an audit framework. Drift, by rule, by window. Click any MR..."

**Verified + corrected 2026-05-21:** Dashboard live, exact label is **"last 30d"** (corrected from "this week" → "the last thirty days" in narration). MRs scored = 8, distribution 6/1/1 verified. Top-5 rule **order** corrected: `integration-boundaries-explicit` is 2nd (not `auth-on-new-public-endpoints`). All five rule names match live data. **After v2 archetypes seed,** dashboard count will jump to 12 MRs, distribution + top-5 ordering will shift — record AFTER the seed has settled and re-verify these numbers.

### Shot 8 — Audit drill-down (2:20–2:40, 20s)

**Visual:** Click MR `!10` row in the dashboard. Navigates to `/audit/sgharlow/governance-demo-app/10`. Page shows:
- Verdict badge, score, sha8, rubric version `v2`
- Rule outcomes table — failures first, with control_mapping column populated
- Audit log timeline — `evaluate` and `skip_duplicate` rows visible with timestamps

**Camera:** Cursor hovers the failing rules + the audit log.

**Narration (20s):**
> "...and you're inside the audit log. Every rule outcome. Every control. The exact prompt the agent used to decide. The timeline of every action it took. This is what a compliance auditor asks for at year-end. With MR Sentinel, the audit is the byproduct of doing the work — not a separate exercise."

**Verified 2026-05-21:** `/audit/sgharlow/governance-demo-app/10` renders verdict badge, score, sha8, rubric v2; rule-outcomes table with `control_mapping` column populated; audit log timeline with `evaluate` + `skip_duplicate` entries. All shot elements present.

### Shot 9 — On-camera close (2:40–2:55, 15s)

**Visual:** Picture-in-picture full size, looking at camera. Background blurred.

**Narration (15s):**
> "Eight tool calls. One Gemini evaluation. One rubric. One paper trail. Built on Google Cloud Run, Cloud SQL, Secret Manager, and Vertex AI. The rubric ships open-source. MR Sentinel."

**Verified 2026-05-21:** All four GCP services (Cloud Run, Cloud SQL, Secret Manager, Vertex AI) are deployed per README §"GCP resources live." Repo is MIT (`LICENSE` present, detectable from GitHub About).

### Shot 10 — End card (2:55–3:00, 5s)

**Visual:** Static end card on dark background:

```
MR Sentinel
github.com/sgharlow/mr-sentinel
gitlab.com/sgharlow/governance-demo-app
MIT licensed · Google Cloud Rapid Agent Hackathon · GitLab track
```

**Narration (5s):**
> "Code's on GitHub. Demo's on GitLab. Thanks."

---

## Word count budget vs. measured

| Shot | Spoken seconds | Words |
|---|---|---|
| 1 | 8 | 19 |
| 2 | 17 | 50 |
| 3 | 15 | 47 |
| 4 | 15 | 44 |
| 5 | 25 | 70 |
| 6 | 30 | 92 |
| 7 | 30 | 65 |
| 8 | 20 | 60 |
| 9 | 15 | 32 |
| 10 | 5 | 7 |
| **Total** | **180** | **486** |

~150 wpm average — comfortable, no rush. If timing slips, cut the last sentence of Shot 6 or Shot 7 first.

---

## Edit pass checklist (after first take)

- [ ] Loudness normalized to -16 LUFS (YouTube/Devpost standard)
- [ ] First 8 seconds pulled tight — judges drop off fast
- [ ] Shot 5 logs zoom-in is legible at 1080p (cursor highlight + 1.2x zoom if not)
- [ ] Shot 6 evidence quote is readable — pause cursor on it 0.5s
- [ ] Shot 7 dashboard bars animate cleanly — no jitter
- [ ] Captions burned in (Devpost judges sometimes watch muted on transit)
- [ ] Final still-frame end card holds 2 full seconds before the cut
- [ ] Video uploaded to YouTube as **Unlisted**, link saved for the Devpost form
- [ ] One reduced 720p copy attached directly to the Devpost form as a fallback

---

## Backup talking points (if first take feels flat)

- **If asked "why not Agent Builder":** "Agent Builder adds orchestration value when you have many tools and dynamic planning. For a fifteen-rule rubric and eight deterministic actions, the orchestration is the agent. Visible in plain Python. Replayable from the audit log."
- **If asked "why not MCP":** "REST gave us stability across GitLab tiers and clear semantics in Cloud Logging. The endpoint matrix is preserved as a future-MCP migration reference."
- **If asked "what's the moat":** "The rubric. Most submissions will be 'AI reviews PR.' MR Sentinel ships *with* a methodology — every rule maps to a named control auditors recognize. It's configurable per project via `.mr-sentinel.yaml` at the consumer's repo root."

---

## Recording-day order of operations

1. Open all browser tabs in order (MR `!10` → GCP Cloud Run → Logs → dashboard → audit page)
2. Hard-refresh each tab
3. Verify `.mr-sentinel.yaml` on demo repo's main is still present
4. Verify `/health` returns 200 from Cloud Run
5. Test mic level + screen capture in OBS / equivalent
6. Record Shots 1-8 as one continuous take (cuts in edit, not in record)
7. Record Shots 2 and 9 separately as on-camera segments
8. Record Shot 10 end card as a still image — pulled into final cut
9. Save raw take in case re-cuts needed

---

## 2026-05-21 reconciliation pass — summary

Performed by `/daily-priority mr-sentinel hackathon` Story 5. Each shot annotated above with **Verified** or **STALE** + corrections. Highlights:

- **Hard corrections applied to script:** Shot 6 commit sha8 `5d2e7a14` → `1fb25ad2`; "Failures (4)" → "Failures (2)". Shot 7 top-5 rule order corrected; narration "this week" → "the last thirty days." 2026-05-22 follow-up: file-header (line 5) "four security rules failing" → "secrets-in-diff blocker mapped to SOC 2 + ISO 27001 + OWASP-ASVS" — relive-audit verified 2 fail rows (warning + blocker), not 4 security rules. Header now matches Shot 6 prose.
- **Soft TODO for Steve before record:** Shot 5 log strings need WSL Cloud Logging verification (Norton MITM blocks gcloud from the Windows PC). Latency claim "30 seconds end to end" needs re-measure.
- **Post-v2-seed re-pass required:** When `seed-archetype-mrs-v2.sh` runs, the dashboard counts in Shot 7 (8 → 12 MRs, distribution shifts) and possibly the `!10` commit sha8 (Shot 6) will change. Record AFTER the seed has settled, and either accept the updated numbers or pin the narration to a stable window.
- **No fundamental story drift.** The hero MR `!10` still has score 0.0, verdict block, and the `no-secrets-in-diff` evidence quote matches verbatim. The demo's punchline is intact.
