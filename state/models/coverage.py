from __future__ import annotations

import uuid

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from state.db import Base


class CoverageMap(Base):
    __tablename__ = "coverage_map"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attack_category: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    threat_model_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    total_attacks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    partial_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    residual_risk: Mapped[str] = mapped_column(String(16), nullable=False)
    last_tested_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_patched_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
