#!/usr/bin/env python3
"""Read-only market data collector for the strategy-pivot decision (Tracks 1 & 2).

Pulls HL mainnet book/funding/OI/volume for BTC + HIP-3 (xyz dex) equity perps,
plus Binance and Bybit funding rates for cross-venue spread analysis. Writes a
SQLite DB for offline analysis against the decision rules in
docs/strategy-pivot-plan.md.

No orders, no risk, no strategy logic. Polling-only. Single writer thread.

Cadence:
  - HL book snapshots: every 5s per asset (configurable).
  - HL funding/OI/volume: hourly (per dex, single batched call).
  - Binance + Bybit funding: hourly for BTC and ETH.

Usage:
  python tools/market_survey.py \
    --hl-assets BTC,ETH \
    --xyz-assets xyz:NVDA,xyz:TSLA,xyz:AAPL,xyz:COIN,xyz:MSTR \
    --xvenue-assets BTC,ETH \
    --out evaluations/_market_survey/run-<UTC>.db
"""

from __future__ import annotations

import argparse
import json
import logging
import queue
import signal
import sqlite3
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HL_INFO_URL = "https://api.hyperliquid.xyz/info"
BINANCE_FUNDING_URL = "https://fapi.binance.com/fapi/v1/premiumIndex"
BYBIT_TICKER_URL = "https://api.bybit.com/v5/market/tickers"

log = logging.getLogger("market_survey")
stopping = threading.Event()
write_q: "queue.Queue[Optional[tuple[str, tuple]]]" = queue.Queue(maxsize=10000)

SCHEMA = """
CREATE TABLE IF NOT EXISTS hl_book_snapshots (
  ts REAL NOT NULL, asset TEXT NOT NULL, mid REAL, bid REAL, ask REAL,
  spread_bps REAL, depth_5bps_usd REAL, depth_25bps_usd REAL, depth_100bps_usd REAL
);
CREATE INDEX IF NOT EXISTS idx_book_ts ON hl_book_snapshots(ts);
CREATE INDEX IF NOT EXISTS idx_book_asset_ts ON hl_book_snapshots(asset, ts);

CREATE TABLE IF NOT EXISTS funding_rates (
  ts REAL NOT NULL, venue TEXT NOT NULL, asset TEXT NOT NULL,
  hourly_rate REAL, apy_pct REAL
);
CREATE INDEX IF NOT EXISTS idx_funding_ts ON funding_rates(ts);
CREATE INDEX IF NOT EXISTS idx_funding_va ON funding_rates(venue, asset, ts);

CREATE TABLE IF NOT EXISTS volume_oi (
  ts REAL NOT NULL, asset TEXT NOT NULL,
  daily_volume_usd REAL, oi_usd REAL, mark_px REAL
);
CREATE INDEX IF NOT EXISTS idx_vol_ts ON volume_oi(ts);

CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""

TABLES = ["hl_book_snapshots", "funding_rates", "volume_oi", "meta"]


def _f(x: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        return float(x) if x is not None else default
    except (TypeError, ValueError):
        return default


def enqueue(sql: str, params: tuple) -> None:
    if stopping.is_set():
        return
    try:
        write_q.put((sql, params), block=True, timeout=5.0)
    except queue.Full:
        log.warning("write queue full; dropping row")


def writer_thread(db_path: Path) -> None:
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.executescript(SCHEMA)
    conn.commit()
    pending = 0
    next_commit = time.time() + 1.0
    while True:
        try:
            item = write_q.get(timeout=0.5)
        except queue.Empty:
            if pending:
                conn.commit()
                pending = 0
            continue
        if item is None:
            break
        try:
            conn.execute(item[0], item[1])
            pending += 1
        except Exception as e:
            log.warning("writer sql failed: %s", e)
        if pending >= 50 or time.time() >= next_commit:
            conn.commit()
            pending = 0
            next_commit = time.time() + 1.0
    conn.commit()
    conn.close()


def hl_post(payload: dict, timeout: float = 10.0) -> Any:
    r = requests.post(HL_INFO_URL, json=payload, timeout=timeout)
    r.raise_for_status()
    return r.json()


def book_snapshot(asset: str) -> None:
    """One l2Book pull → spread + depth at ±5/25/100 bps in USD notional."""
    try:
        data = hl_post({"type": "l2Book", "coin": asset})
    except Exception as e:
        log.warning("l2Book %s: %s", asset, e)
        return
    levels = (data or {}).get("levels") or []
    if len(levels) < 2 or not levels[0] or not levels[1]:
        return
    bid = _f(levels[0][0].get("px"))
    ask = _f(levels[1][0].get("px"))
    if bid is None or ask is None or bid <= 0 or ask <= 0:
        return
    mid = (bid + ask) / 2.0
    spread_bps = 1e4 * (ask - bid) / mid

    def depth_usd(side_levels: list, bps: float) -> float:
        lo = mid * (1.0 - bps / 1e4)
        hi = mid * (1.0 + bps / 1e4)
        total = 0.0
        for lvl in side_levels:
            px = _f(lvl.get("px"))
            sz = _f(lvl.get("sz"))
            if px is None or sz is None:
                continue
            if lo <= px <= hi:
                total += px * sz
        return total

    both = list(levels[0]) + list(levels[1])
    enqueue(
        "INSERT INTO hl_book_snapshots(ts, asset, mid, bid, ask, spread_bps, depth_5bps_usd, depth_25bps_usd, depth_100bps_usd) VALUES (?,?,?,?,?,?,?,?,?)",
        (time.time(), asset, mid, bid, ask, spread_bps,
         depth_usd(both, 5), depth_usd(both, 25), depth_usd(both, 100)),
    )


def book_thread(assets: list[str], interval_s: float) -> None:
    while not stopping.is_set():
        for a in assets:
            if stopping.is_set():
                break
            book_snapshot(a)
        if stopping.wait(interval_s):
            break


def hl_funding_volume(dex: Optional[str], assets_filter: Optional[set[str]]) -> None:
    """Pull metaAndAssetCtxs for given dex (None = main HL perps); record funding + vol/OI."""
    try:
        payload = {"type": "metaAndAssetCtxs"}
        if dex:
            payload["dex"] = dex
        meta, ctxs = hl_post(payload)
    except Exception as e:
        log.warning("metaAndAssetCtxs (dex=%s): %s", dex, e)
        return
    universe = meta.get("universe") or []
    now = time.time()
    for u, c in zip(universe, ctxs):
        name = u.get("name", "")
        if assets_filter is not None and name not in assets_filter:
            continue
        funding = _f(c.get("funding"))
        if funding is not None:
            apy = funding * 24 * 365 * 100.0  # HL funding is per-hour
            enqueue(
                "INSERT INTO funding_rates(ts, venue, asset, hourly_rate, apy_pct) VALUES(?,?,?,?,?)",
                (now, "hyperliquid", name, funding, apy),
            )
        mark = _f(c.get("markPx"))
        oi_base = _f(c.get("openInterest"))
        oi_usd = oi_base * mark if (oi_base is not None and mark is not None) else None
        day_ntl = _f(c.get("dayNtlVlm"))
        enqueue(
            "INSERT INTO volume_oi(ts, asset, daily_volume_usd, oi_usd, mark_px) VALUES(?,?,?,?,?)",
            (now, name, day_ntl, oi_usd, mark),
        )


def xvenue_funding_once(assets: list[str]) -> None:
    now = time.time()
    for a in assets:
        sym = f"{a}USDT"
        try:
            r = requests.get(BINANCE_FUNDING_URL, params={"symbol": sym}, timeout=10)
            if r.ok:
                rate = _f(r.json().get("lastFundingRate"))
                if rate is not None:
                    enqueue(
                        "INSERT INTO funding_rates(ts, venue, asset, hourly_rate, apy_pct) VALUES(?,?,?,?,?)",
                        (now, "binance", a, rate / 8.0, rate * 3 * 365 * 100.0),  # 8h interval
                    )
        except Exception as e:
            log.warning("binance %s: %s", a, e)
        try:
            r = requests.get(BYBIT_TICKER_URL, params={"category": "linear", "symbol": sym}, timeout=10)
            if r.ok:
                lst = (r.json().get("result") or {}).get("list") or []
                if lst:
                    rate = _f(lst[0].get("fundingRate"))
                    if rate is not None:
                        enqueue(
                            "INSERT INTO funding_rates(ts, venue, asset, hourly_rate, apy_pct) VALUES(?,?,?,?,?)",
                            (now, "bybit", a, rate / 8.0, rate * 3 * 365 * 100.0),
                        )
        except Exception as e:
            log.warning("bybit %s: %s", a, e)


def hourly_thread(hl_assets: list[str], xyz_assets: list[str], xvenue_assets: list[str]) -> None:
    # First pull immediately.
    while not stopping.is_set():
        hl_main_filter = set(hl_assets) if hl_assets else None
        hl_funding_volume(None, hl_main_filter)
        if xyz_assets:
            hl_funding_volume("xyz", set(xyz_assets))
        if xvenue_assets:
            xvenue_funding_once(xvenue_assets)
        if stopping.wait(3600.0):
            break


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--hl-assets", default="BTC,ETH",
                    help="Main HL perps (control + cross-venue universe)")
    ap.add_argument("--xyz-assets", default="xyz:NVDA,xyz:TSLA,xyz:AAPL,xyz:COIN,xyz:MSTR",
                    help="HIP-3 xyz dex perps to survey")
    ap.add_argument("--xvenue-assets", default="BTC,ETH",
                    help="Assets for cross-venue funding (Binance/Bybit)")
    ap.add_argument("--book-interval", type=float, default=5.0,
                    help="Seconds between book-snapshot cycles")
    ap.add_argument("--out", help="SQLite DB path")
    ap.add_argument("--verbose", action="store_true")
    return ap.parse_args()


def _split_csv(s: str) -> list[str]:
    return [x.strip() for x in s.split(",") if x.strip()]


def main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )

    hl_assets = _split_csv(args.hl_assets)
    xyz_assets = _split_csv(args.xyz_assets)
    xvenue_assets = _split_csv(args.xvenue_assets)
    book_assets = hl_assets + xyz_assets

    if args.out:
        db_path = Path(args.out)
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
        db_path = PROJECT_ROOT / "evaluations" / "_market_survey" / f"run-{stamp}.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"market_survey db: {db_path}")
    print(f"  book assets   ({len(book_assets)}): {','.join(book_assets)}")
    print(f"  xvenue assets ({len(xvenue_assets)}): {','.join(xvenue_assets)}")
    print(f"  book interval: {args.book_interval}s; funding/vol cadence: hourly")

    # Sanity-check HL connectivity.
    try:
        hl_post({"type": "metaAndAssetCtxs"}, timeout=10)
    except Exception as e:
        log.error("HL connectivity check failed: %s", e)
        return 2

    signal.signal(signal.SIGINT, lambda *_: stopping.set())
    signal.signal(signal.SIGTERM, lambda *_: stopping.set())

    w = threading.Thread(target=writer_thread, args=(db_path,), name="writer", daemon=True)
    w.start()

    for k, v in {
        "started_at": str(time.time()),
        "hl_assets": ",".join(hl_assets),
        "xyz_assets": ",".join(xyz_assets),
        "xvenue_assets": ",".join(xvenue_assets),
        "book_interval_s": str(args.book_interval),
    }.items():
        enqueue("INSERT OR REPLACE INTO meta(key, value) VALUES(?, ?)", (k, v))

    threads = [
        threading.Thread(target=book_thread, args=(book_assets, args.book_interval),
                         name="book", daemon=True),
        threading.Thread(target=hourly_thread, args=(hl_assets, xyz_assets, xvenue_assets),
                         name="hourly", daemon=True),
    ]
    for t in threads:
        t.start()

    log.info("market_survey running; Ctrl-C to stop")
    while not stopping.is_set():
        time.sleep(0.5)

    log.info("shutting down; waiting up to 10s for workers")
    for t in threads:
        t.join(timeout=10.0)
    write_q.put(None)
    w.join(timeout=10.0)

    conn = sqlite3.connect(str(db_path))
    print("summary:")
    for tbl in TABLES:
        n = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        print(f"  {tbl}: {n}")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
