#!/usr/bin/env python3
"""Watch SOL dedicated-soak economics: taker% and gross edge vs fee hurdle.

Reads the live shadow DB and prints SOL round-trip stats since the SOL-only
soak start. Convention: closedPnl = gross realized trading PnL, fees netted
separately. Bps are on fill notional; ~RT = x2 (open+close).
"""
import sqlite3, json, datetime as dt, sys

DB = "data/hip3-testnet-shadow.sqlite"
SOAK_START = dt.datetime(2026, 6, 15, 5, 11, tzinfo=dt.timezone.utc).timestamp()
# Before/after cutovers (fills tagged by exchange time, so late DB flushes attribute right):
#   control (sl 200bps)  ->  treat v1 (sl 25bps, whipsawed)  ->  treat v2 (sl 55bps)
CUTOVER = dt.datetime(2026, 6, 17, 3, 39, 0, tzinfo=dt.timezone.utc).timestamp()
CUTOVER_V2 = dt.datetime(2026, 6, 17, 12, 46, 0, tzinfo=dt.timezone.utc).timestamp()


def _stats(sol, label, start_ts):
    if not sol:
        print(f"{label}: no fills yet")
        return
    n = len(sol)
    fees = sum(float(r["fee"]) for r in sol)
    gross = sum(float(r["closedPnl"]) for r in sol)
    notl = sum(float(r["px"]) * float(r["sz"]) for r in sol)
    taker = sum(1 for r in sol if r["crossed"])
    closes = sum(1 for r in sol if r["dir"].startswith("Close"))
    net = gross - fees
    last = dt.datetime.fromtimestamp(max(r["time"] for r in sol) / 1000, dt.timezone.utc)
    hrs = (max(r["time"] for r in sol) / 1000 - start_ts) / 3600
    print(f"{label}  | {hrs:.1f}h | last fill {last:%m-%d %H:%M}Z")
    print(f"  fills={n}  RTs={closes}  taker%={taker/n*100:.1f}  notional=${notl:,.0f}")
    print(f"  GROSS = ${gross:+.4f}  ({gross/notl*1e4:+.2f} bps/fill)")
    print(f"  FEES  = ${fees:.4f}  ({fees/notl*1e4:.2f} bps/fill, ~{fees/notl*2e4:.1f} bps/RT)")
    print(f"  NET   = ${net:+.4f}  ({net/notl*1e4:+.2f} bps/fill)")
    print(f"WATCH[{label}]\t{hrs:.2f}\t{n}\t{closes}\t{taker/n*100:.1f}"
          f"\t{gross/notl*1e4:.3f}\t{fees/notl*2e4:.3f}\t{net/notl*1e4:.3f}")


def main():
    c = sqlite3.connect(DB)
    rows = [json.loads(p) for (p,) in c.execute("select payload from fills order by ts")]
    sol = [r for r in rows if r["coin"] == "SOL" and r["time"] / 1000 >= SOAK_START]
    ctrl = [r for r in sol if r["time"] / 1000 < CUTOVER]
    t25 = [r for r in sol if CUTOVER <= r["time"] / 1000 < CUTOVER_V2]
    t55 = [r for r in sol if r["time"] / 1000 >= CUTOVER_V2]

    def _exits(lo, hi=None):
        q = "select count(*) from snapshots where kind='exit_close' and ts>=?"
        args = [lo]
        if hi is not None:
            q += " and ts<?"; args.append(hi)
        return c.execute(q, args).fetchone()[0]

    print("=== CONTROL (sl 200bps, baseline) ===")
    _stats(ctrl, "CONTROL", SOAK_START)
    print("=== TREAT v1 (sl 25bps, 03:39->12:46Z, whipsawed) ===")
    _stats(t25, "TREAT25", CUTOVER)
    print(f"  STOP FIRINGS: {_exits(CUTOVER, CUTOVER_V2)} in {sum(1 for r in t25 if r['dir'].startswith('Close'))} RTs")
    print("=== TREAT v2 (sl 55bps, since 06-17 12:46Z) ===")
    _stats(t55, "TREAT55", CUTOVER_V2)
    print(f"  STOP FIRINGS: {_exits(CUTOVER_V2)} in {sum(1 for r in t55 if r['dir'].startswith('Close'))} RTs")


if __name__ == "__main__":
    main()
