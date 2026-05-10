from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class PairOverrides(BaseModel):
    """Per-pair strategy parameter overrides. Fields left None use the base config."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    leverage: int | None = Field(default=None, ge=1, le=50)
    grid_levels: int | None = Field(default=None, ge=1, le=50)
    range_bps_min: int | None = Field(default=None, ge=1)
    tp_pct: float | None = Field(default=None, gt=0, le=0.1)
    sl_pct: float | None = Field(default=None, gt=0, le=0.5)
    exit_ttl_s: int | None = Field(default=None, ge=60)
    inventory_skew_gamma: float | None = Field(default=None, ge=0.0)


class StrategyConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    dex: str | None = None
    pair: str = "BTC"
    leverage: int = Field(default=3, ge=1, le=50)
    grid_levels: int = Field(default=7, ge=1, le=50)
    wallet_exposure_limit: float = Field(default=0.30, gt=0, le=1.0)
    range_bps_min: int = Field(default=30, ge=1)
    rolling_sigma_window_min: int = Field(default=60, ge=1)
    tp_pct: float = Field(default=0.0015, gt=0, le=0.1)
    sl_pct: float = Field(default=0.015, gt=0, le=0.5)
    exit_ttl_s: int = Field(default=86_400, ge=60)
    sl_consecutive_breaches: int = Field(default=2, ge=1, le=10)
    # Avellaneda-Stoikov inventory skew (todo §10). Default 0 disables — grid stays
    # symmetric around mid. Source: evaluations/avellaneda-mm-freqtrade B3.
    inventory_skew_gamma: float = Field(default=0.0, ge=0.0)
    inventory_skew_horizon_s: float = Field(default=300.0, gt=0.0)
    pair_overrides: dict[str, PairOverrides] = Field(default_factory=dict)


class RiskConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    max_daily_loss_pct: float = Field(default=0.05, gt=0, le=1.0)
    min_notional_usd: float = Field(default=10.0, gt=0)


DEFAULT_FORAGER_PAIRS: list[str] = [
    "BTC", "ETH", "SOL", "HYPE", "DOGE", "ARB", "AVAX", "BNB",
]


class ForagerConfig(BaseModel):
    """Multi-pair selection (Passivbot-style log_range * volume ranker).

    Disabled by default — when off, the runner uses cfg.strategy.pair only and
    behavior is identical to single-pair mode. lessons.md:205 — Trial #2
    (single-position forager, top_n=1) was the best per-hour return across
    four trials; multi-position dilutes the gain.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = False
    candidate_pairs: list[str] = Field(default_factory=lambda: list(DEFAULT_FORAGER_PAIRS))
    top_n: int = Field(default=1, ge=1, le=10)
    rotate_every_s: int = Field(default=1800, ge=60)
    log_range_window_min: int = Field(default=16, ge=4)
    min_volume_usd_24h: float = Field(default=10_000.0, ge=0)


class ObservabilityConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    shadow_db_path: str = "data/shadow.sqlite"
    health_port: int = Field(default=8080, ge=1024, le=65535)
    telegram_chat_id: SecretStr | None = None
    telegram_bot_token: SecretStr | None = None


class BaseConfig(BaseModel):
    """Base config; never instantiated directly. Use TestnetConfig / MainnetConfig."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    mode: Literal["testnet", "mainnet"]
    account_address: str
    keyfile_path: str
    keyfile_password: SecretStr
    strategy: StrategyConfig = Field(default_factory=StrategyConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    forager: ForagerConfig = Field(default_factory=ForagerConfig)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)

    @property
    def is_secure(self) -> bool:
        """Marker per design notes §1: every config is secret-aware."""
        return True
