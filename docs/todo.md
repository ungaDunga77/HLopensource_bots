# TODO — Post-M3 Roadmap

Ranked by recommended order. Items are independent unless noted.

## Strategic pivot (2026-05-06)

**The 159h Avellaneda γ=1000 soak settled at −1.18% net.** Annualized linear extrapolation is now negative (~−6.5%/yr); the strategy is capacity-bound, skill-bound, and structurally vulnerable to sustained trends (6 SLs, all stale shorts in uptrends). Tuning γ further would be measuring noise in a hostile regime. **The next investment should be in a different strategy class, not in tuning this one.**

Three candidate classes ranked by effort × expected edge:
1. **Funding-rate harvester (todo §11 below).** Simplest of the three; HL funding APY readings during the soak ranged 100–300% on BTC. Different mechanics (no MM smarts; collect funding while delta-neutral). Realistic +20–50%/year if funding stays elevated; risk is funding flipping negative.
2. **HIP-3 equity perps grid MM (todo §12 below).** Reuse the existing osbot infrastructure (vol-adaptive grid + trend filter + skew + reconnect/retry), point it at NVDA/TSLA/AAPL/COIN/etc. perps. The "weaker MMs / lower-sophistication flow" thesis from lessons.md applies. Needs market-hours logic, weekend gap handling, universe verification (most testnet HIP-3 perps live mainnet-only).
3. **XEMM cross-exchange MM (todo §9, already on backlog).** Highest skill ceiling, two-venue infrastructure, real engineering cost. Defer until 1 or 2 has a baseline.

The current osbot — vol-adaptive grid + Avellaneda + trend filter — stays as the *defensive baseline*. Don't tune; reuse the infrastructure layer (M0–M3 work, WS reconnect, retry backoff, ShadowLogger, throttler, pre-trade checks) for whichever strategy class comes next. Current bot can keep running as a known-floor reference if desired, or stop and free the testnet account for the next strategy.

### 11. Funding-rate harvester (NEW, top priority)
**From:** osbot soak observation — HL funding APY 100–300% during 159h window, far above realized PnL of grid MM.
**Why:** Funding-rate harvesting is a textbook strategy for perps with positive sustained funding. Strategy: hold spot/equivalent or stay flat, short the perp when funding > threshold, collect 8h funding payments, hedge price risk by sizing the perp short against a delta-neutral basket or maintaining tight delta limits. No MM smarts needed; no edge in tight spreads. Edge is in *persistence* of funding skew.
**What:** New strategy module (~200 LOC) replacing GridStrategy in the runner. State machine: monitor funding (already on /health), enter short when funding_rate_hourly > entry threshold (e.g. 0.0001/hour = 0.876% APY) and stay until funding < exit threshold or stop-loss on price. Reuse existing TripleBarrier for SL/TP, but the SL is on accumulated price loss, not per-trade.
**Open questions:**
1. Whether to hedge with spot HYPE/BTC or stay net-short and accept directional risk (cleaner but riskier).
2. Position sizing: full account, or fractional? Funding harvest = leverage amplifier.
3. Funding payment timing: every 1h on HL; need to verify settlement and accounting.
4. Mainnet vs testnet funding pattern — does mainnet show similar persistent skew? Testnet APY may be artificially elevated.
**Size:** Medium — ~200 LOC + tests. Reuses existing connector, throttler, ShadowLogger, runner shell.
**Blocked by:** Decision on whether to keep the grid bot running in parallel or stop. Funding harvester would replace the active strategy in `secrets/roundtrip.yaml`.

### 12. HIP-3 equity perps grid MM (NEW)
**From:** lessons.md HIP-3 first-mover gap + 159h soak verdict that grid mechanics are sound but BTC market is too efficient.
**Why:** Same vol-adaptive grid + Avellaneda + trend filter mechanics, but in markets where the bot competes against weaker MMs and slower flow. Stocks have natural mean-reversion windows (open-close) and predictable vol regimes (intraday vol > overnight vol). The strategy that loses on BTC (where every MM is sophisticated) may win on TSLA-perp.
**What:**
1. Universe verification: query mainnet `meta_and_asset_ctxs` for HIP-3 perps available on testnet vs mainnet only. Likely subset.
2. Market-hours logic: pause grid when underlying equity market is closed (don't quote into a void).
3. Weekend gap handling: flatten Friday close, restart Monday open.
4. Per-asset σ calibration — equity perps may have very different vol characteristics than BTC.
**Size:** Medium — ~150 LOC building on existing forager v1 multi-pair infrastructure.
**Blocked by:** Funding harvester baseline (decide if HIP-3 grid PnL beats funding harvest before committing engineering).

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

### 9. XEMM Pacifica-HL Rust spinoff
**From:** XEMM evaluation  
**Why:** Different problem (cross-exchange MM hedging Pacifica positions on HL). High-quality Rust, blocker is one-line testnet flag fix.  
**Recommendation:** Separate project, only if/when we want a Rust HL bot. Not part of osbot roadmap.

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
