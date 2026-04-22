from __future__ import annotations

from pathlib import Path

import pytest

from osbot.main import main


def test_dry_run_prints_redacted_summary(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg_path = tmp_path / "cfg.yaml"
    cfg_path.write_text(
        """
mode: testnet
account_address: "0xABCDEF0123456789ABCDEF0123456789ABCDEF01"
keyfile_path: "./k"
keyfile_password: "topsecret"
"""
    )
    rc = main(["--dry-run", "--config", str(cfg_path)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "mode: testnet" in out
    assert "topsecret" not in out
    assert "0xABCD...EF01" in out


def test_missing_dry_run_flag_exits_nonzero(tmp_path: Path) -> None:
    cfg_path = tmp_path / "cfg.yaml"
    cfg_path.write_text(
        """
mode: testnet
account_address: "0x0000000000000000000000000000000000000000"
keyfile_path: "./k"
keyfile_password: "pw"
"""
    )
    rc = main(["--config", str(cfg_path)])
    assert rc == 2
