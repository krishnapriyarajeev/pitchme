"""Logging setup: readable console output plus a rotating file per process."""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"


def configure_logging(level: str = "INFO", log_dir: str = "", filename: str = "server.log") -> None:
    """Configure the root logger. An empty `log_dir` logs to the console only."""
    handlers: list[logging.Handler] = [logging.StreamHandler()]

    if log_dir:
        path = Path(log_dir)
        path.mkdir(parents=True, exist_ok=True)
        handlers.append(
            logging.handlers.RotatingFileHandler(
                path / filename, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
            )
        )

    logging.basicConfig(level=level.upper(), format=FORMAT, handlers=handlers, force=True)

    # Third-party loggers that are too chatty at INFO.
    for noisy in ("httpx", "httpcore", "urllib3", "botocore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
