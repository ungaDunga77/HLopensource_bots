"""osbot entry point.

M0 supports only `--dry-run`: loads config, prints redacted summary, exits 0.
No testnet connection, no signing, no strategy — by design.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pydantic import SecretStr

from osbot.config import BaseConfig, load_config
from osbot.observability import get_logger

log = get_logger("osbot.main")


_MIN_ADDR_LEN_FOR_TRUNCATION = 10


def _redact_addr(addr: str) -> str:
    if len(addr) < _MIN_ADDR_LEN_FOR_TRUNCATION:
        return "***"
    return f"{addr[:6]}...{addr[-4:]}"


def _summarize(cfg: BaseConfig) -> str:
    pw_set = isinstance(cfg.keyfile_password, SecretStr)
    lines = [
        "osbot config summary:",
        f"  mode: {cfg.mode}",
        f"  account_address: {_redact_addr(cfg.account_address)}",
        f"  keyfile_path: {cfg.keyfile_path}",
        f"  keyfile_password: {'<set>' if pw_set else '<missing>'}",
        "  strategy:",
        f"    pair: {cfg.strategy.pair}",
        f"    leverage: {cfg.strategy.leverage}",
        f"    grid_levels: {cfg.strategy.grid_levels}",
        f"    wallet_exposure_limit: {cfg.strategy.wallet_exposure_limit}",
        f"    range_bps_min: {cfg.strategy.range_bps_min}",
        "  risk:",
        f"    max_daily_loss_pct: {cfg.risk.max_daily_loss_pct}",
        f"    min_notional_usd: {cfg.risk.min_notional_usd}",
        "  observability:",
        f"    shadow_db_path: {cfg.observability.shadow_db_path}",
        f"    health_port: {cfg.observability.health_port}",
        f"    telegram: {'<configured>' if cfg.observability.telegram_chat_id else '<unset>'}",
    ]
    return "\n".join(lines)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="osbot", description="Hyperliquid trading bot")
    p.add_argument(
        "--config",
        type=Path,
        default=Path("osbot/config/schema.yaml"),
        help="Path to YAML config (default: osbot/config/schema.yaml)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Load config and print a redacted summary. Do not connect or trade.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if not args.dry_run:
        log.error("M0 only supports --dry-run. Strategy loop lands in later milestones.")
        return 2

    try:
        cfg = load_config(args.config)
    except FileNotFoundError:
        log.error("config not found: %s", args.config)
        return 1
    except (ValueError, OSError) as e:
        log.error("config load failed: %s", e)
        return 1

    print(_summarize(cfg))
    return 0


if __name__ == "__main__":
    sys.exit(main())
