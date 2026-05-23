# Parallel Claude Code Agents — Pilot in mr-sentinel

**Date:** 2026-05-22
**Status:** Design approved, ready for implementation plan
**Pilot scope:** mr-sentinel only; portfolio-wide generalization deferred to Phase 3

## Problem

Running multiple Claude Code agents on a single machine introduces three coupled problems: code isolation (agents corrupting each other's edits), work coordination (who owns what), and sync (parallel streams returning to one repo state). Tools that solve only one (worktrees alone, chat-style messaging alone) leave the others broken. We want a pattern that addresses all three with the minimum new tooling, and we want to validate it on a real, time-boxed project before generalizing.

## Decisions

1. **Pilot in mr-sentinel.** Has natural vertical slices (FastAPI backend, Gemini evaluator, demo-data seeding, dashboard, docs/Devpost) and a hard deadline (Devpost submit cliff 2026-06-11) that bounds the experiment.
2. **State-based coordination, not message-based.** A shared task file + an ownership map covers the cases people reach to MCP messaging for, without the wake-up problem (Claude Code does not surface MCP `notifications/message` pushes until the user types).
3. **Worktrees for isolation, human (Steve) for merge.** No lead agent in v1; Steve plays scrum master.
4. **Lane-guard hook is a warning, not a block.** Solo developer; warn is friendlier and Steve decides per-edit. Re-evaluate if a teammate joins or if walk-away sessions become common.
5. **Five lanes, but only spin agents when they have work.** Token cost and review bandwidth are the real caps, not parallelism capacity.

## Lane map for mr-sentinel

`app/` is flat (no subdirs); lane boundaries are by file.

| Lane | Branch | Owns (read+write) | Reads only |
|------|--------|-------------------|------------|
| `backend` | `lane/backend` | `app/main.py`, `app/gitlab_client.py`, `app/persistence.py`, `Dockerfile`, `Makefile`, `db/` | `docs/`, `scripts/`, `rubric/` |
| `evaluator` | `lane/evaluator` | `app/agent_runner.py`, `rubric/` | rest of `app/` |
| `demo-data` | `lane/demo-data` | `scripts/seed-*.sh`, `scripts/gitlab-bootstrap.sh`, `scripts/test-override-live.sh` | `app/` |
| `dashboard` | `lane/dashboard` | `app/dashboard.py` | `app/` (for API shapes), `db/` |
| `docs` | `lane/docs` | `docs/`, `README.md`, `mr-sentinel-hackathon-spec.md`, Devpost form text, demo script | entire repo |

Cross-lane edits require claiming a lock (see Architecture). Steve, in his own un-laned Claude session, has full ownership and does the merges.

WSL shell note: the `demo-data` lane runs from WSL because `gcloud` is blocked by Norton's TLS interception on Windows Git Bash (see [[feedback_norton_windows_tls_mitm]] and [[gcloud-norton-mitm-block]]). Other lanes run from Git Bash. Same worktree directory; different shells.

## Architecture

### Files added to the repo

```
.agent-state/
  OWNERSHIP.md            # Human-readable lane map (table above + cross-lane rules)
  tasks.json              # Shared task list
.claude/
  hooks/
    lane-guard.sh         # PreToolUse hook (warn mode)
  settings.local.json     # Per-worktree env var: LANE=<lane-name>
CLAUDE.md                 # Addendum: lane awareness rules (see below)
```

### `tasks.json` schema

```json
{
  "tasks": [
    {
      "id": "T-001",
      "lane": "demo-data",
      "title": "Run v2 seed script from WSL, capture archetype coverage",
      "status": "pending",
      "owner": null,
      "blocks": [],
      "notes": ""
    }
  ]
}
```

`status` values: `pending`, `in_progress`, `blocked`, `completed`. `owner` is the lane name when claimed. `blocks` lists task IDs that cannot start until this task is `completed`. Agents update `status` and `owner` themselves; Steve adjusts `blocks` graph as planning evolves.

### `lane-guard.sh` (PreToolUse hook, warn mode)

Triggered on `Edit` and `Write` tool calls. Resolves the shared `.agent-state/OWNERSHIP.md` via `git rev-parse --git-common-dir` (NOT `--git-dir`, which returns the worktree-private dir and would miss the shared state). Reads the current lane from `$LANE` (set in `.claude/settings.local.json` per worktree). If the target file is outside the lane's ownership and no lock exists at `<common_dir>/agent-state-locks/<other-lane>.lock`, the hook prints a warning to stderr with the offending path, the agent's lane, the file's owning lane, and instructions for claiming a lock. **It does not block.** Exit code 0 so the edit proceeds.

The warning forces Claude to surface the cross-lane edit in its response text, which gives Steve a visible signal during review without halting work.

### CLAUDE.md addendum

A new section (~10 lines) added at the top of mr-sentinel's CLAUDE.md:

> **Lane awareness.** This repo is configured for parallel Claude Code sessions. Your lane is `$LANE` (set in `.claude/settings.local.json`). Before any `Edit` or `Write`, confirm the target file is owned by your lane in `.agent-state/OWNERSHIP.md`. If it is not, either:
> 1. Tell the user and stop (preferred), or
> 2. Claim a lock by writing `$(git rev-parse --git-common-dir)/agent-state-locks/<owning-lane>.lock` with your lane name, then make the edit. Release the lock by deleting the file when done. The lock lives under the shared `.git/` directory so it is visible across worktrees.
> Read `.agent-state/tasks.json` at session start. Claim a task by setting its `owner` to your lane and `status` to `in_progress`. Mark `completed` when done.

### Per-worktree `.claude/settings.local.json`

```json
{
  "env": { "LANE": "demo-data" }
}
```

One value per worktree, set at worktree creation. Steve's un-laned main checkout has no `LANE` env var; lane-guard skips gracefully when unset.

## Phase plan

### Phase 0 — scaffolding (today, ~30 min)

Land all of the above in mr-sentinel `main`:
- Create `.agent-state/OWNERSHIP.md` with the lane table and cross-lane rules
- Create `.agent-state/tasks.json` pre-populated with the known critical-path tasks (v2 seed run, Devpost form prep, demo video script reconciliation, Cloud Logging latency capture)
- Create `.claude/hooks/lane-guard.sh` in warn mode
- Add the CLAUDE.md addendum
- Commit and push to main

No worktrees yet, no agents launched.

### Phase 1 — two-lane pilot (this week, before June 8 demo video)

Two Windows Terminal tabs:
- Tab A: WSL shell, worktree at `~/CascadeProjects/mr-sentinel-wt/demo-data` on branch `lane/demo-data`. Claude Code session runs the v2 seed script + live-fire dashboard scrape, updates `docs/live-fire-2026-05-21.md` follow-up.
- Tab B: Git Bash shell, worktree at `~/CascadeProjects/mr-sentinel-wt/docs` on branch `lane/docs`. Claude Code session works on Devpost form text and demo-script reconciliation.

Worktree creation per lane:
```bash
git worktree add ../mr-sentinel-wt/<lane> -b lane/<lane>
echo '{"env":{"LANE":"<lane>"}}' > ../mr-sentinel-wt/<lane>/.claude/settings.local.json
```

Both lanes work in isolation. Steve reviews diffs in each tab, merges each branch into `main` when done. No agent talks to another agent.

### Phase 2 — additional lanes only when needed

`backend`, `evaluator`, `dashboard` lanes light up only when a real task lands in them. Pre-spinning idle agents wastes tokens and review time. The bottleneck is Steve's review capacity, not agent capacity.

### Phase 3 — generalize to a `/parallel-init` slash command (after pilot)

Once the pilot has run for at least one merge cycle and the pattern has survived contact with reality, capture it as a Claude Code slash command (or simple bash script) that, given a repo path:
1. Creates `.agent-state/` with an OWNERSHIP.md template (interactive: prompts for lane names + paths)
2. Drops the lane-guard.sh hook
3. Adds the CLAUDE.md addendum

Then the pattern is one command away on any of the other 32 portfolio repos.

## Out of scope (deferred or rejected)

- **MCP message bus / `claude-peers-mcp`.** Solo dev, no negotiation surface — state coordination is sufficient. Revisit only if a real cross-lane refactor (API contract migration, schema change) lands that needs agents to argue.
- **Lead-and-teammates orchestration (Anthropic Agent Teams pattern).** Steve plays this role. Adding a lead Claude session costs tokens without clear payoff at this scale.
- **Per-worktree database / Neon branching.** mr-sentinel uses a single Cloud SQL Postgres dev DB. The lanes do not race on it because only `backend` and `demo-data` touch DB, and they coordinate via tasks.json.
- **Per-worktree dev server ports.** Cloud Run is the deploy target; local server runs are infrequent and serialized.
- **Claude Squad / parallel-cc / Ruflo TUI orchestrators.** The TUI value is real but the underlying primitive (worktree + tab) works fine on Windows Terminal without it. Adopt only if Steve outgrows manual tab management.

## Gotchas to verify during Phase 0

1. **`git rev-parse --git-common-dir` vs `--git-dir`** in the hook — confirm on a real worktree before shipping the hook. `--git-dir` returns the worktree-private `.git/worktrees/<lane>/` dir; `--git-common-dir` returns the shared `.git/`. The hook needs the shared one to find `.agent-state/`.
2. **Pre-commit hooks in mr-sentinel** — audit `.pre-commit-config.yaml` and any `husky`/`scripts/` hooks. Confirm none write to a shared `./tmp` or `./.cache` path that would collide across worktrees. mr-sentinel is FastAPI + minimal JS, so risk is low but worth a one-time check.
3. **Norton TLS MITM on Git Bash** — confirmed already-documented constraint. Demo-data lane uses WSL. Other lanes do not invoke `gcloud` or other Norton-MITM-sensitive tools.
4. **`.claude/settings.local.json` per worktree** — confirm Claude Code reads this file from the worktree directory (not a global), so each lane's `LANE` env var is isolated.

**Locks live under `.git/`, not under `.agent-state/`.** Task 9 smoke testing revealed that `.agent-state/locks/` is PWD-relative: each worktree has its own copy, so a lock claimed in worktree A is invisible to an agent or hook running in worktree B. The fix is to write lock files to `<common_dir>/agent-state-locks/<lane>.lock`, where `<common_dir> = git rev-parse --git-common-dir` — the shared `.git/` directory that backs all worktrees of the same repo. That directory is genuinely shared (worktrees only have a private `.git/worktrees/<name>/` subdir), host-local, and never committed, which makes it the architecturally right place for transient cross-lane coordination state.

## Future work (post-pilot, not committed)

- Promote the pattern to `/parallel-init` (Phase 3).
- Evaluate Anthropic Agent Teams (shipped Feb 2026) as a replacement for the manual `tasks.json` if it becomes available in Claude Code with first-class hooks.
- Optional: visual companion / status dashboard reading `tasks.json` to show lane status across all Windows Terminal tabs at a glance. Only if `tasks.json` proves load-bearing in practice.

## Success criteria for the pilot

- At least two lanes run concurrently for a full work session without an Edit collision on the same file.
- `lane-guard.sh` warns at least once on a real cross-lane edit attempt; the warning visibly surfaces in the agent's response.
- The demo-data lane successfully runs the v2 seed from WSL while the docs lane independently lands Devpost prep, both merged to main with no manual conflict resolution beyond standard rebase.
- The pattern is described well enough that the Phase 3 `/parallel-init` command can be authored without re-discovering anything.

Failure modes that should kill the pilot:
- Lane-guard hook produces false positives often enough that Steve disables it.
- Worktree creation breaks pre-commit hooks or shared-state assumptions.
- Two-lane review takes longer than just running the work serially in one session.
