# Devpost submit-day cheat-sheet

One-screen reference. Long-form field text lives in [`devpost-submission.md`](devpost-submission.md);
this is the index + the bits that are easy to fumble. **Deadline: June 11, 2026 —
14:00 PT hard / target 12:00 PT.**

> ✅ **SUBMITTED to Devpost (GitLab track) 2026-05-31.** Devpost allows edits until the
> deadline, so the checklist below stays useful for any pre-deadline updates.

## Before you open the form
- [x] Final video uploaded to **YouTube** — https://youtu.be/0IlB2KJsJ4A
- [x] URL pasted into the `devpost-submission.md` Links table (Demo video row)
- [x] Gallery screenshots in `docs/screenshots/` (7 captured; JPG ~1900×960)
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
9. ✅ **SUBMITTED** — GitLab track. Edits remain open until June 11, 2026 — 17:00 EDT (14:00 PT).

## Don't forget (the fumble list)
- Track = **GitLab** (not the generic track).
- Video must be set to **Public** — the rules say "publicly visible." (Unlisted *may* be read as non-compliant; don't risk it. Never Private.)
- License is MIT and already detectable in the repo About — no action.
- Solo submission: team = `sgharlow` only.
- All AI is Google-only (Gemini/Vertex) — matches the rules; nothing to disclose.
