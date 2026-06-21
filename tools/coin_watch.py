#!/usr/bin/env python3
"""Generic per-coin grid economics watch (BTC/ETH pivot + v4 fee discipline).

Reports net/gross/taker/SL for each watched coin since a cutover, from the shared
shadow DB, plus the true SL-vs-TP split from the live log (the shadow exit_close
count conflates the two). Convention: closedPnl = gross realized PnL, fees netted
separately; bps on fill notional, ~RT = x2.

Usage: python tools/coin_watch.py [logfile]   (defaults to /tmp/btc_logpath)
"""
import sqlite3, json, datetime as dt, sys, subprocess, re

DB = "data/hip3-testnet-shadow.sqlite"
# BTC/ETH pivot start (SOL abandoned: 210 RTs net -6.04 bps; v4 mechanics moved to majors).
START = dt.datetime(2026, 6, 21, 3, 5, 0, tzinfo=dt.timezone.utc).timestamp()
COINS = ["BTC", "ETH"]


def _stats(rows, label):
    if not rows:
        print(f"{label}: no fills yet")
        return
    n = len(rows)
    fees = sum(float(r["fee"]) for r in rows)
    gross = sum(float(r["closedPnl"]) for r in rows)
    notl = sum(float(r["px"]) * float(r["sz"]) for r in rows)
    taker = sum(1 for r in rows if r["crossed"])
    closes = sum(1 for r in rows if r["dir"].startswith("Close"))
    net = gross - fees
    last = dt.datetime.fromtimestamp(max(r["time"] for r in rows) / 1000, dt.timezone.utc)
    print(f"{label}: fills={n} RTs={closes} taker%={taker/n*100:.1f} last={last:%m-%d %H:%M}Z")
    print(f"  GROSS ${gross:+.4f} ({gross/notl*1e4:+.2f} bps/fill) | "
          f"FEES ${fees:.4f} ({fees/notl*2e4:.1f} bps/RT) | "
          f"NET ${net:+.4f} ({net/notl*1e4:+.2f} bps/fill)")


def main():
    logfile = sys.argv[1] if len(sys.argv) > 1 else None
    if logfile is None:
        try:
            logfile = open("/tmp/btc_logpath").read().strip()
        except OSError:
            logfile = None
    c = sqlite3.connect(DB)
    rows = [json.loads(p) for (p,) in c.execute("select payload from fills order by ts")]
    for coin in COINS:
        seg = [r for r in rows if r["coin"] == coin and r["time"] / 1000 >= START]
        _stats(seg, coin)
    # True SL vs TP from the log (post-only era: also surfaces ALO rejects).
    if logfile:
        try:
            txt = open(logfile, errors="ignore").read()
            reasons = re.findall(r"reason=(sl|tp|ttl)", txt)
            from collections import Counter
            ct = Counter(reasons)
            rejects = len(re.findall(r"[Rr]eject|ALO|post.?only.*reject", txt))
            print(f"exit reasons: SL={ct.get('sl',0)} TP={ct.get('tp',0)} TTL={ct.get('ttl',0)} | ALO-rejects~{rejects}")
        except OSError:
            pass


if __name__ == "__main__":
    main()
