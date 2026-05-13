from __future__ import annotations

import uuid

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from state.db import Base


class RegressionRun(Base):
    __tablename__ = "regression_run"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    total_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    passed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    regressed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_tests: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    passed_tests: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    raw_output: Mapped[str] = mapped_column(String, nullable=False, default="")
