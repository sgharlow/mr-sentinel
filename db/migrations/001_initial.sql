-- 001_initial.sql — MR Sentinel scoring + audit tables.
--
-- Idempotent: safe to re-run (CREATE TABLE IF NOT EXISTS).
-- Applied via scripts/db-migrate.sh which connects through Cloud SQL Auth Proxy.

BEGIN;

CREATE TABLE IF NOT EXISTS mr_scores (
    id              BIGSERIAL PRIMARY KEY,
    project_path    TEXT        NOT NULL,
    mr_iid          INTEGER     NOT NULL,
    commit_sha      TEXT        NOT NULL,
    rubric_version  TEXT        NOT NULL,
    overall_score   NUMERIC(3,1),
    verdict         TEXT        NOT NULL CHECK (verdict IN ('pass', 'warn', 'block')),
    scored_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw_evaluation  JSONB       NOT NULL,
    UNIQUE (project_path, mr_iid, commit_sha, rubric_version)
);

CREATE INDEX IF NOT EXISTS idx_mr_scores_project_mr ON mr_scores (project_path, mr_iid);
CREATE INDEX IF NOT EXISTS idx_mr_scores_scored_at ON mr_scores (scored_at DESC);

CREATE TABLE IF NOT EXISTS rule_outcomes (
    id              BIGSERIAL PRIMARY KEY,
    mr_score_id     BIGINT      NOT NULL REFERENCES mr_scores(id) ON DELETE CASCADE,
    rule_id         TEXT        NOT NULL,
    category        TEXT        NOT NULL,
    outcome         TEXT        NOT NULL CHECK (outcome IN ('pass', 'fail', 'skip')),
    severity        TEXT        NOT NULL,
    message         TEXT,
    remediation     TEXT,
    control_mapping TEXT[]      NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_rule_outcomes_score ON rule_outcomes (mr_score_id);
CREATE INDEX IF NOT EXISTS idx_rule_outcomes_rule ON rule_outcomes (rule_id);

CREATE TABLE IF NOT EXISTS audit_log (
    id              BIGSERIAL PRIMARY KEY,
    occurred_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actor           TEXT        NOT NULL,
    action          TEXT        NOT NULL,
    project_path    TEXT,
    mr_iid          INTEGER,
    details         JSONB       NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_audit_log_occurred ON audit_log (occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_project_mr ON audit_log (project_path, mr_iid);

CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO schema_migrations (version) VALUES ('001_initial')
ON CONFLICT (version) DO NOTHING;

COMMIT;
