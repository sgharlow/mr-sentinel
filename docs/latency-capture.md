# MR Sentinel — evaluation latency capture

**Purpose:** Replace the demo-script's currently-asserted "~30 seconds end to end" claim with a real measurement over the last 30 days. Result lands in this file and gets cited from `README.md` and `docs/demo-script.md` Shot 5.

**Pre-req:** WSL terminal with `gcloud` authenticated and `python3` available. Cannot be run from Windows Git Bash — Norton's TLS interception breaks the gcloud calls (see [[feedback_norton_windows_tls_mitm]]).

---

## Run

Open an interactive WSL terminal. Paste both blocks; ~30 seconds total.

### Step 1 — pull the last 30 days of webhook + evaluation logs

```bash
gcloud logging read '
  resource.type="cloud_run_revision"
  AND resource.labels.service_name="mr-sentinel-webhook"
  AND (textPayload:"received gitlab event"
       OR textPayload:"evaluation: score="
       OR textPayload:"comment note_id=")
  AND timestamp>="'$(date -u -d '30 days ago' +%Y-%m-%dT%H:%M:%SZ)'"
' --project=aicin-477004 --format=json --limit=5000 \
  > /tmp/mr-sentinel-logs.json

echo "log entries pulled: $(jq length /tmp/mr-sentinel-logs.json)"
```

Expected: a few hundred to a few thousand entries depending on how many MRs were evaluated. If `jq length` is very low (<20), either the log filter is wrong or evaluations have not been firing — check `gcloud run services describe mr-sentinel-webhook --region=us-central1 --format='value(status.url)'` and `curl <url>/health`.

### Step 2 — pair start events with finish events and compute percentiles

```bash
python3 <<'PY'
import json, re, statistics
from datetime import datetime

with open('/tmp/mr-sentinel-logs.json') as f:
    entries = json.load(f)

# Each evaluation is bracketed by:
#   start:  "received gitlab event kind=... project=... mr_iid=N action=..."
#   finish: "evaluation: score=X verdict=Y rules=Z"  (Gemini done; the most useful endpoint)
# An optional later marker is "comment note_id=N on MR !K" (full agent loop done).
# We pair by (project, mr_iid) and take the next finish AFTER each start.

events = []
for e in entries:
    payload = e.get('textPayload', '') or ''
    ts = e.get('timestamp', '')
    if not ts:
        continue
    # Drop the trailing 'Z' or fractional seconds — fromisoformat handles either after small massage.
    ts = ts.replace('Z', '+00:00')
    try:
        when = datetime.fromisoformat(ts)
    except ValueError:
        continue

    m = re.search(r'received gitlab event kind=\S+ project=(\S+) mr_iid=(\d+)', payload)
    if m:
        events.append((when, 'start', m.group(1), int(m.group(2))))
        continue
    m = re.search(r'evaluation: score=\S+ verdict=\S+ rules=\d+', payload)
    if m:
        # The Gemini-eval-done log line doesn't carry the mr_iid, so we match against the most recent open start.
        events.append((when, 'gemini_done', None, None))
        continue
    m = re.search(r'comment note_id=\S+ on MR !(\d+)', payload)
    if m:
        events.append((when, 'comment_posted', None, int(m.group(1))))
        continue

events.sort(key=lambda x: x[0])

# Greedy pairing: each gemini_done / comment_posted consumes the earliest unmatched start
# whose mr_iid matches (for comment_posted) or any unmatched start (for gemini_done).
open_starts = []  # list of (when, project, mr_iid)
durs_gemini = []
durs_full = []

for when, kind, project, mr_iid in events:
    if kind == 'start':
        open_starts.append((when, project, mr_iid))
    elif kind == 'gemini_done' and open_starts:
        start_when, _, _ = open_starts.pop(0)
        durs_gemini.append((when - start_when).total_seconds())
    elif kind == 'comment_posted':
        # Match by mr_iid if possible, else FIFO.
        idx = next((i for i, s in enumerate(open_starts) if s[2] == mr_iid), 0 if open_starts else None)
        if idx is not None:
            start_when, _, _ = open_starts.pop(idx)
            durs_full.append((when - start_when).total_seconds())

def pct(xs, p):
    if not xs:
        return float('nan')
    xs = sorted(xs)
    k = int(round((p / 100) * (len(xs) - 1)))
    return xs[k]

print(f"sample size — gemini-call legs: {len(durs_gemini)}")
print(f"sample size — full-loop legs:   {len(durs_full)}")
if durs_gemini:
    print(f"gemini-eval latency (sec):  p50={pct(durs_gemini,50):.1f}  p95={pct(durs_gemini,95):.1f}  p99={pct(durs_gemini,99):.1f}  max={max(durs_gemini):.1f}")
if durs_full:
    print(f"full-loop latency (sec):    p50={pct(durs_full,50):.1f}  p95={pct(durs_full,95):.1f}  p99={pct(durs_full,99):.1f}  max={max(durs_full):.1f}")
PY
```

Expected output looks like:

```
sample size — gemini-call legs: 47
sample size — full-loop legs:   31
gemini-eval latency (sec):  p50=12.3  p95=22.1  p99=28.4  max=35.0
full-loop latency (sec):    p50=18.7  p95=29.2  p99=33.1  max=37.4
```

### Step 3 — paste numbers into the Results section below, commit, and update the demo script

After capture, edit the table in **Results** below with the actual values, then update:

- `docs/demo-script.md` Shot 5 narration "Thirty seconds end to end" → use the **full-loop p50** rounded to whole seconds. If p50 is markedly different from 30 (e.g., 18 or 42), reword to match.
- `README.md` Status section "Latency ~30s p50" → same full-loop p50.

---

## Results

> ⚠️ **These are the PRE-ADK (direct-Vertex + REST) numbers.** They were captured 2026-06-01, before the 2026-06-10 ADK + GitLab MCP migration. The current agentic ADK loop (multi-turn MCP tool calls) runs **~25–30s per evaluation** (observed live on rev `00016-45d`, MR !7/!9). Re-run this capture against the ADK path for a clean p50/p95 before citing latency as "current."

**Captured:** 2026-06-01 in WSL (post-SEED, `docs/closeout-20260531/03-latency-results.txt`)
**Window:** last 30 days ending 2026-06-01 (pre-ADK REST path)
**Sample size:** 19 full-loop legs / 144 Gemini-call legs

| Metric | p50 | p95 | p99 | max |
|--------|-----|-----|-----|-----|
| Gemini eval (start → "evaluation: score=" log) | 12.8s | ⚠️ artifact | ⚠️ artifact | ⚠️ artifact |
| **Full agent loop (start → comment posted)** | **19.7s** | **30.0s** | **33.4s** | **33.4s** |

**Use the full-loop row.** The "~30s" figure that lived in the README/demo for weeks turns out to be the **p95**, not the p50 — the real median is ~20s.

**⚠️ The Gemini-leg tail is a measurement artifact, not real latency.** The `evaluation: score=...` log line carries **no `mr_iid`**, so the aggregator pairs each Gemini-done event FIFO against the oldest unmatched start across the whole 30-day window. With 142 dones vs only 17 cleanly-matched starts, that pairs dones with stale starts → p95 1751s, p99 84517s (~23h). The p50 (10.6s) survives because most pairs are still adjacent. **Fix for a clean future capture:** add `mr_iid=` to the `evaluation: score=` log line in `app/agent_runner.py`, then pair the Gemini leg by iid the way the full loop already does. Not required for submission — the full-loop numbers are the citable ones.

**Demo-script narration update:** done — Shot 5 now says "about twenty seconds end to end." README Status + tagline updated to the measured p50/p95/p99.

### Notes

- If `comment_posted` count is much lower than `gemini_done` count, several evaluations finished but couldn't post (likely auth or rate-limit). Investigate before quoting full-loop p99.
- If p99 ≫ p50 (e.g., 60s vs 18s), some MRs hit Gemini cold-start or GitLab API timeouts. Worth a sentence in the demo script's edit-pass: "p50 ~Xs; p99 ~Ys when GitLab is being slow."
- Cloud Run scale-to-zero adds ~3-8s of cold-start to the first request after idle. If your sample has lots of one-off MRs spaced > 15 min apart, expect higher p50 than a sustained burst would show.

---

## Alternative: built-in Cloud Run request latency

The gcloud command above measures the *application-level* loop. For the *HTTP webhook latency* (which is sub-second because the handler 202s and dispatches to a BackgroundTask), use Cloud Monitoring:

```bash
gcloud monitoring time-series list \
  --filter='metric.type="run.googleapis.com/request_latencies" AND resource.labels.service_name="mr-sentinel-webhook"' \
  --interval-end-time=$(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --interval-start-time=$(date -u -d '30 days ago' +%Y-%m-%dT%H:%M:%SZ) \
  --project=aicin-477004 \
  --format='value(points[].value.distributionValue.mean)' \
  | head -5
```

This is the metric a judge browsing the Cloud Run console sees. It will report ~50-200ms because the webhook handler returns immediately. Cite this only if asked about webhook responsiveness — it's not the metric the demo's "30 seconds" claim refers to.
