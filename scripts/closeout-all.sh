#!/usr/bin/env bash
# closeout-all.sh — run the pre-recording PREP + VERIFY chain back-to-back, in one
# WSL invocation, so you don't call each script by hand.
#
# Chains, in order:
#   [1/3] docs/closeout-runbook.sh   preflight + smoke + latency capture + Shot-5 log
#                                    strings + issue audit (SEED=1 also seeds v2 MRs)
#   [2/3] scripts/audit-issues.sh    list issues + the label they carry
#   [3/3] scripts/demo-capture.sh check   recording-readiness + the tab list
#
# Pass-through flags (env vars inherited by the child scripts):
#   SEED=1   also run the v2 archetype seed (fattens the dashboard) — MUTATES the demo repo
#   SQL=1    also run the Cloud SQL row-count phase
# e.g.:  SEED=1 bash scripts/closeout-all.sh
#
# Deliberately NOT in this chain (they belong to other phases — see
# docs/recording-runbook.md):
#   * scripts/demo-capture.sh fire     -> recording time (Shot 5), run live in a side pane
#   * scripts/verify-tool-logging.sh   -> one-time deploy check (already verified)
#   * scripts/cleanup-demo-artifacts.sh-> AFTER recording
#
# RUN FROM WSL (gcloud is Norton-blocked elsewhere).
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || { echo "FATAL: cannot cd to repo root"; exit 1; }

run() {  # run "<label>" <cmd...> — never aborts the chain; records pass/non-zero
  local label="$1"; shift
  printf '\n############################################################\n'
  printf '# %s\n' "$label"
  printf '############################################################\n'
  if "$@"; then
    printf '\n>>> %s — done\n' "$label"
  else
    printf '\n>>> %s — returned non-zero (continuing; review output above)\n' "$label"
  fi
}

echo "closeout-all starting — SEED=${SEED:-0}  SQL=${SQL:-0}"

run "[1/3] batched gcloud closeout (preflight, smoke, latency, Shot-5 logs, issues)" bash docs/closeout-runbook.sh
run "[2/3] issue + label audit" bash scripts/audit-issues.sh
run "[3/3] recording-readiness check + tab list" bash scripts/demo-capture.sh check

printf '\n############################################################\n'
printf '# closeout-all complete\n'
printf '############################################################\n'
echo "Artifacts: docs/closeout-<today>/  (CLOSEOUT-SUMMARY.md, 03-latency-results.txt, ...)"
echo "Next: use 03-latency-results.txt + the dashboard MR count for the doc refresh,"
echo "then continue with Phase B/C in docs/recording-runbook.md."
