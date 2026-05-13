"""regression run table

Revision ID: 0003_regression_run_table
Revises: 0002_taxonomy_table
Create Date: 2026-05-13 23:30:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0003_regression_run_table"
down_revision = "0002_taxonomy_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if inspector.has_table("regression_run"):
        return

    op.create_table(
        "regression_run",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "run_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("total_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("passed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("regressed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "failed_tests",
            sa.dialects.postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "passed_tests",
            sa.dialects.postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("raw_output", sa.String(), nullable=False, server_default=""),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("regression_run")
