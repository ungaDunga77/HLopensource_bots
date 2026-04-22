"""Force-close all HL testnet positions out-of-band to trigger Freqtrade's
_handle_external_close path. Run this mid-trial to validate the fork's
SQLAlchemy rollback+refresh behavior on external close.

Usage:  python evaluations/freqtrade-titouan/force_close_position.py
"""

import json
import sys
import time

from eth_account import Account
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.utils import constants


def main() -> int:
    creds = json.load(open("evaluations/passivbot/api-keys.json"))["hyperliquid_testnet"]
    pk = creds["private_key"]
    if not pk.startswith("0x"):
        pk = "0x" + pk
    agent = Account.from_key(pk)
    main_addr = creds["wallet_address"]

    info = Info(
        constants.TESTNET_API_URL,
        skip_ws=True,
        spot_meta={"universe": [], "tokens": []},
    )
    ex = Exchange(
        agent,
        constants.TESTNET_API_URL,
        account_address=main_addr,
        spot_meta={"universe": [], "tokens": []},
    )

    st = info.user_state(main_addr)
    positions = st.get("assetPositions", [])
    print(
        f"wallet: {main_addr[:6]}...{main_addr[-4:]}  balance: {st['marginSummary']['accountValue']}"
    )
    print(f"open positions: {len(positions)}")

    if not positions:
        print("no positions to close — bot hasn't entered yet or already flat.")
        return 0

    for p in positions:
        pos = p["position"]
        coin = pos["coin"]
        sz = float(pos["szi"])
        print(f"  closing {coin} sz={sz} entry={pos.get('entryPx')} upnl={pos.get('unrealizedPnl')}")
        r = ex.market_close(coin)
        status = r.get("status") if isinstance(r, dict) else str(r)
        print(f"    market_close result: {status}")

    time.sleep(3)
    st = info.user_state(main_addr)
    print(f"\nafter: positions={len(st['assetPositions'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
