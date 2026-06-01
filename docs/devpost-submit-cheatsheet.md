# Devpost submit-day cheat-sheet

One-screen reference. Long-form field text lives in [`devpost-submission.md`](devpost-submission.md);
this is the index + the bits that are easy to fumble. **Deadline: June 11, 2026 —
14:00 PT hard / target 12:00 PT.**

## Before you open the form
- [ ] Final video uploaded to **YouTube → Unlisted**, URL copied
- [ ] URL pasted into the `devpost-submission.md` Links table (Demo video row)
- [ ] 5 gallery screenshots ready in `docs/screenshots/` (1920×1080 PNG)
- [ ] `bash scripts/demo-capture.sh` → all green (live demo still up)

## Fill the form in this order
1. **Project name:** `MR Sentinel`
2. **Tagline:** `An AI governance agent for merge requests — applies a written compliance rubric in 20 seconds.`
3. **Body fields** — paste each from `devpost-submission.md`:
   - "What it does" · "How we built it" · "Challenges" · "Accomplishments" · "What we learned" · "What's next"
   - If there's a "how does it fit the judging criteria" box → paste the **Judging-criteria mapping** block.
4. **Track:** select **GitLab**.
5. **Built with** (paste these tags; ~15 cap):
   ```
   google-cloud, vertex-ai, gemini, cloud-run, cloud-sql, secret-manager,
   python, fastapi, postgresql, gitlab, docker, github-actions, yaml, mit-license
   ```
6. **Links** — paste from the `devpost-submission.md` Links table:
   - GitHub `https://github.com/sgharlow/mr-sentinel`
   - Live dashboard `https://mr-sentinel-webhook-n6oitfxdra-uc.a.run.app/dashboard`
   - Sample audit `https://mr-sentinel-webhook-n6oitfxdra-uc.a.run.app/audit/sgharlow/governance-demo-app/10`
   - Demo GitLab repo `https://gitlab.com/sgharlow/governance-demo-app`
7. **Media:** YouTube URL in the video field; upload the 5 screenshots; thumbnail
   = `docs/assets/devpost-thumbnail.png` (1280×720) if a thumbnail field exists.
8. **Read-through** the rendered preview once — fix anything that wraps badly or any broken link.
9. **Submit** before 12:00 PT.

## Don't forget (the fumble list)
- Track = **GitLab** (not the generic track).
- Video must be **Unlisted or Public**, not Private (judges can't open Private).
- License is MIT and already detectable in the repo About — no action.
- Solo submission: team = `sgharlow` only.
- All AI is Google-only (Gemini/Vertex) — matches the rules; nothing to disclose.
