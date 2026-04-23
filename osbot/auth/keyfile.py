"""Keyfile load/save via eth_keyfile (JSON Web3 Secret Storage, scrypt/PBKDF2).

M1 uses the pre-built `eth_keyfile` package so we don't hand-roll crypto.
Returns raw 32-byte private key; caller is responsible for immediate use and
discard (no module-level caching).
"""

from __future__ import annotations

import json
from pathlib import Path

from eth_keyfile import create_keyfile_json, decode_keyfile_json  # type: ignore[attr-defined]

from osbot.connector.errors import AuthError


def load_keyfile(path: str | Path, password: str) -> bytes:
    p = Path(path)
    try:
        keyfile = json.loads(p.read_text())
    except FileNotFoundError as e:
        raise AuthError(f"keyfile not found: {p}", cause=e) from e
    except json.JSONDecodeError as e:
        raise AuthError(f"keyfile is not valid JSON: {p}", cause=e) from e
    try:
        return bytes(decode_keyfile_json(keyfile, password.encode("utf-8")))  # type: ignore[arg-type]
    except ValueError as e:
        raise AuthError("keyfile decrypt failed (wrong password?)", cause=e) from e


def save_keyfile(path: str | Path, private_key: bytes, password: str) -> None:
    p = Path(path)
    keyfile = create_keyfile_json(private_key, password.encode("utf-8"))  # type: ignore[arg-type]
    p.write_text(json.dumps(keyfile))
