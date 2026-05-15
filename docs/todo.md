# TODO — Post-M3 Roadmap

Ranked by recommended order. Items are independent unless noted.

## Strategic pivot — resolved (2026-05-15)

**HIP-3 equity perps grid MM is the confirmed path forward.** Validated by:
- 129h testnet soak: +2.06%, Sharpe 8.52, max DD 1.86%, zero errors (see `docs/hip3-soak-verdict.md`)
- 8-day market survey: all 5 xyz assets pass spread rule at 5.3–36.5× BTC (see `docs/market-survey-verdict.md`)
- XEMM definitively rejected: HL-CEX funding spread 2.4–5.6% APY (need >8%), 0% persistence
- Funding-rate harvester deprioritized: funding differential too small for standalone strategy

**Recommended xyz pair set:** NVDA (best depth/spread), TSLA (most liquid), MSTR (widest spread).

**Next phase:** mainnet deployment planning. Testnet soak validated infra; market survey validated thesis. Remaining work is pair-specific config tuning and mainnet operational readiness.

### 11. HIP-3 mainnet deployment planning (NEXT)
**From:** Soak verdict + market survey verdict (2026-05-15)
**Why:** Infra validated (129h, +2.06%), thesis validated (5.3–36.5× spreads). Next step is operational readiness for mainnet xyz equity perps.
**What:**
1. **Pair-specific config:** Per-pair overrides for NVDA/TSLA/MSTR — grid spacing calibrated to each asset's spread/depth profile (NVDA tighter, MSTR wider).
2. **Market-hours logic:** Pause grid when underlying equity market is closed. xyz perps trade 24/7 but spreads blow out after-hours — quoting into that is adverse selection.
3. **Weekend gap handling:** Flatten Friday close, restart Monday open. Or: keep quoting with wider spacing if weekend volume justifies it.
4. **Mainnet sizing:** Micro-size initial deployment. Suggested: $100–200 per pair, 3× leverage, total $300–600 at risk.
5. **Maker rebate accounting:** Mainnet has maker rebates (testnet doesn't). Recalculate expected net PnL with rebates — fees were 60% of closed PnL in the soak, rebates would flip this.
6. **Operational runbook:** Health checks, alerting, position limits, kill-switch procedure.
**Size:** Config + ~100 LOC for market-hours module.
**Blocked by:** Manual mainnet deployment decision (not automated — testnet-only rule for code execution).

### 1. Enable + observe forager v1 on testnet
**From:** v1 shipped 2026-04-26 (`9d050b1`), disabled by default  
**Why:** v1 is committed and tested (117/117 green) but never run live. Need ≥24h steady-state observation before queuing v2.  
**What:** Add `forager: { enabled: true, ... }` block to `secrets/roundtrip.yaml`, restart bot. Watch /health for: candidate validation passes, ~16-min warm-up completes, top_n=1 pair gets selected, first rotation fires at +30min. Monitor for: rejected orders on non-BTC pairs (price-rounder bug), draining-loop bugs, position carry-over surprises.  
**Risk:** Restart cancels current orders. Open position (if any) carries across. Bot is idle ~16 min during selector warm-up.  
**Success criteria:** 24h continuous run, ≥1 rotation observed, no rejected orders, no unhandled exceptions.

### 3b. Forager v2 — alt-asset forager (stocks/commodities)
**From:** v1 design discussion + custom-bot-design-notes.md:252  
**Why:** HL has `PAXG` (gold) and HIP-3 equity perps (`SPX`, mainnet adds NVDA/TSLA/AAPL/MSFT/GOOGL/COIN/MSTR/etc.). Lessons flag HIP-3 as a confirmed gap with first-mover advantage — "lower-sophistication flow and weaker MMs". DO NOT MIX with crypto in v1: stocks have weekend gaps, market hours, and different vol regimes — would either always-pick-crypto or get stuck Fri-close into Mon-gap.  
**What:** Second forager *instance* alongside v1 with its own params: market-hours awareness (pause grid when market closed), gap-risk-aware position sizing, separate candidate universe `[PAXG, SPX, ...]`. Per-instance cloid prefix (item 4 dependency) attributes fills cleanly across both. Most testnet HIP-3 perps live mainnet-only — universe will need verification.  
**Refinements distilled from v1 disabled run (2026-04-26 → 2026-04-29) vs Passivbot Trial #2 (lessons.md:205):** v1 underperformed; comparison shows three deltas worth correcting before re-enabling any forager:
  1. v1 used flat `min_volume_usd_24h` threshold; Passivbot used a 365-span volume EMA (smoothed, gives ranker a continuous signal not a hard cutoff). Switch to volume EMA.
  2. v1 used `rotate_every_s=1800` (30min); Passivbot used 5min (300s). Faster cadence reaches the right pair sooner; Passivbot pairs this with 60s entry-order retire so old orders don't linger after rotation. Adopt 300s.
  3. v1 `log_range_window_min=16` matches Passivbot's `filter_log_range_ema_span=16` — keep as-is.
**Size:** Medium — ~150 LOC building on v1 infrastructure.  
**Blocked by:** Item 10 (Avellaneda skew) shipping and demonstrating measurable PnL improvement on single-pair BTC. Forager interactions with skew need its baseline first.

### 5. TrendRegularityFilter
**From:** freqtrade-titouan  
**Why:** Replaces our slope-bps gate with OLS + R² regime classifier. R² says "is this trend a *line* or just noise that *looks* trendy?" — fewer false-positive trend pauses during choppy markets. Now that dual-EMA slope is in, marginal gain is smaller but still real.  
**What:** New `strategy/regime.py` module. Window of N samples → OLS fit → return (slope_bps_per_hour, r2). Strategy uses both: pause only if `|slope| > threshold AND r2 > 0.6`.  
**Size:** ~80 LOC + tests.

### 10. Avellaneda-Stoikov inventory skew — **SHIPPED + 111h soak complete**
**Status (2026-05-04):** γ=1000 default shipped at `568bee0`. 111h live soak complete: net +0.12% in a mostly-trending regime. Skew engaged correctly throughout (max −18.84bps observed, no instability). Annualized linear extrapolation +9.5%/yr (optimistic) → +3-5%/yr after mainnet haircuts. **Decision: keep γ=1000, do not A/B vs 500/2000 until a calm-market window can be isolated.** See lessons.md "Avellaneda γ=1000 Soak" section.

**From:** `evaluations/avellaneda-mm-freqtrade/evaluation.md` (B3, lines 84, 94) — "the *entire point* of A-S inventory management" is disabled in the OSS bot via hardcoded `q_inventory_exposure = 0.0` at avellaneda.py lines 473/494/515. Eval recommends: "When we implement A-S ourselves, actually compute `q`: normalized inventory (position notional / capital, signed), and feed it to `r = s - q·γ·σ²·T`. This is 3 lines to uncomment."
**Why:** Forager v1 disabled run (2026-04-26 → 2026-04-29) and the BTC-only baseline both showed the same loss mechanism: persistent trends build asymmetric inventory, and the slope-bps gate is *reactive* (fires only after inventory is on the books). A-S inventory skew is *inventory-aware* — when q grows positive (long), it shifts the entire grid mid downward so sells become more aggressive (closer to mid) and buys less aggressive (further from mid), naturally rebalancing toward flat. Math is textbook; only the OSS implementation we tested left it disabled.
**What:**
1. New config: `strategy.inventory_skew_gamma: float = 0.0` (default disables) and `strategy.inventory_skew_horizon_s: float = 300.0` (T parameter, default 5min).
2. `runner._do_pair_tick` extracts signed `szi` from `user_state["assetPositions"]` and passes to `grid.plan(...)`.
3. `GridStrategy.plan()` computes `q = (szi · mid) / max(balance, 1)`, `σ_frac = sigma_bps / 10_000`, `T_min = horizon_s / 60`, `skew_frac = q · γ · σ_frac² · T_min`, then builds the grid around `reservation_price = mid · (1 - skew_frac)` instead of `mid`.
4. Log skew_frac alongside sigma/slope each replan for visibility.
5. Unit tests: γ=0 → symmetric grid regardless of position; γ>0 + long → reservation < mid; γ>0 + short → reservation > mid.
**Size:** ~30 LOC + 3 tests.
**Tuning:** γ=0 ships disabled. Recommended starting value γ=1000 (gives ~0.5bps skew per 10% inventory at σ=3bps, T=5min — small enough to A/B safely).

### 6. DSL trailing stop
**From:** senpi-skills  
**Why:** TripleBarrier currently has consecutive-breach gating on a *fixed* SL price. A trailing stop that follows the high-water-mark on the favorable side lets winners run while protecting profits.  
**What:** Augment `PositionExitState` with `peak_favorable_price`. New trailing logic in `TripleBarrier.evaluate()`.  
**Size:** ~50 LOC + tests.  
**Note:** Low priority while `tp_pct=15bps` exits faster than a trail could chase. Revisit if we widen TP.

## Bigger / structural (your call)

### 7. DCA / unstuck
**From:** Passivbot  
**Why:** When a position drifts toward SL, average down with a sized DCA order rather than liquidating. Passivbot's killer feature.  
**Status:** Synthesis §5.7 explicitly excluded — Passivbot's Trial #3 showed this is non-trivial on HL's margin model. Real risk of catastrophic loss if buggy.  
**Recommendation:** Defer until we have a concrete reason to need it.

### 8. WebAuthn passkey + PRF-derived agent-wallet lockbox
**From:** hyperopen  
**Why:** Production-grade key handling. Never store the main wallet key; HL agent wallet approved once, encrypted with passkey-PRF-derived key, unlocked per-session via passkey touch.  
**Status:** We use `eth_keyfile` + password-from-env. Fine for research project.  
**Recommendation:** Defer until user-facing deployment.

### 9. XEMM Pacifica-HL Rust spinoff — **CLOSED**
**From:** XEMM evaluation
**Closed (2026-05-15):** Market survey Track 2 showed HL-CEX funding spread is 2.4–5.6% APY (threshold was 8%) with 0% tradeable persistence. The differential is structural (level shift), not episodic (tradeable dislocation). See `docs/market-survey-verdict.md`.

## Done (for reference)

- M0: scaffold (2026-04-22)
- M1: read-only connector (2026-04-23)
- M2: write-path + 10-step startup + round-trip (2026-04-23)
- M3: strategy loop + grid + TripleBarrier (2026-04-23)
- M3 acceptance: 70h unbounded run (2026-04-23 → 2026-04-26)
- Trend-pause replan thrash fix (2026-04-26)
- Exponential backoff on retryable errors (2026-04-26)
- WS allMids+userFills with REST fallback (2026-04-26)
- WS auto-reconnect watchdog (2026-04-26)
- Strategy parameter tweaks (2026-04-26)
- 1-min sigma + dual-EMA slope (2026-04-26)
- Funding APY tracking (`9d580c2`, 2026-04-26)
- WEL 0.20 → 0.30 (`dba3543`, 2026-04-26)
- Per-pair cloid prefix (shipped with forager v1 C3, was original todo.md §4)
- Forager v1 — crypto-major rotation (`0250270` C1 + `d34f9fd` C2 + `9d050b1` C3, 2026-04-26)
- Avellaneda-Stoikov inventory skew (`568bee0`, 2026-04-29) — γ=1000 default, soak complete 2026-05-04
- Avellaneda γ=1000 111h live soak (2026-04-29 → 2026-05-04): net +0.12%, behaviors verified, default kept
- HIP-3 multi-pair grid MM infrastructure, Phases 1-4 (`978edc4`, 2026-05-10)
- HIP-3 129h testnet soak (2026-05-10 → 2026-05-15): +2.06%, Sharpe 8.52, max DD 1.86%, zero errors
- 8-day market survey (2026-05-07 → 2026-05-15): 631K book snapshots, Track 1 PASS (5.3–36.5× spreads), Track 2 FAIL (XEMM dead)
- XEMM permanently deferred: funding differential too small and structural, not episodic
