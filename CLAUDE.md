# mr-sentinel — Claude Code Context

This repo is the MR Sentinel hackathon project (Google Cloud Rapid Agent, GitLab track). FastAPI on Cloud Run + Vertex AI Gemini 2.5 Flash + Cloud SQL Postgres. Devpost submit cliff: 2026-06-11 12:00 PT.

## Lane awareness (parallel Claude Code sessions)

This repo is configured for parallel Claude Code sessions via the pattern in `docs/2026-05-22-parallel-agent-workflow-design.md`. Your lane is `$LANE` — check it at session start:

```bash
echo $LANE
```

If `$LANE` is unset, you are in Steve's main checkout. You have full ownership and act as the merge gate.

If `$LANE` is set, you are in a worktree on branch `lane/$LANE`. Before any `Edit` or `Write`:

1. Confirm the target file is owned by your lane in `.agent-state/OWNERSHIP.md`.
2. If it is not, either (a) tell the user and stop — preferred — or (b) claim a lock by writing `$LANE` into `.agent-state/locks/<owning-lane>.lock`, make the edit, then delete the lock when done.

The `lane-guard.sh` PreToolUse hook will surface a warning in your response context when a cross-lane edit is attempted without a lock. The warning is not a block — it is information for you and the user.

## Task list

Read `.agent-state/tasks.json` at session start. Find a task in your lane with `status: pending`. Claim it by setting `owner: "$LANE"` and `status: "in_progress"`. Mark `status: "completed"` when done. Do not claim tasks marked `blocked` — their dependencies are not yet met.

## Useful repo facts

- Python 3 + FastAPI; tests via pytest under `tests/`.
- Deployed to Cloud Run (image `webhook:0.6.0`, app v0.4.0 at time of writing).
- Vertex AI Gemini 2.5 Flash for MR evaluation (see `app/agent_runner.py` + `rubric/v1.yaml`).
- Demo data is seeded via `scripts/seed-*.sh` — these require `gcloud`, which is Norton-blocked on Windows Git Bash. Run from WSL.
- Live dashboard at https://mr-sentinel-webhook-n6oitfxdra-uc.a.run.app/dashboard.

## Out of scope reminders

- No MCP message bus between agents — coordination is via `.agent-state/tasks.json`, not messaging.
- No automated merge — Steve is the merge gate.
- No per-worktree DB — single dev DB is shared.
