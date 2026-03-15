"""owner_phone_auth_and_block_flags

Revision ID: e4b2c8f19a31
Revises: d9a41b7e2c6f
Create Date: 2026-03-15 23:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "e4b2c8f19a31"
down_revision: Union[str, Sequence[str], None] = "d9a41b7e2c6f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(inspector) -> set[str]:
    return {col["name"] for col in inspector.get_columns("owner_accounts")}


def _index_names(inspector) -> set[str]:
    return {idx["name"] for idx in inspector.get_indexes("owner_accounts")}


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())
    if "owner_accounts" not in tables:
        return

    columns = _column_names(inspector)

    if "two_fa_enabled" not in columns:
        op.add_column("owner_accounts", sa.Column("two_fa_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
    if "is_blocked" not in columns:
        op.add_column("owner_accounts", sa.Column("is_blocked", sa.Boolean(), nullable=False, server_default=sa.false()))
    if "blocked_at" not in columns:
        op.add_column("owner_accounts", sa.Column("blocked_at", sa.DateTime(), nullable=True))
    if "blocked_reason" not in columns:
        op.add_column("owner_accounts", sa.Column("blocked_reason", sa.String(), nullable=True, server_default=""))

    # Backfill/normalize stored phone values by stripping spaces.
    op.execute("UPDATE owner_accounts SET owner_phone = REPLACE(owner_phone, ' ', '') WHERE owner_phone IS NOT NULL")

    inspector = inspect(conn)
    indexes = _index_names(inspector)
    if "ix_owner_accounts_owner_phone" not in indexes:
        op.create_index("ix_owner_accounts_owner_phone", "owner_accounts", ["owner_phone"], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())
    if "owner_accounts" not in tables:
        return

    indexes = _index_names(inspector)
    if "ix_owner_accounts_owner_phone" in indexes:
        op.drop_index("ix_owner_accounts_owner_phone", table_name="owner_accounts")

    columns = _column_names(inspector)
    if "blocked_reason" in columns:
        op.drop_column("owner_accounts", "blocked_reason")
    if "blocked_at" in columns:
        op.drop_column("owner_accounts", "blocked_at")
    if "is_blocked" in columns:
        op.drop_column("owner_accounts", "is_blocked")
    if "two_fa_enabled" in columns:
        op.drop_column("owner_accounts", "two_fa_enabled")
