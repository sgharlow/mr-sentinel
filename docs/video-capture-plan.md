# Video capture plan — getting the screen clips to narrate over

Pairs with `docs/recording-teleprompter.md` (the script) and `docs/youtube-metadata.md`.
**Production model:** capture **silent** screen clips → record the **voiceover** separately
against the teleprompter → **stitch** (clips + VO + captions) under 3:00.

## Decision: hybrid capture (proven 2026-06-10)
Verified on this box: **Playwright navigates + screenshots our live Cloud Run pages cleanly**
(`/dashboard`, `/audit`). So:
- **Automate** the surfaces we control — they're server-rendered, public, no auth/banners/JS-framework.
- **Manual-capture** the third-party surfaces (GitLab MR, GitHub rubric) — they're the "real running
  app" money shots anyway and dodge the auth/banner/cursor problems.
- **Render the terminal trace as HTML** — a browser can't record a terminal; an HTML page showing the
  **real** log lines can. (Built: `docs/demo/agent-trace.html`.)

> **Run automated capture from WSL.** Norton doesn't MITM WSL traffic, so Playwright won't hit the
> intermittent connection resets it gets under Norton on the Windows side.

---

## The 6 clips (mapped to teleprompter shots)

| Clip | Shots | Surface | Method | ~Dur | Notes |
|------|-------|---------|--------|------|-------|
| **C1 trace** | D | `docs/demo/agent-trace.html` (real logs) | **Automated** (or screenshot-scroll) | 32s | the eligibility shot |
| **C2 dashboard** | F | `/dashboard` | **Automated** | 14s | scroll the verdict distribution + top rules |
| **C3 audit** | E-alt, G | `/audit/.../10` | **Automated** | 16s | scroll rule outcomes + control_mapping |
| **C4 gitlab-diff** | A, B | GitLab MR `!10` Changes | **Manual (OBS)** | 20s | the `.env.production` secret diff — the hook |
| **C5 gitlab-comment** | E | GitLab MR `!10` comment | **Manual (OBS, logged-in)** *or fold into C3* | 26s | notes API is 401 anon → may not render logged-out |
| **C6 rubric** | H | GitHub `rubric/v1.yaml` | **Manual (OBS)** or automated | 10s | scroll to `no-secrets-in-diff` control_mapping |

**If you want zero manual steps:** drop C4/C5/C6 to our surfaces — the cold-open secret can be shown
from the `/audit/.../10` page (it lists the detected secrets + controls), and the verdict from the same
page. You lose the visceral GitLab diff, but the whole video becomes automatable. Recommended only if
recording time is tight; the GitLab diff is a strong hook worth 20s of manual capture.

---

## Method A — Automated (our surfaces + trace-HTML)

Two reliable sub-options; pick per clip:

**A1 — Screenshot + ffmpeg motion (rock-solid).** Take a full-page PNG of each surface (proven), then
let ffmpeg pan/scroll it for motion. No live-video dependency, deterministic, looks like "scrolling the
app."
```bash
# capture (WSL or Windows): full-page screenshots via the harness
python scripts/capture_clips.py            # writes docs/demo/shots/*.png  (+ tries webm)
# motion from a tall screenshot (example: scroll C2 dashboard over 14s):
ffmpeg -loop 1 -i docs/demo/shots/dashboard.png -vf \
 "scale=1920:-1,crop=1080:1920:0:'min(ih-1920,(ih-1920)*t/14)'" -t 14 -r 30 clips/C2.mp4
```

**A2 — Live webm (more "alive," less certain).** The harness opens each page in a real browser context
with `record_video`, injects a moving cursor + element highlight, scrolls, and writes a `.webm`. Run it
in **WSL** (`xvfb-run` headed for cursor visibility). If `record_video` isn't available in your install,
fall back to A1.

The harness (`scripts/capture_clips.py`) is provided and does both: always writes screenshots; attempts
webm. It injects a visible cursor dot + a highlight outline so the eye is led (Playwright video has no OS
cursor).

## Method B — Manual capture (third-party surfaces)
**OBS Studio**, 1920×1080/60fps, capture the browser window, dark mode, bookmarks hidden.
- **C4 — GitLab MR `!10` → Changes tab.** Expand `.env.production`; slow-scroll past the secret lines.
- **C5 — GitLab MR `!10` → Overview.** Scroll to the **MR Sentinel** comment; pan badge → evidence →
  linked issue → `blocked-compliance` label. *(Be logged in — the comment may not render anonymously.)*
- **C6 — GitHub `rubric/v1.yaml`.** Scroll to the `no-secrets-in-diff` rule, control_mapping on screen.
Record ~5s longer than each shot for trim slack. Dismiss any cookie banner before you start.

## Shot D — the trace clip (C1)
`docs/demo/agent-trace.html` renders the **real** captured trace (from a live `!9` fire, including the
new per-tool lines `agent tool-call [GitLab MCP] -> get_merge_request_diffs`). It self-types/scrolls on
load. Capture it like any page (harness or OBS). It's honest — real log content — and looks clean.
**Re-stage a fresh trace right before recording** (logs are not needed for the HTML, but keep the lines
current): `bash scripts/demo-capture.sh fire 9` then refresh the page if you wire it to live logs; the
committed HTML already embeds a real captured trace.

---

## Stitch (clips + VO + captions)
1. Normalize every clip to 1920×1080 / 30fps / same codec:
   `for f in clips/*; do ffmpeg -i "$f" -vf scale=1920:1080 -r 30 -c:v libx264 -pix_fmt yuv420p norm/$(basename "$f" | sed 's/\..*/.mp4/'); done`
2. Concat in script order (A→I): `printf "file '%s'\n" norm/C1.mp4 norm/C4.mp4 … > list.txt && ffmpeg -f concat -safe 0 -i list.txt -c copy silent.mp4`
   *(order the clips to the shot sequence: C4(A,B)→C1(D)→C5/C3(E)→C2(F)→C3(G)→C6(H)→end card.)*
3. Lay the VO over it: `ffmpeg -i silent.mp4 -i vo.wav -c:v copy -c:a aac -shortest demo.mp4`
4. Burn captions (optional, satisfies the English-subtitles rule): from an SRT of the [SAY] lines.
5. Trim to **< 3:00**. Add the 3–5s end card.

## Gallery screenshots (submission needs 5)
The harness writes them too (full-page PNGs of MR comment, dashboard, audit, rubric, and the trace) →
`docs/demo/shots/`. **Re-grab `05-agent-loop` = the trace** so it shows the MCP calls.

---

## Reliability checklist
- [ ] Run automated capture from **WSL** (Norton dodge).
- [ ] Be **logged in** for the GitLab comment clip (C5), or fold the verdict into the audit page (C3).
- [ ] Dismiss cookie/consent banners before manual clips.
- [ ] Dark mode, bookmarks bar hidden, 1920×1080 everywhere for clean concat.
- [ ] Final video **Public** on YouTube, **< 3:00**.
