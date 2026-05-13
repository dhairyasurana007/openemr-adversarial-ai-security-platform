from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from state.models.regression import RegressionRun


class RegressionReporter:
    async def history(self, db: AsyncSession) -> list[dict]:
        result = await db.execute(select(RegressionRun).order_by(RegressionRun.run_at.desc()))
        rows = result.scalars().all()
        return [
            {
                "id": str(row.id),
                "run_at": row.run_at.isoformat() if row.run_at else None,
                "total": row.total_count,
                "passed": row.passed_count,
                "failed": row.failed_count,
                "regressed": row.regressed_count,
                "failed_tests": row.failed_tests,
                "passed_tests": row.passed_tests,
            }
            for row in rows
        ]

    async def diff_report(self, db: AsyncSession) -> dict:
        result = await db.execute(
            select(RegressionRun).order_by(RegressionRun.run_at.desc()).limit(2)
        )
        runs = result.scalars().all()

        if not runs:
            return {"newly_failed": [], "newly_passed": [], "current_failed": []}

        latest = runs[0]
        previous_failed = set(runs[1].failed_tests if len(runs) > 1 else [])
        latest_failed = set(latest.failed_tests)

        return {
            "newly_failed": sorted(latest_failed - previous_failed),
            "newly_passed": sorted(previous_failed - latest_failed),
            "current_failed": sorted(latest_failed),
        }
