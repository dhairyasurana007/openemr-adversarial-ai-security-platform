"""users table for api auth

Revision ID: 0004_users_table
Revises: 0003_regression_run_table
Create Date: 2026-05-13 23:59:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0004_users_table"
down_revision = "0003_regression_run_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    table_name = "users"

    if not inspector.has_table(table_name):
        op.create_table(
            table_name,
            sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("email", sa.String(length=320), nullable=False),
            sa.Column("hashed_password", sa.String(length=255), nullable=False),
            sa.Column("role", sa.String(length=32), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
        )

    existing_index_names = {idx["name"] for idx in inspector.get_indexes(table_name)}
    email_index = op.f("ix_users_email")
    role_index = op.f("ix_users_role")
    if email_index not in existing_index_names:
        op.create_index(email_index, table_name, ["email"], unique=True)
    if role_index not in existing_index_names:
        op.create_index(role_index, table_name, ["role"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_users_role"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
