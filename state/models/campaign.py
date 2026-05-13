from __future__ import annotations

import uuid

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from state.db import Base


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, unique=True, index=True
    )
    execution_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    testing_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    target_category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    cost_cap_usd: Mapped[float] = mapped_column(Float, nullable=False)
    mutation_depth: Mapped[int] = mapped_column(Integer, nullable=False)
    concurrency: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    cost_so_far_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
