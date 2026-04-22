"""AES-CTR keyfile load/save (stub for M0). To be implemented in M1 via `eth_keyfile`."""

from __future__ import annotations

from pathlib import Path


def load_keyfile(path: str | Path, password: str) -> bytes:
    del path, password
    raise NotImplementedError("keyfile load deferred to M1")


def save_keyfile(path: str | Path, private_key: bytes, password: str) -> None:
    del path, private_key, password
    raise NotImplementedError("keyfile save deferred to M1")
