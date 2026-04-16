# Chainstack Grid Bot — Shadow Data Collection

Out-of-process, read-only telemetry that runs alongside the bot on Hyperliquid
testnet so we can evaluate trial results without depending on the bot's broken
in-process profit calculator (see
[`../testnet-results.md`](../testnet-results.md) Issue #5 for the root cause).

Everything here is research tooling — no part of it modifies the bot or its
trading strategy.

## Why

The bot's `total_profit` is a placeholder (1% of sell notional) and
`on_trade_executed` fires on order submission, not fill. We cannot trust the
bot's own reporting, so we compute P&L and fit diagnostics from the exchange
directly.

## Files

- `*.db` — SQLite databases, one per trial (gitignored, ephemeral).
- `report-*.md` — generated analysis reports (committed).

## Collector

`tools/shadow_collector.py` is a long-running multi-threaded process that:

- Subscribes to HL WebSocket `allMids` (falls back to 2s polling).
- Polls `user_state`, `open_orders`, `user_fills` every 30s.
- Polls `l2_snapshot` every 60s for best bid/ask.
- Optionally tails `docker logs -f sandbox-bot-testnet-chainstack-1`.
- Optionally captures `docker stats` every 60s.

It writes to a single SQLite DB per trial with WAL mode. One dedicated writer
thread serializes all writes. Fills are deduped by `tid` via `INSERT OR IGNORE`.

### Run

```bash
source venv/bin/activate

# Start: picks up HYPERLIQUID_TESTNET_PRIVATE_KEY from .env, derives address,
# writes to evaluations/chainstack-grid-bot/shadow/trial-<UTC>.db
python tools/shadow_collector.py

# Or pin an address explicitly and skip the key:
python tools/shadow_collector.py \
  --address 0xYOURADDR \
  --out evaluations/chainstack-grid-bot/shadow/trial-$(date -u +%Y%m%d-%H%M).db

# Useful flags:
#   --assets BTC,ETH        Comma-separated watch list (default BTC)
#   --bot-container NAME    Docker container to tail (default sandbox-bot-testnet-chainstack-1)
#   --no-docker-logs        Skip log tailing
#   --no-docker-stats       Skip CPU/mem sampling
#   --verbose               DEBUG logging to stderr
```

Stop with Ctrl-C (SIGINT) or `kill` (SIGTERM); the collector drains its write
queue, closes WS + DB, prints a per-table row count, and exits cleanly.

Runs on the host (not inside Docker) to avoid needing to expose the docker
socket. Same pattern as `tools/check_testnet.py`.

## Analyzer

`tools/shadow_analyze.py` reads a DB and emits a markdown research report.
Stdlib only — no pandas.

### Run

```bash
source venv/bin/activate

python tools/shadow_analyze.py \
  evaluations/chainstack-grid-bot/shadow/trial-YYYYMMDD-HHMM.db \
  --coin BTC \
  --config-range-pct 5.0 \
  --config-levels 5 \
  --out evaluations/chainstack-grid-bot/shadow/report-$(date -u +%Y%m%d).md
```

If `--out` is omitted, the report is written next to the DB with a
`-report-<UTC>.md` suffix.

## Schema

One DB per trial. Tables (all `ts` fields are float UNIX epoch seconds):

| Table              | Purpose                                         |
|--------------------|-------------------------------------------------|
| `mids`             | WS mid prices (+ sparse bid/ask from L2 polls)  |
| `account_snapshots`| equity / withdrawable / margin used every 30s   |
| `positions`        | per-asset size, entry px, unrealized PnL        |
| `open_orders`      | one row per live order per 30s snapshot         |
| `fills`            | realized trades from `user_fills` (PK = `tid`)  |
| `grid_snapshots`   | derived: n_buy, n_sell, min/max/center px       |
| `rebalance_events` | derived: detected mass cancel + re-place        |
| `bot_log`          | parsed lines from `docker logs`                 |
| `resource_usage`   | cpu % and mem MB from `docker stats`            |
| `meta`             | started_at, address, assets, collector_version  |

Indexes on `ts` (and `asset`/`coin` where relevant). Schema is a strict
superset of the spec — extra columns (`raw_json`, `reduce_only`, `order_type`,
leverage fields) are present for forensic value.

## What the report answers

1. Realized volatility vs configured `range_pct` — is the grid wide enough?
2. Per-level fill histogram — are edge levels idle?
3. Real P&L from `closedPnl - fee` — contrast with bot's fake `total_profit`.
4. Inventory-vs-price correlation — is the bot accumulating trend exposure?
5. Rebalance frequency and cost.
6. WebSocket / container stability over the run.

Heuristic suggestions in section 10 only fire when their trigger condition is
met against the real data. None of this changes bot parameters — edits to
`testnet-config.yaml` are still manual.

## Out of scope here

- Re-simulating the grid on captured tick data with grid-search over
  `(range_pct, levels, rebalance_threshold_pct)`. That's a follow-up once we
  have ≥7 days of trials.
- Fixing the bot's profit calc upstream. We compute P&L out-of-band instead.
