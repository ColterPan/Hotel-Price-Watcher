"""Logging setup. Application code uses logging, never print()."""

from __future__ import annotations

import logging
import sys

_CONFIGURED = False


def configure_logging(level: str | int = logging.INFO) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
    )
    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(handler)
    # httpx logs every request URL at INFO, which would leak the SerpApi key
    # (it travels as a query parameter) into the logs.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)
