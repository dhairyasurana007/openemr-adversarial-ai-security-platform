from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from state.db import Base


class TaxonomyTechnique(Base):
    __tablename__ = "taxonomy_techniques"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    atlas_tactic: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    technique_pattern: Mapped[str] = mapped_column(String, nullable=False)
    mutation_strategies: Mapped[str] = mapped_column(String, nullable=False)
    healthcare_relevance: Mapped[str] = mapped_column(String, nullable=False)
    severity_prior: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    threat_model_ref: Mapped[str | None] = mapped_column(String(256), nullable=True)
    copilot_trust_zone: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_ingested: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    source_url: Mapped[str] = mapped_column(String(512), nullable=False)
    deprecated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
