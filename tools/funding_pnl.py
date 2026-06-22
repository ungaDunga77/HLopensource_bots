#!/usr/bin/env python3
"""Funding-aware net PnL + inventory-lean readout.

The watch tools compute net = closedPnl - fees, which is FUNDING-BLIND. Fine for
majors (funding ~0) but materially wrong for the mainnet xyz profit gate, where
funding is +13-20% APY: a persistent LONG lean bleeds funding the trade-PnL view
never shows; a SHORT lean earns it. This tool folds actual funding payments (HL
`userFunding`) into net and reports the time-weighted inventory lean per coin so a
costly drift is visible.

Run with the signing key in env (same override as the bot):
  set -a; source .env; set +a
  export HYPERLIQUID_TESTNET_PRIVATE_KEY="$HYPERLIQUID_MAINNET_PRIVATE_KEY"
  python tools/funding_pnl.py

Env:
  OSBOT_NET = testnet (default) | mainnet  — picks endpoint + which key to derive address from
  OSBOT_SHADOW_DB = path (default data/hip3-testnet-shadow.sqlite)
"""
import os, sqlite3, json, datetime as dt, sys
from collections import defaultdict

NET = os.environ.get("OSBOT_NET", "testnet")
API = ("https://api.hyperliquid-testnet.xyz/info" if NET == "testnet"
       else "https://api.hyperliquid.xyz/info")
KEY_ENV = "HYPERLIQUID_TESTNET_PRIVATE_KEY" if NET == "testnet" else "HYPERLIQUID_MAINNET_PRIVATE_KEY"
DB = os.environ.get("OSBOT_SHADOW_DB", "data/hip3-testnet-shadow.sqlite")
# Default window = BTC/ETH pivot start; override with argv[1] as 'YYYY-MM-DDTHH:MMZ'.
START = dt.datetime(2026, 6, 21, 3, 5, 0, tzinfo=dt.timezone.utc).timestamp()


def _account_address():
    try:
        from eth_account import Account
        k = os.environ.get(KEY_ENV)
        return Account.from_key(k).address if k else None
    except Exception:
        return None


def _funding_by_coin(addr, start_ms):
    """{coin: usdc} actual funding payments since start. Empty on any failure."""
    if not addr:
        return None
    try:
        import requests
        r = requests.post(API, json={"type": "userFunding", "user": addr,
                                     "startTime": int(start_ms)}, timeout=10).json()
        by = defaultdict(float)
        for e in r if isinstance(r, list) else []:
            d = e.get("delta", {})
            if d.get("coin"):
                by[d["coin"]] += float(d.get("usdc", 0))
        return dict(by)
    except Exception as e:
        print(f"  (funding query failed: {e})", file=sys.stderr)
        return None


def _twa_inventory(fills):
    """Time-weighted average signed position (coin units) from a fill sequence."""
    if len(fills) < 2:
        return 0.0
    seq = sorted(fills, key=lambda r: r["time"])
    pos = 0.0
    area = 0.0
    t0 = seq[0]["time"]
    for i, r in enumerate(seq):
        if i > 0:
            area += pos * (r["time"] - seq[i - 1]["time"])  # position held since prev fill
        sz = float(r["sz"])
        pos += sz if r["side"] == "B" else -sz
    span = seq[-1]["time"] - t0
    return area / span if span > 0 else pos


def main():
    if len(sys.argv) > 1:
        global START
        START = dt.datetime.fromisoformat(sys.argv[1].replace("Z", "+00:00")).timestamp()
    addr = _account_address()
    c = sqlite3.connect(DB)
    rows = [json.loads(p) for (p,) in c.execute("select payload from fills order by ts")]
    coins = sorted({r["coin"] for r in rows if r["time"] / 1000 >= START})
    funding = _funding_by_coin(addr, START * 1000)
    print(f"=== FUNDING-AWARE PnL ({NET}, since {dt.datetime.fromtimestamp(START, dt.timezone.utc):%m-%d %H:%MZ}) ===")
    if funding is None:
        print("  funding: UNAVAILABLE (no key in env or query failed) — net below is funding-blind")
    tot = 0.0
    for coin in coins:
        seg = [r for r in rows if r["coin"] == coin and r["time"] / 1000 >= START]
        if not seg:
            continue
        gross = sum(float(r["closedPnl"]) for r in seg)
        fees = sum(float(r["fee"]) for r in seg)
        fund = (funding or {}).get(coin, 0.0)
        net_blind = gross - fees
        net_full = net_blind + fund
        lean = _twa_inventory(seg)
        tot += net_full
        fstr = f"{fund:+.4f}" if funding is not None else "n/a"
        print(f"{coin}: gross ${gross:+.4f}  fees ${fees:.4f}  funding ${fstr}  "
              f"NET(full) ${net_full:+.4f}  (blind ${net_blind:+.4f})")
        print(f"    inventory lean (time-weighted signed pos): {lean:+.4f} {coin}  "
              f"{'LONG (pays funding)' if lean > 1e-6 else 'SHORT (earns funding)' if lean < -1e-6 else 'flat'}")
    if funding is not None:
        print(f"TOTAL funding-aware net: ${tot:+.4f}")


if __name__ == "__main__":
    main()
