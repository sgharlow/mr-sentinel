"""Agent orchestration — loads rubric, calls Gemini, parses structured score.

Design:
- The rubric is the product. We load `rubric/v1.yaml` once at module import.
- For 15 rules (~3-5K tokens), we inline the rubric in the Gemini system prompt
  rather than running RAG over a Vertex AI Data Store. Simpler, faster, demos
  better. If rules grow past ~50 or per-project customization gets complex,
  revisit with `vertexai.preview.rag` or Discovery Engine.
- Gemini call returns structured JSON (response_mime_type=application/json).
- The caller (webhook background task) takes the evaluation and persists +
  posts a comment via GitLabClient.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from app.gitlab_client import DiffEntry, MergeRequest

logger = logging.getLogger("mr_sentinel.agent")

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RUBRIC_PATH = REPO_ROOT / "rubric" / "v1.yaml"

OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["overall_score", "verdict", "summary", "rule_evaluations"],
    "properties": {
        "overall_score": {"type": "number", "minimum": 0, "maximum": 10},
        "verdict": {"type": "string", "enum": ["pass", "warn", "block"]},
        "summary": {"type": "string"},
        "rule_evaluations": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["rule_id", "outcome", "evidence"],
                "properties": {
                    "rule_id": {"type": "string"},
                    "outcome": {"type": "string", "enum": ["pass", "fail", "skip"]},
                    "evidence": {"type": "string"},
                    "remediation": {"type": "string"},
                },
            },
        },
    },
}


@dataclass(frozen=True)
class RuleEvaluation:
    rule_id: str
    outcome: str  # pass | fail | skip
    evidence: str
    remediation: str | None = None


@dataclass(frozen=True)
class Evaluation:
    overall_score: float
    verdict: str  # pass | warn | block
    summary: str
    rule_evaluations: list[RuleEvaluation] = field(default_factory=list)
    rubric_version: str = ""
    raw_response: dict[str, Any] = field(default_factory=dict)


def load_rubric(path: Path = DEFAULT_RUBRIC_PATH) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


_REQUIRED_OUTPUT_KEYS_HINT = (
    'Your response MUST be valid JSON matching this shape exactly:\n'
    '{\n'
    '  "overall_score": <number 0-10>,\n'
    '  "verdict": "pass" | "warn" | "block",\n'
    '  "summary": "<one or two sentences explaining the verdict>",\n'
    '  "rule_evaluations": [\n'
    '    {"rule_id": "<id from rubric>", "outcome": "pass" | "fail" | "skip",\n'
    '     "evidence": "<specific line or pattern observed>",\n'
    '     "remediation": "<required for fail; optional otherwise>"}\n'
    '  ]\n'
    '}\n'
    'Include every rule from the rubric in rule_evaluations.'
)


def build_system_prompt(rubric: dict[str, Any]) -> str:
    rubric_json = json.dumps(rubric, indent=2)
    return f"""You are MR Sentinel — a governance agent for code merge requests.

{_REQUIRED_OUTPUT_KEYS_HINT}


You apply a written rubric to every MR with the consistency of a machine and the
judgment of a senior reviewer. Every rule maps to a named compliance control.
Every comment you produce must tie back to a specific rule_id.

Your job for each MR:
1. Read the MR description, source/target branches, and the diff.
2. For each rule in the rubric, decide: pass, fail, or skip (skip = not applicable
   to this diff).
3. Compute an overall_score from 0-10. Failing blockers = score ≤ 3.
4. Decide a verdict: pass | warn | block.
5. Output structured JSON matching the schema, nothing else.

Rules:
- If the diff is missing context you need (e.g., a referenced spec), use skip
  not fail — say so in evidence.
- Be specific in `evidence` — quote the line or pattern that triggered the
  outcome.
- Remediation is required for any fail; optional for pass.
- Tone: direct, helpful, no hedging. The MR author will read these comments.

Rubric (v{rubric.get('version', 'unknown')}):
```json
{rubric_json}
```
"""


def build_user_prompt(mr: MergeRequest, diffs: list[DiffEntry]) -> str:
    diff_blocks = []
    for d in diffs:
        diff_blocks.append(
            f"## {d.new_path}"
            f" ({'NEW' if d.new_file else 'DELETED' if d.deleted_file else 'RENAMED' if d.renamed_file else 'MODIFIED'})\n"
            f"```diff\n{d.diff}\n```"
        )
    diff_section = "\n\n".join(diff_blocks) if diff_blocks else "(no diff entries returned)"

    return f"""MR: {mr.project_path}!{mr.iid} ({mr.source_branch} → {mr.target_branch})
Title: {mr.title}
Author: @{mr.author_username}
Description:
{mr.description or '(empty)'}

Files changed: {len(diffs)}

{diff_section}
"""


class AgentRunner:
    """Evaluates an MR against the rubric using Vertex AI Gemini."""

    def __init__(
        self,
        *,
        project_id: str | None = None,
        location: str = "us-central1",
        model_name: str = "gemini-2.5-flash",
        rubric_path: Path = DEFAULT_RUBRIC_PATH,
        model_factory: Any = None,
    ) -> None:
        self.project_id = project_id or os.environ.get("GCP_PROJECT_ID") or os.environ.get("GCP_PROJECT")
        self.location = location
        self.model_name = model_name
        self.rubric = load_rubric(rubric_path)
        self._model_factory = model_factory  # injectable for tests

    def _get_model(self) -> Any:
        if self._model_factory is not None:
            return self._model_factory(self.model_name)
        import vertexai
        from vertexai.generative_models import GenerativeModel

        if not self.project_id:
            raise RuntimeError("GCP_PROJECT_ID env var must be set to call Vertex AI")
        vertexai.init(project=self.project_id, location=self.location)
        return GenerativeModel(self.model_name, system_instruction=build_system_prompt(self.rubric))

    async def evaluate(self, mr: MergeRequest, diffs: list[DiffEntry]) -> Evaluation:
        model = self._get_model()
        user_prompt = build_user_prompt(mr, diffs)
        logger.info(
            "evaluating MR %s!%s (%d files) with model=%s",
            mr.project_path, mr.iid, len(diffs), self.model_name,
        )

        # Run blocking SDK call in a thread to keep the event loop free.
        # Note: response_schema is intentionally omitted — Vertex AI's proto layer
        # requires its own Schema type, not JSONSchema dicts. response_mime_type
        # forces JSON output; _parse_response uses defensive defaults if fields
        # are missing.
        import asyncio
        response = await asyncio.to_thread(
            model.generate_content,
            user_prompt,
            generation_config={
                "response_mime_type": "application/json",
                "temperature": 0.2,
            },
        )

        return self._parse_response(response)

    def _parse_response(self, response: Any) -> Evaluation:
        try:
            text = response.text
        except AttributeError:
            text = str(response)
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            logger.error("Gemini returned non-JSON: %r", text[:500])
            raise RuntimeError(f"Gemini response was not valid JSON: {exc}") from exc

        if not isinstance(data, dict):
            raise RuntimeError(f"Gemini returned non-object JSON: {type(data).__name__}")

        rule_evals = [
            RuleEvaluation(
                rule_id=r.get("rule_id", "unknown"),
                outcome=r.get("outcome", "skip"),
                evidence=r.get("evidence", ""),
                remediation=r.get("remediation"),
            )
            for r in (data.get("rule_evaluations") or [])
        ]

        # Defensive: derive sensible defaults if Gemini omitted required fields.
        # response_schema in generation_config should prevent this but belt-and-braces.
        overall_score = float(data.get("overall_score", 5.0))
        verdict = data.get("verdict") or _derive_verdict(rule_evals, overall_score)
        summary = data.get("summary") or _derive_summary(rule_evals)

        return Evaluation(
            overall_score=overall_score,
            verdict=verdict,
            summary=summary,
            rule_evaluations=rule_evals,
            rubric_version=self.rubric.get("version", ""),
            raw_response=data,
        )


def _derive_verdict(rule_evals: list[RuleEvaluation], score: float) -> str:
    if any(r.outcome == "fail" for r in rule_evals) and score <= 3:
        return "block"
    if any(r.outcome == "fail" for r in rule_evals):
        return "warn"
    return "pass"


def _derive_summary(rule_evals: list[RuleEvaluation]) -> str:
    fails = [r for r in rule_evals if r.outcome == "fail"]
    if not fails:
        return f"All {len(rule_evals)} rules passed or were not applicable."
    return f"{len(fails)} rule(s) failed: " + ", ".join(r.rule_id for r in fails[:3])


AGENT_COMMENT_MARKER = "<!-- mr-sentinel:v1 -->"


def render_comment(
    evaluation: Evaluation, mr: MergeRequest,
    *,
    followup_issue_url: str | None = None,
    pipeline_status: str | None = None,
) -> str:
    """Render the evaluation as a Markdown comment to post on the MR.

    Includes a hidden marker so we can find + update this comment instead of
    posting a new one on every re-evaluation.
    """
    verdict_emoji = {"pass": "✅", "warn": "⚠️", "block": "🛑"}.get(evaluation.verdict, "❔")
    lines = [
        AGENT_COMMENT_MARKER,
        f"## {verdict_emoji} MR Sentinel — verdict: **{evaluation.verdict}** (score {evaluation.overall_score:.1f}/10)",
        "",
        f"_Applied rubric `{evaluation.rubric_version}` to {len(evaluation.rule_evaluations)} rules._  ",
        f"_Commit `{mr.sha[:8]}` · pipeline `{pipeline_status or 'n/a'}`_",
        "",
        f"**Summary.** {evaluation.summary}",
        "",
    ]

    fails = [r for r in evaluation.rule_evaluations if r.outcome == "fail"]
    passes = [r for r in evaluation.rule_evaluations if r.outcome == "pass"]
    skips = [r for r in evaluation.rule_evaluations if r.outcome == "skip"]

    if fails:
        lines.append(f"### Failures ({len(fails)})")
        for r in fails:
            lines.append(f"- **`{r.rule_id}`** — {r.evidence}")
            if r.remediation:
                lines.append(f"  - _Remediation:_ {r.remediation}")
        lines.append("")

    if followup_issue_url:
        lines.append(f"📋 **Follow-up issue:** {followup_issue_url}")
        lines.append("")

    lines.append(
        f"<details><summary>Passes ({len(passes)}) · Skipped ({len(skips)})</summary>\n"
    )
    for r in passes:
        lines.append(f"- ✅ `{r.rule_id}` — {r.evidence}")
    for r in skips:
        lines.append(f"- ⏭️ `{r.rule_id}` — {r.evidence}")
    lines.append("\n</details>")

    return "\n".join(lines)


def render_followup_issue_body(evaluation: Evaluation, mr: MergeRequest) -> str:
    """Render a remediation issue body listing each failed rule as a checklist item."""
    fails = [r for r in evaluation.rule_evaluations if r.outcome == "fail"]
    lines = [
        f"Compliance follow-up for {mr.project_path}!{mr.iid} — _{mr.title}_.",
        "",
        f"MR Sentinel scored this merge request **{evaluation.overall_score:.1f}/10** ({evaluation.verdict}) against rubric `{evaluation.rubric_version}`.",
        "",
        f"Source: {mr.web_url}",
        f"Commit: `{mr.sha[:8]}`",
        "",
        f"## Failing rules ({len(fails)})",
        "",
    ]
    for r in fails:
        lines.append(f"- [ ] **`{r.rule_id}`** — {r.evidence}")
        if r.remediation:
            lines.append(f"      _Suggested fix:_ {r.remediation}")
    lines.append("")
    lines.append("_This issue was opened automatically by MR Sentinel. Close it when all checks pass on the MR._")
    return "\n".join(lines)
