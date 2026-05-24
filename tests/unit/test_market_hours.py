"""Tests for osbot.strategy.market_hours."""

from __future__ import annotations

from datetime import datetime, timezone

from osbot.strategy.market_hours import Session, classify, dex_for_pair, is_equity_perp, should_flatten_for_weekend


def _ts(year: int, month: int, day: int, hour: int, minute: int) -> float:
    """Build a UTC timestamp from components."""
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc).timestamp()


# --- classify ---

class TestClassifyCase:
    def test_regular_hours_monday(self):
        # Mon May 18 2026, 15:00 UTC = 11:00 ET (regular)
        assert classify(_ts(2026, 5, 18, 15, 0)) == Session.REGULAR

    def test_regular_open_boundary(self):
        # 13:30 UTC = 09:30 ET (first second of regular)
        assert classify(_ts(2026, 5, 18, 13, 30)) == Session.REGULAR

    def test_regular_close_boundary(self):
        # 20:00 UTC = 16:00 ET (first second after regular = extended)
        assert classify(_ts(2026, 5, 18, 20, 0)) == Session.EXTENDED

    def test_extended_premarket(self):
        # 08:00 UTC = 04:00 ET (pre-market open)
        assert classify(_ts(2026, 5, 18, 8, 0)) == Session.EXTENDED

    def test_extended_after_hours(self):
        # 22:00 UTC = 18:00 ET (after-hours)
        assert classify(_ts(2026, 5, 18, 22, 0)) == Session.EXTENDED

    def test_closed_overnight(self):
        # 02:00 UTC = 22:00 ET previous day (overnight)
        assert classify(_ts(2026, 5, 19, 2, 0)) == Session.CLOSED

    def test_closed_after_extended(self):
        # 00:00 UTC May 19 = 20:00 ET May 18 (after extended close)
        assert classify(_ts(2026, 5, 19, 0, 0)) == Session.CLOSED

    def test_saturday(self):
        # Sat May 16 2026
        assert classify(_ts(2026, 5, 16, 15, 0)) == Session.CLOSED

    def test_sunday(self):
        # Sun May 17 2026
        assert classify(_ts(2026, 5, 17, 15, 0)) == Session.CLOSED

    def test_holiday_christmas(self):
        # Thu Dec 25 2026, regular-hours time but holiday
        assert classify(_ts(2026, 12, 25, 15, 0)) == Session.CLOSED

    def test_holiday_thanksgiving(self):
        assert classify(_ts(2026, 11, 26, 15, 0)) == Session.CLOSED

    def test_friday_regular(self):
        # Fri May 22 2026, 14:00 UTC = 10:00 ET
        assert classify(_ts(2026, 5, 22, 14, 0)) == Session.REGULAR


# --- is_equity_perp ---

class TestIsEquityPerpCase:
    def test_xyz_prefix(self):
        assert is_equity_perp("xyz:NVDA") is True
        assert is_equity_perp("xyz:TSLA") is True

    def test_bare_ticker(self):
        assert is_equity_perp("NVDA") is True
        assert is_equity_perp("TSLA") is True
        assert is_equity_perp("MSTR") is True

    def test_crypto_not_equity(self):
        assert is_equity_perp("BTC") is False
        assert is_equity_perp("ETH") is False
        assert is_equity_perp("SOL") is False
        assert is_equity_perp("HYPE") is False


# --- dex_for_pair ---

class TestDexForPairCase:
    def test_crypto_returns_none(self):
        assert dex_for_pair("BTC") is None
        assert dex_for_pair("ETH") is None
        assert dex_for_pair("SOL") is None

    def test_equity_returns_xyz(self):
        assert dex_for_pair("xyz:NVDA") == "xyz"
        assert dex_for_pair("xyz:TSLA") == "xyz"
        assert dex_for_pair("MSTR") == "xyz"


# --- should_flatten_for_weekend ---

class TestShouldFlattenForWeekendCase:
    def test_friday_1555_triggers(self):
        # Fri May 22 2026, 19:55 UTC = 15:55 ET
        assert should_flatten_for_weekend(_ts(2026, 5, 22, 19, 55)) is True

    def test_friday_1558_triggers(self):
        # Fri May 22 2026, 19:58 UTC = 15:58 ET
        assert should_flatten_for_weekend(_ts(2026, 5, 22, 19, 58)) is True

    def test_friday_1600_does_not_trigger(self):
        # Fri May 22 2026, 20:00 UTC = 16:00 ET (already CLOSED territory)
        assert should_flatten_for_weekend(_ts(2026, 5, 22, 20, 0)) is False

    def test_friday_1554_does_not_trigger(self):
        # Fri May 22 2026, 19:54 UTC = 15:54 ET (too early)
        assert should_flatten_for_weekend(_ts(2026, 5, 22, 19, 54)) is False

    def test_monday_1555_does_not_trigger(self):
        # Mon May 18 2026, 19:55 UTC = 15:55 ET (not Friday)
        assert should_flatten_for_weekend(_ts(2026, 5, 18, 19, 55)) is False

    def test_thursday_1555_does_not_trigger(self):
        # Thu May 21 2026, 19:55 UTC = 15:55 ET (not Friday)
        assert should_flatten_for_weekend(_ts(2026, 5, 21, 19, 55)) is False

    def test_saturday_does_not_trigger(self):
        # Sat May 16 2026
        assert should_flatten_for_weekend(_ts(2026, 5, 16, 19, 55)) is False
