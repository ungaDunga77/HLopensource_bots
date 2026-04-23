"""Startup sequence — the 10 enforced steps from phase5-synthesis.md §5.3.

Every bot run threads through `run_startup(cfg)`. Steps are explicit, ordered,
and fail-fast: if any step raises, no Exchange writes have happened yet (with
the lone exception of step 7 `set_leverage` and step 9 `cancel_all_orders`,
which are intentional state mutations performed early so the strategy loop
inherits a known-good slate).

Steps:
 1. Config load (already done by the caller; we re-validate mode here).
 2. Assert mode is testnet or mainnet (no implicit defaults at runtime).
 3. Decrypt keyfile via env-var password.
 4. Derive LocalAccount from the raw key; zero the key bytes.
 5. Construct HLClient with explicit account_address (agent-wallet-safe).
 6. Fetch clearinghouseState; verify accountValue is parseable.
 7. set_leverage(strategy.pair, strategy.leverage, is_cross=False).
 8. meta() fetch; cache szDecimals for the configured pair.
 9. Cancel all open orders for the pair (clean slate).
10. Snapshot to shadow DB (account_value, position count, order count).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from eth_account import Account
from eth_account.signers.local import LocalAccount

from osbot.auth.keyfile import load_keyfile
from osbot.config import BaseConfig
from osbot.connector.errors import AppError, AuthError, StructuralError
from osbot.connector.hl_client import HLClient
from osbot.observability import get_logger
from osbot.observability.shadow import ShadowLogger

log = get_logger("osbot.startup")

KEYFILE_PASSWORD_ENV = "OSBOT_KEYFILE_PASSWORD"


@dataclass
class StartupContext:
    cfg: BaseConfig
    client: HLClient
    shadow: ShadowLogger
    sz_decimals: int
    initial_account_value: float


def _resolve_password(cfg: BaseConfig) -> str:
    password = os.environ.get(KEYFILE_PASSWORD_ENV)
    if password:
        return password
    secret = cfg.keyfile_password.get_secret_value()
    if secret:
        return secret
    raise AuthError(f"keyfile password not set ({KEYFILE_PASSWORD_ENV} env var)")


def _derive_wallet(cfg: BaseConfig) -> LocalAccount:
    password = _resolve_password(cfg)
    key_bytes = load_keyfile(cfg.keyfile_path, password)
    try:
        wallet: LocalAccount = Account.from_key(key_bytes)
    finally:
        # Best-effort: rebind to make the original buffer unreachable. CPython
        # doesn't guarantee zeroing of bytes objects.
        key_bytes = b"\x00" * len(key_bytes)
        del key_bytes
    if wallet.address.lower() != cfg.account_address.lower():
        log.info("startup step 4: signing wallet differs from account_address (agent mode)")
    else:
        log.info("startup step 4: wallet derived (master key mode)")
    return wallet


def _parse_account_value(state: dict[str, Any]) -> float:
    margin = state.get("marginSummary") or {}
    try:
        value = float(margin.get("accountValue", "0"))
    except (TypeError, ValueError) as e:
        raise StructuralError(f"invalid accountValue in clearinghouseState: {margin!r}") from e
    if value <= 0:
        raise StructuralError(f"accountValue not positive: {value}")
    return value


def _find_sz_decimals(meta: dict[str, Any], pair: str) -> int:
    for u in meta.get("universe", []) or []:
        if u.get("name") == pair:
            return int(u.get("szDecimals", 0))
    raise StructuralError(f"pair {pair!r} not found in HL meta universe")


async def _cancel_open_for_pair(client: HLClient, pair: str) -> int:
    open_orders = await client.open_orders()
    cancelled = 0
    for o in open_orders:
        if o.get("coin") != pair:
            continue
        oid = o.get("oid")
        if oid is None:
            continue
        try:
            await client.cancel(pair, int(oid))
            cancelled += 1
        except AppError as e:
            log.error("startup step 9: cancel oid=%s failed: %s", oid, e.message)
    return cancelled


async def run_startup(cfg: BaseConfig) -> StartupContext:
    # Step 2: mode assertion. Pydantic Literal enforces it; runtime check keeps
    # future config refactors honest.
    if cfg.mode not in {"testnet", "mainnet"}:
        raise StructuralError(f"invalid mode: {cfg.mode!r}")
    log.info("startup step 2: mode=%s", cfg.mode)

    # Steps 3+4: decrypt + derive wallet.
    wallet = _derive_wallet(cfg)

    # Step 5: HLClient with explicit account_address.
    client = HLClient(mode=cfg.mode, account_address=cfg.account_address, wallet=wallet)
    log.info("startup step 5: HLClient ready")

    # Step 6: clearinghouse sanity.
    state = await client.user_state()
    account_value = _parse_account_value(state)
    log.info("startup step 6: account_value=%.6f", account_value)

    # Step 7: explicit set_leverage.
    pair = cfg.strategy.pair
    leverage = cfg.strategy.leverage
    try:
        await client.set_leverage(pair, leverage, is_cross=False)
    except AppError as e:
        raise StructuralError(f"set_leverage failed: {e.message}", cause=e) from e
    log.info("startup step 7: leverage set pair=%s leverage=%dx isolated", pair, leverage)

    # Step 8: meta + szDecimals.
    meta = await client.meta()
    sz_decimals = _find_sz_decimals(meta, pair)
    log.info("startup step 8: pair=%s szDecimals=%d", pair, sz_decimals)

    # Step 9: clean slate.
    cancelled = await _cancel_open_for_pair(client, pair)
    log.info("startup step 9: cancelled %d open orders for %s", cancelled, pair)

    # Step 10: snapshot.
    shadow = ShadowLogger(cfg.observability.shadow_db_path)
    positions = state.get("assetPositions") or []
    shadow.snapshot(
        "startup",
        {
            "mode": cfg.mode,
            "pair": pair,
            "leverage": leverage,
            "account_value": account_value,
            "n_positions": len(positions),
            "n_orders_cancelled_at_startup": cancelled,
            "sz_decimals": sz_decimals,
        },
    )
    log.info(
        "startup step 10: shadow snapshot recorded (positions=%d, cancelled=%d)",
        len(positions),
        cancelled,
    )

    return StartupContext(
        cfg=cfg,
        client=client,
        shadow=shadow,
        sz_decimals=sz_decimals,
        initial_account_value=account_value,
    )
