from __future__ import annotations

import asyncio

from orchestration.graph import AgentGraph


async def main() -> None:
    graph = AgentGraph()
    await graph.run()


if __name__ == "__main__":
    asyncio.run(main())
