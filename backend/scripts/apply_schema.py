"""Apply the idempotent Armstrong PostgreSQL schema during a Vercel backend build.

The database credential is injected by the Neon/Vercel integration.  This
script never prints it, and the SQL contains only CREATE ... IF NOT EXISTS
statements, so it is safe for a repeat production deployment.
"""

import os
from pathlib import Path

import psycopg


SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema.sql"


def main() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required to apply the Armstrong schema")

    with psycopg.connect(database_url, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(SCHEMA_PATH.read_text(encoding="utf-8"))

    print("Armstrong database schema is ready.")


if __name__ == "__main__":
    main()
