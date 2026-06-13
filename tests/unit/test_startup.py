from __future__ import annotations

from pathlib import Path

from eth_account import Account

from osbot.config import load_config
from osbot.startup import redact_addr, resolve_account_address

# Deterministic throwaway key (a public test vector, never funded). Used only to
# derive a stable address for the resolver tests — never a real account.
_TEST_KEY = "0x" + "01" * 32


def _cfg(tmp_path: Path, account_address_line: str = "") -> object:
    body = f"mode: testnet\n{account_address_line}\n"
    p = tmp_path / "c.yaml"
    p.write_text(body)
    return load_config(p)


def test_resolve_uses_explicit_account_address(tmp_path: Path) -> None:
    explicit = "0xABCDEF0123456789ABCDEF0123456789ABCDEF01"
    cfg = _cfg(tmp_path, f'account_address: "{explicit}"')
    wallet = Account.from_key(_TEST_KEY)
    # Explicit config value wins even though the signing wallet differs (agent mode).
    assert wallet.address.lower() != explicit.lower()
    assert resolve_account_address(cfg, wallet) == explicit


def test_resolve_derives_from_wallet_when_omitted(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)  # no account_address in the file
    assert cfg.account_address is None
    wallet = Account.from_key(_TEST_KEY)
    assert resolve_account_address(cfg, wallet) == wallet.address


def test_redact_addr_truncates() -> None:
    assert redact_addr("0x0d3Bc6B8BA597c1AC2a0E8a2d2C969372f1B4e88") == "0x0d3B...4e88"


def test_redact_addr_handles_none_and_short() -> None:
    assert redact_addr(None) == "<derived from private key>"
    assert redact_addr("0xabc") == "***"
