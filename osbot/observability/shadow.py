"""SQLite shadow log.

Append-only state snapshots and fill records. Schema is intentionally tiny —
this is forensic / post-hoc inspection, not a primary store.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any


class ShadowLogger:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS snapshots ("
                "ts REAL NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS fills ("
                "ts REAL NOT NULL, tid TEXT NOT NULL UNIQUE, payload TEXT NOT NULL)"
            )

    def snapshot(self, kind: str, payload: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO snapshots (ts, kind, payload) VALUES (?, ?, ?)",
                (time.time(), kind, json.dumps(payload)),
            )

    def record_fill(self, tid: str, payload: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO fills (ts, tid, payload) VALUES (?, ?, ?)",
                (time.time(), tid, json.dumps(payload)),
            )
