"""add_owner_network_link_tables

Revision ID: c1b7d3e9f4a2
Revises: 8f9e2a9c4f01
Create Date: 2026-03-15 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "c1b7d3e9f4a2"
down_revision: Union[str, Sequence[str], None] = "8f9e2a9c4f01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_owner_tenant_links() -> None:
    op.create_table(
        "owner_tenant_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=True),
        sa.Column("phone", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="invited"),
        sa.Column("invited_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["owner_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id", "phone", name="uq_owner_tenant_phone"),
    )
    op.create_index("ix_owner_tenant_links_id", "owner_tenant_links", ["id"], unique=False)
    op.create_index("ix_owner_tenant_links_owner_id", "owner_tenant_links", ["owner_id"], unique=False)
    op.create_index("ix_owner_tenant_links_tenant_id", "owner_tenant_links", ["tenant_id"], unique=False)
    op.create_index("ix_owner_tenant_links_phone", "owner_tenant_links", ["phone"], unique=False)
    op.create_index("ix_owner_tenant_links_status", "owner_tenant_links", ["status"], unique=False)


def _create_owner_contractor_links() -> None:
    op.create_table(
        "owner_contractor_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("contractor_id", sa.Integer(), nullable=True),
        sa.Column("phone", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="invited"),
        sa.Column("invited_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["owner_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contractor_id"], ["contractors.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id", "phone", name="uq_owner_contractor_phone"),
    )
    op.create_index("ix_owner_contractor_links_id", "owner_contractor_links", ["id"], unique=False)
    op.create_index("ix_owner_contractor_links_owner_id", "owner_contractor_links", ["owner_id"], unique=False)
    op.create_index("ix_owner_contractor_links_contractor_id", "owner_contractor_links", ["contractor_id"], unique=False)
    op.create_index("ix_owner_contractor_links_phone", "owner_contractor_links", ["phone"], unique=False)
    op.create_index("ix_owner_contractor_links_status", "owner_contractor_links", ["status"], unique=False)


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())

    if "owner_tenant_links" not in tables:
        _create_owner_tenant_links()

    if "owner_contractor_links" not in tables:
        _create_owner_contractor_links()


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())

    if "owner_contractor_links" in tables:
        op.drop_index("ix_owner_contractor_links_status", table_name="owner_contractor_links")
        op.drop_index("ix_owner_contractor_links_phone", table_name="owner_contractor_links")
        op.drop_index("ix_owner_contractor_links_contractor_id", table_name="owner_contractor_links")
        op.drop_index("ix_owner_contractor_links_owner_id", table_name="owner_contractor_links")
        op.drop_index("ix_owner_contractor_links_id", table_name="owner_contractor_links")
        op.drop_table("owner_contractor_links")

    if "owner_tenant_links" in tables:
        op.drop_index("ix_owner_tenant_links_status", table_name="owner_tenant_links")
        op.drop_index("ix_owner_tenant_links_phone", table_name="owner_tenant_links")
        op.drop_index("ix_owner_tenant_links_tenant_id", table_name="owner_tenant_links")
        op.drop_index("ix_owner_tenant_links_owner_id", table_name="owner_tenant_links")
        op.drop_index("ix_owner_tenant_links_id", table_name="owner_tenant_links")
        op.drop_table("owner_tenant_links")
