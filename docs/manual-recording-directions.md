# Manual recording — exact directions (only 3 pieces)

Everything else is **already produced** for you (see "Done for you" below). You only need to
screen-record **three** clips. Record them **silent** (no mic — narration is separate against
`docs/recording-teleprompter.md`). Target the durations shown; the whole video stays **under 3:00**.

## One-time setup (all three clips)
- **OBS Studio** → Settings ▶ Video: Base & Output 1920×1080, 30 or 60 fps.
- Add a **Window Capture** source on your browser. Browser **maximized**, **dark mode**, **bookmarks bar hidden** (Ctrl+Shift+B), zoom **100–110%**.
- Record each clip **~3–5s longer** than its target for trim slack.
- Save clips into `docs\demo\clips\` as `C1-trace.mp4`, `C4-gitlab-diff.mp4`, `C5-gitlab-comment.mp4`.

---

## CLIP C1 — the agent loop / GitLab MCP trace  ·  Shot D  ·  ~16s  ⭐ (the eligibility shot)
1. Open **`docs\demo\agent-trace.html`** in your browser (double-click the file, or Ctrl+O). Press **F11** for full-screen.
2. It auto-plays the log reveal (~11s) then holds. **Press `R`** to restart it cleanly.
3. **Start OBS recording**, press **`R`**, and let all seven lines reveal — especially the three
   `agent tool-call [GitLab MCP] -> get_merge_request / …_diffs / …_pipelines` lines — then the red
   `block` verdict and the green footer. Hold ~2s. **Stop.**
4. This is the proof all three required techs run at runtime. The content is the **real** captured log.
- **Narrate:** Shot D.

## CLIP C4 — the secret diff  ·  Shots A + B  ·  ~20s  (GitLab — **must be logged in**)
> The diff does **not** render logged-out (sign-in wall), so log into gitlab.com first.
1. **Sign in** to gitlab.com (your account).
2. Go to **`https://gitlab.com/sgharlow/governance-demo-app/-/merge_requests/10/diffs`** . Dismiss any cookie banner. Wait for the diff to fully render.
3. **Start recording.** Make sure the **`.env.production`** file is expanded; slow-scroll so the secret lines are clearly visible — `DATABASE_URL`, `JWT_SECRET`, `STRIPE_SECRET_KEY`, **`AWS_ACCESS_KEY_ID`**. **Pause ~1s on the AWS key line.** **Stop.**
- **Narrate:** Shots A (cold open) + B (the stakes).

## CLIP C5 — the verdict comment  ·  Shot E  ·  ~26s  (GitLab — **must be logged in**)
1. Same login. Go to **`https://gitlab.com/sgharlow/governance-demo-app/-/merge_requests/10`** (Overview/Activity).
2. Scroll to the **MR Sentinel** comment. **Start recording**, then slowly pan:
   verdict badge (**block**) → the **score 0.0** → the cited **`no-secrets-in-diff`** evidence + the **SOC 2 / ISO 27001 / OWASP** control line → the **linked remediation issue** → the **`blocked-compliance`** label in the right sidebar. **Stop.**
- **Narrate:** Shot E.
- **Don't want to film GitLab's comment?** Skip C5 — the auto-built **`clips\C3-audit.mp4`** already shows the same verdict, score, failing rule, and control mappings on our own page. Use it for Shot E.

---

## Done for you (no recording needed)
| File | Shot | What it is |
|------|------|-----------|
| `docs\demo\clips\C2-dashboard.mp4` (14s) | F | slow pan of the live `/dashboard` |
| `docs\demo\clips\C3-audit.mp4` (16s) | G (and E-alt) | slow pan of the live `/audit/!10` |
| `docs\demo\clips\C6-rubric.mp4` (30s) | H | slow scroll of `rubric/v1.yaml` (control_mapping) |
| `docs\demo\shots\{dashboard,audit-10,rubric}.png` | — | the stills behind those clips (and gallery use) |
| `docs\demo\agent-trace.html` | D | the trace you record as C1 |

---

## Assemble (after you record C1, C4, C5 and the voiceover)
Put clips in **script order**, normalize, concat, lay the VO, caption, keep **< 3:00**:
```bash
cd docs/demo/clips
# 1) order to the teleprompter: A/B → D → E → F → G → H
printf "file '%s'\n" C4-gitlab-diff.mp4 C1-trace.mp4 C5-gitlab-comment.mp4 C2-dashboard.mp4 C3-audit.mp4 C6-rubric.mp4 > list.txt
# 2) concat (all are already 1920x1080/30fps; re-encode to be safe)
ffmpeg -f concat -safe 0 -i list.txt -c:v libx264 -pix_fmt yuv420p -r 30 -an silent.mp4
# 3) lay your voiceover over it
ffmpeg -i silent.mp4 -i ../vo.wav -c:v copy -c:a aac -shortest ../demo-final.mp4
```
Add a 3–5s end card (in `recording-teleprompter.md`) and optional burned captions. **Upload Public.**

**Running time check:** C4 20 + C1 16 + C5 26 + C2 14 + C3 16 + C6 30 + end 8 ≈ **2:10** — comfortably under 3:00. If you film looser, trim C5 and C6 first.
