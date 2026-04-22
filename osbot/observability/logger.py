"""Structured logger: `ts - logger - LEVEL - msg` format.

Format mirrored from Hummingbot per design notes §6. Intentionally plain-text at
M0; M2 can swap to JSON if we want structured-log ingestion.
"""

from __future__ import annotations

import logging
import sys

_FMT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
_STATE: dict[str, bool] = {"configured": False}


def _configure_root() -> None:
    if _STATE["configured"]:
        return
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(_FMT))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    # CCXT-style suppression baked in even though v0 doesn't use CCXT —
    # future-proofs against accidental pulls via transitive deps.
    logging.getLogger("ccxt").setLevel(logging.WARNING)
    _STATE["configured"] = True


def get_logger(name: str) -> logging.Logger:
    _configure_root()
    return logging.getLogger(name)
