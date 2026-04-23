"""osbot entry point.

M0: `--dry-run` prints redacted config summary.
M1: `--smoke-test` fetches testnet user_state (read-only) and prints balance + position count.
M2: `--round-trip-test` runs full startup + opens/closes one $15-notional BTC position.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from pydantic import SecretStr

from osbot.config import BaseConfig, load_config
from osbot.connector.errors import AppError
from osbot.connector.hl_client import HLClient
from osbot.observability import get_logger
from osbot.roundtrip import run_round_trip

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
    p.add_argument(
        "--smoke-test",
        action="store_true",
        help="Fetch testnet user_state read-only, print balance + position count, exit.",
    )
    p.add_argument(
        "--round-trip-test",
        action="store_true",
        help="Run full startup + open/close one $15-notional BTC position on testnet, exit.",
    )
    return p


async def _smoke_test(cfg: BaseConfig) -> int:
    client = HLClient(mode=cfg.mode, account_address=cfg.account_address)
    try:
        state = await client.user_state()
    except AppError as e:
        log.error("user_state failed: %s (%s)", e.message, e.category)
        return 1
    margin = state.get("marginSummary", {}) or {}
    balance = margin.get("accountValue", "?")
    positions = state.get("assetPositions", []) or []
    print(f"smoke-test OK: account_value={balance} positions={len(positions)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if not (args.dry_run or args.smoke_test or args.round_trip_test):
        log.error(
            "Specify --dry-run (M0), --smoke-test (M1), or --round-trip-test (M2). "
            "Strategy loop lands later."
        )
        return 2

    try:
        cfg = load_config(args.config)
    except FileNotFoundError:
        log.error("config not found: %s", args.config)
        return 1
    except (ValueError, OSError) as e:
        log.error("config load failed: %s", e)
        return 1

    if args.dry_run:
        print(_summarize(cfg))
        return 0

    if args.smoke_test:
        return asyncio.run(_smoke_test(cfg))

    return asyncio.run(run_round_trip(cfg))


if __name__ == "__main__":
    sys.exit(main())
