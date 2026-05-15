# Market Survey Verdict — 8-Day Data Collection

**Decided 2026-05-15.** Eight days of mainnet read-only data (631K book snapshots, 2,105 funding rows, 1,337 volume/OI rows). Track 1 (HIP-3) passes decisively. Track 2 (XEMM) fails on both criteria. HIP-3 is the confirmed path forward.

## 1. Collection overview

- **Period:** 2026-05-07 12:28 → 2026-05-15 12:16 UTC (7d 23h)
- **DB:** `evaluations/_market_survey/run-20260507-1227.db`
- **Assets monitored:**
  - HL main perps: BTC, ETH (control + XEMM Track 2)
  - HL xyz equity perps: NVDA, TSLA, AAPL, COIN, MSTR (HIP-3 Track 1)
  - Cross-venue funding: Binance + Bybit for BTC, ETH

## 2. Track 1 — HIP-3 thesis validation

**Decision rule** (from `strategy-pivot-plan.md`): HIP-3 is a go if spreads ≥ 3× BTC.

| Asset | Avg Spread (bps) | vs BTC | Depth ±5bps | Depth ±25bps | Verdict |
|---|---|---|---|---|---|
| BTC (control) | 0.13 | 1.0× | $10.2M | $10.2M | — |
| ETH | 0.44 | 3.4× | $11.8M | $26.5M | — |
| xyz:TSLA | 0.68 | **5.3×** | $128K | $163K | **PASS** |
| xyz:NVDA | 1.54 | **11.8×** | $169K | $357K | **PASS** |
| xyz:MSTR | 3.52 | **27.1×** | $45K | $189K | **PASS** |
| xyz:AAPL | 3.91 | **30.1×** | $86K | $282K | **PASS** |
| xyz:COIN | 4.74 | **36.5×** | $33K | $229K | **PASS** |

All five HIP-3 assets pass with margin (5.3× to 36.5× BTC spreads). The "weaker MMs, wider quotes" thesis from the catalog is confirmed by data.

### Depth vs spread tradeoff

TSLA and NVDA have tighter spreads but deeper books. COIN and MSTR have widest spreads but thinnest books. For grid MM sizing:
- **NVDA** is the sweet spot: 11.8× spread advantage with $169K at ±5bps — enough depth for micro-sizing without getting adversely selected.
- **COIN** has the widest spread but only $33K at ±5bps — thin enough that our orders would be a significant fraction of the book, increasing information leakage.

### HIP-3 funding rates (HL-only, no cross-venue comparison possible)

| Asset | Avg APY | Persistence (same-sign) | % Positive |
|---|---|---|---|
| xyz:MSTR | 19.77% | 91.6% | 93% |
| xyz:COIN | 15.46% | 88.4% | 92% |
| xyz:TSLA | 13.77% | 95.8% | 96% |
| xyz:NVDA | 13.02% | 94.7% | 95% |
| xyz:AAPL | 5.66% | 90.0% | 90% |

Funding is consistently positive and persistent across all xyz assets. This means long bias costs funding; short bias earns it. A grid MM that stays near-neutral gets funding drag proportional to any directional lean.

### Volume and open interest

| Asset | 24h Volume | Open Interest | OI/Vol Ratio |
|---|---|---|---|
| xyz:NVDA | $115M | $104M | 0.90 |
| xyz:TSLA | $34M | $39M | 1.14 |
| xyz:COIN | $33M | $8.4M | 0.26 |
| xyz:MSTR | $12.8M | $16.8M | 1.32 |
| xyz:AAPL | $8.7M | $14.1M | 1.62 |

NVDA dominates with $115M/day volume — ample flow for micro-sized grid MM. AAPL has the lowest volume but the highest OI/Vol ratio, suggesting position-holders rather than active traders.

## 3. Track 2 — XEMM thesis validation

**Decision rule** (from `strategy-pivot-plan.md`): XEMM is a go if mean HL-CEX spread > 8% APY AND persistence > 60%.

| Pair | HL APY | Best CEX | CEX APY | Spread | Spread test | Persistence test |
|---|---|---|---|---|---|---|
| BTC | 4.47% | Bybit | 2.04% | +2.43% | **FAIL** (need >8%) | **FAIL** (0%) |
| ETH | 9.66% | Bybit | 4.10% | +5.56% | **FAIL** (need >8%) | **FAIL** (0%) |

**XEMM is dead.** Neither asset reaches the 8% APY spread threshold. Persistence is 0% because HL funding never exceeded the corresponding CEX rate on an hourly basis during the full 8-day window (funding rates are reported at the same time and the HL premium is structural, not episodic — it's a level shift, not a tradeable dislocation).

This confirms the earlier borderline assessment (day 5 memo) and closes the XEMM path definitively.

## 4. Pair selection for HIP-3 deployment

Ranking by composite score (spread advantage × depth × volume):

1. **NVDA** — Best overall: 11.8× spread, $169K depth, $115M volume. Top pick.
2. **TSLA** — 5.3× spread, $128K depth, $34M volume. Second pick (tightest spread but most liquid after NVDA).
3. **MSTR** — 27.1× spread, $45K depth, $12.8M volume. Wide spreads but thin book. Third pick if sizing stays micro.
4. **COIN** — 36.5× spread but only $33K depth at ±5bps. Risk of being a large fraction of the book. Monitor only.
5. **AAPL** — 30.1× spread, $86K depth, but only $8.7M volume. Low flow means fewer fills. Monitor only.

**Recommended starting set: NVDA + TSLA + MSTR** — covers the range from tight-but-deep to wide-but-thin.

## 5. Combined verdict

| Track | Thesis | Data says | Decision |
|---|---|---|---|
| Track 1 — HIP-3 spreads | xyz perps have ≥3× BTC spreads | 5.3× to 36.5× — all pass | **GO** |
| Track 2 — XEMM funding arb | HL-CEX spread >8% APY, 60% persistence | 2.4–5.6% spread, 0% persistence | **NO GO** |

**HIP-3 is the sole remaining strategy candidate, supported by both the 129h soak (infra validation) and 8-day market survey (thesis validation).** XEMM is permanently deferred — the funding differential exists but is too small and too structural (not episodic) to trade.
