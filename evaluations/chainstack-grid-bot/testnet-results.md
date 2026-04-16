# Chainstack Grid Bot — Testnet Trial Results

**Date started**: 2026-04-15
**Trial status**: In progress (launched, orders placed, observation ongoing)
**Environment**: HL testnet, Docker sandbox (`bot-testnet-chainstack` service)
**Initial balance**: $999 mock USDC

## Configuration Used

`evaluations/chainstack-grid-bot/testnet-config.yaml`:
- Symbol: BTC
- Grid levels: 5
- Allocation: 10% ($100)
- Range: ±5% auto (min 3%, max 10%)
- Stop loss: 10%, max drawdown: 15%, max position: 20%
- Log level: DEBUG

## Launch Sequence (Successful)

1. Docker build with uv support (~60s)
2. Config validation via `--validate` flag — passed
3. Container start — testnet API connection, WebSocket subscription, strategy init all succeeded
4. Initial grid placed within 10 seconds of startup:

| Side | Price | Size (BTC) | Notional |
|------|-------|-----------|----------|
| Buy  | $72,047 | 0.000278 | ~$20.00 |
| Buy  | $73,873 | 0.000271 | ~$20.02 |
| Buy  | $75,744 | 0.000264 | ~$20.00 |
| Sell | $77,664 | 0.000258 | ~$20.00 |
| Sell | $79,631 | 0.000251 | ~$20.00 |

BTC at launch: ~$75,700 (grid properly centered).

## Issues Encountered

### 1. SDK spot_meta bug on testnet (BLOCKER → patched)
- `hyperliquid-python-sdk` 0.22.0 `Info.__init__` and `Exchange.__init__` fail with `IndexError: list index out of range` on testnet
- Root cause: `spot_meta["tokens"][base]` lookup for spot universe token that has mismatched index on testnet
- Workaround: pass `spot_meta={"universe": [], "tokens": []}` to both `Info()` and `Exchange()` to skip spot mapping
- Patched in `bots/chainstack-grid-bot/src/exchanges/hyperliquid/adapter.py:78-79`
- Since `bots/` is gitignored/ephemeral, the patch is lost on re-clone. Should be upstreamed or re-applied each trial.

### 2. Min notional $10 enforcement (config issue → fixed)
- First run at `max_allocation_pct: 5%` = $50 / 5 levels = $10/level
- Orders at higher grid prices rounded to 0.00013 BTC × ~$75k = $9.75, rejected with `"Order must have minimum value of $10. asset=3"`
- Fix: bumped `max_allocation_pct` to 10% ($100 / 5 levels = $20/level)
- Lesson: HL min notional is strict; bot does not check before submission

### 3. Agent (API) wallet doesn't work with this bot (design limitation)
- User initially configured an HL agent wallet key, derived address showed $0 balance
- Chainstack bot calls `Info(url)` and `Exchange(wallet, url)` without `account_address` parameter
- Means it queries balances at the signing wallet's own address, not the master address
- Workaround: use master wallet private key directly (testnet-only — acceptable risk)
- Known improvement: patch adapter to accept `account_address` for agent wallet support

### 4. Faucet required mainnet activation
- Testnet drip at `app.hyperliquid-testnet.xyz/drip` requires ~$5 USDC bridged on Arbitrum to the HL bridge
- Returns generic "Something went wrong" otherwise
- User resolved by doing the mainnet activation step

### 6. Risk manager fires but cannot close positions (bot bug, not patched)
Surfaced by shadow data during the 2026-04-15 trial — captured repeatedly in `bot_log`:

```
core.engine - WARNING - 🚨 Risk Event: Position too large: 65.xx% >= 20.00%
core.engine - ERROR   - ❌ Error closing position BTC:
    Exchange.order() missing 4 required positional arguments:
    'is_buy', 'sz', 'limit_px', and 'order_type'
```

**Root cause** (`bots/chainstack-grid-bot/src/exchanges/hyperliquid/adapter.py:441-450`):

```python
order_request = {
    "coin": asset, "is_buy": close_side == "B", "sz": close_size,
    "limit_px": None, "order_type": {"limit": {"tif": "Ioc"}},
    "reduce_only": True,
}
result = self.exchange.order(order_request)  # ← dict as one positional arg
```

The HL SDK signature is positional: `Exchange.order(name, is_buy, sz, limit_px, order_type, reduce_only=False, ...)`. The bot's **other two** `exchange.order()` call sites at `adapter.py:185` and `:198` use the correct positional form and do work — so grid placement succeeds, but **the close-position path has never worked**. Additionally, `limit_px=None` would fail on HL even with correct signature: HL has no true market orders, and aggressive IOC still requires a real price.

**Consequence**: the risk manager (`risk_manager.py:269`) detects position > `max_position_size_pct` and raises a `CLOSE_POSITION` event every tick. Engine at `engine.py:299-306` tries `exchange.close_position()`, catches the TypeError, logs it, and returns False. Position is **never actually reduced**.

Observed during the 2026-04-15 trial: with `max_position_size_pct: 20` configured, margin_used reached ~73% of equity ($1.97 / $2.71) after the second buy fill. The risk event fired every minute thereafter but had no effect. On testnet with a $3 account this is harmless; on mainnet it would be a material defect — the bot ships with the *appearance* of risk control but no working enforcement.

**Not patched.** Per the project's "don't modify bot trading logic" rule and because `bots/` is gitignored/ephemeral, this is recorded as an evaluation finding rather than fixed. Fix would be ~8 lines: replace the dict with positional args and compute a real IOC price (e.g. mid ±3%).

**Rubric impact**: lowers engineering-quality and HL-integration subscores. The close-position code path appears untested against the SDK — no integration test would have missed this.

### 5. Profit calculator is a placeholder + fill detection is faked (bot bug, no upstream fix)
Two independent layers of broken reporting discovered while designing shadow data collection:

**Layer A — engine fakes fills** (`bots/chainstack-grid-bot/src/core/engine.py:394-399`):

```python
# Simulate immediate execution for now (real implementation would track fills)
executed_price = order.price or 0.0
self.strategy.on_trade_executed(signal, executed_price, order.size)
self.executed_trades += 1
```

`on_trade_executed` fires the moment a limit order is **submitted**, not when it fills. `_update_order_statuses()` at `engine.py:427` is a stub that only garbage-collects orders after 1h — it never polls `info.user_fills`. Therefore `total_trades`, `filled_levels`, and `GridLevel.is_filled` all actually mean "orders placed," not "fills observed."

**Layer B — profit formula is a fixed constant** (`bots/chainstack-grid-bot/src/strategies/grid/basic_grid.py:253-257`):

```python
if signal.signal_type == SignalType.SELL:
    buy_price = executed_price * 0.99  # Approximate
    profit = (executed_price - buy_price) * executed_size
    self.total_profit += profit
```

This adds a fixed **1% of sell notional** per SELL signal, regardless of any matching buy. No fees, no funding, no pair matching, no inventory mark-to-market.

**Conclusion**: `get_status()["total_profit"]` is fictional and `total_trades` counts submissions. Do not trust either. Because `bots/` is gitignored/ephemeral we are not patching the bot; we compute real P&L out-of-band from `user_fills` via `tools/shadow_collector.py` — see [`shadow/README.md`](shadow/README.md).

## Observations So Far

- Build + launch pipeline end-to-end: works
- Docker sandbox testnet profile: works (env_file, config mount, read-only FS, 512MB memory)
- Order signing and submission: works
- WebSocket subscription and price feed: works
- Grid placement logic: works, correctly centers around current price
- Order fill detection: NOT YET OBSERVED (known weakness — bot assumes immediate execution)

## 24-Hour Trial Complete (2026-04-15 04:11 UTC → 2026-04-16 04:14 UTC, 25.04h)

Full analyzer output: [`shadow/report-20260416-final.md`](shadow/report-20260416-final.md).

**Headline numbers**

| | |
|---|---|
| Trial duration | 25.04h |
| BTC first/last | $75,855.50 → $75,164.50 (**−0.91%**) |
| Realized 1h σ (mean / max) | 0.093% / 0.397% |
| Fills | **2 buys, 0 sells** — no round-trip |
| Total notional volume | $39.64 |
| Total fees paid | $0.005945 |
| Sum `closedPnL` | **$0.00** |
| Net realized P&L | **−$0.006** (just the fees) |
| Equity first / last | $3.0184 → $3.0061 (−0.41%) |
| Max equity / min equity | $3.2466 / $2.4125 |
| Max drawdown | **21.21%** intra-trial (recovered by end) |
| Margin used (end) | $1.99 (~66% of equity — above the 20% cap, risk mgr couldn't enforce) |
| Rebalance events | **0** (price drift stayed within 10% threshold) |
| Position size (end) | 0.00053 BTC |
| Position / price correlation (Pearson) | −0.52 — bot correctly bought into dips |
| CPU mean / max | 0.08% / 4.54% |
| Memory mean / max | 76.5 MB / 78.8 MB (of 512 MB limit) |
| WS/API disconnects | observed 1× HL 502 outage (11:52 UTC), absorbed cleanly |

**Fill detail**

| Time (UTC) | Side | Size | Price | Fee | closedPnL |
|---|---|---|---|---|---|
| 2026-04-15 03:12 | BUY | 0.00026 | $75,744 | $0.00295 | $0.00 |
| 2026-04-15 11:49 | BUY | 0.00027 | $73,872 | $0.00299 | $0.00 |

**Bot reported vs reality**

- Bot's `Total trades: 5` counter vs 2 actual exchange fills → confirms Issue #5 in live data.
- Bot's `total_profit` field never even emits (the bot only writes that field internally, never logs it).
- Real P&L is dominated by fees; no round-trip completed in 25h.

**Questions now answered** (replaces the earlier 24-48h TODO list)

| Question | Finding |
|---|---|
| Rebalance behavior on price drift | Not exercised — BTC stayed in 2.2% p99 1h range vs 10% trigger. Code path untested. |
| Fill detection accuracy | Broken (Issue #5). Shadow collector got ground truth via `user_fills`. |
| WebSocket stability over time | Mixed. Bot's WS held up. Our shadow WS silently stopped firing callbacks for several hours once (caught on collector restart). Suggests HL testnet WS is not perfectly reliable — `allMids` can go quiet without an observable disconnect. |
| Memory/CPU profile | Excellent — 77 MB flat, 0.08% CPU avg. No leaks over 25h. |
| Disconnection events | One HL-side 502 Bad Gateway wave (~30s), recovered cleanly. 52 "reconnect" keyword hits in bot logs — most are normal httpcore request cycles, not WS reconnects. |
| P&L accounting | Only fees incurred; `closedPnL = 0` on both fills (both Open Long). No mechanism exposes the unrealized equity curve outside of HL account state. |

**New findings surfaced during the trial**

- Issue #5 (placeholder profit calc + fake fill detection) — confirmed end-to-end in live data.
- Issue #6 (broken `close_position` + non-functional risk manager) — directly observed; risk event fired every minute from ~11:50 UTC onward with no effect.
- **Grid never re-plants filled levels.** After the 2 buys filled, levels 73,872 and 75,744 went idle permanently. No rebalance triggered. The strategy only reconstructs the grid on rebalance, leaving fills "dead" in the meantime — a material architecture flaw for a sideways market.
- **Bid-ask spread tight on testnet**: 5.4 bps average. Not the blocker for low fill rate.
- **Grid too wide for realized vol**: 10% configured range vs p99 1-hour excursion of 2.23% → grid levels at ±5% rarely reachable. Config should have been ±2% for this vol regime.

## What Still Needs to Be Documented (post 24-48h)

— Superseded by the "24-Hour Trial Complete" section above. All items addressed.

## Files Touched

- `sandbox/Dockerfile.python` — Python 3.13, uv.lock support, venv PATH
- `sandbox/docker-compose.yml` — added `bot-testnet-chainstack` service
- `.env.example` — added Chainstack env var names (HYPERLIQUID_TESTNET_PRIVATE_KEY, HYPERLIQUID_TESTNET)
- `evaluations/chainstack-grid-bot/testnet-config.yaml` — trial config (ultra-conservative then bumped allocation)
- `tools/check_testnet.py` — diagnostic script (SDK connectivity, account balance, open orders)
- `bots/chainstack-grid-bot/src/exchanges/hyperliquid/adapter.py` — spot_meta workaround (ephemeral, must be re-applied on re-clone)

## Shadow Data Collection

Runs alongside the bot to capture ground-truth fills, equity, open orders,
mid prices, and bot log output into a SQLite research DB — independent of
the bot's broken internal reporting (Issue #5).

- `tools/shadow_collector.py` — long-running host-side collector (WS + polling + docker log tail).
- `tools/shadow_analyze.py` — generates a markdown report from the DB.
- `shadow/` — per-trial DBs (gitignored) and committed reports.

See [`shadow/README.md`](shadow/README.md) for usage, schema, and what
questions the report answers.

## How to Run / Monitor / Stop

```bash
# Start
BOT_NAME=dummy BOT_PATH=bots/dummy docker compose -f sandbox/docker-compose.yml \
  --profile testnet up -d bot-testnet-chainstack

# Watch
docker logs -f sandbox-bot-testnet-chainstack-1

# Stop
docker stop sandbox-bot-testnet-chainstack-1

# Diagnose wallet state (from host, not container)
source venv/bin/activate && python tools/check_testnet.py
```

(`BOT_NAME`/`BOT_PATH` dummies are needed because other compose services interpolate them; the chainstack service hardcodes its own BOT_PATH.)
