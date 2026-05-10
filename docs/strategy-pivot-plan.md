# Strategy Pivot Plan — Framing B

**Decided 2026-05-06.** osbot Avellaneda γ=1000 159h soak landed at -1.18%; user rejected the entire single-pair-grid-MM-on-BTC strategy class. Live bot stopped this session (clean SIGTERM at NAV $847.71, 0 positions). No more incremental tweaks — committing to a real strategy bet from the underexplored directions in the catalog.

## Project framing

The 25-bot eval is finished and produced two assets: `docs/lessons.md` (506 lines) and `docs/custom-bot-design-notes.md` (277 lines). The osbot infrastructure (connector, throttler, ShadowLogger, retry, WS resilience, dual cloid↔oid, fill reconciliation) is solid and lifts directly from those lessons.

**Framing A** (eval was the project, wrap up) was rejected.
**Framing B** (eval was input, output is a profitable bot) was chosen.

This means committing weeks — not 200-LOC patches — to a strategy class that actually has structural edge.

## Two real candidates

After dropping DCA/unstuck (a feature on top of grid MM, not a different class):

- **XEMM-class cross-venue** — short HL when funding/price dislocates from another venue, long the counter-venue, hedged. Documented institutional strategy. OSS XEMM eval shows working Rust implementation. Engineering cost: high (multi-venue infra, leg-sync, multi-margin tracking).
- **HIP-3 first-mover** — equity perps grid MM where the "weaker MMs and slower flow" thesis from the catalog applies. Reuses all existing osbot infra. Engineering cost: medium (~150 LOC on existing forager work). Thesis is currently **inferred, not measured**.

## Rule before committing: one week of measurement

We picked Avellaneda partly because "skew is textbook" — that was vibes, not evidence, and it cost weeks. Will not repeat. **Both candidate theses are testable with read-only mainnet data before any strategy code is written.**

## Track 1 — HIP-3 thesis validation (1-2 days)

Read-only mainnet data pull. For each HIP-3 perp (NVDA, TSLA, AAPL, COIN, MSTR, plus whatever else is live) vs BTC-PERP as control:

- Time-weighted spread (bid-ask, normalized by mid).
- Top-of-book quote update frequency (proxy for MM aggressiveness).
- Depth at ±5bps, ±25bps, ±100bps.
- Daily volume and open interest.
- Funding rate level and stability.

**Decision rule**: HIP-3 is a go if **spreads ≥3× BTC AND quote turnover ≤1/3 of BTC's**. Otherwise "weaker MMs" is mostly a story.

## Track 2 — XEMM-class thesis validation (1-2 days)

Read-only data pull. BTC-PERP and ETH-PERP funding rates on HL vs Binance vs Bybit, hourly, over 7-14 days.

- Mean spread between HL funding and best counter-venue.
- Persistence: fraction of hours where spread > tradeable threshold for ≥4 consecutive hours.
- Volatility of the spread (matters for hedge sizing).

**Decision rule**: XEMM is a go if **mean spread > 8% APY AND persistence > 60% of hours**. Otherwise hedge costs eat the edge.

## Track 3 — XEMM OSS sanity check (half day)

Re-read the OSS XEMM repo (Pacifica-HL Rust). Confirm:
- What it actually does end-to-end (which legs, which hedge model, how it sizes).
- Testnet support story (we know one-line flag fix; verify nothing else is hardcoded).
- Whether porting/forking is realistic given our Python infra, or if XEMM stays its own Rust spinoff.

## First concrete action

Write `tools/market_survey.py` — read-only data collector that produces a SQLite file for Track 1 + Track 2 analysis. ~150 LOC, no strategy logic, no risk, no order placement. Pulls from:
- HL Info API (mainnet) for spreads, depth, funding, volume per asset.
- Binance / Bybit public funding-rate endpoints (no API keys needed for public data).

Schema sketch (one table per data class is fine):
- `hl_book_snapshots(ts, asset, mid, spread_bps, depth_5bps, depth_25bps, depth_100bps, top_update_hz)` — sampled every N seconds.
- `funding_rates(ts, venue, asset, hourly_rate, apy_pct)` — sampled hourly, includes HL/Binance/Bybit.
- `volume_oi(ts, asset, daily_volume_usd, oi_usd)` — sampled hourly.

Run for 7-14 days. Then analyze against the decision rules. Then pick the bet.

## What we will NOT do during the measurement week

- Restart the live bot.
- Tune γ, Avellaneda, or any grid params.
- Build forager v2.
- Touch the strategy module at all.
- Call this measurement "the next milestone" — it's the gate before the next milestone.

## Deferred (still in catalog, not in this plan)

- DCA/unstuck (deferred — same strategy class as what just failed).
- TrendRegularityFilter (deferred — wrong layer of problem).
- WebAuthn lockbox (deferred — research project doesn't need production key handling).

## Success criteria for the measurement phase

By end of measurement week we have:
1. A SQLite file with 7-14 days of HL spread/depth/funding/volume data + cross-venue funding data.
2. A short analysis writeup (one section in this doc) applying the decision rules.
3. A go/no-go on each track, evidence-based.
4. A picked direction (XEMM-class or HIP-3) with the engineering shape understood.

Only then does strategy code start.
