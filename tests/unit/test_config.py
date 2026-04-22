from __future__ import annotations

from pathlib import Path

import pytest

from osbot.config import MainnetConfig, TestnetConfig, load_config


def _write(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "cfg.yaml"
    p.write_text(body)
    return p


def test_testnet_config_loads(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        """
mode: testnet
account_address: "0x0000000000000000000000000000000000000000"
keyfile_path: "./k"
keyfile_password: "pw"
""",
    )
    cfg = load_config(path)
    assert isinstance(cfg, TestnetConfig)
    assert cfg.mode == "testnet"
    assert cfg.keyfile_password.get_secret_value() == "pw"


def test_mainnet_requires_explicit_opt_in(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        """
mode: mainnet
account_address: "0x0000000000000000000000000000000000000000"
keyfile_path: "./k"
keyfile_password: "pw"
""",
    )
    with pytest.raises(ValueError, match="confirm_mainnet"):
        load_config(path)


def test_mainnet_with_confirmation(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        """
mode: mainnet
confirm_mainnet: true
account_address: "0x0000000000000000000000000000000000000000"
keyfile_path: "./k"
keyfile_password: "pw"
""",
    )
    cfg = load_config(path)
    assert isinstance(cfg, MainnetConfig)


def test_secret_never_in_repr(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        """
mode: testnet
account_address: "0x0000000000000000000000000000000000000000"
keyfile_path: "./k"
keyfile_password: "topsecret"
""",
    )
    cfg = load_config(path)
    assert "topsecret" not in repr(cfg)
    assert "topsecret" not in str(cfg)
