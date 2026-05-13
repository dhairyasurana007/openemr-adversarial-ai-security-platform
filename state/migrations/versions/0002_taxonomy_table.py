"""taxonomy techniques table

Revision ID: 0002_taxonomy_table
Revises: 0001_initial_schema
Create Date: 2026-05-13 00:30:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0002_taxonomy_table"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    table_name = "taxonomy_techniques"

    if not inspector.has_table(table_name):
        op.create_table(
            table_name,
            sa.Column("id", sa.String(length=128), nullable=False),
            sa.Column("source", sa.String(length=32), nullable=False),
            sa.Column("atlas_tactic", sa.String(length=128), nullable=False),
            sa.Column("category", sa.String(length=64), nullable=False),
            sa.Column("name", sa.String(length=256), nullable=False),
            sa.Column("description", sa.String(), nullable=False),
            sa.Column("technique_pattern", sa.String(), nullable=False),
            sa.Column("mutation_strategies", sa.String(), nullable=False),
            sa.Column("healthcare_relevance", sa.String(), nullable=False),
            sa.Column("severity_prior", sa.String(length=16), nullable=False),
            sa.Column("threat_model_ref", sa.String(length=256), nullable=True),
            sa.Column("copilot_trust_zone", sa.String(length=128), nullable=True),
            sa.Column("last_ingested", sa.DateTime(timezone=True), nullable=False),
            sa.Column("source_url", sa.String(length=512), nullable=False),
            sa.Column("deprecated", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("fingerprint", sa.String(length=64), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("fingerprint"),
        )

    existing_index_names = {idx["name"] for idx in inspector.get_indexes(table_name)}
    index_specs = [
        ("ix_taxonomy_techniques_source", ["source"], False),
        ("ix_taxonomy_techniques_category", ["category"], False),
        ("ix_taxonomy_techniques_severity_prior", ["severity_prior"], False),
        ("ix_taxonomy_techniques_last_ingested", ["last_ingested"], False),
        ("ix_taxonomy_techniques_deprecated", ["deprecated"], False),
        ("ix_taxonomy_techniques_fingerprint", ["fingerprint"], True),
    ]
    for name, columns, unique in index_specs:
        if name not in existing_index_names:
            op.create_index(name, table_name, columns, unique=unique)


def downgrade() -> None:
    op.drop_index("ix_taxonomy_techniques_fingerprint", table_name="taxonomy_techniques")
    op.drop_index("ix_taxonomy_techniques_deprecated", table_name="taxonomy_techniques")
    op.drop_index("ix_taxonomy_techniques_last_ingested", table_name="taxonomy_techniques")
    op.drop_index("ix_taxonomy_techniques_severity_prior", table_name="taxonomy_techniques")
    op.drop_index("ix_taxonomy_techniques_category", table_name="taxonomy_techniques")
    op.drop_index("ix_taxonomy_techniques_source", table_name="taxonomy_techniques")
    op.drop_table("taxonomy_techniques")
