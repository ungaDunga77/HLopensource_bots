# Shadow Analysis Report

- DB: `evaluations/chainstack-grid-bot/shadow/trial-20260415-0411.db`
- Coin: `BTC`
- Config range_pct: 5.0
- Config levels: 5
- Generated: 2026-04-16 04:14:38Z

## 1. Trial metadata

| Key | Value |
|---|---|
| started_at | 1776270103.2088678 |
| address | 0x0d3Bc6B8BA597c1AC2a0E8a2d2C969372f1B4e88 |
| assets | BTC |
| collector_version | 1.0 |
| bot_container | sandbox-bot-testnet-chainstack-1 |

- Span: 2026-04-15 03:12:23Z -> 2026-04-16 04:14:35Z (25.037h)

Row counts:

| Table | Rows |
|---|---|
| mids | 2439 |
| account_snapshots | 2396 |
| positions | 2396 |
| open_orders | 7633 |
| fills | 2 |
| grid_snapshots | 2395 |
| rebalance_events | 0 |
| bot_log | 36285 |
| resource_usage | 1409 |
| meta | 5 |

## 2. Market conditions (BTC)

- First mid: 75855.50
- Last mid:  75164.50
- Min mid:   73917.00
- Max mid:   76056.00
- Cumulative return: -0.911%

- 1-min realized sigma: 0.117%
- Annualized sigma:    84.815%
- Rolling 1h sigma (mean): 0.093%
- Rolling 1h sigma (max):  0.397%
- Avg bid-ask spread: 5.364 bps (1203 samples)

## 3. Grid configuration fit

| Metric | Mean | Min | Max |
|---|---|---|---|
| center_px | 75839.0000 | 75839.0000 | 75839.0000 |
| spread_pct | 10.0001 | 10.0001 | 10.0001 |
| n_buy | 1.1871 | 1.0000 | 2.0000 |
| n_sell | 2.0000 | 2.0000 | 2.0000 |

Configured full grid width: 10.000%

| Percentile | 1h excursion % | Ratio to grid width |
|---|---|---|
| p50 | 0.494 | 0.049 |
| p90 | 1.147 | 0.115 |
| p99 | 2.230 | 0.223 |

Rebalance events: 0.

## 4. Fills and realized P&L

- Total fills: 2 (buys=2, sells=0)
- Total notional volume: $39.64
- Total fees: $0.005945
- Sum closed_pnl: $0.000000
- Net realized PnL (closed_pnl - fees): $-0.005945
- Buy VWAP:  74790.34
- Sell VWAP: N/A

Top 10 hours by fill count:

| Hour (UTC) | Fills |
|---|---|
| 2026-04-15 03:00:00Z | 1 |
| 2026-04-15 11:00:00Z | 1 |

Per-level fill histogram (4 distinct levels observed):

| Level price | Fills |
|---|---|
| 72047.00 | 0 |
| 73872.00 | 2 |
| 77663.00 | 0 |
| 79631.00 | 0 |

Config `levels` = 5; observed distinct levels = 4.

## 5. Equity curve

- First equity: $3.0184
- Last equity:  $3.0061
- Max equity:   $3.2466
- Min equity:   $2.4125
- Max drawdown: 21.208%

Sampled equity trajectory:

| ts | equity | margin_used |
|---|---|---|
| 2026-04-15 04:11:35Z | 3.0184 | 0.9860 |
| 2026-04-15 10:18:11Z | 2.7828 | 0.9776 |
| 2026-04-15 12:32:20Z | 2.7246 | 1.9728 |
| 2026-04-15 14:46:29Z | 2.6544 | 1.9701 |
| 2026-04-15 17:03:05Z | 2.5237 | 1.9648 |
| 2026-04-15 19:17:44Z | 2.9180 | 1.9851 |
| 2026-04-15 21:31:52Z | 2.8852 | 1.9839 |
| 2026-04-15 23:45:59Z | 2.9233 | 1.9866 |
| 2026-04-16 02:00:08Z | 2.8604 | 1.9845 |
| 2026-04-16 04:14:17Z | 3.0061 | 1.9923 |

## 6. Bot reported vs. reality

- Bot-reported `Total trades` (last seen): 5
- 'Placed BUY/SELL order' log lines: 0
- Actual fills recorded: 2
- Gap (bot_reported_trades - fills): 3
  - Interpretation: bot's `executed_trades` counts orders SUBMITTED, not exchange fills. Gap = pending orders + orders that never filled (see engine.py:394-399).

- No 'profit' log lines found.

## 7. Inventory drift

- Position size — min: 0.000260, max: 0.000530, mean: 0.000480, final: 0.000530
- Pearson correlation (size vs mid): -0.5162 (n=1212)
  - Positive correlation = bot accumulates inventory as price rises (trend-exposed, bad for a grid).

## 8. Resource usage

- CPU %: mean 0.077, max 4.540
- Memory MB: mean 76.464, max 78.820 (docker limit: 512MB)

## 9. Error summary

- WARNING lines: 0
- ERROR lines:   0

Keyword counts (case-insensitive, any level):
- disconnect: 0
- reconnect: 52
- traceback: 0

## 10. Suggested parameter adjustments

- 80%+ of fills in central 50% of levels; edge levels idle — capital inefficient.

## 11. Raw data summaries

| Table | Rows | Min ts | Max ts |
|---|---|---|---|
| mids | 2439 | 2026-04-15 04:11:35Z | 2026-04-16 04:14:35Z |
| account_snapshots | 2396 | 2026-04-15 04:11:35Z | 2026-04-16 04:14:17Z |
| positions | 2396 | 2026-04-15 04:11:35Z | 2026-04-16 04:14:17Z |
| open_orders | 7633 | 2026-04-15 04:11:35Z | 2026-04-16 04:14:17Z |
| fills | 2 | 2026-04-15 03:12:23Z | 2026-04-15 11:49:48Z |
| grid_snapshots | 2395 | 2026-04-15 04:11:35Z | 2026-04-16 04:14:17Z |
| rebalance_events | 0 | N/A | N/A |
| bot_log | 36285 | 2026-04-15 04:11:35Z | 2026-04-16 04:13:56Z |
| resource_usage | 1409 | 2026-04-15 04:11:36Z | 2026-04-16 04:14:28Z |
| meta | 5 | N/A | N/A |

