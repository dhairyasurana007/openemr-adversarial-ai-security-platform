"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-13 00:00:00
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

import state.models  # noqa: F401
from state.db import Base

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)

    coverage_table = sa.table(
        "coverage_map",
        sa.column("id", sa.dialects.postgresql.UUID(as_uuid=True)),
        sa.column("attack_category", sa.String()),
        sa.column("threat_model_ref", sa.String()),
        sa.column("total_attacks", sa.Integer()),
        sa.column("success_count", sa.Integer()),
        sa.column("partial_count", sa.Integer()),
        sa.column("failure_count", sa.Integer()),
        sa.column("residual_risk", sa.String()),
        sa.column("last_tested_at", sa.DateTime(timezone=True)),
        sa.column("last_patched_at", sa.DateTime(timezone=True)),
    )

    existing_categories = {
        row[0] for row in bind.execute(sa.text("SELECT attack_category FROM coverage_map"))
    }
    seed_rows = [
        {
            "id": uuid.uuid4(),
            "attack_category": "prompt_injection",
            "threat_model_ref": "THREAT_MODEL.md#3",
            "total_attacks": 0,
            "success_count": 0,
            "partial_count": 0,
            "failure_count": 0,
            "residual_risk": "HIGH",
            "last_tested_at": None,
            "last_patched_at": None,
        },
        {
            "id": uuid.uuid4(),
            "attack_category": "state_corruption",
            "threat_model_ref": "THREAT_MODEL.md#5",
            "total_attacks": 0,
            "success_count": 0,
            "partial_count": 0,
            "failure_count": 0,
            "residual_risk": "HIGH",
            "last_tested_at": None,
            "last_patched_at": None,
        },
        {
            "id": uuid.uuid4(),
            "attack_category": "data_exfiltration",
            "threat_model_ref": "THREAT_MODEL.md#4",
            "total_attacks": 0,
            "success_count": 0,
            "partial_count": 0,
            "failure_count": 0,
            "residual_risk": "HIGH",
            "last_tested_at": None,
            "last_patched_at": None,
        },
        {
            "id": uuid.uuid4(),
            "attack_category": "tool_misuse",
            "threat_model_ref": "THREAT_MODEL.md#6",
            "total_attacks": 0,
            "success_count": 0,
            "partial_count": 0,
            "failure_count": 0,
            "residual_risk": "HIGH",
            "last_tested_at": None,
            "last_patched_at": None,
        },
        {
            "id": uuid.uuid4(),
            "attack_category": "dos_cost",
            "threat_model_ref": "THREAT_MODEL.md#7",
            "total_attacks": 0,
            "success_count": 0,
            "partial_count": 0,
            "failure_count": 0,
            "residual_risk": "MEDIUM",
            "last_tested_at": None,
            "last_patched_at": None,
        },
        {
            "id": uuid.uuid4(),
            "attack_category": "identity_trust",
            "threat_model_ref": "THREAT_MODEL.md#8",
            "total_attacks": 0,
            "success_count": 0,
            "partial_count": 0,
            "failure_count": 0,
            "residual_risk": "HIGH",
            "last_tested_at": None,
            "last_patched_at": None,
        },
    ]
    missing_rows = [row for row in seed_rows if row["attack_category"] not in existing_categories]
    if missing_rows:
        op.bulk_insert(coverage_table, missing_rows)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
