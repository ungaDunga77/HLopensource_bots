from __future__ import annotations

from typing import Literal

from osbot.config.base import BaseConfig


class TestnetConfig(BaseConfig):
    mode: Literal["testnet"] = "testnet"
