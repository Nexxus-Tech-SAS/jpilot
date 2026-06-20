"""Configure application loggers for uvicorn (which only configures its own loggers)."""

from __future__ import annotations

import logging
import sys


def configure_app_logging(level: int = logging.INFO) -> None:
    """Attach a stdout handler to the ``app`` logger tree once."""
    app_logger = logging.getLogger("app")
    if app_logger.handlers:
        return
    app_logger.setLevel(level)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(message)s"))
    app_logger.addHandler(handler)
    app_logger.propagate = False
