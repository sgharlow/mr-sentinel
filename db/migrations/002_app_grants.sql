-- 002_app_grants.sql — give the `app` user write access to schema objects.
--
-- The `app` user was created via `gcloud sql users create` which grants CONNECT
-- to the database but no default privileges on tables/sequences owned by
-- postgres. Without this, asyncpg INSERTs from the Cloud Run service fail with
-- "permission denied for table mr_scores".

BEGIN;

GRANT USAGE ON SCHEMA public TO app;

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app;

-- Future tables/sequences created in this schema by postgres will also be
-- accessible by app, so we don't need to re-grant after each migration.
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO app;

INSERT INTO schema_migrations (version) VALUES ('002_app_grants')
ON CONFLICT (version) DO NOTHING;

COMMIT;
