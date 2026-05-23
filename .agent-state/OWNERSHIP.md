# Lane Ownership Map

This file is the human-readable counterpart to `ownership.json`. Both must stay in sync — the lane-guard hook reads the JSON, agents read this file.

## Lanes

| Lane | Branch | Owns (read+write) | Reads only |
|------|--------|-------------------|------------|
| `backend` | `lane/backend` | `app/main.py`, `app/gitlab_client.py`, `app/persistence.py`, `app/__init__.py`, `Dockerfile`, `Makefile`, `db/`, `scripts/cloud-run-deploy.sh`, `scripts/db-migrate.sh`, `scripts/gcp-bootstrap.sh`, `tests/test_gitlab_client.py`, `tests/test_webhook.py` | `docs/`, `scripts/` (read-only for non-owned), `rubric/` |
| `evaluator` | `lane/evaluator` | `app/agent_runner.py`, `rubric/`, `tests/test_agent_runner.py`, `tests/test_rubric.py` | rest of `app/` |
| `demo-data` | `lane/demo-data` | `scripts/seed-*.sh`, `scripts/gitlab-bootstrap.sh`, `scripts/test-override-live.sh`, `scripts/cleanup-override-verification.sh` | `app/` |
| `dashboard` | `lane/dashboard` | `app/dashboard.py`, `tests/test_dashboard.py` | `app/`, `db/` |
| `docs` | `lane/docs` | `docs/`, `README.md`, `mr-sentinel-hackathon-spec.md` | entire repo |

Steve's main checkout (no `LANE` env var set) has full ownership and is the merge gate.

## Cross-lane edits

If your lane needs to edit a file owned by another lane:

1. **Preferred:** Stop, tell the user, let them decide whether to merge first or coordinate via the task list.
2. **Alternative:** Claim a lock by writing your lane name into `.agent-state/locks/<owning-lane>.lock`. Make the edit. Delete the lock file when done.

The lane-guard hook does not block — it warns. Cross-lane edits without a lock will surface a warning in the agent's response so the user can intervene.

## How to update

When repo structure changes:
1. Edit this file (keep table accurate).
2. Edit `ownership.json` (keep machine map accurate).
3. Commit both together so they cannot drift.

If a new lane is added, also update `.claude/settings.json` if any settings are lane-specific (currently none).

## Files NOT owned by any lane

Some files are intentionally unowned because they are genuinely cross-cutting — any lane could legitimately need to change them, and the lane-guard hook will surface a warning so the user can decide. Examples currently in the repo:

- `pyproject.toml`, `requirements.txt`, `requirements-dev.txt` — Python dependencies
- `.github/` — CI workflow files
- `scripts/diag.sh` — repo-wide diagnostic
- `scripts/smoke-test.sh` — cross-cutting smoke test
- `.env`, `.env.example`, `.gcloudignore`, `.gitignore`, `LICENSE`, `CODE_OF_CONDUCT.md` — top-level config
- `scratch/` — ad-hoc working directory, not lane-specific

Edits to these files from inside a lane will produce a warning. Default to telling the user before proceeding.
