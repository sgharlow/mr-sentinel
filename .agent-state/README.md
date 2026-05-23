# `.agent-state/` — parallel-agent coordination

This directory holds shared state for parallel Claude Code sessions running in this repo.

- `OWNERSHIP.md` — human-readable lane → file map. Read at session start.
- `ownership.json` — machine-readable copy of the same. Consumed by `.claude/hooks/lane-guard.sh`.
- `tasks.json` — shared task list. Agents claim tasks (set `owner` + `status`). Steve edits the `blocks` graph as planning evolves.
- `locks/` — transient cross-lane edit claims. Lock files are git-ignored.

See `docs/2026-05-22-parallel-agent-workflow-design.md` for the full design and the rationale behind state-based (not message-based) coordination.

If you are a Claude Code agent reading this on session start: confirm `$LANE` is set (`echo $LANE`). If unset, you are in Steve's main checkout with full ownership. If set, restrict your edits to your lane per `OWNERSHIP.md`.
