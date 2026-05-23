# Parallel Agent Scaffolding — Phase 0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land the Phase 0 scaffolding from the design (`docs/2026-05-22-parallel-agent-workflow-design.md`) in mr-sentinel so that two-lane parallel Claude Code sessions can begin in Phase 1.

**Architecture:** Add `.agent-state/` (ownership map in human + JSON form, shared task list, lock directory), a `PreToolUse` lane-guard hook in warn mode using JSON `additionalContext` so warnings surface in Claude's response, and a CLAUDE.md addendum so any Claude session in this repo reads the lane rules at startup. No changes to existing app code, tests, or scripts.

**Tech Stack:** Bash (hook), JSON (machine-readable state), Markdown (human-readable state + CLAUDE.md), Claude Code hooks API (PreToolUse).

---

## File Structure

Files created (all new — no edits to existing app code):

- `.agent-state/OWNERSHIP.md` — human-readable lane map + cross-lane rules (~80 lines)
- `.agent-state/ownership.json` — machine-readable lane → path-prefix map for the hook (~25 lines)
- `.agent-state/tasks.json` — shared task list with initial critical-path items (~50 lines)
- `.agent-state/locks/.gitkeep` — preserves the directory while keeping individual lock files git-ignored
- `.agent-state/README.md` — one-paragraph pointer for first-time readers
- `.claude/hooks/lane-guard.sh` — the PreToolUse hook itself, warn mode (~60 lines)
- `.claude/settings.json` — registers the hook with Claude Code (~15 lines)
- `tests/test_lane_guard.sh` — bash test harness for the hook (~80 lines)
- `CLAUDE.md` — new file at repo root with project context + lane-awareness addendum (~50 lines)

Files modified:

- `.gitignore` — add `.agent-state/locks/*.lock` so transient lock files are not committed

One responsibility per file. The hook (`lane-guard.sh`) reads `ownership.json` only. Agents read `OWNERSHIP.md` and `CLAUDE.md`. Steve edits `tasks.json` directly when planning; agents update only the `status` and `owner` fields.

---

## Task 1: Create `.agent-state/ownership.json`

**Files:**
- Create: `.agent-state/ownership.json`

- [ ] **Step 1: Write the file**

```json
{
  "lanes": {
    "backend": [
      "app/main.py",
      "app/gitlab_client.py",
      "app/persistence.py",
      "Dockerfile",
      "Makefile",
      "db/"
    ],
    "evaluator": [
      "app/agent_runner.py",
      "rubric/"
    ],
    "demo-data": [
      "scripts/seed-",
      "scripts/gitlab-bootstrap.sh",
      "scripts/test-override-live.sh"
    ],
    "dashboard": [
      "app/dashboard.py"
    ],
    "docs": [
      "docs/",
      "README.md",
      "mr-sentinel-hackathon-spec.md"
    ]
  },
  "shared_state": ".agent-state/",
  "version": 1
}
```

Path entries are prefix matches against the repo-relative path. A directory entry must end with `/`. A file entry is a literal exact path. A prefix without a slash (e.g., `scripts/seed-`) matches any file starting with that string.

- [ ] **Step 2: Validate JSON**

Run: `python -c "import json; json.load(open('.agent-state/ownership.json'))"`
Expected: no output, exit 0.

- [ ] **Step 3: Commit**

```bash
git add .agent-state/ownership.json
git commit -m "feat(agent-state): add machine-readable lane ownership map"
```

---

## Task 2: Create `.agent-state/OWNERSHIP.md`

**Files:**
- Create: `.agent-state/OWNERSHIP.md`

- [ ] **Step 1: Write the file**

```markdown
# Lane Ownership Map

This file is the human-readable counterpart to `ownership.json`. Both must stay in sync — the lane-guard hook reads the JSON, agents read this file.

## Lanes

| Lane | Branch | Owns (read+write) | Reads only |
|------|--------|-------------------|------------|
| `backend` | `lane/backend` | `app/main.py`, `app/gitlab_client.py`, `app/persistence.py`, `Dockerfile`, `Makefile`, `db/` | `docs/`, `scripts/`, `rubric/` |
| `evaluator` | `lane/evaluator` | `app/agent_runner.py`, `rubric/` | rest of `app/` |
| `demo-data` | `lane/demo-data` | `scripts/seed-*.sh`, `scripts/gitlab-bootstrap.sh`, `scripts/test-override-live.sh` | `app/` |
| `dashboard` | `lane/dashboard` | `app/dashboard.py` | `app/`, `db/` |
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

Anything outside the `Owns` columns above is unowned. Examples: `pyproject.toml`, `requirements*.txt`, `.github/`, `.env*`, top-level config files. Cross-lane edits to these surface a warning and you should default to telling the user.
```

- [ ] **Step 2: Commit**

```bash
git add .agent-state/OWNERSHIP.md
git commit -m "docs(agent-state): human-readable lane ownership map"
```

---

## Task 3: Create `.agent-state/tasks.json` and `.agent-state/README.md`

**Files:**
- Create: `.agent-state/tasks.json`
- Create: `.agent-state/README.md`

- [ ] **Step 1: Write `tasks.json` with the known critical-path items**

```json
{
  "tasks": [
    {
      "id": "T-001",
      "lane": "demo-data",
      "title": "Run scripts/seed-archetype-mrs-v2.sh from WSL and capture per-rule coverage",
      "status": "pending",
      "owner": null,
      "blocks": ["T-002"],
      "notes": "Norton blocks gcloud on Git Bash — must run from WSL. Target coverage: 14/15 rubric rules tripped after seed."
    },
    {
      "id": "T-002",
      "lane": "demo-data",
      "title": "Update docs/live-fire-2026-05-21.md with post-v2-seed dashboard scrape",
      "status": "blocked",
      "owner": null,
      "blocks": [],
      "notes": "Depends on T-001."
    },
    {
      "id": "T-003",
      "lane": "docs",
      "title": "Devpost form text — copy refinement and final paste-ready version",
      "status": "pending",
      "owner": null,
      "blocks": [],
      "notes": "Source: docs/devpost-submission.md. Cliff: 2026-06-11 12:00 PT."
    },
    {
      "id": "T-004",
      "lane": "docs",
      "title": "Demo-script reconciliation — apply pending Shot 6 + Shot 7 corrections",
      "status": "pending",
      "owner": null,
      "blocks": [],
      "notes": "Source: docs/demo-script.md. Shot 6 sha8 5d2e7a14 → 1fb25ad2, failure count 4 → 2. Shot 7 rule-order + last 30d."
    },
    {
      "id": "T-005",
      "lane": null,
      "title": "Verify scaffolding on a real worktree before launching Phase 1",
      "status": "pending",
      "owner": null,
      "blocks": [],
      "notes": "Owner: Steve. Smoke test described in Task 9 of the implementation plan."
    }
  ],
  "version": 1
}
```

- [ ] **Step 2: Write `.agent-state/README.md`**

```markdown
# `.agent-state/` — parallel-agent coordination

This directory holds shared state for parallel Claude Code sessions running in this repo.

- `OWNERSHIP.md` — human-readable lane → file map. Read at session start.
- `ownership.json` — machine-readable copy of the same. Consumed by `.claude/hooks/lane-guard.sh`.
- `tasks.json` — shared task list. Agents claim tasks (set `owner` + `status`). Steve edits the `blocks` graph as planning evolves.
- `locks/` — transient cross-lane edit claims. Lock files are git-ignored.

See `docs/2026-05-22-parallel-agent-workflow-design.md` for the full design and the rationale behind state-based (not message-based) coordination.

If you are a Claude Code agent reading this on session start: confirm `$LANE` is set (`echo $LANE`). If unset, you are in Steve's main checkout with full ownership. If set, restrict your edits to your lane per `OWNERSHIP.md`.
```

- [ ] **Step 3: Validate `tasks.json`**

Run: `python -c "import json; json.load(open('.agent-state/tasks.json'))"`
Expected: no output, exit 0.

- [ ] **Step 4: Commit**

```bash
git add .agent-state/tasks.json .agent-state/README.md
git commit -m "feat(agent-state): seed task list and contributor pointer"
```

---

## Task 4: Create lock directory placeholder

**Files:**
- Create: `.agent-state/locks/.gitkeep`
- Modify: `.gitignore`

- [ ] **Step 1: Create the placeholder**

```bash
mkdir -p .agent-state/locks
touch .agent-state/locks/.gitkeep
```

- [ ] **Step 2: Add ignore rule for lock files**

Append to `.gitignore`:

```
# Parallel-agent transient locks (the locks/ directory itself is kept via .gitkeep)
.agent-state/locks/*.lock
```

- [ ] **Step 3: Verify `.gitkeep` is tracked, future `.lock` files are not**

Run: `git status --ignored .agent-state/locks/`
Expected: `.gitkeep` shows as untracked; no `.lock` files exist yet.

Run a real test:

```bash
echo "test" > .agent-state/locks/test.lock
git status --ignored .agent-state/locks/ | grep test.lock
```

Expected: `test.lock` appears under `Ignored files` (or no output if your git version's --ignored is implicit). Then clean up:

```bash
rm .agent-state/locks/test.lock
```

- [ ] **Step 4: Commit**

```bash
git add .agent-state/locks/.gitkeep .gitignore
git commit -m "feat(agent-state): lock directory + gitignore for transient locks"
```

---

## Task 5: Write failing test for `lane-guard.sh`

**Files:**
- Create: `tests/test_lane_guard.sh`

- [ ] **Step 1: Write the test harness**

```bash
#!/usr/bin/env bash
# Test harness for .claude/hooks/lane-guard.sh.
# The hook receives a JSON tool-call payload on stdin, reads $LANE from env,
# reads .agent-state/ownership.json, and prints JSON to stdout when a
# cross-lane edit is detected (warn mode). Always exits 0.

set -u

HOOK="${PWD}/.claude/hooks/lane-guard.sh"
FAILED=0

run_case() {
    local name="$1"
    local lane="$2"
    local file_path="$3"
    local expect_warning="$4"  # "yes" or "no"

    local stdin_json
    stdin_json=$(printf '{"tool_name":"Edit","tool_input":{"file_path":"%s"}}' "$file_path")

    local stdout
    stdout=$(printf '%s' "$stdin_json" | LANE="$lane" bash "$HOOK" 2>/dev/null)
    local rc=$?

    if [ "$rc" -ne 0 ]; then
        echo "FAIL [$name]: hook exited $rc (expected 0)"
        FAILED=1
        return
    fi

    local has_warning="no"
    if echo "$stdout" | grep -q "additionalContext"; then
        has_warning="yes"
    fi

    if [ "$has_warning" != "$expect_warning" ]; then
        echo "FAIL [$name]: expected warning=$expect_warning, got warning=$has_warning"
        echo "       stdout: $stdout"
        FAILED=1
    else
        echo "PASS [$name]"
    fi
}

# In-lane edit: backend editing app/main.py → no warning
run_case "in-lane backend" "backend" "$(pwd)/app/main.py" "no"

# Cross-lane edit: backend editing app/dashboard.py → warning
run_case "cross-lane backend→dashboard" "backend" "$(pwd)/app/dashboard.py" "yes"

# Cross-lane edit: docs editing app/main.py → warning
run_case "cross-lane docs→backend" "docs" "$(pwd)/app/main.py" "yes"

# In-lane edit: docs editing README.md → no warning
run_case "in-lane docs README" "docs" "$(pwd)/README.md" "no"

# In-lane edit: demo-data editing scripts/seed-archetype-mrs-v2.sh → no warning
run_case "in-lane demo-data seed" "demo-data" "$(pwd)/scripts/seed-archetype-mrs-v2.sh" "no"

# Unset LANE: Steve's main checkout → no warning
run_case "no LANE set" "" "$(pwd)/app/main.py" "no"

# Cross-lane edit but lock exists → no warning
mkdir -p .agent-state/locks
echo "backend" > .agent-state/locks/dashboard.lock
run_case "cross-lane with lock" "backend" "$(pwd)/app/dashboard.py" "no"
rm -f .agent-state/locks/dashboard.lock

# Unowned file: editing pyproject.toml from backend → warning
run_case "unowned file" "backend" "$(pwd)/pyproject.toml" "yes"

if [ "$FAILED" -eq 0 ]; then
    echo "All tests passed."
    exit 0
else
    echo "Some tests failed."
    exit 1
fi
```

- [ ] **Step 2: Make it executable**

```bash
chmod +x tests/test_lane_guard.sh
```

- [ ] **Step 3: Run it to verify it fails (hook does not exist yet)**

Run: `bash tests/test_lane_guard.sh`
Expected: FAIL — the hook file does not exist, so every case will exit non-zero. Output should mention "hook exited" with a non-zero code on at least one case. This confirms the test harness itself runs.

- [ ] **Step 4: Commit**

```bash
git add tests/test_lane_guard.sh
git commit -m "test(lane-guard): failing test harness for cross-lane edit detection"
```

---

## Task 6: Implement `lane-guard.sh` to make tests pass

**Files:**
- Create: `.claude/hooks/lane-guard.sh`

- [ ] **Step 1: Write the hook**

```bash
#!/usr/bin/env bash
# PreToolUse hook — warns on cross-lane Edit/Write attempts.
# Always exits 0 (warn mode, not block mode).
#
# Contract:
#   stdin:  JSON {"tool_name": "...", "tool_input": {"file_path": "..."}}
#   env:    LANE — the current agent's lane (unset = Steve's main checkout)
#   stdout: JSON additionalContext when a warning is emitted, otherwise empty
#   exit:   always 0
#
# All non-trivial logic lives in the single Python block below; bash is only
# the entrypoint. This sidesteps Windows/Git-Bash path-format mismatches
# (/c/Users vs C:/Users) by letting pathlib do path normalization.

set -u

# Short-circuit if LANE is unset — this is Steve's main checkout.
if [ -z "${LANE:-}" ]; then
    exit 0
fi

# Resolve the shared .git common dir (works in both main checkout and worktrees).
common_dir=$(git rev-parse --git-common-dir 2>/dev/null) || exit 0
repo_root=$(cd "$(dirname "$common_dir")" 2>/dev/null && pwd) || exit 0

# Read stdin once; hand off to Python.
payload=$(cat)

LANE="$LANE" REPO_ROOT="$repo_root" PAYLOAD="$payload" python <<'PY'
import json, os, sys, pathlib

try:
    payload = json.loads(os.environ["PAYLOAD"])
except (ValueError, KeyError):
    sys.exit(0)

if payload.get("tool_name", "") not in ("Edit", "Write", "NotebookEdit"):
    sys.exit(0)

file_path = payload.get("tool_input", {}).get("file_path", "")
if not file_path:
    sys.exit(0)

repo_root = pathlib.Path(os.environ["REPO_ROOT"]).resolve()
lane = os.environ["LANE"]

# Normalize file_path to repo-relative POSIX form.
try:
    abs_path = pathlib.Path(file_path).resolve()
    rel_path = abs_path.relative_to(repo_root).as_posix()
except (ValueError, OSError):
    # File not under repo root (temp file, etc.) — silently allow.
    sys.exit(0)

ownership_path = repo_root / ".agent-state" / "ownership.json"
if not ownership_path.exists():
    sys.exit(0)

with ownership_path.open() as f:
    data = json.load(f)

owning_lane = None
for ln, patterns in data["lanes"].items():
    for pat in patterns:
        matched = False
        if pat.endswith("/"):
            matched = rel_path.startswith(pat)
        elif pat == rel_path:
            matched = True
        elif "/" in pat and rel_path.startswith(pat):
            # Prefix-without-slash match (e.g., "scripts/seed-")
            matched = True
        if matched:
            owning_lane = ln
            break
    if owning_lane:
        break

# In-lane edit → silent allow.
if owning_lane == lane:
    sys.exit(0)

# Lock check.
if owning_lane:
    lock_file = repo_root / ".agent-state" / "locks" / f"{owning_lane}.lock"
    if lock_file.exists():
        try:
            if lock_file.read_text().strip() == lane:
                sys.exit(0)
        except OSError:
            pass

if owning_lane:
    msg = (
        f"Lane guard: file '{rel_path}' is owned by lane '{owning_lane}', "
        f"but you are in lane '{lane}'. Either stop and notify the user, "
        f"or claim a lock by writing '{lane}' into "
        f".agent-state/locks/{owning_lane}.lock before editing."
    )
else:
    msg = (
        f"Lane guard: file '{rel_path}' is not owned by any lane. "
        f"You are in lane '{lane}'. Cross-lane edits to unowned files "
        f"should be flagged to the user before proceeding."
    )

print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "additionalContext": msg
    }
}))
PY

exit 0
```

- [ ] **Step 2: Make it executable**

```bash
chmod +x .claude/hooks/lane-guard.sh
```

- [ ] **Step 3: Run the test harness**

Run: `bash tests/test_lane_guard.sh`
Expected: all 8 cases PASS, exit 0. Output ends with `All tests passed.`

If any case fails, read the failure message and the stdout shown. The most likely fix points are: the Python JSON parsing block (if `python` is not on PATH, try `python3`), the path normalization (if running from Git Bash on Windows, double-check the `sed` for backslash → forward-slash conversion), or the `--git-common-dir` resolution (verify by running `git rev-parse --git-common-dir` manually from the repo root — should print `.git`).

- [ ] **Step 4: Commit**

```bash
git add .claude/hooks/lane-guard.sh
git commit -m "feat(lane-guard): warn-mode PreToolUse hook for cross-lane edits"
```

---

## Task 7: Register the hook in `.claude/settings.json`

**Files:**
- Create: `.claude/settings.json`

- [ ] **Step 1: Write the settings file**

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write|NotebookEdit",
        "hooks": [
          {
            "type": "command",
            "command": "bash .claude/hooks/lane-guard.sh"
          }
        ]
      }
    ]
  }
}
```

The `$LANE` env var is NOT set here — it is set per worktree in `.claude/settings.local.json` (which is git-ignored) when Phase 1 begins. Steve's main checkout has no `settings.local.json` and therefore no `$LANE`, so the hook short-circuits.

- [ ] **Step 2: Verify Claude Code parses it**

Run: `python -c "import json; json.load(open('.claude/settings.json'))"`
Expected: no output, exit 0.

- [ ] **Step 3: Commit**

```bash
git add .claude/settings.json
git commit -m "feat(claude): register lane-guard hook for Edit/Write/NotebookEdit"
```

---

## Task 8: Create root `CLAUDE.md` with lane-awareness addendum

**Files:**
- Create: `CLAUDE.md`

- [ ] **Step 1: Write the file**

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs(claude): add CLAUDE.md with project context + lane awareness"
```

---

## Task 9: Smoke-test on a real worktree

This task is destructive only in that it creates a worktree. Steve can remove it afterward.

**Files:** (no edits — verification only)

- [ ] **Step 1: Create a smoke-test worktree**

```bash
git worktree add ../mr-sentinel-wt/docs -b lane/docs
```

Expected: worktree created at `~/CascadeProjects/mr-sentinel-wt/docs`, branch `lane/docs` checked out.

- [ ] **Step 2: Set `$LANE` for that worktree**

```bash
mkdir -p ../mr-sentinel-wt/docs/.claude
cat > ../mr-sentinel-wt/docs/.claude/settings.local.json <<'EOF'
{
  "env": { "LANE": "docs" }
}
EOF
```

Note: `settings.local.json` is git-ignored by Claude Code default behavior — confirm by running `git -C ../mr-sentinel-wt/docs status`. The file should NOT appear as untracked. If it does appear, add `.claude/settings.local.json` to `.gitignore` in a follow-up commit.

- [ ] **Step 3: Verify the hook fires in the worktree**

From the worktree directory, simulate an Edit tool call via the hook directly:

```bash
cd ../mr-sentinel-wt/docs
echo '{"tool_name":"Edit","tool_input":{"file_path":"'"$(pwd)"'/app/main.py"}}' | LANE=docs bash .claude/hooks/lane-guard.sh
```

Expected: JSON output containing `"additionalContext"` with a message naming `app/main.py` and lane `backend`.

Run the same with an in-lane file:

```bash
echo '{"tool_name":"Edit","tool_input":{"file_path":"'"$(pwd)"'/README.md"}}' | LANE=docs bash .claude/hooks/lane-guard.sh
```

Expected: no output, exit 0.

- [ ] **Step 4: Verify common-dir resolution from worktree**

```bash
git rev-parse --git-common-dir
```

Expected: a path ending in `.git` (the main checkout's `.git/`), NOT a path containing `worktrees`. This confirms the hook will find the shared `.agent-state/` no matter which lane is active.

- [ ] **Step 5: Verify pre-commit hooks don't collide (if any)**

```bash
ls .pre-commit-config.yaml 2>/dev/null && echo "pre-commit config exists — audit needed"
ls package.json 2>/dev/null && grep -q husky package.json && echo "husky present — audit needed"
```

If either prints "audit needed", read the relevant config and confirm no hook writes to a shared `./tmp`, `./.cache`, or absolute-path location that would collide across worktrees. For mr-sentinel as of 2026-05-22, neither exists.

- [ ] **Step 6: Remove the smoke-test worktree (optional — keep if starting Phase 1 immediately)**

```bash
cd ~/CascadeProjects/mr-sentinel
git worktree remove ../mr-sentinel-wt/docs
git branch -D lane/docs
```

Skip Step 6 if you want to roll directly into Phase 1 (the design intends the `docs` lane to be one of the first two pilot lanes). In that case, leave the worktree intact and confirm `lane/docs` is on the remote: `git -C ../mr-sentinel-wt/docs push -u origin lane/docs`.

- [ ] **Step 7: No commit needed for this task.** Phase 0 is complete when this verification passes.

---

## Self-Review Notes

**Spec coverage:**
- `.agent-state/OWNERSHIP.md` → Task 2 ✓
- `.agent-state/tasks.json` → Task 3 ✓
- `.agent-state/locks/` → Task 4 ✓
- `lane-guard.sh` (warn mode, common-dir, additionalContext) → Tasks 5 + 6 ✓
- `.claude/settings.json` (hook registration) → Task 7 ✓
- CLAUDE.md addendum → Task 8 ✓
- Per-worktree settings.local.json with `LANE` env var → Task 9 (smoke test)
- Phase 0 gotcha verification (common-dir, pre-commit collision, settings.local.json gitignore) → Task 9 ✓

**Out-of-plan items (intentionally deferred to Phase 1+):**
- Actually launching two Claude sessions in parallel — Phase 1, not Phase 0.
- `/parallel-init` slash command for portfolio-wide reuse — Phase 3.

**Placeholder scan:** No TBDs, TODOs, or "implement later" steps. Every code block contains the actual content. Commit commands are explicit.

**Type / naming consistency:** Lane names `backend`, `evaluator`, `demo-data`, `dashboard`, `docs` are used identically in `ownership.json`, `OWNERSHIP.md`, `tasks.json`, `CLAUDE.md`, and the hook test cases. Branch names follow `lane/<name>` everywhere.
