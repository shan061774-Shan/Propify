"""make unit rent amount real

Revision ID: 7e3fb72e4c91
Revises: 30cac156c554
Create Date: 2026-03-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7e3fb72e4c91"
down_revision: Union[str, Sequence[str], None] = "30cac156c554"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("units") as batch_op:
        batch_op.alter_column(
            "rent_amount",
            existing_type=sa.Integer(),
            type_=sa.Float(),
            existing_nullable=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("units") as batch_op:
        batch_op.alter_column(
            "rent_amount",
            existing_type=sa.Float(),
            type_=sa.Integer(),
            existing_nullable=False,
        )