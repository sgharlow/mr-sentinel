"""Apply SQL migrations to Cloud SQL via cloud-sql-proxy + asyncpg.

Connects to localhost:<PROXY_PORT> (default 5433) where cloud-sql-proxy is
listening, applies each numbered *.sql file in db/migrations/, and records
applied versions in the schema_migrations table.

Usage:
    DB_PASSWORD=... PROXY_PORT=5433 python db/migrate.py [--dry-run]
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

import asyncpg

logger = logging.getLogger("db-migrate")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

REPO_ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = REPO_ROOT / "db" / "migrations"


async def applied_versions(conn: asyncpg.Connection) -> set[str]:
    has_table = await conn.fetchval(
        "SELECT 1 FROM information_schema.tables WHERE table_name = 'schema_migrations'"
    )
    if not has_table:
        return set()
    rows = await conn.fetch("SELECT version FROM schema_migrations")
    return {r["version"] for r in rows}


async def apply_one(conn: asyncpg.Connection, sql_file: Path, dry_run: bool) -> bool:
    version = sql_file.stem
    sql = sql_file.read_text(encoding="utf-8")
    logger.info("  %s (%d bytes)", version, len(sql))
    if dry_run:
        logger.info("    DRY_RUN — skipping apply")
        return False
    # asyncpg supports multi-statement strings via execute() (uses simple-query protocol)
    await conn.execute(sql)
    logger.info("    applied")
    return True


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--host", default=os.environ.get("DB_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PROXY_PORT", "5433")))
    parser.add_argument("--user", default=os.environ.get("DB_USER", "postgres"))
    parser.add_argument("--database", default=os.environ.get("DATABASE", "mrsentinel"))
    args = parser.parse_args()

    password = os.environ.get("DB_PASSWORD")
    if not password:
        logger.error("DB_PASSWORD env var is required")
        return 1

    conn = await asyncpg.connect(
        host=args.host, port=args.port, user=args.user,
        password=password, database=args.database,
    )

    try:
        already = await applied_versions(conn)
        logger.info("already applied: %s", sorted(already) or "(none)")

        sql_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
        if not sql_files:
            logger.warning("no migrations found in %s", MIGRATIONS_DIR)
            return 0

        applied_count = 0
        for sql_file in sql_files:
            if sql_file.stem in already:
                logger.info("  %s: already applied, skipping", sql_file.stem)
                continue
            if await apply_one(conn, sql_file, args.dry_run):
                applied_count += 1

        logger.info("done — applied %d migration(s)", applied_count)

        rows = await conn.fetch("SELECT version, applied_at FROM schema_migrations ORDER BY version")
        logger.info("final state:")
        for r in rows:
            logger.info("  %s @ %s", r["version"], r["applied_at"])
    finally:
        await conn.close()

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
