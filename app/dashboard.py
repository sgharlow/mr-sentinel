"""Leadership dashboard — server-rendered HTML over the persisted scoring data.

Two routes:
- GET /dashboard         — portfolio-wide rollup over the last 30 days
- GET /audit/{project}/{mr_iid}  — per-MR audit log + rule outcomes

No Jinja2, no React, no JS framework — plain HTML strings with minimal CSS.
This is the spec §5 leadership UI surface, scoped to the MVP per the
2026-05-18 PRD decision (server-rendered, no Recharts).

The two routes are registered into the main FastAPI app at startup.
"""

from __future__ import annotations

import html
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Path
from fastapi.responses import HTMLResponse

logger = logging.getLogger("mr_sentinel.dashboard")

router = APIRouter()

# --- CSS shared by both pages -----------------------------------------------

_CSS = """
:root {
  --bg: #0b1220; --panel: #131c2e; --ink: #e6edf3; --mute: #8b95a7;
  --pass: #2ea043; --warn: #d29922; --block: #cf222e; --link: #58a6ff;
  --border: #1f2940;
}
* { box-sizing: border-box; }
body { margin: 0; padding: 2rem 1.5rem; font: 14px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
       background: var(--bg); color: var(--ink); }
header { display: flex; align-items: baseline; gap: 1rem; margin-bottom: 1.5rem; }
header h1 { font-size: 1.4rem; margin: 0; font-weight: 600; }
header .sub { color: var(--mute); font-size: 0.9rem; }
.container { max-width: 960px; margin: 0 auto; }
.panel { background: var(--panel); border: 1px solid var(--border); border-radius: 6px;
         padding: 1.25rem 1.5rem; margin-bottom: 1.25rem; }
.panel h2 { margin: 0 0 0.75rem 0; font-size: 1.05rem; font-weight: 600; }
.kv { display: grid; grid-template-columns: max-content 1fr; gap: 0.35rem 1.25rem; }
.kv dt { color: var(--mute); }
.bar-row { display: grid; grid-template-columns: 80px 1fr 60px; align-items: center;
           gap: 0.75rem; margin: 0.4rem 0; }
.bar-row .label { color: var(--mute); }
.bar { height: 14px; border-radius: 3px; background: var(--border); }
.bar > span { display: block; height: 100%; border-radius: 3px; }
.bar.pass > span { background: var(--pass); }
.bar.warn > span { background: var(--warn); }
.bar.block > span { background: var(--block); }
.bar-row .count { text-align: right; font-variant-numeric: tabular-nums; }
table { width: 100%; border-collapse: collapse; }
th, td { text-align: left; padding: 0.5rem 0.6rem; border-bottom: 1px solid var(--border); }
th { color: var(--mute); font-weight: 500; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.04em; }
td.num { font-variant-numeric: tabular-nums; text-align: right; }
.tag { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 0.8rem; }
.tag.pass { background: rgba(46, 160, 67, 0.16); color: var(--pass); }
.tag.warn { background: rgba(210, 153, 34, 0.16); color: var(--warn); }
.tag.block { background: rgba(207, 34, 46, 0.16); color: var(--block); }
.tag.skip { background: rgba(139, 149, 167, 0.16); color: var(--mute); }
a { color: var(--link); text-decoration: none; }
a:hover { text-decoration: underline; }
.empty { color: var(--mute); font-style: italic; }
.muted { color: var(--mute); font-size: 0.85rem; }
.mono { font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace; font-size: 0.85rem; }
"""


def _page(title: str, body: str) -> str:
    """Wrap a body fragment in the full HTML shell."""
    return (
        "<!doctype html>\n"
        f"<html lang=\"en\"><head><meta charset=\"utf-8\">"
        f"<title>{html.escape(title)} · MR Sentinel</title>"
        f"<style>{_CSS}</style></head><body><div class=\"container\">{body}"
        "</div></body></html>"
    )


def _verdict_tag(verdict: str) -> str:
    v = (verdict or "").lower()
    cls = v if v in ("pass", "warn", "block") else "skip"
    return f'<span class="tag {cls}">{html.escape(v or "—")}</span>'


def _outcome_tag(outcome: str) -> str:
    o = (outcome or "").lower()
    cls = "pass" if o == "pass" else "block" if o == "fail" else "skip"
    return f'<span class="tag {cls}">{html.escape(o or "—")}</span>'


# --- /dashboard -------------------------------------------------------------

async def _dashboard_data(window_days: int = 30) -> dict[str, Any]:
    """Pull the portfolio-wide rollup from Cloud SQL."""
    from app.persistence import get_pool

    pool = await get_pool()
    since = datetime.now(tz=timezone.utc) - timedelta(days=window_days)

    async with pool.acquire() as conn:
        total = await conn.fetchval(
            "SELECT COUNT(*) FROM mr_scores WHERE scored_at >= $1", since
        )
        verdict_rows = await conn.fetch(
            """
            SELECT verdict, COUNT(*) AS n
            FROM mr_scores
            WHERE scored_at >= $1
            GROUP BY verdict
            ORDER BY n DESC
            """,
            since,
        )
        top_rules = await conn.fetch(
            """
            SELECT ro.rule_id, COUNT(*) AS n
            FROM rule_outcomes ro
            JOIN mr_scores s ON s.id = ro.mr_score_id
            WHERE s.scored_at >= $1 AND ro.outcome = 'fail'
            GROUP BY ro.rule_id
            ORDER BY n DESC
            LIMIT 5
            """,
            since,
        )
        recent_mrs = await conn.fetch(
            """
            SELECT project_path, mr_iid, verdict, overall_score, rubric_version, scored_at
            FROM mr_scores
            WHERE scored_at >= $1
            ORDER BY scored_at DESC
            LIMIT 10
            """,
            since,
        )

    return {
        "window_days": window_days,
        "total": int(total or 0),
        "verdicts": [{"verdict": r["verdict"], "n": int(r["n"])} for r in verdict_rows],
        "top_rules": [{"rule_id": r["rule_id"], "n": int(r["n"])} for r in top_rules],
        "recent_mrs": [
            {
                "project_path": r["project_path"],
                "mr_iid": int(r["mr_iid"]),
                "verdict": r["verdict"],
                "overall_score": float(r["overall_score"]) if r["overall_score"] is not None else None,
                "rubric_version": r["rubric_version"],
                "scored_at": r["scored_at"],
            }
            for r in recent_mrs
        ],
    }


def _render_dashboard(data: dict[str, Any]) -> str:
    """Render dashboard data dict to HTML. Pure function — testable without a DB."""
    window = data["window_days"]
    total = data["total"]
    verdicts = data["verdicts"]
    top_rules = data["top_rules"]
    recent = data["recent_mrs"]

    if total == 0:
        body = (
            f'<header><h1>MR Sentinel</h1><span class="sub">Leadership dashboard · last {window}d</span></header>'
            f'<div class="panel"><p class="empty">No evaluations recorded in the last {window} days.</p>'
            f'<p class="muted">The dashboard populates as MRs are scored. See <span class="mono">/health</span> for liveness.</p></div>'
        )
        return _page("Dashboard", body)

    verdict_max = max((v["n"] for v in verdicts), default=1) or 1
    verdict_bars = "".join(
        f'<div class="bar-row">'
        f'<span class="label">{html.escape(v["verdict"])}</span>'
        f'<div class="bar {html.escape(v["verdict"])}"><span style="width: {(v["n"] / verdict_max) * 100:.1f}%"></span></div>'
        f'<span class="count">{v["n"]}</span>'
        f'</div>'
        for v in verdicts
    )

    if top_rules:
        rule_max = max((r["n"] for r in top_rules), default=1) or 1
        rule_bars = "".join(
            f'<div class="bar-row">'
            f'<span class="label mono">{html.escape(r["rule_id"])}</span>'
            f'<div class="bar block"><span style="width: {(r["n"] / rule_max) * 100:.1f}%"></span></div>'
            f'<span class="count">{r["n"]}</span>'
            f'</div>'
            for r in top_rules
        )
        rules_panel = f'<div class="panel"><h2>Top-5 rules failing</h2>{rule_bars}</div>'
    else:
        rules_panel = '<div class="panel"><h2>Top-5 rules failing</h2><p class="empty">No rule failures in window.</p></div>'

    recent_rows = "".join(
        f'<tr>'
        f'<td><a href="/audit/{html.escape(m["project_path"])}/{m["mr_iid"]}">'
        f'{html.escape(m["project_path"])}!{m["mr_iid"]}</a></td>'
        f'<td>{_verdict_tag(m["verdict"])}</td>'
        f'<td class="num">{(m["overall_score"] or 0):.1f}</td>'
        f'<td class="mono">{html.escape(m["rubric_version"] or "—")}</td>'
        f'<td class="muted">{html.escape(m["scored_at"].strftime("%Y-%m-%d %H:%M UTC") if m["scored_at"] else "—")}</td>'
        f'</tr>'
        for m in recent
    )

    body = (
        f'<header><h1>MR Sentinel</h1><span class="sub">Leadership dashboard · last {window}d</span></header>'
        f'<div class="panel"><h2>This window</h2>'
        f'<dl class="kv"><dt>MRs scored</dt><dd>{total}</dd>'
        f'<dt>Latest scored</dt><dd>{html.escape(recent[0]["scored_at"].strftime("%Y-%m-%d %H:%M UTC") if recent and recent[0]["scored_at"] else "—")}</dd></dl></div>'
        f'<div class="panel"><h2>Verdict distribution</h2>{verdict_bars}</div>'
        f'{rules_panel}'
        f'<div class="panel"><h2>Recent MRs</h2>'
        f'<table><thead><tr><th>MR</th><th>Verdict</th><th>Score</th><th>Rubric</th><th>Scored</th></tr></thead>'
        f'<tbody>{recent_rows}</tbody></table></div>'
    )
    return _page("Dashboard", body)


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard() -> str:
    data = await _dashboard_data()
    return _render_dashboard(data)


# --- /audit/{project_path:path}/{mr_iid} ------------------------------------

async def _audit_data(project_path: str, mr_iid: int) -> dict[str, Any] | None:
    """Pull the audit-log + rule outcomes for one MR. Returns None if no scores exist."""
    from app.persistence import get_pool

    pool = await get_pool()
    async with pool.acquire() as conn:
        score = await conn.fetchrow(
            """
            SELECT id, commit_sha, rubric_version, overall_score, verdict, scored_at
            FROM mr_scores
            WHERE project_path = $1 AND mr_iid = $2
            ORDER BY scored_at DESC
            LIMIT 1
            """,
            project_path, mr_iid,
        )
        if score is None:
            return None

        rules = await conn.fetch(
            """
            SELECT rule_id, category, outcome, severity, message, remediation, control_mapping
            FROM rule_outcomes
            WHERE mr_score_id = $1
            ORDER BY
              CASE outcome WHEN 'fail' THEN 0 WHEN 'pass' THEN 1 WHEN 'skip' THEN 2 ELSE 3 END,
              rule_id
            """,
            score["id"],
        )

        audit_rows = await conn.fetch(
            """
            SELECT occurred_at, actor, action, details
            FROM audit_log
            WHERE project_path = $1 AND mr_iid = $2
            ORDER BY occurred_at DESC
            LIMIT 50
            """,
            project_path, mr_iid,
        )

    return {
        "project_path": project_path,
        "mr_iid": mr_iid,
        "score": {
            "commit_sha": score["commit_sha"],
            "rubric_version": score["rubric_version"],
            "overall_score": float(score["overall_score"]) if score["overall_score"] is not None else None,
            "verdict": score["verdict"],
            "scored_at": score["scored_at"],
        },
        "rules": [
            {
                "rule_id": r["rule_id"], "category": r["category"], "outcome": r["outcome"],
                "severity": r["severity"], "message": r["message"], "remediation": r["remediation"],
                "control_mapping": list(r["control_mapping"] or []),
            }
            for r in rules
        ],
        "audit": [
            {
                "occurred_at": r["occurred_at"], "actor": r["actor"], "action": r["action"],
                "details": r["details"],
            }
            for r in audit_rows
        ],
    }


def _render_audit(data: dict[str, Any]) -> str:
    """Render audit-log data dict to HTML. Pure function."""
    project = data["project_path"]
    iid = data["mr_iid"]
    s = data["score"]
    sha8 = (s["commit_sha"] or "")[:8]

    rule_rows = "".join(
        f'<tr>'
        f'<td class="mono">{html.escape(r["rule_id"])}</td>'
        f'<td class="muted">{html.escape(r["category"])}</td>'
        f'<td>{_outcome_tag(r["outcome"])}</td>'
        f'<td class="muted">{html.escape(r["severity"])}</td>'
        f'<td class="mono muted">{html.escape(", ".join(r["control_mapping"]))}</td>'
        f'<td>{html.escape(r["message"] or "")}</td>'
        f'</tr>'
        for r in data["rules"]
    )

    audit_rows = "".join(
        f'<tr>'
        f'<td class="muted">{html.escape(r["occurred_at"].strftime("%Y-%m-%d %H:%M:%S UTC") if r["occurred_at"] else "—")}</td>'
        f'<td class="mono">{html.escape(r["actor"])}</td>'
        f'<td class="mono">{html.escape(r["action"])}</td>'
        f'<td class="mono muted">{html.escape(str(r["details"]))[:200]}</td>'
        f'</tr>'
        for r in data["audit"]
    )

    body = (
        f'<header><h1>MR Sentinel</h1>'
        f'<span class="sub">Audit log · <a href="/dashboard">← dashboard</a></span></header>'
        f'<div class="panel"><h2>{html.escape(project)}!{iid}</h2>'
        f'<dl class="kv">'
        f'<dt>Verdict</dt><dd>{_verdict_tag(s["verdict"])}</dd>'
        f'<dt>Score</dt><dd>{(s["overall_score"] or 0):.1f} / 10</dd>'
        f'<dt>Rubric</dt><dd class="mono">{html.escape(s["rubric_version"] or "—")}</dd>'
        f'<dt>Commit</dt><dd class="mono">{html.escape(sha8)}</dd>'
        f'<dt>Scored</dt><dd class="muted">{html.escape(s["scored_at"].strftime("%Y-%m-%d %H:%M:%S UTC") if s["scored_at"] else "—")}</dd>'
        f'</dl></div>'
        f'<div class="panel"><h2>Rule outcomes ({len(data["rules"])})</h2>'
        f'<table><thead><tr><th>Rule</th><th>Category</th><th>Outcome</th><th>Severity</th>'
        f'<th>Controls</th><th>Evidence</th></tr></thead>'
        f'<tbody>{rule_rows}</tbody></table></div>'
        f'<div class="panel"><h2>Audit log ({len(data["audit"])})</h2>'
        f'<table><thead><tr><th>When</th><th>Actor</th><th>Action</th><th>Details</th></tr></thead>'
        f'<tbody>{audit_rows}</tbody></table></div>'
    )
    return _page(f"Audit · {project}!{iid}", body)


@router.get("/audit/{project_path:path}/{mr_iid}", response_class=HTMLResponse)
async def audit(
    project_path: str = Path(..., description="GitLab project path-with-namespace, e.g. sgharlow/governance-demo-app"),
    mr_iid: int = Path(..., ge=1),
) -> str:
    data = await _audit_data(project_path, mr_iid)
    if data is None:
        raise HTTPException(status_code=404, detail=f"no evaluations recorded for {project_path}!{mr_iid}")
    return _render_audit(data)
