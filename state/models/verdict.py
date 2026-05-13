from __future__ import annotations

import uuid

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from state.db import Base


class Verdict(Base):
    __tablename__ = "verdicts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attack_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("attack_records.id"), nullable=False, index=True
    )
    verdict: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_excerpt: Mapped[str] = mapped_column(String, nullable=False)
    layer_triggered: Mapped[str] = mapped_column(String(32), nullable=False)
    model_a_verdict: Mapped[str | None] = mapped_column(String(32), nullable=True)
    model_b_verdict: Mapped[str | None] = mapped_column(String(32), nullable=True)
    regression_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rubric_version: Mapped[str] = mapped_column(String(64), nullable=False)
    evaluated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    evaluator_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
