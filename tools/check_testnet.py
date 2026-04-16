#!/usr/bin/env python3
"""Diagnose Hyperliquid testnet connectivity and account state."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from eth_account import Account
from hyperliquid.info import Info
from hyperliquid.utils.constants import TESTNET_API_URL


def main():
    env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(env_path)

    key = os.getenv("HYPERLIQUID_TESTNET_PRIVATE_KEY") or os.getenv("HL_PRIVATE_KEY")
    if not key:
        print("ERROR: No private key found in .env")
        print("Set HYPERLIQUID_TESTNET_PRIVATE_KEY or HL_PRIVATE_KEY")
        sys.exit(1)

    if not key.startswith("0x"):
        key = "0x" + key

    account = Account.from_key(key)
    address = account.address
    print(f"Wallet address: {address[:6]}...{address[-4:]}")
    print(f"Testnet API:    {TESTNET_API_URL}")
    print()

    # Workaround: testnet spot_meta has token index mismatches; pass empty to skip
    info = Info(TESTNET_API_URL, skip_ws=True, spot_meta={"universe": [], "tokens": []})

    # 1. Check API connectivity via market data
    print("--- Market Data ---")
    try:
        mids = info.all_mids()
        print(f"OK: {len(mids)} markets active")
        for symbol in ["BTC", "ETH", "SOL"]:
            if symbol in mids:
                print(f"  {symbol}: ${float(mids[symbol]):,.2f}")
    except Exception as e:
        print(f"FAIL: {e}")
        sys.exit(1)

    print()

    # 2. Check account state
    print("--- Account State ---")
    try:
        state = info.user_state(address)
        if state and "marginSummary" in state:
            margin = state["marginSummary"]
            equity = float(margin.get("accountValue", 0))
            available = float(margin.get("totalRawUsd", 0))
            print(f"Account equity:    ${equity:,.2f}")
            print(f"Available balance: ${available:,.2f}")
            if state.get("assetPositions"):
                print(f"Open positions:    {len(state['assetPositions'])}")
                for pos in state["assetPositions"]:
                    p = pos.get("position", {})
                    print(f"  {p.get('coin')}: size={p.get('szi')} entry={p.get('entryPx')}")
            else:
                print("Open positions:    none")

            if equity == 0:
                print()
                print("WARNING: Account has zero balance.")
                print("The testnet faucet may not have worked.")
                print("Options:")
                print("  1. Retry faucet: https://app.hyperliquid-testnet.xyz/drip")
                print("  2. Try a different address")
                print("  3. Ask on HL Discord for testnet USDC")
        else:
            print("Account not found on testnet (no margin data)")
            print("This address may not have been activated on testnet yet.")
    except Exception as e:
        print(f"FAIL: {e}")

    print()

    # 3. Check open orders
    print("--- Open Orders ---")
    try:
        orders = info.open_orders(address)
        print(f"Open orders: {len(orders)}")
    except Exception as e:
        print(f"FAIL: {e}")


if __name__ == "__main__":
    main()
