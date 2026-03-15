"""add_owner_password_resets

Revision ID: d9a41b7e2c6f
Revises: c1b7d3e9f4a2
Create Date: 2026-03-15 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "d9a41b7e2c6f"
down_revision: Union[str, Sequence[str], None] = "c1b7d3e9f4a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_owner_password_resets() -> None:
    op.create_table(
        "owner_password_resets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["owner_id"], ["owner_accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_owner_password_resets_id", "owner_password_resets", ["id"], unique=False)
    op.create_index("ix_owner_password_resets_owner_id", "owner_password_resets", ["owner_id"], unique=False)
    op.create_index("ix_owner_password_resets_token_hash", "owner_password_resets", ["token_hash"], unique=True)
    op.create_index("ix_owner_password_resets_expires_at", "owner_password_resets", ["expires_at"], unique=False)
    op.create_index("ix_owner_password_resets_used_at", "owner_password_resets", ["used_at"], unique=False)
    op.create_index("ix_owner_password_resets_created_at", "owner_password_resets", ["created_at"], unique=False)


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())

    if "owner_password_resets" not in tables:
        _create_owner_password_resets()


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())

    if "owner_password_resets" in tables:
        op.drop_index("ix_owner_password_resets_created_at", table_name="owner_password_resets")
        op.drop_index("ix_owner_password_resets_used_at", table_name="owner_password_resets")
        op.drop_index("ix_owner_password_resets_expires_at", table_name="owner_password_resets")
        op.drop_index("ix_owner_password_resets_token_hash", table_name="owner_password_resets")
        op.drop_index("ix_owner_password_resets_owner_id", table_name="owner_password_resets")
        op.drop_index("ix_owner_password_resets_id", table_name="owner_password_resets")
        op.drop_table("owner_password_resets")
