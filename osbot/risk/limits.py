"""Hard risk limits: WEL, TWEL, max daily loss (stub)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskLimits:
    wallet_exposure_limit: float
    total_wallet_exposure_limit: float
    max_daily_loss_pct: float
