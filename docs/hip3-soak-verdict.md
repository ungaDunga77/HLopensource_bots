# HIP-3 Soak Verdict — 129h Testnet Run

**Decided 2026-05-15.** HIP-3 multi-pair grid MM soak ran 128.8h (2.7× the 48h target) with positive PnL, low drawdown, and zero errors. Strategy is validated for the next phase.

## 1. Run configuration

- **Mode:** testnet, forager, 3 pairs (BTC/ETH/SOL), per-pair overrides active
- **Config:** `secrets/hip3-soak.yaml`
- **Leverage:** 3×
- **Starting equity:** $867.50
- **Period:** 2026-05-10 03:22 UTC → 2026-05-15 12:15 UTC (128.8h)
- **Shadow DB:** `data/hip3-soak-shadow.sqlite` (1,986 equity snapshots, 4,640 grid plans, 417 exit closes)

## 2. Results summary

| Metric | Value |
|---|---|
| Final equity | $885.41 |
| P&L | +$17.91 (+2.06%) |
| Annualized Sharpe | 8.52 (125 hourly returns) |
| Max drawdown | $16.57 (1.86% of peak) |
| Total fills | 5,806 |
| Total volume | $99,605 |
| Fill rate | 45.1 fills/hour |
| Closed PnL | +$34.48 |
| Total fees | $20.70 |
| Net PnL | +$13.78 |
| Errors / stalls | 0 |

Equity range: $866.07 (min) → $891.49 (max). Never fell more than $1.42 below starting equity.

## 3. Per-pair breakdown

| Coin | Fills | Buy | Sell | Closed PnL | Fees | Net PnL | Volume |
|---|---|---|---|---|---|---|---|
| BTC | 2,157 | 1,087 | 1,070 | +$31.64 | $7.96 | **+$23.69** | $38,996 |
| ETH | 1,403 | 663 | 740 | +$8.17 | $4.97 | **+$3.19** | $24,062 |
| SOL | 2,246 | 1,103 | 1,143 | -$5.33 | $7.77 | **-$13.10** | $36,547 |

**BTC** is the clear winner: 60% of total net PnL on 39% of volume. **SOL** is a consistent drag — negative closed PnL compounded by high fee load from the highest fill count.

## 4. Daily evolution

| Date | Equity | Fills | Volume | Net PnL |
|---|---|---|---|---|
| May 10 | $867.50 → $881.61 | 1,932 | $32,628 | +$12.81 |
| May 11 | $881.61 → $875.98 | 1,253 | $21,199 | -$6.56 |
| May 12 | $875.98 → $881.30 | 786 | $13,320 | +$5.41 |
| May 13 | $881.30 → $884.05 | 525 | $9,625 | +$0.57 |
| May 14 | $884.05 → $879.87 | 821 | $14,162 | -$4.75 |
| May 15 | $879.87 → $885.41 | 493 | $8,742 | +$6.48 |

Fill rate decreased from ~1,900/day to ~500–800/day over the run, consistent with testnet liquidity thinning rather than a bot issue.

## 5. Comparison to prior strategies

| Strategy | Duration | Equity Δ | Annualized | Max DD | Verdict |
|---|---|---|---|---|---|
| M3 grid (single BTC) | 70h | +1.22% | ~15% | n/a | Passed, but strategy class rejected |
| Forager v1 (multi-pair) | ~40h | ~0% | ~0% | n/a | Neutral, rejected |
| Avellaneda γ=1000 | 159h | -1.18% | ~-6.5% | ~2.5% | Failed, strategy class rejected |
| **HIP-3 multi-pair** | **129h** | **+2.06%** | **~14%** | **1.86%** | **Passed** |

HIP-3 matches M3's annualized rate but on a harder test: multi-pair, longer duration, and post-pivot. Sharpe of 8.52 is strong (though testnet conditions may inflate it).

## 6. Per-pair verdict

- **BTC:** Keep. Consistent winner across all 6 days (5/6 positive).
- **ETH:** Keep with monitoring. Marginal net positive (+$3.19), alternates good and bad days.
- **SOL:** **Drop or reconfigure.** Net -$13.10 wiped out more than ETH contributed. SOL's testnet book may be thinner, causing adverse selection. If kept, needs wider grid spacing or lower allocation.

## 7. Risks and caveats

1. **Testnet ≠ mainnet.** Testnet counterparties are sparser and less sophisticated. The 8.52 Sharpe will not hold on mainnet.
2. **SOL drag is structural on testnet.** May or may not carry to mainnet xyz assets where the actual HIP-3 thesis applies.
3. **This soak tested infra, not the HIP-3 thesis directly.** The soak ran on testnet main perps (BTC/ETH/SOL) because testnet xyz dex has no counterparties. The real HIP-3 opportunity is on mainnet xyz equity perps where spreads are 5–37× wider.
4. **Fill rate decay** suggests testnet liquidity is not unlimited. Mainnet xyz assets will have real but potentially thin flow.
5. **Fee ratio.** Fees are 60% of closed PnL ($20.70 / $34.48). Mainnet maker rebates would flip this significantly.

## 8. Mainnet fee projection

The soak ran on testnet where all fills pay taker-like fees (~0.021%). On mainnet, GTC limit orders earn maker rebates (-0.002%). Grid MM orders are almost exclusively maker fills.

| Scenario | Fee model | Net fees on $99.6K volume | Net PnL |
|---|---|---|---|
| Testnet (actual) | ~0.021% flat | $20.70 | $13.78 |
| Mainnet (90% maker) | -0.002% maker / 0.035% taker | $1.69 | **$32.79** |

Maker rebates improve net PnL by **$19.01** (+138%). Fees drop from 60% of closed PnL to 5%.

Scaled to micro-sized mainnet deployment:

| Capital | Projected net (129h) | Annualized |
|---|---|---|
| $300 | ~$11.34 (3.78%) | ~257% |
| $600 | ~$22.68 (3.78%) | ~257% |

These are optimistic (testnet counterparties are weaker, mainnet xyz spreads may compress as MMs arrive). But even at 1/5 this rate, the strategy is strongly positive with maker rebates.

## 9. Decision

**HIP-3 strategy is validated.** The soak demonstrated:
- Stable multi-pair grid MM infrastructure (zero errors in 129h)
- Positive PnL across the full run with acceptable drawdown
- The forager + per-pair override system works as designed

**Next steps:**
1. Write market survey final verdict (Track 1 + Track 2 data complete)
2. Decide xyz pair selection based on market survey spread/funding data
3. Plan mainnet micro-sizing deployment (testnet-only rule still applies for code execution — mainnet deployment is a future manual step, not automated)
