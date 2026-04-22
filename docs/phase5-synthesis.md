# Phase 5 — Synthesis

Final rankings, compiled lessons, build-vs-fork decision, and architecture plan for a custom Hyperliquid bot, distilled from evaluation of 11 open-source bots + 4 testnet trials.

---

## 1. Final rankings

Scores are weighted per the rubric: Security 40%, Functionality 30%, Engineering 20%, HL Integration 10%. All evaluations live under `evaluations/<bot>/evaluation.md`.

| Rank | Bot | Score | Testnet trial? | One-line verdict |
|---:|---|---:|:-:|---|
| 1 | **hypersdk (Rust)** | **4.34** | ❌ (SDK) | Best-in-class Rust SDK. Structured error enum with `is_retryable()` classifiers + WS resilience baked in + `PriceTick::round_by_side`. Sets the reference bar for connector quality. |
| 2 | **Hummingbot** | 4.18 | ✅ (V1 + V2) | Best full bot overall: native HL integration, encrypted keys, production polish. V2 has a reduce-only position-sync bug; V1 and most paths sound. |
| 3 | **go-hyperliquid** | 3.95 | ❌ (SDK) | Most mature Go SDK. `signing.go`'s msgpack walker documents Python-SDK-compat wire edges. WS reconnect design strictly better than Python SDK. |
| 4 | **Passivbot** | 3.83 | ✅ (3 trials) | Best strategy code (forager, grid, DCA, unstuck). Weak HL integration (no testnet upstream). Multi-position has margin-accounting defect. |
| 5 | **freqtrade-titouan** | 3.75 | ❌ | Freqtrade fork with genuinely novel features: **liquidation detection** via polling, **TrendRegularityFilter** (OLS+R² regime classifier), custom hyperopt loss + 6 Optuna samplers. Claims validated — not marketing. `dry_run: false` in default config is the blocker. |
| 6 | **HL Python SDK** | 3.73 | (reference) | Not a bot — authoritative reference for wire format, signing, typed dicts. Still the baseline for Python. |
| 7 | **Chainstack Grid Bot** | 3.60 | ✅ (25h) | Clean architecture, survived a 30s HL 502. Submissions-as-fills bug, no trend filter, grid width guessed not measured. |
| 8 | **XEMM Pacifica-HL (Rust)** | 3.53 | ❌ | Highest-quality Rust *bot* in the study. 5-layer fill-detection pipeline + hot-WS trading with REST fallback + post-hedge verification. Hardcoded `false` testnet at every construction site is the one blocker. |
| 9 | Copy Trading Bot | 2.87 | ❌ | TypeScript/Zod config is excellent. Trading logic is AI-generated and incoherent. |
| 10 | OctoBot MM | 2.86 | ❌ | 120-LOC distribution wrapper. Advanced MM features paywalled, HL treated as generic CEX. |
| 11 | Rust Bot (0xNoSystem) | 2.84 | ❌ | Agent-wallet approval pattern is best-in-class. Rest underdeveloped. |
| 11 | Copy Trader | 2.84 | ❌ | Telegram ops controls done well. Custom EIP-712 signing silently broken. |
| 13 | Hyper-Alpha-Arena | 2.81 | ❌ | Deep HL integration (D=4.3), weak LLM harness: regex-fallback JSON parsing can fabricate decisions; single squashed "Admin" commit on a 961-star repo. |
| 14 | Nova funding hub | 2.80 | ❌ | Data-hub only (no execution). Uniform Exchange ABC + funding APY normalization portable for future funding-arb layer. |
| 15 | Drift Arbitrage | 2.70 | ❌ | Cleanest Python config architecture. Arb logic off-topic for HL. |
| 16 | Avellaneda MM Freqtrade | 2.59 | ❌ | A-S parameter-estimation code is publishable quality (GARCH(1,1) + MLE intensity). **Live strategy has `q_inventory_exposure = 0.0` hardcoded** — the skew that is the entire point of A-S is disabled. Harvest the research code, ignore the live bot. |
| 17 | Grid Bot (SrDebiasi) | 2.47 | ❌ | Unauthenticated API storing private keys as `VARCHAR(255)`. Do not touch. |
| 18 | HyperLiquidAlgoBot | 2.39 | ❌ | Renamed dYdX scalper, inconsistent testnet flags, RiskManager defined but never called on live path. |
| 19 | Market Maker (Novus) | 1.47 | ❌ | `panic!()` in exchange data handlers, `f64::from_bits(1)` sentinels, unauthenticated dashboard. |
| — | **Phase 5b honorable mentions (2026-04-22)** | | | |
| 20 | **hyperopen (ClojureScript)** | 3.94 | ❌ | Reference-quality engineering (562 test files / 186 ADRs / per-ns LOC caps). **Not a bot** — it's HL's best OSS trading UI with full vault analytics. AGPL blocks direct reuse but patterns transfer. |
| 21 | senpi-skills | 3.79 | ❌ | 52+ scanner-strategy "animals" trading live HL through Senpi's **closed** MCP/Hyperfeed runtime. Not OSS-runnable. Harvest the DSL trailing-stop + scanner/executor separation + fee-optimized-limit wrapper. |
| 22 | vnpy-hyperliquid | 3.00 | ❌ | 1-day-old real-but-untested HL gateway for VeighNa. Dual-ID cloid tracking + multi-perp-dex support are keepers. Mainnet hardcoded, no tests. |
| 23 | memlabs-hl-bot | 2.71 | ❌ | Clean streaming-feature classes (`Window`, `LogReturn`, `Lags`) + textbook WS reconnect, but every-bar churn loop + zero risk controls. Single-commit code-dump. |
| 24 | redm3-lstm | 1.06 | ❌ | LSTM long-gate computed *at module import* from stale 2023 CSV with hardcoded `C:/Users/...` paths. Anti-pattern gold. |
| 25 | xlev-hl-bot | 0.23 | ❌ | **Wallet-drainer repo** — 79 stars, zero source, install = `powershell iwr .../main.ps1 \| iex` + `PRIVATE_KEY=...` in `.env`. Added to internal deny-list. |

**Skipped from Tier 3** with documented reason (duplicate of already-reviewed pattern, hype wrapper, or non-trading): AI Trading Bot, Hypercopy-xyz, AI Crypto Bot, Bybit-HL Arb, Rust Bot (RUBE40), Rust Bot (0xTan), Telegram Info Bot. (LSTM Bot moved from skipped → evaluated in 5b as redm3-lstm.)

**New patterns from the Phase 5b honorable-mentions batch (added 2026-04-22):**

- **WebAuthn passkey + PRF-derived agent-wallet lockbox** — hyperopen. Never stores the main wallet key; HL agent wallet is approved once on HL, encrypted with a passkey-PRF-derived key, unlocked per-session via passkey touch. Python analogue: `cryptography.fernet` + OS keyring. Strictly better than `PRIVATE_KEY=...` in `.env` — adopt for any user-facing deployment.
- **EIP-712 action-surface coverage checklist** — hyperopen's `hl_signing.cljs` enumerates every HL action we can sign. Use as a coverage checklist when building our signing layer; any action not in that list is either unsupported or recent.
- **Dual-ID (cloid↔oid) order tracking with three mapping tables + `cancelByCloid`** — vnpy-hyperliquid. Maintain `local_order_id ↔ cloid ↔ oid` dicts; cancel by cloid to avoid the oid-race when HL's oid hasn't propagated back yet. Our `tags.py` module should expose both identifiers.
- **Fill-dedup via bounded `tid` set across multiple WS channels** — vnpy-hyperliquid merges `userEvents` and `userFills` channels (same fills arrive via both with different field shapes), dedups via a trade-id set. Closely related to XEMM's 5-layer design but simpler for a single-venue bot.
- **DSL two-phase trailing stop with `consecutiveBreachesRequired` noise suppression** — senpi-skills. Trailing stop requires N consecutive price breaches before firing, not just one tick crossing. Eliminates whipsaw exits on thin books. Port to our exits module.
- **Scanner/executor separation as a structural rule** — senpi-skills: "scanners enter, DSL exits, never both." Forces entry and exit logic into separate modules that can't reach into each other's state. Good structural rule for our `strategy/` layout — `selection.py` picks, `exits.py` manages position, they communicate only via a decision-output JSON schema.
- **Uniform decision-output JSON schema → one executor, many strategies** — senpi-skills. Every strategy emits `{action, size, price, reason, strategy_id}`; one executor consumes that schema regardless of which scanner produced it. Complements HAA's `AIDecisionLog`: HAA is how to *log* decisions, senpi-skills is how to *structure* N strategies behind one executor.
- **`FEE_OPTIMIZED_LIMIT` maker-first-then-taker wrapper** — senpi-skills. Place limit at maker side, wait N seconds, cancel + repost aggressively, eventually cross if still unfilled. Encodes the maker-rebate vs fill-certainty tradeoff as a single order type. Candidate for our connector's submit API.
- **Per-strategy cooldown + daily entry cap as state files** — senpi-skills. Persisted per-strategy so restarts don't re-open channels immediately. Cheap, shift-left safety bound.
- **Streaming feature classes (`Window`, `LogReturn`, `Lags`)** — memlabs-hl-bot. Minimal reusable building blocks for incremental feature computation over a streaming tick/bar feed. Lift the three classes (~100 LOC total) into our `state/features.py`.
- **Interval-aligned scheduler** — memlabs-hl-bot's `trade_periodically`. Sleeps to the next exact multiple of the bar interval, not `now + interval`. Avoids drift across days. Adopt for any periodic decision loop.

**New anti-patterns from the 5b batch:**

- **Inference at module import** — redm3-lstm computes its LSTM gate once on `import`, from a stale 2023 CSV with hardcoded `C:/Users/macmw/...` paths, then reuses the boolean forever in the 900s loop. Our rule: all model inference happens at decision time, reading the current market; never at import.
- **Training/live data distribution mismatch** — redm3-lstm trained on stale historical data, deployed against live. No validation that live distribution matches training. Any ML path must have a live-vs-training drift monitor as a pre-gate.
- **Regressor collapsed to boolean via `np.sign(y_hat)`** — redm3-lstm. Discards the entire magnitude/confidence signal. If we use regressors, the size should scale with predicted return, not jump to full-size on the first positive signal.
- **Mismatched units in risk thresholds** — redm3-lstm compared `pnl_perc * pos_size` against `target=0.2` and `-max_loss=0.01`. Dimensional error — a 0.2 target in "position-currency units" is not a 20% target. Enforce unit tags on all risk constants, reject at startup if dimensions don't match.
- **Identical bid/ask from L2 level 0** — redm3-lstm assigned `bid = ask = l2[0][0]['px']`, collapsing the spread. Any L2-derived quote needs paired `[bids[0], asks[0]]` access.
- **High-stars-near-zero-source repos** — xlev-hl-bot is the canonical wallet-drainer pattern: SEO-padded README is >80% of total LOC, install is a remote-fetch-and-execute, and the "bot" is an opaque release binary. **Scouting heuristic added to the secret-scan front-door**: any repo where README ≫ source (files-to-README line ratio) and there's no actual source directory is presumptively hostile. Do not clone for eval; document from metadata only.

---

## 2. Testnet trial results summary

Across 4 testnet trials, one result dominates: **Passivbot's Trial #2 (single-position forager, long-only) produced the highest per-hour return (+$0.116/h) with zero defects triggered**.

| Trial | Bot | Config | Duration | Net PnL | Per-hour | Notes |
|---|---|---|---:|---:|---:|---|
| Chainstack | Chainstack Grid | Static grid, BTC | 25h | — | — | Bot's self-reported PnL fictional; shadow collector gave real numbers. Submission≠fill bug confirmed. |
| Hummingbot V2 | Hummingbot | `pmm_simple`, BTC | 5.5h | +$3.06 incl. MTM | +$0.556/h | V2 reduce-only position-sync bug documented; executors poisoned after ~3h. Stopped early. |
| Passivbot #1 | Passivbot | Single BTC, long | 30.5h | +$0.06 | +$0.002/h | 502-outage-kills-bot defect documented (segment 1 crashed at 5.5h). Small sample. |
| **Passivbot #2** | **Passivbot** | **Forager 1L, long** | **20.75h** | **+$2.40** | **+$0.116/h** | **No defects. Best config discovered.** |
| Passivbot #3 | Passivbot | Forager 3L/1S | 15.9h | +$0.96 | +$0.060/h | Surfaced insufficient-margin restart loop defect. Multi-position underperforms single. |

**Caveats (same for all):**
- Testnet liquidity ≠ mainnet; favorable ETH volatility during Passivbot trials may not repeat.
- Weekend vs weekday crypto volatility differ; results span both.
- $200 account is small enough that HL's $10 min notional constrains sizing on multi-position configs.

---

## 3. Lessons compilation (pointer to detailed docs)

The full lesson bank lives in two places:

- **[docs/lessons.md](lessons.md)** — trial-by-trial chronological findings, one section per bot / trial. Includes reduce-only race, insufficient-margin loop, V2 position-sync bug, 502-kills-bot, grid-width-vs-volatility mismatch, etc.
- **[docs/custom-bot-design-notes.md](custom-bot-design-notes.md)** — structured by concern (key management, state, strategy, risk, observability, testing). Every entry attributed to the bot(s) where it was seen. 12 sections.

**New patterns from the Phase 5 expanded-search batch (added 2026-04-21):**

- **Structured error enum with `is_retryable()` / `is_network_error()` / `is_api_error()` classifiers** — hypersdk. Exactly the pattern the Passivbot Trial #3 failure demanded. Rust `thiserror` or Python enum-based equivalent. Lift verbatim.
- **WebSocket resilience spec** — hypersdk + go-hyperliquid converge on the same design: 50s ping + 90s read deadline (invariant: read timeout > ping interval), exp-backoff reconnect capped at 60s, `HashSet<Subscription>` auto-replayed, missed-pong liveness (2× interval) — reconnect not on single miss. Adopt this as the spec for our WS layer regardless of language.
- **5-layer fill detection** — XEMM. `(WS orders, WS positions, REST orders poll, REST positions poll, safety monitor)` funneled through bounded mpsc into single `HedgeService` consumer, with `FillDedup` (bounded FIFO, key = `OrderId | Cloid`) + `FillAggregator` (terminal / emergency-notional / idle-flush emission). Over-engineered for v0 but the *layered* approach is the right default. Our single-WS design is fragile.
- **Hot WS trading connection with REST fallback** — XEMM. Sign once, send over warm WS, retry with transport switch (250ms, 750ms) + refreshed price. Distinguishes transport errors from HL terminal statuses (`OrderStatus::Error/Resting`). Halves tail latency on order submission.
- **`PriceTick::round_by_side(side, price, conservative)`** — hypersdk. Directional tick rounding with explicit maker/taker semantics. Avoids "rounded toward cross" bugs on tight ticks. Adopt as a utility.
- **Msgpack wire-format edge documentation** — go-hyperliquid's `signing.go` has a `walkMsgpackValue` that rewrites `str16`→`str8` for strings <256 bytes to match Python msgpack output. Plus `hashStructLenient` that filters EIP-712 message fields to match Python `eth_account` tolerance. If we ever hand-craft signatures, read this file; the Python SDK's dynamism hides these edges.
- **Pluggable signer interfaces** — go-hyperliquid's `L1ActionSigner` / `UserSignedActionSigner` / `AgentSigner`. Cleanest HSM/KMS-capable path. Raw private-key bytes never touch the SDK. Adopt as the abstraction for our signing layer.
- **HL liquidation-price closed-form formula** — freqtrade-titouan. Validated against 196 real positions (avg 0.00029% deviation). Directly embed in risk module for precheck before entry.
- **Liquidation-fill polling via `fetch_my_trades` for `liquidationMarkPx`** — freqtrade-titouan. Polling (not WS), NaN guards. Useful for strategies that want to react to liquidation cascades.
- **`_handle_external_close` with SQLAlchemy rollback+refresh on failure** — freqtrade-titouan. The bug class most bots miss: when the exchange closes your position behind your back, your DB must catch up or future decisions are based on phantom state. Port the pattern.
- **LLM-style `AIDecisionLog`** — Hyper-Alpha-Arena. Prompt snapshot + raw response + reasoning + executed flag + realized PnL — all persisted per decision. Even if we don't use LLMs, the schema (intent + rationale + outcome) is the right shape for post-hoc analysis of any strategy that makes non-deterministic calls.
- **`EnvironmentMismatchError` on every HL client call** — Hyper-Alpha-Arena. Every client call carries the environment (testnet|mainnet) and raises if it mismatches the client's configured env. Cheap invariant; eliminates testnet-to-mainnet cross-contamination bugs entirely.
- **Avellaneda parameter-estimation pipeline** — avellaneda-mm-freqtrade's `volatility.py` + `intensity.py`. GARCH(1,1) Student-t with rescaling + EWMA rolling-σ fallback + 2× divergence sanity check. MLE fit of `λ(δ) = A·exp(-k·δ)` as a Poisson process with log-linear initial guess. Publishable quality; wholesale-liftable into our research repo.
- **Producer/consumer parameter handoff** — avellaneda-mm-freqtrade. Slow estimator writes `params_{TICKER}.json`; live strategy reads with 15-min file-mutex rate limit. Decouples hot-path from heavy compute, makes params auditable.
- **Effective-mid from depth-walk instead of BBO** — avellaneda-mm-freqtrade. `get_mid_price` walks the order book until cumulative notional ≥ threshold (e.g. $1k). Robust to tight-top spoofing. Adopt instead of naive `(bid+ask)/2`.
- **Uniform `Exchange` ABC for funding-rate aggregation** — Nova. `{rate, interval_hours, nextFundingTime}` + central `normalize_symbol` + `calculate_apy = rate * (24/h) * 365 * 100`. Per-venue `asyncio.Semaphore` + `gather` with task-level exception isolation. Interval-inference state machine snaps to {1,4,8}h with catchup flag. Skeleton for our future funding-arb layer.

**Top 10 transferable lessons (in rough priority order):**

1. **Submission is not a fill.** Every trading decision must key off exchange-confirmed `userFills` events, not off `place_order()` returning. Chainstack's canonical failure.
2. **Margin must be checked against exchange truth before posting.** Don't trust a snapshotted balance. Passivbot Trial #3's insufficient-margin loop was caused by the bot believing it had capacity HL disagreed with.
3. **Testnet by default, mainnet is opt-in.** Never assume the SDK default is safe (HL SDK defaults to mainnet).
4. **Encrypted keyfile, not plaintext JSON.** Hummingbot's `eth_keyfile` AES-CTR is the reference.
5. **Grid width must be measured from realized volatility**, not hand-picked. Chainstack's ±5% grid vs 2.23% p99 excursion = near-zero fills.
6. **Circuit breakers must classify errors.** `InsufficientFunds` is not the same as `5xx` — restarting on the former is a bug, restarting on the latter is correct.
7. **Docker health checks must reflect internal state**, not just `ps alive`. Passivbot's `RestartBotException` loop reported "Up 14h" while thrashing.
8. **Reduce-only submits must re-query position state immediately before submit.** Hummingbot V2 and Passivbot both hit races here.
9. **Order tags encode intent** — `entry_initial_normal_long`, `close_grid_long`, etc. Makes post-hoc analysis trivial. Adopt from Passivbot.
10. **Coin selection (forager) outperforms static pair selection** — but only when executed at single-position scope on the best-volatility coin. Multi-position forager did not compound the gain in Trial #3.

---

## 4. Build-vs-fork-vs-combine decision

**Recommendation: build fresh, in Python, on top of the official HL SDK.** Do not fork any evaluated bot.

### Why not fork

| Candidate | Why not |
|---|---|
| Hummingbot | Too big (134 connectors, thousands of files). Forking means inheriting its complexity. Specific HL files have bugs we'd need to rewrite anyway (V2 position sync, perp nonce). |
| Passivbot | Best strategy code, but CCXT abstraction blocks HL-native features (testnet, agent wallets, HIP-3). Rewriting the connector layer is most of the work. Also the multi-position margin defect. |
| Chainstack | Cleanest architecture in the Tier 1 set. Strategy is naive and has the submission≠fill bug wired into the core event loop. Could steal the skeleton but strategy work is 80% of the effort. |
| Anything Tier 2 | None are production-capable. Building from them means fixing more than keeping. |

### Why build

- **HL SDK is the right base.** It's the authoritative wire format, gets updated with HL's protocol changes, and has VCR cassette tests we can extend.
- **Scope is modest.** V0 is single strategy, single pair, single position, single account. This is 2–3k lines of Python, not 30k.
- **Design-notes driven.** We've already distilled the patterns in `custom-bot-design-notes.md`. Writing from scratch lets us encode them directly rather than grafting onto someone else's abstractions.
- **Patterns we're adopting are mostly small & well-isolated**: Hummingbot's `AsyncThrottler` + `_NonceManager`, Passivbot's order-intent tags + forager-ranking-signal, Chainstack's endpoint health checks, Drift's Pydantic config, the HL SDK's `float_to_wire` validation, **hypersdk's error-enum classifier design** (Phase 5 batch), **go-hyperliquid's signer-interface abstraction** (Phase 5 batch), **freqtrade-titouan's liquidation-price closed-form formula** (Phase 5 batch), **Nova's funding-rate normalization ABC** (Phase 5 batch). Each is portable in isolation.

### Language reconsideration after Phase 5 batch

The Phase 5 batch reshaped my view on Rust:
- **hypersdk (4.34)** and the official HL Rust SDK both cover the full feature set with idiomatic Rust error handling.
- **XEMM Pacifica-HL (3.53)** shows a real Rust trading bot can be built to a high bar — the 5-layer fill pipeline and hot-WS trading patterns are better than anything in the Python set.
- **Market Maker Novus (1.47)**'s failure modes were *specific to that author*, not inherent to Rust.

**Revised stance**: Python for v0 is still correct (faster iteration, we know it). But Rust is a more viable v1-v2 target than I implied in the first synthesis draft. Go remains a serious option per go-hyperliquid quality. Writing in a typed language earlier may be worth considering if we expect the bot to become long-lived production code rather than a research project. Decision point: defer to M3 (24h testnet run). If by then the Python bot's steady-state quality is clear, we can make an informed port/no-port call.

### What to fork / borrow verbatim

Not fork — **copy with attribution** into a `vendor/` directory so we control the code but credit the source:

- `_NonceManager` (Hummingbot spot auth, monotonic + locked).
- `AsyncThrottler` per-endpoint rate limiter (Hummingbot).
- `float_to_wire()` precision validation (HL SDK).
- VCR cassette test harness (HL SDK).
- Order-tag convention — reimplement, not copy, from Passivbot's design.

Everything else gets written fresh against our own design.

---

## 5. Architecture plan for v0

**Objective:** a Hyperliquid testnet bot that runs single-position grid on BTC-perp for weeks without intervention, with measurable profitability and zero known defects.

### 5.1 Stack

- **Language**: Python 3.12 (matches HL SDK, broad community, we know it).
- **Connector**: official HL Python SDK (`hyperliquid-python-sdk`). No CCXT. No custom signing.
- **Config**: YAML (strategy params, committed) + env vars (secrets, never committed) + Pydantic (validation). Separate `TestnetConfig` / `MainnetConfig` classes.
- **Persistence**: SQLite for shadow logs, fills, equity snapshots, grid state.
- **Runtime**: Docker, read-only root filesystem, tmpfs for `/tmp`, named volume for SQLite, ~512MB memory cap.
- **Tests**: `pytest-asyncio` + VCR cassettes for HTTP, `aioresponses` for async mocks, integration tests hit testnet for destructive paths (close-position, reduce-only, leverage changes).

### 5.2 Module layout

```
osbot/
  config/
    __init__.py
    base.py              # Pydantic BaseModel, allowlist-protected mutation
    testnet.py           # TestnetConfig — default
    mainnet.py           # MainnetConfig — explicit opt-in
    schema.yaml          # strategy params example
  auth/
    keyfile.py           # eth_keyfile AES-CTR load/save
    nonce.py             # _NonceManager, monotonic + locked
  connector/
    hl_client.py         # wraps HL SDK Info + Exchange
    throttler.py         # AsyncThrottler, per-endpoint budgets
    endpoints.py         # hardcoded URLs, no override
    errors.py            # AppError hierarchy, retryable flag, classify(HL error code → class)
  state/
    fills.py             # FillEventsManager (WS + REST reconciliation, fills→state)
    positions.py         # live positions, <1s TTL cache, margin-aware
    persistence.py       # SQLite write-ahead before act
  strategy/
    grid.py              # re-plant-on-fill, vol-adaptive range, trend pause
    selection.py         # log_range + volume EMA ranker (forager-style, optional)
    exits.py             # TripleBarrier (SL/TP/time), reduce-only safe submit
    tags.py              # order-intent tag vocabulary + cloid encoder
  risk/
    manager.py           # margin precheck, leverage set, min-notional guard
    limits.py            # WEL, TWEL, max daily loss
  observability/
    shadow.py            # SQLite shadow logger (mids, fills, equity, grid state)
    health.py            # /health endpoint — fill-in-last-N, restart-rate, error-rate
    logger.py            # structured logger, CCXT-style suppression (even though we don't use it)
    telegram.py          # pause/resume/stop, allowed_chat_id
  main.py                # entry point: load config, start loop, trap signals
tests/
  unit/
  integration/           # testnet-hitting, destructive-path tests
  cassettes/             # VCR tapes
```

### 5.3 Startup sequence (enforce every step)

1. Load config with Pydantic validation → fail fast on any error.
2. Assert `config.mode in {"testnet", "mainnet"}`; reject unset.
3. Decrypt keyfile (password from env var for headless).
4. Derive `LocalAccount`; zero out the password/key bytes.
5. Construct `HLClient` with `account_address` explicitly set (agent-wallet-safe).
6. Fetch `clearinghouseState` → sanity check balance, leverage.
7. Call `set_leverage(config.leverage)` — never trust account state.
8. Reconcile fills: query `user_fills` since `max(persisted_last_fill_ts, now - 24h)` → rebuild grid state.
9. Reconcile open orders: cancel any that don't match current strategy state.
10. Start WS subscriptions (`userFills`, `allMids`, `clearinghouseState` at lower cadence).
11. Arm WS liveness watchdog.
12. Enter main loop.

### 5.4 Main loop (single tick, ~1–5s cadence)

1. Drain WS events into `FillEventsManager`.
2. Pull latest mid from `allMids` cache.
3. `risk.precheck()` — if any hard limit breached, enter graceful_stop.
4. `strategy.next_actions(state, mid)` — returns a list of `(tag, side, size, price)` tuples + cancellations.
5. For each action:
   a. `risk.margin_ok(action)` — live margin check, <1s TTL cache of `marginSummary`.
   b. If ok, submit via `HLClient.place_order(..., cloid=tag.to_cloid())`.
   c. Persist submission intent to SQLite **before** awaiting result.
   d. On result: update in-memory state, persist result.
   e. On error: `errors.classify(err)` → retryable → backoff + retry; structural (margin, reduce-only) → suppress the action, log, continue; auth → stop + alert.
6. Every N ticks: reconciliation sweep (compare in-memory open orders vs `open_orders` REST).
7. Every M ticks: shadow-log equity + grid depth to SQLite.

### 5.5 Strategy v0: vol-adaptive grid + trend pause

- **Pair**: BTC-USDC (HL perp).
- **Range**: `range_pct = max(50 bps, 3 × rolling_σ_1h)`. Recompute every 5 min.
- **Levels**: 5 each side, linearly spaced in `range_pct / 5` ticks.
- **Position sizing**: fixed WE per level = `balance × 0.1 / 5_levels`. Check each against HL's $10 min; if under, bump to min and log a `size_bumped` warning (never silently distort).
- **Trend filter**: pause new add-to-inventory if `|EMA_4h_slope| > 50 bps`. Keep existing close_grid orders active. Resume when slope re-enters dead band.
- **TripleBarrier exit per filled level**:
  - TP: `entry ± close_grid_markup` (markup = `0.5 × range_pct / 5`, i.e., half a grid step).
  - SL: `entry ± 3 × range_pct` (well outside the grid envelope — this is the unstuck trigger).
  - Time: 24h (flat-at-market if unfilled).
- **No DCA, no martingale in v0**. Passivbot's DCA is the right idea but the Trial #3 defects show it's non-trivial to get right on HL's margin model. Defer to v1.
- **No forager in v0**. Nail single-pair grid + trend pause first. Forager scaffolding (selection module) is in the layout so it can be enabled in v1, but it's wired out of main.py initially.

### 5.6 Rollout plan

| Milestone | Criterion |
|---|---|
| M0: compile-clean scaffold | All modules typecheck, tests scaffolded, `main.py --dry-run` prints config summary. |
| M1: testnet connectivity | Bot connects to testnet, reads state, places and cancels a single test order correctly. No strategy loop. |
| M2: single-trip round trip | Bot opens + closes 1 position on testnet via the strategy path. All 10 startup steps enforced. |
| M3: 24h testnet run | Zero unhandled exceptions, `/health` reports healthy throughout, shadow log has equity/fills. |
| M4: 1-week testnet run | Measurable net PnL (even if ~zero, not negative), no defects, Telegram ops controls used at least once. |
| M5: 1-week mainnet run (small, $100–200) | Decision point before scaling. |

Each milestone has a go/no-go before the next. Treat M4 as the minimum bar to consider scaling.

### 5.7 What v0 intentionally excludes

- Multi-position. Start single, add later if measured reason exists.
- Forager. Code stubs present, disabled in main.py.
- Shorts. Long-only until strategy is proven; short-side config path exists but `n_positions_short=0`.
- Multi-pair. Single BTC-perp. Adding pairs comes after proving steady-state.
- HIP-3 perps. Ignore unless a specific need arises.
- Vaults. Not a v0 concern.
- Optimization / backtesting. Passivbot's optimizer is excellent; if we want this later, revisit then.
- Web dashboard. Every dashboard in Tier 2 was an attack surface. Use Telegram + shadow SQLite + `/health` endpoint. No HTTP UI.

### 5.8 Risks this plan does NOT address (carry forward to v1)

1. **Funding rate drag**: our 30h+ trials lost ~$0.12–$0.16 to HL funding. A strategy that holds directional exposure over hours pays this. v0's tight grid rarely holds long enough for funding to dominate, but monitor.
2. **Liquidation cascade jump risk**: HL occasionally has jumps outside normal volatility models. Grid `SL = 3× range_pct` helps; no deeper hedge.
3. **Mainnet slippage ≠ testnet**: every number in this synthesis is testnet. Mainnet's deeper books may make entries harder to get filled at maker; may require tuning close_grid markups downward.
4. **Single-account single-bot**: if we want to run multiple bots later (grid + forager + arb), fill attribution requires per-bot cloid prefixes (Passivbot lesson) and we haven't designed the orchestration.

---

## 6. Next concrete actions

Order of operations for the user:

1. **Review this synthesis and `docs/custom-bot-design-notes.md`** — call out anything that's wrong or incomplete.
2. **Scaffold the repo layout** from section 5.2. I can do this on request — creates empty modules + tests + CI skeleton. No business logic yet.
3. **M0 milestone**: make the scaffold typecheck-clean, Pydantic config load example working, `python -m osbot --dry-run` prints a config summary.
4. **M1**: testnet connectivity smoke test — single order placed and cancelled via the real HL SDK against testnet.
5. Everything from M2 onward is strategy work, which will benefit from the lessons above but is the real product engineering.

All evaluation material, patches, configs, and shadow data from Phases 1–4 remain in this repo for future reference. The `bots/` directory (gitignored) can be regenerated on demand via `tools/clone_bot.sh` if any evaluated bot needs to be re-opened.
