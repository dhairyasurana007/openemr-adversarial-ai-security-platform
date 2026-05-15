from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Ensure repository root is importable when executed as a script entrypoint.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from orchestration.graph import AgentGraph


async def main() -> None:
    graph = AgentGraph()
    await asyncio.gather(
        graph.run(),
        graph.judge.run_loop(),
        graph.documentation.run_loop(),
    )


if __name__ == "__main__":
    asyncio.run(main())
