from __future__ import annotations

import os
from pathlib import Path
from typing import Any, cast

import yaml

from osbot.config.base import BaseConfig
from osbot.config.mainnet import MainnetConfig
from osbot.config.testnet import TestnetConfig

_ENV_PREFIX = "OSBOT_"


def _apply_env_overrides(data: dict[str, Any]) -> dict[str, Any]:
    """Env vars with `OSBOT_` prefix override top-level fields (secrets only for M0)."""
    for key, value in os.environ.items():
        if not key.startswith(_ENV_PREFIX):
            continue
        field = key[len(_ENV_PREFIX) :].lower()
        if field in {"keyfile_password", "account_address", "keyfile_path"}:
            data[field] = value
    return data


def load_config(path: str | Path) -> BaseConfig:
    """Load YAML from path, apply env overrides, dispatch to Testnet/Mainnet by `mode`."""
    raw = yaml.safe_load(Path(path).read_text())
    if not isinstance(raw, dict):
        raise ValueError(f"Config root must be a mapping; got {type(raw).__name__}")
    data = cast(dict[str, Any], raw)
    data = _apply_env_overrides(data)

    mode = data.get("mode", "testnet")
    if mode == "testnet":
        return TestnetConfig.model_validate(data)
    if mode == "mainnet":
        return MainnetConfig.model_validate(data)
    raise ValueError(f"Unknown mode: {mode!r} (expected 'testnet' or 'mainnet')")
