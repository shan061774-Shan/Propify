"""Starter data migration script: SQLite -> Snowflake.

Usage:
  export SQLITE_URL='sqlite:///./rental.db'
  export SNOWFLAKE_URL='snowflake://user:password@account/db/schema?warehouse=WH&role=ROLE'
  python scripts/migrate_sqlite_to_snowflake.py

Notes:
- This script assumes schema already exists in Snowflake (run Alembic first).
- It does simple full-table copy in FK-safe order.
- For large datasets, replace with batched COPY/PUT strategy.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Iterable

from sqlalchemy import MetaData, Table, create_engine, select, text

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


SQLITE_URL = os.getenv("SQLITE_URL", "sqlite:///./rental.db")
SNOWFLAKE_URL = os.getenv("SNOWFLAKE_URL")
SNOWFLAKE_DATABASE = os.getenv("SNOWFLAKE_DATABASE", "PROPIFY_DB")
SNOWFLAKE_SCHEMA = os.getenv("SNOWFLAKE_SCHEMA", "APP")

TABLE_ORDER: list[str] = [
    "owner_accounts",
    "contractors",
    "properties",
    "tenants",
    "units",
    "leases",
    "maintenance_requests",
    "documents",
    "payments",
    "utility_charges",
]


def chunked(rows: list[dict], size: int = 1000) -> Iterable[list[dict]]:
    for i in range(0, len(rows), size):
        yield rows[i : i + size]


def main() -> None:
    if not SNOWFLAKE_URL:
        raise SystemExit("Set SNOWFLAKE_URL before running this script")

    src_engine = create_engine(SQLITE_URL)
    dst_engine = create_engine(SNOWFLAKE_URL)

    src_meta = MetaData()
    src_meta.reflect(bind=src_engine)

    with src_engine.connect() as src_conn, dst_engine.connect() as dst_conn:
        dst_conn.execute(text(f'CREATE DATABASE IF NOT EXISTS "{SNOWFLAKE_DATABASE}"'))
        dst_conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{SNOWFLAKE_DATABASE}"."{SNOWFLAKE_SCHEMA}"'))
        dst_conn.execute(text(f'USE DATABASE "{SNOWFLAKE_DATABASE}"'))
        dst_conn.execute(text(f'USE SCHEMA "{SNOWFLAKE_SCHEMA}"'))
        dst_conn.commit()

        dst_meta = MetaData()
        dst_meta.reflect(bind=dst_conn)

        missing_tables = [name for name in TABLE_ORDER if name in src_meta.tables and name not in dst_meta.tables]
        if missing_tables:
            build_meta = MetaData()
            for src_table in src_meta.tables.values():
                cloned = src_table.to_metadata(build_meta)
                # Snowflake does not support standard indexes on regular tables.
                for idx in list(cloned.indexes):
                    cloned.indexes.discard(idx)
            build_meta.create_all(bind=dst_conn, checkfirst=True)
            dst_conn.commit()
            dst_meta = MetaData()
            dst_meta.reflect(bind=dst_conn)

        for table_name in TABLE_ORDER:
            src_table: Table | None = src_meta.tables.get(table_name)
            dst_table: Table | None = dst_meta.tables.get(table_name)

            if src_table is None:
                print(f"[skip] source table missing: {table_name}")
                continue
            if dst_table is None:
                print(f"[skip] target table missing after create_all: {table_name}")
                continue

            rows = [dict(row) for row in src_conn.execute(select(src_table)).mappings().all()]

            print(f"[copy] {table_name}: {len(rows)} rows")
            if not rows:
                continue

            # Truncate target table first for deterministic full refresh.
            dst_conn.execute(dst_table.delete())

            for batch in chunked(rows, size=1000):
                dst_conn.execute(dst_table.insert(), batch)

        dst_conn.commit()

    print("Done: SQLite -> Snowflake migration completed.")


if __name__ == "__main__":
    main()
