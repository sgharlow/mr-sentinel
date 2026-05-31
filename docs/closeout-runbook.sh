#!/usr/bin/env bash
# =============================================================================
# MR Sentinel — WSL CLOSEOUT RUNBOOK
# =============================================================================
# Batches every gcloud-gated closeout task into ONE interactive run, writing all
# results to files under docs/closeout-<date>/ so a Claude Code session on Windows
# can read them back (the repo is the same bytes at /mnt/c/... and C:\...).
#
# WHY THIS MUST RUN INTERACTIVELY IN WSL — NOT VIA CLAUDE/wsl.exe:
#   1. Norton's TLS MITM blocks gcloud's network calls from Windows Git Bash.
#      WSL traffic is not intercepted, so gcloud works here.
#   2. When Claude drives gcloud through `wsl.exe -e bash -c`, command
#      substitution `TOKEN=$(gcloud ...)` captures ZERO bytes (TTY/fork quirk in
#      gcloud's bundled Python). The seed scripts use that pattern → empty token
#      → silent 401s. In a real interactive WSL terminal this works fine.
#
#   ==> Open a WSL Ubuntu terminal and run:
#         cd /mnt/c/Users/$USER/CascadeProjects/mr-sentinel   # adjust if needed
#         bash docs/closeout-runbook.sh
#
# MONITORING FROM CLAUDE (Windows side): point the Read tool at
#   docs/closeout-<date>/run.log  (tail it) and the individual *.txt result files.
#
# PHASE TOGGLES (default: read-only/safe phases ON; mutating/heavy phases OFF).
#   Override by exporting before running, e.g.:  SEED=1 SQL=1 bash docs/closeout-runbook.sh
SEED="${SEED:-0}"   # 1 = run seed-archetype-mrs-v2.sh (MUTATES the demo GitLab repo)
SQL="${SQL:-0}"     # 1 = Cloud SQL audit row count (spins the Cloud SQL Auth Proxy)
# Read-only phases (preflight, smoke, latency, log-strings, issue-audit) always run.
# =============================================================================

set -uo pipefail   # deliberately NOT -e: one failing phase must not abort the batch.

# ---- constants (verified live 2026-05-31) -----------------------------------
PROJECT="aicin-477004"
REGION="us-central1"
SERVICE="mr-sentinel-webhook"
BASE_URL="https://mr-sentinel-webhook-n6oitfxdra-uc.a.run.app"
GL_PROJECT="sgharlow/governance-demo-app"
GL_PROJECT_ENC="sgharlow%2Fgovernance-demo-app"
GL_TOKEN_SECRET="mr-sentinel-gitlab-token"
HERO_MR="10"
SEED_SCRIPT="scripts/seed-archetype-mrs-v2.sh"
SMOKE_SCRIPT="scripts/smoke-test.sh"

# ---- output dir + master log ------------------------------------------------
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT" || { echo "FATAL: cannot cd to repo root"; exit 1; }
DATE="$(date +%Y%m%d)"
OUT="docs/closeout-${DATE}"
mkdir -p "$OUT"
LOG="$OUT/run.log"
# Tee everything (stdout+stderr) to the log AND the terminal, so Claude can tail $LOG.
exec > >(tee -a "$LOG") 2>&1

hr()   { printf '\n========== %s ==========\n' "$1"; }
ok()   { printf '  [OK]   %s\n' "$1"; }
warn() { printf '  [WARN] %s\n' "$1"; }
fail() { printf '  [FAIL] %s\n' "$1"; }

echo "MR Sentinel closeout — $(date -u +%Y-%m-%dT%H:%M:%SZ) — output dir: $OUT"
echo "Phase toggles: SEED=$SEED  SQL=$SQL"

# =============================================================================
# PHASE 0 — PREFLIGHT (auth, project, service health)
# =============================================================================
hr "PHASE 0: preflight"
{
  echo "## whoami: $(whoami)"
  echo "## gcloud path: $(command -v gcloud || echo MISSING)"
  echo "## project (config): $(gcloud config get-value project 2>&1)"
  # Canonical auth check per the Norton memory: if this errors, you must re-auth.
  if gcloud auth print-access-token >/dev/null 2>&1; then
    ok "gcloud token refresh works"
    echo "## active account: $(gcloud auth list --filter=status:ACTIVE --format='value(account)' 2>&1)"
  else
    fail "gcloud token refresh FAILED — run 'gcloud auth login' (browser), then re-run this script."
    echo "## token error:"; gcloud auth print-access-token 2>&1 | head -5
  fi
  echo "## project set to expected ($PROJECT)? $([ "$(gcloud config get-value project 2>/dev/null)" = "$PROJECT" ] && echo yes || echo NO)"
} | tee "$OUT/00-preflight.txt"

# Service health via curl (WSL curl is not Norton-blocked).
if curl -fsS -m 20 "$BASE_URL/health" -o "$OUT/00-health.txt" 2>/dev/null; then
  ok "/health -> $(cat "$OUT/00-health.txt")"
else
  fail "/health unreachable — check 'gcloud run services describe $SERVICE --region=$REGION'"
fi

# =============================================================================
# PHASE 1 — SMOKE TEST
# =============================================================================
hr "PHASE 1: smoke test"
if [ -x "$SMOKE_SCRIPT" ] || [ -f "$SMOKE_SCRIPT" ]; then
  bash "$SMOKE_SCRIPT" 2>&1 | tee "$OUT/01-smoke.txt"
  ok "smoke-test.sh ran (review $OUT/01-smoke.txt for the 4 checks)"
else
  warn "$SMOKE_SCRIPT not found — skipping"
fi

# =============================================================================
# PHASE 2 — V2 ARCHETYPE SEED  (MUTATING — opt-in via SEED=1)
# =============================================================================
hr "PHASE 2: v2 archetype seed (SEED=$SEED)"
if [ "$SEED" = "1" ]; then
  if [ -f "$SEED_SCRIPT" ]; then
    echo "Running $SEED_SCRIPT — this opens new MRs on $GL_PROJECT and pushes to GitLab."
    bash "$SEED_SCRIPT" 2>&1 | tee "$OUT/02-seed.txt"
    ok "seed ran — let webhooks settle ~60s, then the dashboard count will climb toward 12-14."
    echo "NOTE: re-record demo numbers AFTER this; hero MR !$HERO_MR sha8 may change."
  else
    fail "$SEED_SCRIPT not found"
  fi
else
  warn "skipped (SEED!=1). To seed v2 archetypes: SEED=1 bash docs/closeout-runbook.sh"
fi

# =============================================================================
# PHASE 3 — LATENCY CAPTURE  (replaces the asserted "~30s" with measured p50/p95)
# =============================================================================
hr "PHASE 3: latency capture (last 30 days)"
LAT_RAW="/tmp/mr-sentinel-logs.json"
gcloud logging read '
  resource.type="cloud_run_revision"
  AND resource.labels.service_name="'"$SERVICE"'"
  AND (textPayload:"received gitlab event"
       OR textPayload:"evaluation: score="
       OR textPayload:"comment note_id=")
  AND timestamp>="'"$(date -u -d '30 days ago' +%Y-%m-%dT%H:%M:%SZ)"'"
' --project="$PROJECT" --format=json --limit=5000 > "$LAT_RAW" 2>"$OUT/03-latency-fetch.err"
N_LOG="$(jq length "$LAT_RAW" 2>/dev/null || echo 0)"
echo "log entries pulled: $N_LOG"
cp "$LAT_RAW" "$OUT/03-latency-raw.json" 2>/dev/null || true

python3 - "$LAT_RAW" <<'PY' | tee "$OUT/03-latency-results.txt"
import json, re, sys
from datetime import datetime
with open(sys.argv[1]) as f:
    entries = json.load(f)
events = []
for e in entries:
    payload = e.get('textPayload', '') or ''
    ts = (e.get('timestamp', '') or '').replace('Z', '+00:00')
    if not ts: continue
    try: when = datetime.fromisoformat(ts)
    except ValueError: continue
    if re.search(r'received gitlab event kind=\S+ project=(\S+) mr_iid=(\d+)', payload):
        m = re.search(r'received gitlab event kind=\S+ project=(\S+) mr_iid=(\d+)', payload)
        events.append((when,'start',m.group(1),int(m.group(2))))
    elif re.search(r'evaluation: score=\S+ verdict=\S+ rules=\d+', payload):
        events.append((when,'gemini_done',None,None))
    elif re.search(r'comment note_id=\S+ on MR !(\d+)', payload):
        m = re.search(r'comment note_id=\S+ on MR !(\d+)', payload)
        events.append((when,'comment_posted',None,int(m.group(1))))
events.sort(key=lambda x: x[0])
open_starts=[]; dg=[]; dfull=[]
for when,kind,proj,iid in events:
    if kind=='start': open_starts.append((when,proj,iid))
    elif kind=='gemini_done' and open_starts:
        s=open_starts.pop(0); dg.append((when-s[0]).total_seconds())
    elif kind=='comment_posted':
        idx=next((i for i,s in enumerate(open_starts) if s[2]==iid), 0 if open_starts else None)
        if idx is not None:
            s=open_starts.pop(idx); dfull.append((when-s[0]).total_seconds())
def pct(xs,p):
    if not xs: return float('nan')
    xs=sorted(xs); k=int(round((p/100)*(len(xs)-1))); return xs[k]
print(f"sample size -- gemini-call legs: {len(dg)}")
print(f"sample size -- full-loop legs:   {len(dfull)}")
if dg:   print(f"gemini-eval latency (sec):  p50={pct(dg,50):.1f}  p95={pct(dg,95):.1f}  p99={pct(dg,99):.1f}  max={max(dg):.1f}")
if dfull:print(f"full-loop latency (sec):    p50={pct(dfull,50):.1f}  p95={pct(dfull,95):.1f}  p99={pct(dfull,99):.1f}  max={max(dfull):.1f}")
if not dfull and not dg:
    print("NO PAIRS FOUND — log wording may have drifted from the regex, or no MRs evaluated in 30d.")
    print("If SEED ran this session, the new evaluations are in here too — re-run after they settle.")
PY
ok "latency results -> $OUT/03-latency-results.txt (paste p50 into demo-script Shot 5 + README Status)"

# =============================================================================
# PHASE 4 — SHOT 5 LOG-STRING VERIFICATION (exact webhook log lines for hero MR)
# =============================================================================
hr "PHASE 4: Shot 5 log-string verification (MR !$HERO_MR)"
gcloud logging read '
  resource.type="cloud_run_revision"
  AND resource.labels.service_name="'"$SERVICE"'"
  AND timestamp>="'"$(date -u -d '30 days ago' +%Y-%m-%dT%H:%M:%SZ)"'"
' --project="$PROJECT" --format='value(timestamp, textPayload)' --limit=2000 \
  | grep -E "received gitlab event|using project override|get_merge_request|get_file_content|get_merge_request_diffs|get_latest_pipeline|list_vulnerability|evaluation: score=|created followup issue|comment note_id=" \
  > "$OUT/04-shot5-logstrings.txt" 2>"$OUT/04-shot5.err" || true
LINES="$(wc -l < "$OUT/04-shot5-logstrings.txt" 2>/dev/null || echo 0)"
echo "captured $LINES candidate log lines -> $OUT/04-shot5-logstrings.txt"
ok "Compare these EXACT strings against demo-script.md Shot 5 visual cues; update wording if drifted."

# =============================================================================
# PHASE 5 — LINKED-ISSUE AUDIT (one remediation issue per block verdict)
# =============================================================================
hr "PHASE 5: linked-issue audit (GitLab REST)"
# Pull the PAT from Secret Manager (direct stdout -> file; safe even via wsl.exe).
gcloud secrets versions access latest --secret="$GL_TOKEN_SECRET" --project="$PROJECT" \
  > /tmp/gl-pat.txt 2>"$OUT/05-issue.err"
GL_PAT="$(tr -d '\r\n' < /tmp/gl-pat.txt)"
if [ -n "$GL_PAT" ]; then
  # Issues opened by the agent carry the mr-sentinel label (per spec §5 / app/main.py).
  curl -fsS -m 30 -H "PRIVATE-TOKEN: $GL_PAT" \
    "https://gitlab.com/api/v4/projects/$GL_PROJECT_ENC/issues?labels=mr-sentinel&per_page=50" \
    | jq -r '.[] | "issue #\(.iid)  \(.title)  state=\(.state)  url=\(.web_url)"' \
    > "$OUT/05-linked-issues.txt" 2>>"$OUT/05-issue.err" || true
  echo "remediation issues found: $(wc -l < "$OUT/05-linked-issues.txt" 2>/dev/null || echo 0)"
  # Cross-check: which MRs are block verdicts (from dashboard) should each have an issue.
  ok "review $OUT/05-linked-issues.txt — expect 1 issue per block verdict (!6,!7,!9,!10,!11,!13)"
  rm -f /tmp/gl-pat.txt
else
  fail "could not read GitLab PAT from Secret Manager (see $OUT/05-issue.err)"
fi

# =============================================================================
# PHASE 6 — CLOUD SQL AUDIT ROW COUNT  (heavy — opt-in via SQL=1)
# =============================================================================
hr "PHASE 6: Cloud SQL audit row count (SQL=$SQL)"
if [ "$SQL" = "1" ]; then
  echo "Starting Cloud SQL Auth Proxy is environment-specific; document the connection here."
  echo "Manual: connect via proxy, then:"
  echo "  SELECT verdict, COUNT(*) FROM mr_scores GROUP BY verdict;"
  echo "Expected: block/warn/pass counts match the dashboard (currently 6/1/1, or higher post-seed)."
  warn "Phase 6 left as a documented manual step — fill $OUT/06-sql-rowcount.txt with the query output."
else
  warn "skipped (SQL!=1). The dashboard already reflects DB state, so this is optional verification."
fi

# =============================================================================
# SUMMARY — single file for Claude to read first
# =============================================================================
hr "SUMMARY"
SUMMARY="$OUT/CLOSEOUT-SUMMARY.md"
{
  echo "# MR Sentinel closeout summary — $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo
  echo "| Phase | Artifact | Status |"
  echo "|---|---|---|"
  echo "| 0 preflight | 00-preflight.txt / 00-health.txt | $([ -s "$OUT/00-health.txt" ] && echo 'health OK' || echo 'CHECK') |"
  echo "| 1 smoke | 01-smoke.txt | $([ -s "$OUT/01-smoke.txt" ] && echo 'ran' || echo 'skipped') |"
  echo "| 2 seed | 02-seed.txt | $([ "$SEED" = 1 ] && echo 'ran' || echo 'skipped (SEED=0)') |"
  echo "| 3 latency | 03-latency-results.txt | $([ -s "$OUT/03-latency-results.txt" ] && echo 'captured' || echo 'CHECK') |"
  echo "| 4 shot5 logs | 04-shot5-logstrings.txt | $([ -s "$OUT/04-shot5-logstrings.txt" ] && echo 'captured' || echo 'CHECK') |"
  echo "| 5 issue audit | 05-linked-issues.txt | $([ -s "$OUT/05-linked-issues.txt" ] && echo 'captured' || echo 'CHECK') |"
  echo "| 6 cloud sql | 06-sql-rowcount.txt | $([ "$SQL" = 1 ] && echo 'manual' || echo 'skipped (SQL=0)') |"
  echo
  echo "## Next actions for Claude (Windows session)"
  echo "1. Read 03-latency-results.txt -> patch demo-script.md Shot 5 + README Status with the full-loop p50."
  echo "2. Read 04-shot5-logstrings.txt -> reconcile Shot 5 visual cues against the real log wording."
  echo "3. Read 05-linked-issues.txt -> confirm one issue per block verdict; flag any missing."
  echo "4. If SEED ran: re-run the dashboard scrape and update demo-script Shot 7 + live-fire doc counts."
} | tee "$SUMMARY"

echo
ok "DONE. All artifacts in: $OUT/"
echo "Tell your Claude session: \"read $OUT/CLOSEOUT-SUMMARY.md and process the closeout results\""
