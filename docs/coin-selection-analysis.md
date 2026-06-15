# Coin Selection Analysis — Which HL Perps Suit the Vol-Scaled Grid?

**Date:** 2026-06-14 · **Author:** Claude · **Data:** HL public API (`metaAndAssetCtxs`, `candleSnapshot` 1m, ~3.5 days), 55 liquid perps (24h vol > $1M), calibrated to the live testnet soak.

## TL;DR

The data does **not** reveal a hidden goldmine coin. It reveals a structural tension that explains why BTC/ETH come out break-even:

- **In this universe, liquidity and mean-reversion are anti-correlated.** The most liquid coins (BTC/ETH/SOL) trend more and mean-revert less; the strongly mean-reverting coins (KAITO, PUMP, kPEPE, TRX) are illiquid ($1–4M/day), where the grid's fee assumptions (maker 1.5bps / taker 4.5bps) and small taker exits get punished by wide spreads.
- **The one actionable, liquid, untested candidate is SOL** ($117M/day, 66% of time un-paused, mildly mean-reverting). It is the best "add to the forager candidate list and testnet-soak it next" bet — BTC/ETH are already shown to be break-even.
- **No backtest settles this. Only a testnet soak does** — see the validation failure below.

## The fee hurdle (calibrated from today's live soak)

From the live shadow DB (446 ETH fills): grid **entries fill maker @ 1.5 bps**, **exits are taker `market_close` @ 4.5 bps**. A round-trip therefore pays **≈ 5.5 bps** against a **20 bps TP target** → ~14.5 bps net per *winning* RT. The soak still netted **−$1.98 / 18.4h** because not every RT wins: adverse-selected maker fills + trend exits erase the gross edge (gross closedPnl was −$0.22; fees did the rest). **A coin is only worth trading if its short-horizon oscillation reliably clears ~5.5 bps after adverse selection.**

## What actually drives per-coin profitability

1. **Mean-reversion at the 13–45 bps scale** (the grid's spacing). Measured by variance ratio VR(30) (<1 = mean-reverting, >1 = trending) and 1-min return autocorrelation (more negative = better). **This is the edge.**
2. **Trend-pause avoidance** — `active%` = fraction of time `|EMA30m−EMA4h| ≤ range_min`. When a coin trends, the grid goes cancel-only and only eats taker exits. Higher = better.
3. **Liquidity** — needed for maker fills to actually rest-and-fill and for taker exits not to slip past 4.5 bps. The forager's existing `log_range × volume` score captures vol×liquidity but **ignores mean-reversion vs. trend**, which is the real discriminator.
4. **Realized vol** — must be high enough to generate fills, but the grid auto-scales its range, so *excess* vol just signals whippiness/trend. Sweet spot ≈ 5–12 bps/min; >15 bps/min coins rank terribly.
5. **Funding** — negligible here (positions are short-lived; most coins sit at the +0.0013%/h cap).

## Ranking (composite of robust regime stats; backtest shown as cross-check only)

Composite favors mean-reversion + liquidity + active%, penalizes extreme vol. `btBps/hr` is the grid sim — **directional only, see caveat.**

| Rank | Coin | VR30 | ac1(1m) | σ1m bps | active% | vol $M/d | btBps/hr | Note |
|---|---|---|---|---|---|---|---|---|
| 1 | **BTC** | 0.85 | −0.029 | 5.0 | 94% | 1300 | +12 | liquid, un-trendy, mild MR — but tightest spreads = least edge (live: break-even) |
| 2 | **ETH** | 0.92 | −0.019 | 6.4 | 90% | 688 | +11 | live-tested = **break-even after fees** |
| 3 | **SOL** | 0.98 | −0.019 | 7.6 | 66% | 118 | +16 | **best untested liquid candidate** |
| 4 | kPEPE | 0.75 | −0.064 | 9.3 | 72% | 3.8 | −4 | strong MR but thin book |
| 5 | KAITO | 0.54 | −0.008 | 22.2 | 43% | 1.2 | +17 | strongest MR, but illiquid + high vol = execution risk |
| 6 | BNB | 0.91 | −0.030 | 4.5 | 89% | 4.0 | +5 | calm, un-trendy, modest volume |
| 7 | TON | 0.77 | −0.054 | 14.0 | 29% | 11.7 | −5 | MR but trends often (low active%) |
| 8 | ZEC | 0.88 | −0.043 | 15.5 | 41% | 72 | −1 | liquid + MR but high vol/low active% |
| 9 | XRP | 0.97 | −0.037 | 6.8 | 74% | 11 | +8 | liquid, calm, weak MR |
| 10 | LTC | 0.83 | 0.000 | 6.0 | 78% | 1.7 | +12 | un-trendy, mild MR, thin |

**Bottom of the list (avoid):** high-σ / trending names — XMR & VVV (VR>1.25, i.e. *trending*), HYPE (VR 1.01, 27% active, bt −28), XPL/MEGA/WLD/PYTH/TRUMP (σ > 24 bps/min, whippy), EIGEN (bt −43). High volume ≠ tradeable: HYPE is $273M/day and ranks near the bottom because it trends.

## Validation failure — why the backtest is cross-check only

I built a faithful grid simulator (vol-scaled range, 3 levels, maker entries, taker TP/SL/TTL exits, trend-pause, live-calibrated fees) and **it failed validation against today's live soak:**

- Sim says ETH **+11 bps/hr (positive)**; live ETH was **net negative**.
- Sim does **~2.4 fills/hr**; live did **24 fills/hr** — a **10× fill-rate miss**.

Root cause: maker fills cannot be faithfully reconstructed from 1-minute OHLC. The first version even double-counted same-bar straddles (buy-low + sell-high in one candle = phantom profit, biased toward high-vol coins). Fixing that (one fill/bar, no same-bar RT, exits at close) tightened it but couldn't close the 10× gap or fix the sign. **Lesson: for a maker grid, an OHLC backtest is directionally suggestive at the extremes and worthless near zero. The only trustworthy test is a live testnet soak** — which is exactly what caught ETH's true break-even.

## Recommendation

1. **Add SOL to the forager candidate list** (`configs/hip3-testnet.yaml` → `forager.candidates: [BTC, ETH, SOL]`) and run a multi-day testnet soak. It's the only liquid, plausibly-better-than-ETH candidate, and the forager's `log_range × volume` rotation will naturally favor it when it's the most active.
2. **Do not chase the strong-MR low-caps (KAITO/PUMP/kPEPE) yet** — their edge is real on paper but their books are too thin to trust the 1.5/4.5 bps fee model; a single bad taker exit eats days of edge. Only revisit if maker-only exits are implemented.
3. **The honest conclusion stands:** this strategy is structurally thin on liquid HL perps. The genuine spread edge measured earlier lives on the HIP-3 equity perps (can't run safely at this capital) and on thin alts (execution-risk). Expanding the *liquid* candidate set buys diversification of regime, not a step-change in EV.

## Reproduce

- `/tmp/hl_universe.json` — full 179-coin snapshot · `/tmp/candles/*.json` — 1m candles (55 coins)
- `/tmp/grid_backtest.py` — simulator + regime metrics → `/tmp/backtest_results.json`
- `/tmp/composite.json` — composite ranking
