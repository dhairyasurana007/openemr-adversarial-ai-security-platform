from __future__ import annotations

import asyncio
import json
import os

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from state.models.taxonomy import TaxonomyTechnique
from taxonomy.healthcare import HealthcareIngestor
from taxonomy.ingest.atlas import AtlasIngestor
from taxonomy.ingest.garak import GarakIngestor
from taxonomy.ingest.harmbench import HarmBenchIngestor
from taxonomy.ingest.jailbreakbench import JailbreakBenchIngestor
from taxonomy.normalize import TechniqueRecord


class TaxonomyRefresher:
    def __init__(self) -> None:
        self.engine = create_async_engine(os.environ["DATABASE_URL"], echo=False)
        self.session_maker = async_sessionmaker(self.engine, expire_on_commit=False)
        self.ingestors = [
            AtlasIngestor(),
            GarakIngestor(),
            HarmBenchIngestor(),
            JailbreakBenchIngestor(),
            HealthcareIngestor(),
        ]

    async def refresh(self) -> dict[str, int]:
        all_records: list[TechniqueRecord] = []
        for ingestor in self.ingestors:
            all_records.extend(await ingestor.ingest())

        seen_fingerprints = {record.fingerprint for record in all_records}
        inserted = 0
        updated = 0
        deprecated = 0

        async with self.session_maker() as session:
            existing = (
                await session.execute(select(TaxonomyTechnique.fingerprint, TaxonomyTechnique.id))
            ).all()
            existing_fingerprints = {row[0] for row in existing}
            existing_ids = {row[1] for row in existing}

            for record in all_records:
                if record.fingerprint in existing_fingerprints:
                    db_row = await session.get(TaxonomyTechnique, record.id)
                    if db_row is not None:
                        db_row.deprecated = False
                        updated += 1
                    continue
                payload = record.model_dump()
                payload["mutation_strategies"] = json.dumps(payload["mutation_strategies"])
                session.add(TaxonomyTechnique(**payload))
                inserted += 1

            current_ids = {r.id for r in all_records}
            stale_ids = existing_ids.difference(current_ids)
            for stale_id in stale_ids:
                row = await session.get(TaxonomyTechnique, stale_id)
                if row and not row.deprecated:
                    row.deprecated = True
                    deprecated += 1

            # Also deprecate same id+changed description records not present by fingerprint.
            if seen_fingerprints:
                rows = (await session.execute(select(TaxonomyTechnique))).scalars().all()
                for row in rows:
                    if (
                        row.fingerprint not in seen_fingerprints
                        and row.id in current_ids
                        and not row.deprecated
                    ):
                        row.deprecated = True
                        deprecated += 1

            await session.commit()

        return {"inserted": inserted, "updated": updated, "deprecated": deprecated}


async def _amain() -> None:
    summary = await TaxonomyRefresher().refresh()
    print(summary)


if __name__ == "__main__":
    asyncio.run(_amain())
