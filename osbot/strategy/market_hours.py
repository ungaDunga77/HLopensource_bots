"""US equity market session classifier for xyz equity perps.

xyz perps trade 24/7 but spreads blow out when the underlying equity market is
closed. This module tells the runner when to quote actively vs pause.

Sessions (all Eastern Time):
  - REGULAR: Mon-Fri 09:30-16:00 ET
  - EXTENDED: Mon-Fri 04:00-09:30 and 16:00-20:00 ET
  - CLOSED: overnight + weekends + US market holidays

The runner uses this to decide: REGULAR → normal grid, EXTENDED → optional
wider grid, CLOSED → cancel-only (no new orders).
"""

from __future__ import annotations

from datetime import date, datetime, time
from enum import Enum
from zoneinfo import ZoneInfo

_ET = ZoneInfo("America/New_York")

# NYSE observed holidays for 2026 (static; update annually).
_HOLIDAYS_2026: frozenset[date] = frozenset({
    date(2026, 1, 1),   # New Year's Day
    date(2026, 1, 19),  # MLK Day
    date(2026, 2, 16),  # Presidents' Day
    date(2026, 4, 3),   # Good Friday
    date(2026, 5, 25),  # Memorial Day
    date(2026, 7, 3),   # Independence Day (observed)
    date(2026, 9, 7),   # Labor Day
    date(2026, 11, 26), # Thanksgiving
    date(2026, 12, 25), # Christmas
})

_REGULAR_OPEN = time(9, 30)
_REGULAR_CLOSE = time(16, 0)
_EXTENDED_OPEN = time(4, 0)
_EXTENDED_CLOSE = time(20, 0)


class Session(Enum):
    REGULAR = "regular"
    EXTENDED = "extended"
    CLOSED = "closed"


def classify(ts: float) -> Session:
    """Classify a Unix timestamp into a US equity market session."""
    dt = datetime.fromtimestamp(ts, tz=_ET)
    if dt.weekday() >= 5:  # Saturday=5, Sunday=6
        return Session.CLOSED
    if dt.date() in _HOLIDAYS_2026:
        return Session.CLOSED
    t = dt.time()
    if _REGULAR_OPEN <= t < _REGULAR_CLOSE:
        return Session.REGULAR
    if _EXTENDED_OPEN <= t < _EXTENDED_CLOSE:
        return Session.EXTENDED
    return Session.CLOSED


def is_equity_perp(pair: str) -> bool:
    """True if the pair is an xyz equity perp (prefixed or known ticker)."""
    if pair.startswith("xyz:"):
        return True
    # Bare tickers that live on xyz dex
    return pair in {"NVDA", "TSLA", "AAPL", "COIN", "MSTR", "MSFT", "GOOGL", "AMZN", "SPX"}
