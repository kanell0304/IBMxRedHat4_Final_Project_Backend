"""Add issue count columns to c_results

Revision ID: 7c9a4e8f4dcb
Revises: a3f8e9b2c1d4
Create Date: 2025-02-13 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7c9a4e8f4dcb"
down_revision: Union[str, Sequence[str], None] = "a3f8e9b2c1d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add missing issue count columns expected by the application models
    # Check if column exists before adding to avoid duplicate column error
    from sqlalchemy import inspect
    from alembic import op
    
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_columns = {col['name'] for col in inspector.get_columns('c_results')}
    
    if 'curse' not in existing_columns:
        op.add_column("c_results", sa.Column("curse", sa.Integer(), nullable=False, server_default="0"))
    if 'filler' not in existing_columns:
        op.add_column("c_results", sa.Column("filler", sa.Integer(), nullable=False, server_default="0"))
    if 'biased' not in existing_columns:
        op.add_column("c_results", sa.Column("biased", sa.Integer(), nullable=False, server_default="0"))
    if 'slang' not in existing_columns:
        op.add_column("c_results", sa.Column("slang", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    # Remove the issue count columns
    op.drop_column("c_results", "slang")
    op.drop_column("c_results", "biased")
    op.drop_column("c_results", "filler")
    op.drop_column("c_results", "curse")
