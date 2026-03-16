"""add_owner_admins

Revision ID: f2a7d9c1b8e3
Revises: e4b2c8f19a31
Create Date: 2026-03-15 23:59:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "f2a7d9c1b8e3"
down_revision: Union[str, Sequence[str], None] = "e4b2c8f19a31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _index_names(inspector) -> set[str]:
    return {idx["name"] for idx in inspector.get_indexes("owner_admins")}


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())
    if "owner_accounts" not in tables:
        return

    if "owner_admins" not in tables:
        op.create_table(
            "owner_admins",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("owner_id", sa.Integer(), nullable=False),
            sa.Column("phone", sa.String(), nullable=False),
            sa.Column("name", sa.String(), nullable=True, server_default=""),
            sa.Column("email", sa.String(), nullable=True, server_default=""),
            sa.Column("password_hash", sa.String(), nullable=True, server_default=""),
            sa.Column("password_salt", sa.String(), nullable=True, server_default=""),
            sa.Column("status", sa.String(), nullable=False, server_default="invited"),
            sa.Column("invited_at", sa.DateTime(), nullable=False),
            sa.Column("accepted_at", sa.DateTime(), nullable=True),
            sa.Column("approved_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["owner_id"], ["owner_accounts.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("owner_id", "phone", name="uq_owner_admin_phone"),
        )

    inspector = inspect(conn)
    indexes = _index_names(inspector)
    if "ix_owner_admins_owner_id" not in indexes:
        op.create_index("ix_owner_admins_owner_id", "owner_admins", ["owner_id"], unique=False)
    if "ix_owner_admins_phone" not in indexes:
        op.create_index("ix_owner_admins_phone", "owner_admins", ["phone"], unique=False)
    if "ix_owner_admins_status" not in indexes:
        op.create_index("ix_owner_admins_status", "owner_admins", ["status"], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())
    if "owner_admins" not in tables:
        return

    indexes = _index_names(inspector)
    if "ix_owner_admins_status" in indexes:
        op.drop_index("ix_owner_admins_status", table_name="owner_admins")
    if "ix_owner_admins_phone" in indexes:
        op.drop_index("ix_owner_admins_phone", table_name="owner_admins")
    if "ix_owner_admins_owner_id" in indexes:
        op.drop_index("ix_owner_admins_owner_id", table_name="owner_admins")
    op.drop_table("owner_admins")