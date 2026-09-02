"""Apply schema changes to whatever database DATABASE_URL points at.

Why this exists
---------------
This project has no migration tool. `seed_data.py` calls `create_all()`, which
creates MISSING TABLES but never alters an existing one, so a new column on an
existing model silently does not reach a database that already has the table.

That is not a theoretical problem. Adding `dispatched_at` in v1.17 took the
whole deployed API down: every endpoint touching `emergency_requests` returned
500, because SQLAlchemy selected a column the hosted table did not have, while
`/hospitals` and `/ambulances` kept working and made it look like a partial
outage rather than a schema mismatch.

This is deliberately not Alembic. It is an idempotent list of `ALTER TABLE`
statements that is safe to run on every deploy and on an already-current
database. Alembic is the right answer for a system with real data to preserve;
this is the honest minimum for a portfolio project, and it removes the manual
step that actually broke production.

Usage
-----
    python migrate.py              # uses DATABASE_URL, or localhost
"""

import os
import sys

from sqlalchemy import text

from app.db import engine

# Every statement here MUST be idempotent: safe to run twice, safe to run on a
# fresh database. Append new ones, never edit or reorder old ones.
MIGRATIONS = [
    (
        "emergency_requests.severity",
        "ALTER TABLE emergency_requests "
        "ADD COLUMN IF NOT EXISTS severity VARCHAR NOT NULL DEFAULT 'standard'",
    ),
    (
        "emergency_requests.required_facility",
        "ALTER TABLE emergency_requests "
        "ADD COLUMN IF NOT EXISTS required_facility VARCHAR",
    ),
    (
        "emergency_requests.dispatched_at",
        "ALTER TABLE emergency_requests "
        "ADD COLUMN IF NOT EXISTS dispatched_at TIMESTAMP",
    ),
    (
        "hospitals.has_icu",
        "ALTER TABLE hospitals "
        "ADD COLUMN IF NOT EXISTS has_icu BOOLEAN NOT NULL DEFAULT FALSE",
    ),
    (
        "hospitals.has_trauma_unit",
        "ALTER TABLE hospitals "
        "ADD COLUMN IF NOT EXISTS has_trauma_unit BOOLEAN NOT NULL DEFAULT FALSE",
    ),
    (
        "hospitals.has_cardiac_unit",
        "ALTER TABLE hospitals "
        "ADD COLUMN IF NOT EXISTS has_cardiac_unit BOOLEAN NOT NULL DEFAULT FALSE",
    ),
]


def main():
    target = os.environ.get("DATABASE_URL", "localhost default")
    # Never print the URL itself: it carries the password.
    print(f"Migrating: {'DATABASE_URL' if 'DATABASE_URL' in os.environ else target}")

    applied = 0
    with engine.begin() as conn:
        for name, statement in MIGRATIONS:
            try:
                conn.execute(text(statement))
                print(f"  ok   {name}")
                applied += 1
            except Exception as exc:  # noqa: BLE001 - report and keep going
                print(f"  FAIL {name}: {exc}", file=sys.stderr)
                return 1

    print(f"{applied} statement(s) applied. Schema is current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
