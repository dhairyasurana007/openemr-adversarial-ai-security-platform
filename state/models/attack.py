from __future__ import annotations

import uuid

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from state.db import Base


class AttackRecord(Base):
    __tablename__ = "attack_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False, index=True
    )
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    threat_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    attack_category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    technique_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    prompt_sequence: Mapped[list[dict]] = mapped_column(JSONB, nullable=False)
    target_response: Mapped[str] = mapped_column(String, nullable=False)
    response_status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    connection_path: Mapped[str] = mapped_column(String(64), nullable=False)
    testing_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    token_cost_usd: Mapped[float] = mapped_column(Float, nullable=False)
    executed_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_variant: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    parent_attack_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
