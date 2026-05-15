from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

_configured = False


def _configure() -> None:
    global _configured
    if _configured:
        return

    log_file = os.getenv(
        "AGENTS_LOG_FILE",
        str(Path(__file__).parents[1] / "logs" / "agents.log"),
    )
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger("agents")
    root.setLevel(logging.DEBUG)

    if root.handlers:
        _configured = True
        return

    fmt = logging.Formatter(
        "%(asctime)s [%(name)s] %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    fh = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB per file
        backupCount=5,
        encoding="utf-8",
    )
    fh.setFormatter(fmt)
    root.addHandler(fh)

    _configured = True


def get_logger(agent_name: str) -> logging.Logger:
    """Return a child logger scoped to the given agent name."""
    _configure()
    return logging.getLogger(f"agents.{agent_name}")
