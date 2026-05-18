# HIP-3 Mainnet Operational Runbook

## 1. Pre-launch checklist

Before starting the bot on mainnet:

- [ ] Config copied: `cp docs/hip3-mainnet.yaml.template secrets/hip3-mainnet.yaml`
- [ ] `account_address` set to your mainnet wallet
- [ ] `keyfile_path` points to your mainnet keyfile
- [ ] `confirm_mainnet: true` set (bot refuses to start without this)
- [ ] `OSBOT_KEYFILE_PASSWORD` env var set (or `keyfile_password` in config)
- [ ] Dry-run passes: `python -m osbot --config secrets/hip3-mainnet.yaml --dry-run`
- [ ] Smoke-test passes: `python -m osbot --config secrets/hip3-mainnet.yaml --smoke-test`
- [ ] Account has sufficient USDC deposited (minimum $300 for 3-pair micro deployment)
- [ ] No stale positions or open orders from prior sessions (smoke-test prints position count)
- [ ] Current time is within US market hours (Mon–Fri, 09:30–16:00 ET ideally)

## 2. Starting the bot

```bash
source venv/bin/activate
export OSBOT_KEYFILE_PASSWORD='...'

# Dry-run first — verify config loads and looks right
python -m osbot --config secrets/hip3-mainnet.yaml --dry-run

# Smoke-test — verify connectivity and account balance
python -m osbot --config secrets/hip3-mainnet.yaml --smoke-test

# Launch
nohup python -m osbot --config secrets/hip3-mainnet.yaml --run \
  > data/hip3-mainnet-$(date +%Y%m%d-%H%M%S).log 2>&1 &
echo $! > data/hip3-mainnet.pid
```

Startup sequence (10 steps, all logged):
1. Config validation (mainnet opt-in gate)
2. Mode assertion
3. Keyfile decryption
4. Wallet derivation (agent-wallet or master key)
5. HLClient construction
6. Account value fetch and validation
7. Leverage set (isolated, per-pair)
8. Meta fetch (szDecimals)
9. Cancel all open orders for configured pairs (clean slate)
10. Shadow DB startup snapshot

Watch the first 30 seconds of logs for all 10 steps completing:
```bash
tail -f data/hip3-mainnet-*.log | head -50
```

## 3. Health checks

### Automated health endpoint

The bot runs a `/health` endpoint on `127.0.0.1:8080`:
```bash
curl -s localhost:8080/health | python -m json.tool
```

Response fields:
| Field | Healthy value | Investigate if |
|-------|---------------|----------------|
| `status` | `"healthy"` | `"unhealthy"` |
| `last_tick_age_s` | < 5 | > 30 (stale — bot stuck or crashed) |
| `errors` | low, stable | rapidly increasing |
| `account_value` | near starting equity | dropping > 3% from session start |
| `graceful_stop` | `false` | `true` (bot is shutting down) |
| `ws_connected` | `true` | `false` (WS down, running on REST fallback) |

HTTP 200 = healthy, HTTP 503 = unhealthy.

### Shadow DB spot-checks

The shadow DB (`data/hip3-mainnet-shadow.sqlite`) records everything:

```bash
# Latest equity reading
sqlite3 data/hip3-mainnet-shadow.sqlite \
  "SELECT datetime(ts, 'unixepoch'), json_extract(payload, '$.value')
   FROM snapshots WHERE kind='equity' ORDER BY ts DESC LIMIT 5"

# Fill count and volume in the last hour
sqlite3 data/hip3-mainnet-shadow.sqlite \
  "SELECT count(*), sum(json_extract(payload, '$.px') * json_extract(payload, '$.sz'))
   FROM fills WHERE ts > unixepoch() - 3600"

# Per-pair net PnL
sqlite3 data/hip3-mainnet-shadow.sqlite \
  "SELECT json_extract(payload, '$.coin'),
          sum(json_extract(payload, '$.closedPnl')),
          sum(json_extract(payload, '$.fee'))
   FROM fills GROUP BY 1"

# Weekend flatten events
sqlite3 data/hip3-mainnet-shadow.sqlite \
  "SELECT datetime(ts, 'unixepoch'), payload
   FROM snapshots WHERE kind='weekend_flatten' ORDER BY ts DESC LIMIT 10"

# Check for errors or stops
sqlite3 data/hip3-mainnet-shadow.sqlite \
  "SELECT datetime(ts, 'unixepoch'), payload
   FROM snapshots WHERE kind='runner_exit' ORDER BY ts DESC LIMIT 3"
```

### Manual monitoring cadence

First week on mainnet:
- **Every 2h during market hours**: `curl localhost:8080/health`
- **At Friday 16:05 ET**: confirm weekend flatten fired (check logs or shadow DB)
- **Monday 09:35 ET**: confirm grid resumed after market open
- **Daily**: run the per-pair net PnL query above

After first week (if stable):
- **2–3x per day during market hours**: health check
- **Friday evening + Monday morning**: verify weekend transition

## 4. Exit codes and automatic stops

| Exit code | Meaning | What happened | Action |
|-----------|---------|---------------|--------|
| 0 | Clean exit | SIGINT/SIGTERM or `--max-ticks` reached | Normal. Restart if desired. |
| 2 | Auth failure | HL rejected credentials (key expired, agent wallet revoked) | Fix credentials, do not restart blindly. |
| 3 | Risk breach | Drawdown exceeded `max_daily_loss_pct` (3%) | **Do not restart immediately.** Investigate position state and market conditions. |

On any non-zero exit, check the runner_exit snapshot:
```bash
sqlite3 data/hip3-mainnet-shadow.sqlite \
  "SELECT datetime(ts, 'unixepoch'), payload
   FROM snapshots WHERE kind='runner_exit' ORDER BY ts DESC LIMIT 1"
```

### What graceful shutdown does

On SIGINT/SIGTERM (or risk breach):
1. Cancels all tracked grid orders for each pair
2. Sweeps any stray orders via `open_orders()` + cancel
3. **Does NOT close open positions** — they remain on the account

This is by design: a graceful stop should not force-liquidate into a bad market. Positions are managed manually after a stop (see kill-switch below).

## 5. Kill-switch procedure

### Soft kill (graceful)

```bash
kill $(cat data/hip3-mainnet.pid)
```
Triggers graceful shutdown: cancels all grid orders, leaves positions open, writes runner_exit snapshot. Bot exits within a few seconds.

### Hard kill (immediate)

```bash
kill -9 $(cat data/hip3-mainnet.pid)
```
Process dies immediately. **Orders remain live on HL.** You must cancel them manually.

### After any kill — clean up on HL

1. Go to [app.hyperliquid.xyz](https://app.hyperliquid.xyz) → Portfolio → Orders
2. Cancel all open orders for NVDA, TSLA, MSTR
3. Review open positions — decide whether to:
   - Hold (if small and market is calm)
   - Market-close via the HL UI (if you want flat)
4. Verify account state is clean before restarting the bot

### Emergency: risk breach during market hours

If the bot stopped due to exit code 3 (risk breach):
1. **Do not restart.** The 3% daily loss limit triggered for a reason.
2. Check what happened: sudden move in one pair? Cascade of adverse fills?
3. Check positions on HL UI — are they still open? How large?
4. Decide: close positions manually, or wait for mean-reversion?
5. If restarting same day: the bot uses session-start equity as baseline, so a restart resets the 3% limit to current (lower) equity.

## 6. Market hours behavior

The bot has three modes for equity perps:

| Session | When (Eastern) | Bot behavior |
|---------|----------------|--------------|
| REGULAR | Mon–Fri 09:30–16:00 | Normal grid: plan, submit, replan |
| EXTENDED | Mon–Fri 04:00–09:30, 16:00–20:00 | Normal grid (same as regular) |
| CLOSED | 20:00–04:00, weekends, holidays | Cancel grid, no new orders, positions held |

### Weekend flatten (Friday close)

At **15:55 ET Friday** (5 minutes before regular close):
1. All grid orders cancelled
2. All open equity perp positions market-closed
3. `weekend_flatten` event logged to shadow DB

From 16:00 ET Friday to 04:00 ET Monday: CLOSED session. No trading, no positions.

**If the bot is not running at 15:55 ET Friday:** positions from the week are NOT automatically closed. You must close them manually via the HL UI before the weekend.

### Crypto pairs (BTC, ETH, etc.)

Not affected by market hours. If you add crypto pairs to the forager, they trade 24/7 regardless of session.

## 7. Position sizing and limits

From `hip3-mainnet.yaml.template`:

| Parameter | Value | Effect |
|-----------|-------|--------|
| `leverage` | 3× (MSTR: 2×) | Max position = 3× allocated capital per pair |
| `wallet_exposure_limit` | 0.15 | ~$150 total exposure per pair on $1000 account |
| `max_daily_loss_pct` | 0.03 | Bot halts if session equity drops 3% from start |
| `min_notional_usd` | 10.0 | HL minimum; orders below this are bumped up |
| `grid_levels` | 5 (MSTR: 3) | Orders per side of the grid |

With $1000 account and 3 pairs: each pair gets ~$333 allocation, 0.15 WEL = ~$50 max position per pair, ~$150 total exposure across all pairs.

**Worst-case scenario:** all 3 pairs hit SL simultaneously at 2% each = ~$3 loss per pair = $9 total (~0.9% of account). Well within the 3% daily limit.

## 8. Restarting after a crash

If the bot dies unexpectedly (OOM, machine reboot, unhandled exception):

1. Check if it's still running: `ps -p $(cat data/hip3-mainnet.pid) > /dev/null && echo running || echo stopped`
2. Check last exit event: `sqlite3 data/hip3-mainnet-shadow.sqlite "SELECT payload FROM snapshots WHERE kind='runner_exit' ORDER BY ts DESC LIMIT 1"`
3. Check for open positions/orders on HL UI
4. If positions exist: the bot's ExitManager re-tracks any non-zero position on first tick after restart and applies TripleBarrier exits. Safe to restart.
5. If orders exist: startup step 9 cancels all open orders for configured pairs. Safe to restart.
6. Restart using the same launch command from section 2.

**Position carry-over is safe.** The bot is designed for it: startup cancels stale orders, ExitManager picks up existing positions, and the grid replans from scratch.

## 9. Log file management

Logs go to `data/hip3-mainnet-YYYYMMDD-HHMMSS.log`. They grow ~1–5 MB/day depending on fill rate.

```bash
# Tail live logs
tail -f data/hip3-mainnet-*.log

# Search for errors
grep -i "error\|warning\|failed\|breach" data/hip3-mainnet-*.log

# Search for weekend flatten events
grep "weekend_flatten" data/hip3-mainnet-*.log

# Search for risk events
grep "risk precheck" data/hip3-mainnet-*.log
```

Shadow DB grows ~5–20 MB/week. No rotation needed for months at micro-size.
