# TODO — Post-M3 Roadmap

Ranked by recommended order. Items are independent unless noted.

## Next up (small, in-tree)

### 1. Funding APY tracking
**From:** Nova funding hub  
**Why:** We have zero visibility into when funding is bleeding the strategy. Earlier 30h trials showed ~$0.12-0.16 funding cost. If funding drag exceeds grid PnL during slow regimes, we want to know.  
**What:** Per-tick (or every-N-ticks) fetch HL funding rate for the configured pair. Snapshot to a new `funding_rate` table in `data/shadow.sqlite`. Optionally surface via `/health` (current funding rate). Read-only, no strategy change.  
**Size:** ~30 LOC + 1 unit test.

### 2. WEL bump 0.20 → 0.30
**From:** post-run analysis  
**Why:** Capital deployment is the cleanest PnL multiplier. Current $920 wallet has ~$184 exposure (WEL 0.20 × 7 levels). Throttler + risk precheck + TripleBarrier all have headroom.  
**What:** Edit `secrets/roundtrip.yaml` only. Default in `osbot/config/base.py` already 0.20; consider bumping to 0.30 there too. Restart bot.  
**Size:** Config-only.  
**Risk:** Worst-case single-position SL loss scales linearly: 0.30 × $920 / 7 × 0.015 = ~$0.59. Acceptable.

## Next session if time / energy (medium)

### 3. Forager (multi-pair selection)
**From:** Passivbot  
**Why:** Highest single-change PnL multiplier. Trading 5 pairs in parallel multiplies fill opportunities 5x.  
**What:** New `strategy/selection.py` (currently a stub) that ranks pairs by (vol × spread) every M minutes and picks top-N. Per-pair `MarketState`, `GridStrategy`, and `ExitManager`. Per-bot cloid prefix for fill attribution (item 4 below comes free).  
**Size:** Substantial — ~300-500 LOC, real architecture work, full plan-first session.  
**Note:** Synthesis §5.7 deliberately excluded forager from v0 to nail single-pair first. Single-pair is now nailed. This is the natural v1.

### 4. Multi-bot cloid prefix orchestration
**From:** Passivbot  
**Why:** When >1 strategy runs concurrently, fill attribution requires per-strategy cloid prefixes. Currently `OrderTag.strategy_id=0xCAFE` is hardcoded.  
**What:** Per-`GridStrategy` instance configurable strategy_id. Comes free with forager (item 3).  
**Size:** ~10 LOC plus per-pair config wiring.

### 5. TrendRegularityFilter
**From:** freqtrade-titouan  
**Why:** Replaces our slope-bps gate with OLS + R² regime classifier. R² says "is this trend a *line* or just noise that *looks* trendy?" — fewer false-positive trend pauses during choppy markets. Now that dual-EMA slope is in, marginal gain is smaller but still real.  
**What:** New `strategy/regime.py` module. Window of N samples → OLS fit → return (slope_bps_per_hour, r2). Strategy uses both: pause only if `|slope| > threshold AND r2 > 0.6`.  
**Size:** ~80 LOC + tests.

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
