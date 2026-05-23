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
import json, os, sys, re, pathlib

def normalize(p: str) -> pathlib.Path:
    """Convert Git Bash POSIX-style drive paths (/c/Users/...) to Windows form,
    then resolve. On non-Windows platforms this is a no-op pass-through."""
    if sys.platform == "win32":
        m = re.match(r"^/([a-zA-Z])(/.*)?$", p)
        if m:
            drive = m.group(1).upper()
            rest = m.group(2) or "/"
            p = f"{drive}:{rest}"
    return pathlib.Path(p).resolve()

try:
    payload = json.loads(os.environ["PAYLOAD"])
except (ValueError, KeyError):
    sys.exit(0)

if payload.get("tool_name", "") not in ("Edit", "Write", "NotebookEdit"):
    sys.exit(0)

file_path = payload.get("tool_input", {}).get("file_path", "")
if not file_path:
    sys.exit(0)

repo_root = normalize(os.environ["REPO_ROOT"])
lane = os.environ["LANE"]

# Normalize file_path to repo-relative POSIX form.
try:
    abs_path = normalize(file_path)
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
