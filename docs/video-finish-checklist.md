# Finish the MR Sentinel demo video — remaining manual steps

Everything that could be automated is **already built and in the repo**. This doc is the complete,
self-contained checklist for the **3 clips you must record by hand**, plus the voiceover, assembly,
captions, and upload. Target total runtime **under 3:00** (the plan lands at ~2:40).

Related files (already produced): `docs/recording-teleprompter.md` (full script) · `docs/demo/agent-trace.html`
(Shot D source) · `docs/demo/clips/*.mp4` (auto clips) · `docs/demo/captions.srt` · `docs/demo/shots/*.png`.

---

## 0. Status — what's done vs. what's left

**✅ Done for you (no action):**
- `docs/demo/clips/C2-dashboard.mp4` (14s, Shot F) — slow pan of live `/dashboard`
- `docs/demo/clips/C3-audit.mp4` (16s, Shot G; also usable for Shot E) — slow pan of live `/audit/!10`
- `docs/demo/clips/C6-rubric.mp4` (30s, Shot H) — slow scroll of `rubric/v1.yaml`
- `docs/demo/agent-trace.html` — the Shot D trace (real captured MCP log, self-animating)
- `docs/demo/captions.srt` — 30 caption cues timed to the script
- `docs/demo/shots/*.png` — the stills behind the auto clips

**📹 Left for you (this doc):**
1. Record **C1** (trace), **C4** (secret diff), **C5** (verdict comment) — silent.
2. Record the **voiceover**.
3. **Assemble** + caption + **upload Public** + paste the URL.

> Only C4 and C5 need anything special (a GitLab login). C1 is a local file. Budget ~20 min total.

---

## 1. One-time setup

- **Screen recorder:** OBS Studio → *Settings ▸ Video*: Base & Output **1920×1080**, **30 or 60 fps**.
  Add a **Window Capture** source on your browser.
- **Browser:** maximized, **dark mode**, **bookmarks bar hidden** (Ctrl+Shift+B), zoom **100–110%**.
- **Record silent** (no mic — the voiceover is separate). Record each clip **~3–5s longer** than its target.
- **Save** recordings into `docs\demo\clips\` as `C1-trace.mp4`, `C4-gitlab-diff.mp4`, `C5-gitlab-comment.mp4`.
- **Pre-record verify (30s):** open `https://mr-sentinel-webhook-n6oitfxdra-uc.a.run.app/audit/sgharlow/governance-demo-app/10`
  and confirm it still reads **block / 0.0 / no-secrets-in-diff**. (Hero MR `!10` is intentionally pinned there.)

---

## 2. Record the three clips

> ⚡ **Scripted option (no OBS needed):** `scripts\record-clips.ps1` captures each clip with ffmpeg's
> screen grabber. Same script for rehearsal and the real take:
> `.\scripts\record-clips.ps1 -Clip C1 -Test` (→ `C1-trace-TEST.mp4`) then drop `-Test` for the real one;
> `-Clip all` does C1→C4→C5 in order; `-AutoKey` also presses F11/R/Page-Down for you. It opens the
> surface, counts you in, then records the clip's duration to `docs\demo\clips\`. The manual OBS steps
> below are the fallback / reference for what to do on screen during each recording.

### 🎬 C1 — agent loop / GitLab MCP trace · Shot D · ~16s ⭐ (the eligibility shot)
1. Open **`docs\demo\agent-trace.html`** in your browser (double-click, or Ctrl+O). Press **F11** (full-screen).
2. It auto-plays a ~11s log reveal, then holds. Press **`R`** to replay it cleanly.
3. **Start OBS**, press **`R`**, and let all seven lines reveal — especially the three
   **`agent tool-call [GitLab MCP] -> get_merge_request / …_diffs / …_pipelines`** lines — then the red
   `block` verdict and the green footer line. Hold ~2s. **Stop.**
4. *Why it matters:* this is the on-screen proof all three required techs run at runtime. The content is the
   **real** captured Cloud Run log (rev `00017-d54`, MR `!9`).
- **Narration (Shot D):** *"Read the log — this is the agent running. 'ADK evaluate, via GitLab MCP': it spins
  up GitLab's own MCP server and calls it directly — get-merge-request, get-merge-request-diffs, list-pipelines,
  each one going through MCP. It hands all that to Gemini, on Vertex AI, which judges the diff against fifteen
  rules at once and records a structured verdict. Every MCP call logged and replayable — about thirty seconds
  end to end."*

### 🎬 C4 — the secret diff · Shots A + B · ~20s · ⚠️ MUST BE LOGGED IN
> The GitLab page is **sign-in-walled** when logged out (verified — anon shows only nav + a sign-in prompt),
> so the diff won't render unless you're signed in.
1. **Sign in** to gitlab.com (your account).
2. Go to **`https://gitlab.com/sgharlow/governance-demo-app/-/merge_requests/10/diffs`** . Dismiss any cookie
   banner. Wait for the diff to fully render.
3. **Start OBS.** Ensure **`.env.production`** is expanded; slow-scroll so the secret lines are clearly on
   screen — `DATABASE_URL`, `JWT_SECRET`, `STRIPE_SECRET_KEY`, **`AWS_ACCESS_KEY_ID`**. **Pause ~1s on the
   AWS key line.** **Stop.**
- **Narration (Shots A + B):** *"Friday, four-fifty PM. A merge request lands — 'add the production env file.'
  The reviewer's tired, with eight more in the queue. Inside this diff: a database password, a JWT secret, a
  live Stripe key, an AWS access key — everything policy says must never hit the repo. This is how secrets
  ship. MR Sentinel is the reviewer that never gets tired."*

### 🎬 C5 — the verdict comment · Shot E · ~26s · LOGGED IN (OPTIONAL)
1. Same login. Go to **`https://gitlab.com/sgharlow/governance-demo-app/-/merge_requests/10`** (Overview).
2. Scroll to the **MR Sentinel** comment. **Start OBS** and slowly pan:
   verdict badge (**block**) → **score 0.0** → cited **`no-secrets-in-diff`** evidence + the
   **SOC 2 / ISO 27001 / OWASP** control line → the **linked remediation issue** → the **`blocked-compliance`**
   label in the right sidebar. **Stop.**
- **Narration (Shot E):** *"And here's what it leaves on the merge request that started this. Verdict: block.
  Score: zero out of ten. It cites no-secrets-in-diff by rule ID — mapped to SOC 2, ISO 27001, OWASP — quotes
  the exact lines, opens a remediation issue with a checklist, and labels it blocked-compliance so the merge
  button is one step further away. Every action ties back to a named control."*
- **⏭️ Skip option:** don't want to film GitLab's comment? Use the auto-built **`clips\C3-audit.mp4`** for
  Shot E — it shows the same verdict, score, failing rule, and control mappings on our own public page.

### Shot C (the handoff, ~10s) has no dedicated clip
Narrate it over the **tail of C4 → head of C1** (the cut from the diff to the trace):
*"The moment an MR opens, MR Sentinel — a Google Agent Development Kit agent on Cloud Run — wakes up. Watch it
actually run."* In the edit, hold the last frame of C4 for ~2s under this line, or let it ride the first
seconds of C1.

---

## 3. Record the voiceover
Read the **[SAY]** lines top-to-bottom from `docs/recording-teleprompter.md` (or the inline narration above).
- **Your voice:** any decent mic + Audacity. Quiet room, ~15 cm off-axis, record a 10s room-tone pad first.
- **AI voice (allowed):** paste the lines into **ElevenLabs** or **Descript**, one consistent voice, export `vo.wav`.
- Target **~-16 LUFS**, no clipping. **Check the audio first** — judges forgive a rough picture, not bad sound.

---

## 4. Assemble (ffmpeg — all clips are already 1920×1080/30fps)
```bash
cd docs/demo/clips
# order to the script:  A/B → D → E → F → G → H
printf "file '%s'\n" C4-gitlab-diff.mp4 C1-trace.mp4 C5-gitlab-comment.mp4 C2-dashboard.mp4 C3-audit.mp4 C6-rubric.mp4 > list.txt
#   (using the skip option? replace C5-gitlab-comment.mp4 above with C3-audit.mp4 and drop the later C3)
ffmpeg -f concat -safe 0 -i list.txt -c:v libx264 -pix_fmt yuv420p -r 30 -an silent.mp4
ffmpeg -i silent.mp4 -i ../vo.wav -c:v copy -c:a aac -shortest demo-final.mp4
```
Add the 3–5s end card from `recording-teleprompter.md` at the end (optional).

**Running-time check:** C4 20 + C1 16 + C5 26 + C2 14 + C3 16 + C6 30 + end 8 ≈ **2:10**. If looser, trim C5
and C6 first. **Hard cap 3:00.**

---

## 5. Captions
- **Burn in:**
  `ffmpeg -i demo-final.mp4 -vf "subtitles=../captions.srt:force_style='FontName=DejaVu Sans,FontSize=22,BorderStyle=3,OutlineColour=&H80000000'" -c:a copy demo-captioned.mp4`
- **Or** upload `captions.srt` as a sidecar on YouTube (Subtitles ▸ Upload) — keeps the picture clean.
- The SRT is timed to the script's pacing; if your VO drifts, nudge cues in Descript/Aegisub (most tools auto-align).

---

## 6. Upload + propagate
1. **YouTube → Public** (rules require "publicly visible"; **not** Unlisted/Private). Confirm playback ≤ 3:00.
2. Title / description / tags / chapters: paste from `docs/youtube-metadata.md`.
3. Put the new URL into: the **Devpost submission form**, `README.md` (top banner), and
   `docs/devpost-submission.md` (Links table + asset checklist).
4. **Gallery screenshots (5):** re-grab from the recorded surfaces (see `docs/screenshots/CAPTURE-GUIDE.md`) —
   especially **`05-agent-loop`** = the trace (must show the GitLab MCP tool-call lines). The stills in
   `docs/demo/shots/` are a starting point.

---

## 7. Post-record cleanup (run once, AFTER all recording)
Recording fires real evaluations on the demo repo, which leave throwaway artifacts. From **WSL**:
```bash
bash scripts/cleanup-demo-artifacts.sh          # closes dup follow-up issues + deletes marker files
```
Then re-confirm hero `!10` is still **block / 0.0** at `/audit/sgharlow/governance-demo-app/10`.

---

## Final checklist
- [ ] C1 trace recorded (the three `[GitLab MCP] ->` lines visible)
- [ ] C4 secret diff recorded (logged in; AWS key visible)
- [ ] C5 verdict comment recorded (logged in) **or** using `C3-audit.mp4` for Shot E
- [ ] Voiceover recorded, audio checked (~-16 LUFS)
- [ ] Assembled, captioned, **< 3:00**
- [ ] Uploaded **Public**; URL in Devpost + README + devpost-submission.md
- [ ] 5 gallery screenshots updated (esp. the MCP trace)
- [ ] `cleanup-demo-artifacts.sh` run; hero `!10` still block/0.0
