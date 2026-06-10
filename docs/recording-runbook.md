# MR Sentinel — recording-day runbook (1-pass)

> ⚠️ **Updated 2026-06-10 for the ADK+MCP re-record.** Narrate from [`recording-teleprompter.md`](recording-teleprompter.md) (the ADK + GitLab MCP cut), NOT the superseded `demo-script.md`. Shot 5 must show the **GitLab MCP** tool trace (`scripts/demo-capture.sh fire 9` → the `ADK evaluate … via GitLab MCP` / `Starting GitLab MCP Server` / `evaluation: score=` lines), not the old REST `tool=` ×8 loop. Upload the video **PUBLIC** (the rules say "publicly visible"), not unlisted. Use the re-measured agentic-loop latency (~25–30s), not "~twenty seconds".

Exact commands, in order, to capture the demo video and submit. **Every command
runs in a WSL Ubuntu terminal** (gcloud/PAT calls are Norton-blocked elsewhere).
**Never paste multi-line PAT commands** — always use the `scripts/*.sh` files (they
keep the token in a variable and can't be mangled by terminal wrapping).

Narration + shot framing live in [`demo-script.md`](demo-script.md). This file is the
operator's command sequence.

---

## Phase A — Data prep (do once, before recording)

```bash
cd /mnt/c/Users/sghar/CascadeProjects/mr-sentinel

# A1. auth gate — if this errors, run `gcloud auth login` then retry
gcloud auth print-access-token >/dev/null && echo "auth OK"

# A2. fatten the dashboard (v2 archetypes) + re-measure latency over the fuller sample
SEED=1 bash docs/closeout-runbook.sh
```

- **A3.** Using the new `docs/closeout-<today>/03-latency-results.txt`, update the
  latency numbers in README + demo-script + devpost, re-check
  whether hero `!10`'s sha8 changed (it shouldn't — seed adds new MRs), and commit.
- **A4.** Note the new dashboard MR count + top-5 rules (you'll narrate them in Shot 7);
  refresh demo-script Shot 7 if they shifted.

> If SEED created new block MRs, they get their own legit follow-up issues. Note their
> issue iids — you'll add them to `KEEP` in Phase D.

---

## Phase B — Recording readiness (15 min before record)

```bash
# B1. all three on-camera surfaces must be green; this also prints the tabs to open
bash scripts/demo-capture.sh
```

- **B2.** Open the tabs it printed, in shot order.
- **B3.** OS + browser to **dark mode**. OBS scenes ready. Record a 10-second mic pad.

---

## Phase C — Record (follow `demo-script.md` narration)

- **Shots 1–4** — hero MR `!10`, on-camera intro, the `.env.production` diff, the
  Cloud Run + `rubric/v1.yaml` architecture orientation. **Do not run any trigger
  against `!10`** — keep its diff and sha pristine for these shots.

- **Shot 5 (live agent loop)** — in a side terminal pane:

  ```bash
  bash scripts/demo-capture.sh fire 9     # !9 = the /admin/dump-patients block
  ```

  Film the printed **AGENT LOOP** block (chronological):
  `received → using override (v2) → tool= ×8 → evaluation: score=… mr_iid=9 → created issue → posted comment`.
  Narrate generically ("when an MR opens, the agent runs its plan…"). Using `!9`
  (not `!10`) keeps the hero pristine; the slight iid difference between Shot 5 and
  Shot 6 is invisible to viewers.

- **Shots 6–10** — back to `!10` for the verdict comment, then `/dashboard`,
  `/audit/.../10`, on-camera close, end card.

- **Screenshots (same browser session, for the Devpost gallery)** — capture the
  five images per [`screenshots/CAPTURE-GUIDE.md`](screenshots/CAPTURE-GUIDE.md)
  (dashboard, MR comment, audit page, rubric, agent-loop trace). It lists the exact
  proof elements that must be in each frame. 1920×1080 PNG → `docs/screenshots/`.

---

## Phase D — Post-record

```bash
# D1. DONE — published: https://youtu.be/S93xnolHRe0

# D3. clean up everything the fire/verify runs created (dup issues + marker files).
#     If Phase A added new legit follow-up issues, extend KEEP, e.g. KEEP="1 2 3 4 5 14 15".
bash scripts/cleanup-demo-artifacts.sh

# D4. confirm surfaces still green after cleanup
bash scripts/demo-capture.sh
```

- **D2.** Paste the YouTube URL into the `docs/devpost-submission.md`
  Links table + commit. Commit the screenshots too.

---

## Phase E — Submit (before June 11, 12:00 PT)

1. Open the Devpost form. Paste each field from [`devpost-submission.md`](devpost-submission.md)
   (project name, tagline, all body sections, judging-criteria map, built-with tags).
2. Attach the **YouTube (unlisted) URL** + the **gallery screenshots**.
3. Set track = **GitLab**. Add the tag list.
4. One full read-through of the rendered preview; fix anything that wraps badly.
5. **Submit.** Hard deadline 14:00 PT; target 12:00 PT.

---

## Gotchas (the things that bite)

- **WSL only** for every command here. Git Bash → Norton SSL failure on gcloud.
- **Use the scripts, don't paste** PAT-bearing one-liners (they leak + wrap).
- **Record after Phase A**, not before — the SEED pass changes the dashboard counts.
- **Never `fire 10`** — it adds a junk file to `!10`'s diff (ruins Shot 3) and changes
  its sha8 (breaks Shot 6's `1fb25ad2`). Use `fire 9` or `fire 7`.
- **`/health` cold start** — the first hit after idle can take a few seconds; the
  readiness check warms it. Hit `/dashboard` once before rolling so it's warm on camera.
