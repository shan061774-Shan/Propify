"""add property late fee settings

Revision ID: c3f4a6c3bb12
Revises: 7e3fb72e4c91
Create Date: 2026-03-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3f4a6c3bb12"
down_revision: Union[str, Sequence[str], None] = "7e3fb72e4c91"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("properties") as batch_op:
        batch_op.add_column(sa.Column("grace_period_days", sa.Integer(), nullable=False, server_default="3"))
        batch_op.add_column(sa.Column("late_fee_amount", sa.Integer(), nullable=False, server_default="30"))


def downgrade() -> None:
    with op.batch_alter_table("properties") as batch_op:
        batch_op.drop_column("late_fee_amount")
        batch_op.drop_column("grace_period_days")