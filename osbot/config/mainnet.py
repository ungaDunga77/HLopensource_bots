from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from osbot.config.base import BaseConfig


class MainnetConfig(BaseConfig):
    """Mainnet requires explicit opt-in: `confirm_mainnet: true` in YAML."""

    mode: Literal["mainnet"] = "mainnet"
    confirm_mainnet: bool = Field(default=False)

    @model_validator(mode="after")
    def _require_explicit_opt_in(self) -> MainnetConfig:
        if not self.confirm_mainnet:
            raise ValueError(
                "MainnetConfig requires `confirm_mainnet: true` — explicit opt-in required"
            )
        return self
