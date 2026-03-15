"""add_owner_id_to_properties

Revision ID: 8f9e2a9c4f01
Revises: 4073e2513c19
Create Date: 2026-03-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "8f9e2a9c4f01"
down_revision: Union[str, Sequence[str], None] = "4073e2513c19"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_columns = {col["name"] for col in inspector.get_columns("properties")}
    existing_indexes = {idx["name"] for idx in inspector.get_indexes("properties")}

    if conn.dialect.name == "sqlite":
        if "owner_id" not in existing_columns:
            with op.batch_alter_table("properties", recreate="auto") as batch_op:
                batch_op.add_column(sa.Column("owner_id", sa.Integer(), nullable=True))
                batch_op.create_index("ix_properties_owner_id", ["owner_id"], unique=False)
                batch_op.create_foreign_key(
                    "fk_properties_owner_id",
                    "owner_accounts",
                    ["owner_id"],
                    ["id"],
                    ondelete="CASCADE",
                )
        elif "ix_properties_owner_id" not in existing_indexes:
            op.create_index("ix_properties_owner_id", "properties", ["owner_id"], unique=False)
    else:
        if "owner_id" not in existing_columns:
            op.add_column("properties", sa.Column("owner_id", sa.Integer(), nullable=True))
        if "ix_properties_owner_id" not in existing_indexes:
            op.create_index("ix_properties_owner_id", "properties", ["owner_id"], unique=False)

        existing_fks = {fk.get("name") for fk in inspector.get_foreign_keys("properties")}
        if "fk_properties_owner_id" not in existing_fks:
            op.create_foreign_key(
                "fk_properties_owner_id",
                "properties",
                "owner_accounts",
                ["owner_id"],
                ["id"],
                ondelete="CASCADE",
            )

    row = conn.execute(sa.text("SELECT id FROM owner_accounts ORDER BY id LIMIT 1")).fetchone()
    if row and row[0] is not None:
        conn.execute(sa.text("UPDATE properties SET owner_id = :owner_id WHERE owner_id IS NULL"), {"owner_id": row[0]})


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_columns = {col["name"] for col in inspector.get_columns("properties")}
    existing_indexes = {idx["name"] for idx in inspector.get_indexes("properties")}

    if conn.dialect.name == "sqlite":
        if "owner_id" in existing_columns:
            with op.batch_alter_table("properties", recreate="auto") as batch_op:
                if "ix_properties_owner_id" in existing_indexes:
                    batch_op.drop_index("ix_properties_owner_id")
                batch_op.drop_column("owner_id")
    else:
        existing_fks = {fk.get("name") for fk in inspector.get_foreign_keys("properties")}
        if "fk_properties_owner_id" in existing_fks:
            op.drop_constraint("fk_properties_owner_id", "properties", type_="foreignkey")
        if "ix_properties_owner_id" in existing_indexes:
            op.drop_index("ix_properties_owner_id", table_name="properties")
        if "owner_id" in existing_columns:
            op.drop_column("properties", "owner_id")
