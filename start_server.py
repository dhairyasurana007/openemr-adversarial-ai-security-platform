from __future__ import annotations

import os
import subprocess
import sys


def main() -> int:
    migrate = subprocess.run(["alembic", "upgrade", "head"], check=False)
    if migrate.returncode != 0:
        return migrate.returncode

    port = os.getenv("PORT", "10000")
    server = subprocess.run(
        ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", port],
        check=False,
    )
    return server.returncode


if __name__ == "__main__":
    raise SystemExit(main())

