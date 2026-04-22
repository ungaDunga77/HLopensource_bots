"""SQLite shadow log (stub for M0). Wired in M2."""

from __future__ import annotations

from pathlib import Path


class ShadowLogger:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
