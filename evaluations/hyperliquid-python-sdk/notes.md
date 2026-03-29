# Baseline Reference Notes: hyperliquid-python-sdk

This document captures the SDK patterns that define "good HL integration" for scoring bots.

---

## Architecture

```
hyperliquid/
  api.py              — Base HTTP client (requests.Session, POST /info and /exchange)
  info.py             — Read-only queries (Info class extends API)
  exchange.py         — Write operations (Exchange class extends API, requires wallet)
  websocket_manager.py — WebSocket subscriptions (threading.Thread)
  utils/
    constants.py      — API URLs (mainnet, testnet, local)
    types.py          — TypedDict definitions for all data structures
    signing.py        — EIP-712 signing, action hashing, order wire conversion
    error.py          — ClientError / ServerError exceptions
```

Two main entry points:
- `Info(base_url)` — for read-only queries + websocket subscriptions
- `Exchange(wallet, base_url)` — for trading operations (internally creates an Info instance)

---

## Auth / Key Management Reference Pattern

1. Key is loaded externally (from config file or keystore)
2. `eth_account.Account.from_key(key)` creates a `LocalAccount`
3. `LocalAccount` passed to `Exchange(wallet=account)`
4. All signing happens through `wallet.sign_message(encode_typed_data(data))`
5. Only the signature `{r, s, v}` is sent to the API
6. Key is never serialized, logged, transmitted, or stored beyond the LocalAccount object

**What bots should do**:
- Load key from env var or encrypted keystore, never hardcode
- Pass to Exchange constructor, never reference directly after that
- Use agent/API wallet when possible (approve_agent creates a sub-key)

---

## Testnet Switching Mechanism

```python
from hyperliquid.utils.constants import MAINNET_API_URL, TESTNET_API_URL

# Testnet
info = Info(TESTNET_API_URL)
exchange = Exchange(wallet, TESTNET_API_URL)

# Mainnet (default if no base_url provided)
info = Info()  # defaults to MAINNET_API_URL
```

The SDK determines mainnet vs testnet internally via:
```python
is_mainnet = self.base_url == MAINNET_API_URL
```

This affects:
- EIP-712 signing chain (`"a"` for mainnet, `"b"` for testnet in phantom agent)
- User-signed actions set `hyperliquidChain` to `"Mainnet"` or `"Testnet"`

**What bots should do**:
- Default to testnet
- Require explicit configuration/flag to enable mainnet
- Never fall through to mainnet by accident

---

## API Surface (for scoring D3 in bot evals)

### Exchange Operations (write)
- `order()` / `bulk_orders()` — place orders (limit, IOC, trigger/TPSL)
- `modify_order()` / `bulk_modify_orders_new()` — modify existing orders
- `cancel()` / `bulk_cancel()` / `cancel_by_cloid()` / `bulk_cancel_by_cloid()`
- `market_open()` / `market_close()` — convenience wrappers with slippage
- `schedule_cancel()` — dead-man's switch
- `update_leverage()` / `update_isolated_margin()`
- `set_referrer()` / `approve_agent()` / `approve_builder_fee()`
- `create_sub_account()` / `sub_account_transfer()` / `sub_account_spot_transfer()`
- `vault_usd_transfer()`
- `usd_transfer()` / `usd_class_transfer()` / `send_asset()` / `spot_transfer()`
- `withdraw_from_bridge()`
- `token_delegate()` (staking)
- `spot_deploy_*()` — spot token deployment (8 methods)
- `perp_deploy_*()` — perp asset deployment (2 methods)
- `multi_sig()` — multi-sig transaction
- `c_signer_*()` / `c_validator_*()` — validator operations
- `user_dex_abstraction()` / `user_set_abstraction()`
- `use_big_blocks()` — EVM block size
- `noop()` — keep-alive

### Info Operations (read)
- `user_state()` / `spot_user_state()` — account/position info
- `open_orders()` / `frontend_open_orders()` / `historical_orders()`
- `all_mids()` / `l2_snapshot()` / `candles_snapshot()`
- `meta()` / `meta_and_asset_ctxs()` / `spot_meta()` / `spot_meta_and_asset_ctxs()`
- `user_fills()` / `user_fills_by_time()`
- `funding_history()` / `user_funding_history()`
- `user_fees()` / `user_rate_limit()`
- `user_staking_summary()` / `user_staking_delegations()` / `user_staking_rewards()` / `delegator_history()`
- `query_order_by_oid()` / `query_order_by_cloid()`
- `query_referral_state()` / `query_sub_accounts()`
- `portfolio()` / `user_vault_equities()` / `user_role()`
- `user_twap_slice_fills()`
- `extra_agents()`
- `perp_dexs()` / `query_perp_deploy_auction_status()`

### WebSocket Subscriptions (13 types)
- `allMids` — all mid prices
- `bbo` — best bid/offer per coin
- `l2Book` — L2 order book per coin
- `trades` — trade feed per coin
- `candle` — candlestick data per coin/interval
- `userEvents` — user trade events
- `userFills` — user fill events
- `orderUpdates` — order status changes
- `userFundings` — funding payments
- `userNonFundingLedgerUpdates` — non-funding ledger
- `webData2` — frontend data
- `activeAssetCtx` — live asset context per coin
- `activeAssetData` — live user+asset data

---

## Order Types and Grouping

```python
# Limit order
order_type = {"limit": {"tif": "Gtc"}}  # or "Alo" (add liquidity only), "Ioc" (immediate or cancel)

# Trigger order (TP/SL)
order_type = {"trigger": {"triggerPx": 50000.0, "isMarket": True, "tpsl": "tp"}}  # or "sl"

# Market order (convenience) — internally uses IOC limit with slippage
exchange.market_open(coin, is_buy=True, sz=1.0, slippage=0.05)

# Grouping for TPSL
grouping = "na"         # independent orders
grouping = "normalTpsl" # TP/SL linked
grouping = "positionTpsl" # position-level TP/SL
```

---

## Scoring Baseline

When scoring bots on D1 (SDK usage), check:
1. Does the bot import and use `hyperliquid.exchange.Exchange` and `hyperliquid.info.Info`?
2. Or does it make raw HTTP calls to the API? (lower score)
3. Does it properly handle the `is_mainnet` distinction?
4. Does it use agent wallets (`approve_agent`) or raw private keys?

When scoring bots on D3 (HL features), compare against the API surface above.
A basic bot uses: orders, cancels, user_state, all_mids.
A sophisticated bot also uses: WebSocket, modify, TPSL, leverage, vaults/subaccounts.
