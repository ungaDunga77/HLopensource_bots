# Custom HL Bot — Design Notes

Distilled patterns worth adopting (and anti-patterns worth avoiding) from evaluating open-source Hyperliquid trading bots. Organized by concern, not by source bot.

Every entry is **attributed** to the bot(s) where the pattern was observed, so the original code can be consulted if needed. "Observed" means seen in code and judged sound; "found wanting" means a specific failure was seen in practice.

Sources evaluated at time of writing: official HL Python SDK, Chainstack Grid Bot, Passivbot, Hummingbot, HyperLiquidAlgoBot, Copy Trader (MaxIsOntoSomething), Copy Trading Bot (gamma-trade-lab), Grid Bot (SrDebiasi), Rust Bot (0xNoSystem), Market Maker (Novus), Drift Arb, plus Phase 5 expanded batch (hypersdk-infinitefield, go-hyperliquid, freqtrade-titouan, XEMM Pacifica-HL, octobot-mm, hyper-alpha-arena, nova-funding-hub, avellaneda-mm-freqtrade), plus Phase 5b honorable mentions (hyperopen, senpi-skills, vnpy-hyperliquid, memlabs-hl-bot, redm3-lstm, xlev-hl-bot).

---

## 1. Key management & auth

### Adopt

- **Encrypted keyfile storage (AES-CTR via `eth_keyfile`) with password prompt** — Hummingbot. Production bots should default to this over plaintext `.env` or JSON. Password can be supplied non-interactively via env var for container deploys.
- **Agent-wallet pattern with EIP-712 approval** — Rust Bot (0xNoSystem). Server-side agent key generation, AES-256-GCM at rest, user approves via wallet signature. The server **never sees the master private key**. Aligns with HL's native agent wallet system. Best-in-class for multi-user services. **Gotcha observed in Phase 4 Passivbot wrap-up**: when using an agent key, the HL Python SDK's `Exchange` class needs `account_address=main_wallet` passed explicitly, otherwise it signs with the agent and targets the agent's (empty) address. Every wrap-up/admin script must know whether the key it loaded is a main-account key or an agent key. Structure: always store both `private_key` + `wallet_address` (main account) + a `key_type: main|agent` field so scripts can't get it wrong.
- **`SecretStr` + `is_secure: True`** (Pydantic) — Hummingbot. Hides credentials in TUIs, logs, and serialization. Cheap to adopt, prevents entire classes of leaks.
- **`LocalAccount` in memory, never raw key** — official SDK. Pass `eth_account.Account.from_key(key)` once at startup, then reference only the `LocalAccount` object. Key never re-serialized; only the `(r, s, v)` signature tuple is transmitted.
- **Signing-only auth (EIP-712 typed data)** — official SDK. Phantom agent pattern for L1 actions (`"a"` mainnet, `"b"` testnet in source field). No API keys in the traditional sense.
- **WebAuthn passkey + PRF-derived agent-wallet lockbox** — hyperopen (`wallet/agent_lockbox.cljs`). Never stores the main private key anywhere. Flow: (1) user approves an HL agent wallet once via master-wallet signature, (2) agent key is encrypted under a key derived from WebAuthn PRF (passkey touch), (3) per session the user touches the passkey to unlock the agent key, (4) agent key signs HL actions. No dotenv secret, no plaintext on disk, no password-prompt UX. Python analogue for v1+: `cryptography.fernet` + OS keyring, or hardware-backed passkey via `webauthn` lib for a web UI. Strictly better than `PRIVATE_KEY=...` in `.env`; adopt for any user-facing deployment.
- **EIP-712 action-surface coverage checklist** — hyperopen's `hl_signing.cljs` enumerates every HL action the UI can sign (order, cancel, modify, batch, approve-agent, vault deposit/withdraw, staking, send, spot-send, sub-account, USD-class-transfer, etc.). Use as the authoritative checklist for our signing layer: anything not on that list is either unsupported by HL or was added after 2026-04-22 and needs fresh reading of the HL docs.

### Avoid

- **Plaintext `api-keys.json`** — Passivbot. Fine for research, unacceptable for production.
- **Private keys in a database** — Grid Bot (SrDebiasi) stored keys as `VARCHAR(255)` in PostgreSQL, exposed via unauthenticated API with wildcard CORS. Multiplied attack surface: DB compromise, SQL injection, or any network access to the API yields all keys.
- **`COPY .env .env` in Dockerfile** — Copy Trader. Bakes credentials into image layers even if overridden at runtime. Use `env_file` / `--env-file` / docker-compose volume mount.
- **Custom EIP-712 signing without reference validation** — Copy Trader had `chainId: 1337` and used `"a": wallet_address` (should be asset index) and `"c": symbol` (not a standard HL field). Produced silently-invalid payloads. If we roll our own signing, validate wire format against official SDK's test vectors.

---

## 2. Nonce management

### Adopt

- **Thread-safe monotonic `_NonceManager`** — Hummingbot spot auth. `threading.Lock` + monotonic increment prevents collisions under concurrent signing. Every bot that signs concurrently needs this.
- **Monotonic guard**: `nonce = max(int(time.time() * 1000), last_nonce + 1)` — a drop-in fix even without an explicit manager class. Preserves the "nonce ≈ time" property for debuggability while guaranteeing uniqueness.

### Avoid

- **Raw `int(time.time() * 1000)`** — Hummingbot perp auth (inherited bug from the port from spot). V1 strategies hit ~50% rejection rate when buy+sell fire in the same millisecond (normal for symmetric PMM). V2 masks this with `PositionExecutor` retry, but that's a workaround, not a fix.

---

## 3. Config architecture

### Adopt — best pattern seen

**Pydantic / Zod validation + YAML (strategy) + env vars (secrets) + docstrings + cross-validation.**

- **Pydantic + YAML + env vars** — Drift Arb. Cleanest config architecture of any bot evaluated. YAML checked into repo, env vars for secrets, Pydantic validates at startup (fails fast). Separate strategy params (checked in) from secrets (never checked in) is the right split.
- **YAML + dataclass with cross-validation and documented defaults** — Chainstack. Runner-up. Cross-validation catches inconsistent parameter combos before runtime.
- **Pydantic `BaseModel` with env overrides** — Copy Trader. Python flavor of the same pattern.
- **Zod schema with transforms, defaults, range constraints** — Copy Trading Bot. TypeScript flavor — strings → number/boolean, catches misconfig at startup.
- **Separate mainnet/testnet config classes** — Hummingbot. Hardcode the domains; no runtime "am I on testnet?" branching in hot paths.
- **HIP-3 enable/disable flag with safe default** — Hummingbot. Optional, buggy code paths should default off.

### Avoid

- **Raw `.env` only** — most bots. No validation, no types, no range checks. Misconfigurations surface as runtime `KeyError` or silent wrong behavior.
- **Gitignored lock files** — Copy Trading Bot gitignored `package-lock.json`. Every install resolves fresh `^` ranges → non-reproducible builds + supply-chain exposure. Commit lock files, always.
- **`.env.example` copy-pasted from a different project** — Copy Trading Bot shipped Solana/Twitter/Discord keys it didn't use. Every variable in `.env.example` should map to an actual `process.env`/`os.getenv()` call in the code.
- **Config without whitelist protection** — Passivbot has `apply_allowed_modifications()` with an explicit allowlist. Without this, arbitrary config injection is possible. Adopt the allowlist pattern.

---

## 4. Connector / SDK approach

### Decision framework

- **Direct implementation** (Hummingbot) gets you HL-native features: vaults, HIP-3, API wallets, TPSL trigger orders, `reduceOnly`, cross/isolated margin. Cost: more code to maintain, more places for bugs.
- **CCXT** (Passivbot) gets you multi-exchange with one abstraction. Cost: no HL-native features, weaker testnet support, credential leak risk via CCXT debug logging.
- **Official HL Python SDK** (reference) — best-supported path for Python. Use this as the baseline unless multi-exchange is a hard requirement.

### Adopt

- **TypedDict-based API types** — official SDK. `Literal` unions for enum-like fields, mypy-strict checking, zero runtime overhead. Adopt for every request/response type.
- **Compact wire format constants** — official SDK. `a`=asset, `b`=isBuy, `p`=price, `s`=size, `r`=reduceOnly, `t`=type, `c`=cloid. Use the SDK's constants rather than string literals.
- **`float_to_wire()` precision validation** — official SDK / Hummingbot. Raises on rounding error >1e-12. Adopt; it catches config-derived precision bugs at submit time rather than as silent order rejections.
- **`AsyncThrottler` with per-endpoint rate limits** — Hummingbot. Global 1200 req/min with linked per-endpoint budgets. Prevents HL rate-limit bans when one code path goes into a retry storm.
- **HBOT-equivalent broker ID** (benign affiliate tracking) — Hummingbot. Set our own identifier. Lets HL team trace volume back to our bot for debugging; minor revenue share if HL offers it.
- **Endpoint routing with health checks + fallback** — Chainstack. Smart routing between premium RPC and public fallback. Forces signing operations through public API (HL protocol requirement).
- **Hardcoded endpoint constants** — Hummingbot. No user-configurable endpoint override system. Simpler, safer than Passivbot's `custom_endpoint_overrides.py` (which allowed URL rewriting without scheme or domain validation).
- **Pluggable signer interfaces** — go-hyperliquid. `L1ActionSigner` / `UserSignedActionSigner` / `AgentSigner` as trait-like abstractions. The SDK never sees raw private-key bytes — the caller passes a signer object that handles signing internally. Cleanest HSM/KMS integration path in the ecosystem. Our bot's signing layer should expose the same abstraction so we can swap `EthAccountSigner` for `HsmSigner` or `AgentWalletSigner` without touching call sites.
- **WS resilience spec (convergent from hypersdk + go-hyperliquid)** — both independently arrive at the same design: **50s ping interval, 90s read deadline** (invariant: read timeout > ping interval — otherwise pongs false-timeout), **exponential-backoff reconnect capped at 60s** with reset-on-success, `HashSet<Subscription>` auto-replayed after reconnect, **missed-pong liveness requires 2 consecutive missed pongs** before triggering reconnect (not one — reduces churn). This is the reference design; adopt it as the WS layer spec regardless of language.
- **Hot WS trading connection + REST fallback** — XEMM. Sign action once, first-attempt over a warm WS trading connection (halves submit latency), retry with transport switch on transport error (250ms, then 750ms, refreshing the price for the retry). Distinguish transport errors from HL-terminal statuses (`OrderStatus::Error`, `OrderStatus::Resting`) — the latter means the order was rejected/accepted and no retry should occur. For v0 we can ship REST-only; adopt this for v1 if submit latency matters.
- **Dual-ID (cloid ↔ oid) order tracking with three mapping tables + `cancelByCloid`** — vnpy-hyperliquid. Maintain `local_order_id ↔ cloid ↔ oid` as three dicts; always cancel by cloid to avoid the oid-race where HL hasn't yet echoed the oid back when we need to cancel. Thin, debuggable. Every order in our `tags.py` module should carry both identifiers.
- **Fill dedup via bounded `tid` set across merged WS channels** — vnpy-hyperliquid. HL's `userEvents` and `userFills` channels overlap; same fill arrives via both with different field shapes. Dedup via a bounded-FIFO set of trade-ids. Simpler cousin of XEMM's 5-layer pipeline; right choice for a single-venue bot where we don't need REST belt-and-suspenders.
- **Thin adapter over signing primitives, not the high-level wrapper** — vnpy-hyperliquid imports only the signing utilities from `hyperliquid-python-sdk` and builds REST actions by hand. Keeps the surface debuggable (the high-level `Exchange` class hides the wire format). If we need to diverge from SDK semantics (e.g. different error handling, different retry), this is the composition seam.
- **Msgpack wire-format edges documented** — go-hyperliquid's `signing.go`. HL's canonical signing uses msgpack with quirks: short strings must use `str8` format even if msgpack would normally use `str16`; EIP-712 message fields need filtering to match Python's `eth_account` tolerance. The Python SDK hides these behind dynamic typing; go-hyperliquid's `walkMsgpackValue` + `hashStructLenient` document them explicitly. If we ever hand-craft a signature (e.g., for an HSM integration), read this file first — it is the authoritative reference for bytes-level compatibility.

### Avoid

- **SDK default to mainnet** — official SDK defaults `base_url = MAINNET_API_URL` if not specified. **Our bot defaults to testnet**; mainnet requires explicit opt-in.
- **CCXT debug logging at default level** — CCXT logs full request/response at DEBUG, including signed payloads. Passivbot correctly suppresses to WARNING (`logging_setup.py`). Do the same.
- **Shipping a multi-exchange bot with no HL testnet path** — Passivbot has no testnet flag, no sandbox mode, no way to route the HL connector through `api.hyperliquid-testnet.xyz` without a code patch. CCXT has had built-in HL sandbox support (`exchange.set_sandbox_mode(True)` also flips the phantom-agent `source` field `"a"` → `"b"` for correct testnet signing) for over a year. The ~8-line fix is trivial. Our bot must have explicit `mode: testnet|mainnet` config at the top level that routes URLs, signing chain, and any rate limits consistently. Never assume CCXT will be called correctly — verify the phantom agent source, the chain ID, and the URL all match the declared mode.
- **Custom endpoint overrides without validation** — Passivbot allowed URL rewriting without scheme/domain checks. If we support overrides, HTTPS-only + domain whitelist.

---

## 5. State management & reconciliation

**This is the single most common failure mode across all evaluated bots.** Every bot that makes decisions on in-memory state without reconciling against exchange truth eventually drifts.

### Adopt

- **Fill-driven state with WS + polling belt-and-suspenders** — Chainstack. WebSocket for real-time (`allMids`, `userFills`), periodic polling for snapshots (`clearinghouseState`, orders). Survived a 30s HL 502 outage cleanly.
- **In-memory state is derived, not authoritative** — our rule. Every trading decision keys off exchange-confirmed events from `userFills` WS / `user_fills` REST. Submission does **not** count as a fill.
- **Balance hysteresis to prevent oscillation** — Passivbot "snaps" balance values so tiny fluctuations don't trigger recalculations. Good for any position-sizing logic.
- **Pre-action persistence** — state persists to disk **before** acting on it. Bot crash → recover state by reading disk + reconciling against exchange, not by replaying from memory.
- **Reconciliation on startup and on a timer** — Chainstack does both. On-startup reconciliation catches crash-gap drift; timer reconciliation catches silent WS drops.
- **Fill-events manager that auto-loads account history at boot** — Passivbot's `FillEventsManager` queries `/userFills` at startup and loads the last N days so PnL tracking starts warm, not zero. Good pattern; our bot should do the same. Caveat: fills are attributed by *account*, not by bot instance — if two bots run serially on the same account, the second picks up the first's fills as its own. Either (a) persist a "bot instance started at" timestamp and filter older fills, or (b) tag orders with a per-bot prefix and filter on that.
- **Exit/entry order tags** — Passivbot tags every order with the intent (`entry_initial_normal_long`, `close_grid_long`, `entry_grid_cropped_long`, `close_trailing_long`, `unstuck_close_long`). Makes fill-history reconstruction trivial without having to cross-reference with bot state. Steal this — every order should carry a human-readable intent tag in the client order ID.

### Avoid

- **Assuming submission = fill** — Chainstack Grid Bot's `on_trade_executed` fired immediately after `place_order()` returned, regardless of actual fill. Reported 5 "trades" vs 2 real fills over 25h. This is **the** canonical failure. Never count submitted-order as trade-done.
- **Caching errors across retry attempts** — Passivbot's `_get_positions_and_balance_cached` stores the last exception and re-raises it on every subsequent call. When HL returned a transient 502, the cached `ExchangeNotAvailable` poisoned 200+ loop iterations in 14 minutes until the container exited. Errors should not be cached, or cached entries should be invalidated aggressively (sub-second TTL) so the next loop iteration retries with a fresh call.
- **Conflating auth failures with transient 5xx in one exception class** — CCXT's `ExchangeNotAvailable` covers both "exchange down" (retry) and "credentials revoked" (stop). Passivbot's error handler treated them the same → exited on a 30-second network blip. In our bot, classify errors by HTTP code at the transport layer: 5xx and timeouts → backoff-retry forever; 401/403 → stop and alert; 429 → exponential backoff with jitter.
- **Fire-and-forget DB updates** — Grid Bot (SrDebiasi) `void updateTradeOrder().catch(...)` updated in-memory before DB write completed. On restart, DB missing orders that existed on exchange.
- **Trusting internal position state for reduce-only submits** — Hummingbot V2 `PositionExecutor`. Executor thinks it's long, submits reduce-only SELL, HL's view is already flat → rejection. Over time, all executor slots get poisoned. **Our reduce-only path must re-query `clearinghouseState` (or a synchronously-updated in-process cache) immediately before submit, with fallback to regular LIMIT if exchange disagrees.**
- **WS silent death without a watchdog** — Chainstack. SDK WS can stop firing callbacks with no observable error. **Liveness watchdog**: warn + reconnect if no callback has fired for >5min.
- **Snapshotted margin accounting vs live exchange margin** — Passivbot Trial #3. At full slot capacity (3L+1S with DCA ladders armed on each), Passivbot posted ~8 simultaneous DCA orders whose combined margin demand HL rejected as `InsufficientFunds`. Bot's internal model thought it had capacity; HL disagreed. Trip → 10-error circuit breaker → restart loop (20+ internal restarts in 3.5h). **Our rule**: before posting any margin-adding order, fetch live `clearinghouseState.marginSummary` (or use a <1s TTL cache) and check `(totalMarginUsed + order_margin) ≤ availableMargin`. Don't trust any snapshotted "free balance" computed against stale state. If the check fails, suppress the post-attempt entirely instead of letting HL reject it.
- **5-layer fill detection funneled through a single consumer** — XEMM Pacifica-HL. Five parallel sources — (a) WS order updates, (b) WS position updates, (c) REST open-orders poll, (d) REST positions poll, (e) an explicit safety monitor — all push into a bounded mpsc channel. A single `HedgeService` consumer dedupes via a bounded FIFO keyed by `OrderId | Cloid` (capacity 4096) and aggregates partials with terminal / emergency-notional / idle-flush emission rules. Over-engineered for v0, but the *layered defense* is the right pattern. Single-WS-listener designs break silently when HL's WS drops.
- **`EnvironmentMismatchError` on every client call** — Hyper-Alpha-Arena. Every call to the HL client carries the environment (`testnet` | `mainnet`) and raises if it doesn't match the client's configured env. Cheap invariant, eliminates an entire class of testnet-to-mainnet cross-contamination bugs. Our `config.mode` gets enforced at every call site, not just at startup.
- **`AIDecisionLog` schema (intent + rationale + outcome)** — Hyper-Alpha-Arena. Every strategy decision persists `{prompt_snapshot, raw_model_response, parsed_intent, executed_flag, realized_pnl}`. Even for deterministic strategies, the (intent, rationale, outcome) triple is the right shape for post-hoc analysis — you can always reconstruct *why* the bot made a decision, not just *what* it did. Adapt for our strategy layer: persist `{strategy_name, regime, signals, chosen_action, reason_code, executed_px_sz, resulting_pnl}` per decision.

---

## 6. Strategy: grid / PMM specifics

### Adopt

- **Re-plant opposite order on fill** — our design. On buy fill at level N → immediately place sell at level N+1. That's the "grid" mechanic. Grid state survives across restarts via fill-driven reconstruction.
- **Vol-adaptive range** — our design from Chainstack lessons. Compute `range_pct` from rolling realized σ (e.g., `k × σ_1h` with k=3–6) every N minutes. Static YAML ranges always end up wrong for the current regime.
- **Regime filter (trend pause)** — our design. 4h EMA slope / Supertrend / similar. Pause adds-to-inventory in confirmed trends. PMM/grid works in ~60% of time; bleeds the rest. Knowing which regime we're in is worth more than parameter tuning.
- **TripleBarrier exits (SL / TP / time_limit)** — Hummingbot V2. Good structural default. But: tune ratios carefully — Hummingbot's 1:4 (SL 200 bps / TP 50 bps) needs ~80% TP-hit rate to break even on matched exits.
- **Entry-quality check** — Copy Trader. Compare target entry price vs current market; skip if deviation > threshold (5% default). Prevents bad fills when latency matters.
- **Coin-selection (forager) logic** — Passivbot. Rank candidate coins by **log-range EMA** (volatility signal, 16-candle span) and **volume EMA** (365-span), pick top-K that exceeds both thresholds. Clean, explainable, avoids static coin lists. Observed to work well at `n_positions=1` (Trial #2: +$0.116/h, best of three trials) — bot parks on whatever coin has the best volatility profile and grid-harvests it. **Adopt**: our bot should have a selection layer that's separate from the grid strategy, so we can ablate selection on/off independently.
- **Order intent tags** — Passivbot. Every submitted order carries a tag like `entry_initial_normal_long` / `close_grid_long` / `entry_grid_cropped_long` / `close_trailing_long` / `unstuck_close_long`. Tag encodes strategy intent + side + level class. Makes post-hoc analysis trivial (grep fills by tag to reconstruct strategy behavior without cross-referencing internal state logs). **Adopt** — every order gets a `tag:<intent>:<side>:<level>` prefix in the client order ID.
- **Avellaneda-Stoikov parameter estimation done right** — avellaneda-mm-freqtrade's `volatility.py` + `intensity.py`. `volatility.py` runs GARCH(1,1) with Student's-t errors (rescaled + re-fit if convergence fails) with an EWMA rolling-σ fallback plus a sanity check that warns if GARCH and EWMA diverge by >2×. `intensity.py` does MLE fit of `λ(δ) = A·exp(-k·δ)` treating fill events as a Poisson process, with a log-linear initial guess to bootstrap the optimizer. This is the cleanest A-S parameter stack in the catalog — lift both files into a `research/` directory and use them as reference implementations if we ever build an A-S-style MM.
- **Effective mid from depth-walk, not BBO** — avellaneda-mm-freqtrade's `get_mid_price`. Walks the book from best-bid and best-ask outward until cumulative notional ≥ a threshold (e.g., $1k), takes the weighted mid of those levels. Robust to tight-top spoofing where a 0.001 BTC BBO quote makes the "mid" look tight but no real liquidity exists at the top. Adopt for any strategy whose decision-price depends on the reference mid.
- **Producer/consumer parameter handoff** — avellaneda-mm-freqtrade. Slow parameter estimator writes `params_{TICKER}.json` on a schedule; live strategy reads with a 15-minute file-mutex rate limit. Decouples heavy compute from the hot path, makes params auditable (old JSON files = parameter history). Use for any strategy with expensive periodic recomputation (forager rank, A-S params, volatility surfaces).
- **HL liquidation-price closed-form formula** — freqtrade-titouan. Formula validated against 196 real HL positions with average deviation 0.00029%. Directly embeddable in the risk module as a precheck before entry: reject any entry whose computed liquidation price is within `N × range_pct` of the intended entry. Beats polling `clearinghouseState` for the liq price on every tick.
- **Liquidation-fill detection via polling** — freqtrade-titouan. Polls `fetch_my_trades` for fills carrying the `liquidationMarkPx` info field (with NaN and ≤0 guards). Not WS — the liquidation signal shows up in trades feed. Useful for strategies that want to react to cascades (liquidation-hunting is a documented gap in the catalog).
- **`_handle_external_close` — DB rollback + refresh on external close** — freqtrade-titouan. When the exchange closes a position without the bot's involvement (forced liq, manual close via UI), the bot must: (1) detect the close from fills feed, (2) SQL rollback any in-flight DB operations against the stale position, (3) refresh from exchange. Passivbot's Trial #1 had a related bug around caching stale exceptions; this pattern is the explicit fix.
- **Post-hedge position verification** — XEMM. After placing a hedge order, query both venues, sum signed positions, WARN if `|net| >= 0.01` of target. Sanity check catches both partial fills and silent hedge-rejection cases. Adopt for any multi-leg strategy.
- **`PriceTick::round_by_side(side, price, conservative)`** — hypersdk. Directional tick rounding with explicit side semantics: a buy limit rounds DOWN (conservative = don't cross), a sell limit rounds UP. A "conservative" flag toggles between cross-avoiding and cross-permitting. Avoids the entire class of "rounded toward the spread" bugs where a maker limit accidentally became a taker.
- **Scanner/executor separation as a structural rule** — senpi-skills. Explicit rule: "scanners enter, DSL exits, never both." Entry logic (selection) and exit logic (position management) live in separate modules that cannot reach into each other's state; they communicate only via a uniform decision-output schema. Forces the right abstraction: `selection.py` picks coin + direction + size; `exits.py` owns the lifecycle from the moment of fill. Adopt as the invariant for our `strategy/` directory.
- **Uniform decision-output JSON schema → one executor, many strategies** — senpi-skills. Every strategy emits `{action, size, price, reason, strategy_id}` (and optional `confidence`, `stop_price`, `target_price`). A single executor consumes that schema regardless of which scanner produced it. Complements HAA's `AIDecisionLog`: HAA = how to *log* decisions with rationale; senpi-skills = how to *structure* N strategies behind one executor. Combining the two gives us a clean plug-in architecture for adding strategies post-v0 without touching the execution path.
- **DSL two-phase trailing stop with `consecutiveBreachesRequired` noise suppression** — senpi-skills. Trailing stop fires only after N consecutive price ticks breach the stop level, not on a single crossing. Phase-1 arms the stop at `entry + k·ATR`; phase-2 ratchets the stop with price. The `consecutiveBreachesRequired` counter eliminates whipsaw exits on thin-book single-tick wicks. Port to our exits module; tune N per-instrument volatility.
- **`FEE_OPTIMIZED_LIMIT` maker-first-then-taker order wrapper** — senpi-skills. Encodes the maker-rebate vs fill-certainty tradeoff as a single composite order type: (1) place limit at passive price, (2) wait `T_maker` seconds, (3) if unfilled, cancel + repost closer to mid, (4) wait `T_cross` more, (5) cross to take if still unfilled. Our connector's submit API can offer this as a named order type alongside `LIMIT` and `IOC`. Straightforward to implement on top of the existing cancel/reprice primitives.
- **Per-strategy cooldown + daily entry cap as state files** — senpi-skills. After each entry, a strategy writes its last-trade timestamp and today's entry count to a strategy-local JSON. Reload on startup. Cheap; prevents a freshly-restarted bot from re-firing an already-traded signal. Our `state/` layer already persists fills; add per-strategy throttle state alongside.
- **Streaming feature classes (`Window`, `LogReturn`, `Lags`)** — memlabs-hl-bot. Three minimal classes (~100 LOC total) for incremental feature computation on a streaming tick/bar feed: `Window` is a bounded deque with O(1) mean/stddev; `LogReturn` emits `ln(p_t/p_{t-1})` per tick; `Lags` exposes the last N values as a feature vector. Use them as the baseline for our `state/features.py` so strategies don't each reinvent a rolling-window class.
- **Interval-aligned scheduler** — memlabs-hl-bot's `trade_periodically`. Sleeps to the next exact multiple of the bar interval (`next_t = ceil(now / interval) * interval`), not `now + interval`. Small detail, meaningful effect: loop stays phase-locked to bar boundaries across restarts and days, rather than drifting by accumulated loop latency. Adopt for any periodic decision loop.

### Avoid

- **Placeholder P&L** — Chainstack's `profit = 0.01 × sell_notional` for every SELL, regardless of pairing. Always compute from `closedPnL - fee` on real fills.
- **Grid that never re-plants** — Chainstack only reconstructed grid on rebalance threshold. After 2 fills, those levels stayed idle. Grid shrinks to zero in sideways markets.
- **No trend filter** — Chainstack. Observed position-price correlation of −0.52 over 25h (classic "grid accumulates into downtrend") with no regime detection.
- **Grid width guessed, not measured** — Chainstack had ±5% grid vs realized p99 1h excursion of 2.23%. Grid 5× wider than vol envelope = near-zero fills.
- **Naive multi-position capacity without margin coordination** — Passivbot Trial #3. 3 long slots + 1 short slot sounded like "4× the Trial #2 harvest" but produced half the per-hour return (+$0.060/h vs +$0.116/h). Two compounding issues: (1) margin-accounting bug triggered restart loops at full capacity (see section 5); (2) per-position WE was sliced 3× smaller, so each round-trip captured ~$0.027 vs Trial #2's ~$0.053 — individual trade size dropped linearly while HL min-notional created a floor that the bot silently bumped entries to meet (distorting the strategy's sizing model). **Lesson**: multi-position is not automatically better than single-position. It only pays if (a) margin is genuinely coordinated across positions, (b) per-position WE stays large enough to make the wins worth the fees, (c) selection signals are actually picking different coins that contribute independent PnL. Trial #3 failed all three. For our bot: start with single-position, and only add multi-position if there's a measured reason (uncorrelated coin signals, e.g.) rather than "because we can."
- **Cross-side forager deadlock** — Passivbot Trial #3. With `auto_gs: true` and independent per-side coin ranking, the bot held an underwater BTC short for 3+ hours while 3 long slots sat idle (long candidates' log_range scores were all below the current short's). Forager refuses to rotate a slot that holds an open position, and neither side yielded. **Lesson**: if we build a two-sided forager, either (a) use a single combined ranking (long-score vs short-score on each coin → net skew) so both sides always fill, or (b) put a time-cap on how long a slot can hold without a close-target fill before forcing close-at-market.
- **GTC limits masquerading as market orders** — HyperLiquidAlgoBot sent `tif: "Gtc"` with ±0.5% price offset. If not filled immediately, orders persisted indefinitely. **Always use `tif: "Ioc"` for market-like behavior.** HL has no true market orders; official SDK's `market_open()` does this correctly.

---

## 7. Risk management

### Adopt

- **Risk wired into the live path, not just backtest** — our rule, lesson from HyperLiquidAlgoBot (which had a sophisticated `RiskManager` class with Kelly / anti-martingale / pyramiding / vol adjustment, but only used it in backtesting; live `controller.js` didn't import it).
- **Close-position / stop-loss paths have integration tests against testnet** — our rule, lesson from Chainstack (close-position path had `TypeError` from positional-vs-dict signature mismatch + `limit_px: None`, apparently never exercised end-to-end).
- **Custom error hierarchy with `retryable` flag** — Copy Trading Bot. `AppError(retryable: bool)` + categorized subclasses (SDK, Network, WebSocket, Trading, Validation, Config, RateLimit, Account). `retryWithBackoff()` checks flag. Prevents retrying validation errors, correctly retries network errors.
- **Explicit leverage on startup** — our rule, lesson from Hummingbot (doesn't call `set_leverage()` → inherits whatever the account has, could be cross-20x by default). Always `set_leverage(1-3)` explicitly; never trust account state.
- **Min notional check in bot-side precision math** — our rule. For every grid/quote level: `size * price ≥ $10`. HL rejects with "Order must have minimum value of $10. asset=N" otherwise.

- **Circuit breaker that treats all errors equally** — Passivbot. 10-errors-per-hour → `RestartBotException` is a solid pattern for transient network blips. But when `InsufficientFunds` is in the mix, restarting doesn't help — the problem state persists across restart, and the bot walks straight back into the same cascade. **Classify errors at the circuit-breaker layer**: `InsufficientFunds`, `ReduceOnlyWouldIncreasePosition`, `OrderWouldImmediatelyMatchUnfavorably` are **structural** errors (don't restart — suppress the submit and skip the cycle); `5xx`, `Timeout`, `NetworkError` are **transient** (retry-backoff, escalate to restart only if persistent). Never put both classes on the same budget.
- **Reference implementation for classified-error design: hypersdk's error enum.** The Rust SDK ships a structured `Error` enum with methods `is_retryable()`, `is_network_error()`, `is_api_error()` that code can branch on. Also: `ActionError<T>` preserves the failed IDs on batch operations so the bot knows which orders to retry/abandon. Our Python equivalent: enum + classify-helpers, or `AppError(retryable: bool, category: Enum)` pattern from Copy Trading Bot. Don't invent this from scratch.
- **`restart: unless-stopped` + internal `RestartBotException`** creates a **soft-recovery loop** that looks healthy at the container level but is thrashing internally. Trial #3 saw 20+ internal restarts across ~3.5h with `docker ps` reporting the container "Up 14h" the whole time. Container uptime alone is a useless health signal for Passivbot-class bots. **Our rule**: health check must incorporate internal state — e.g., fill-in-last-N-minutes, internal-restarts-per-hour, consecutive-errors. Docker `HEALTHCHECK` should poll a bot-internal `/health` endpoint that returns unhealthy if internal-restart-rate > 2/hour, not just "process is alive."

### Avoid

- **Inconsistent testnet flags across functions** — HyperLiquidAlgoBot hardcoded `testnet: false` in `getCandles()`, `testnet: true` in `getUserOpenPositions()`, env var in `trade.js`. **Live trading could mix mainnet data with testnet account state.** Centralize testnet/mainnet in one config source; no per-call flags.
- **`panic!()` in exchange data handlers** — Market Maker (Novus) had `panic!("THIS IS INSANE")` in liquidation parsing and `panic!("ASSET ISN'T TRADABLE")` on missing assets. Exchange APIs return unexpected values during outages/migrations. Always `Result<T, E>` / error returns.
- **Sentinel values instead of `Option`** — Market Maker used `f64::from_bits(1)` (≈5e-324) as "uninitialized price" sentinel. Silently corrupts calculations. Use `Option<f64>`, `NaN`-guard, or dedicated type.
- **Hardcoded `dry_run=True` masking broken live paths** — Copy Trader. Safe in one sense (prevents accidental live trading) but live code path is never exercised → accumulates bugs unnoticed (wrong API payload format was the result). Our approach: testnet by default, live path exercised on testnet.
- **Unit mismatch in sizing** — Copy Trading Bot compared raw base-unit size against equity-as-USD-percent. Dimensional error. **Position-size caps compare notional (size × price) against equity limits.**
- **Unauthenticated dashboards, even on localhost** — Grid Bot (Fastify) and Market Maker (actix-web) both served `origin: true` / `allow_any_origin()`. Any browser tab can place orders / upload keys. **JWT auth minimum for any HTTP surface.**

---

## 8. Observability & operations

### Adopt

- **Shadow observability built into the bot** — our design, from the Chainstack trial where bot self-reporting was fictional and only `tools/shadow_collector.py` gave real numbers. Bot itself logs mids, fills, equity, grid state to local SQLite. Post-mortem data is invaluable; you'll regret not having it.
- **Structured logger with fixed format** — Hummingbot. `ts - logger - LEVEL - msg`. Parseable by downstream tooling. Lesson: don't use loose format with optional fields.
- **Docker-friendly, read-only FS, tight memory cap** — Chainstack ran 77 MB flat / 0.08% CPU over 25h in a 512 MB container. Same envelope for our bot.
- **YAML config bind-mount** — our Phase 4 pattern. Mount `evaluations/<bot>/config.yaml → /app/config.yaml:ro`. Keeps config version-controlled, bot code unmodified.
- **Telegram for ops controls (pause/resume/stop)** — Copy Trader, with `allowed_chat_id` restriction. Simple, effective for single-user bots. Adopt.
- **Benign affiliate/broker ID** — Hummingbot sets HBOT. Helps with HL-side tracing, potential rev share. Set our own ID.

### Avoid

- **MQTT autostart without a broker configured** — Hummingbot. Generated 14 MB of "Reconnecting in 5.0 seconds" spam in 5h of logs. If we use MQTT, default OFF; require explicit enable.
- **Missing docker healthcheck** — most evaluated bots. Add one: hits an internal status endpoint or checks "last fill within N minutes".
- **Private keys in unauthenticated API** — Grid Bot (SrDebiasi). Addressed above but worth repeating in the ops column.

---

## 9. Testing

### Adopt

- **VCR cassette testing for HTTP** — official SDK. Records HL responses, replays deterministically. Zero live-API dependency in CI. Adopt.
- **`aioresponses` / equivalent mock HTTP for async** — Hummingbot. 274 tests, 9.15s total. Comprehensive coverage including HIP-3 edge cases, reconnection, leverage, position management.
- **`pytest-asyncio` with mock connectors + canned order books** — Drift Arb. 637 lines of tests. Proves small bots can have meaningful coverage; zero tests in most Tier 2 bots is a choice, not a constraint.
- **Integration tests on testnet for destructive paths** — our rule. Close-position, stop-loss, reduce-only, leverage changes. Not unit-mockable.
- **Test isolation from filesystem** — lesson from our Phase 3 Passivbot run (22/991 tests failed due to `os.makedirs("caches")` on read-only FS). Tests that need disk should mock or use `tmp_path`.

### Avoid

- **Tests that hit live API without fixtures** — breaks CI, leaks credentials if accidentally run against mainnet.
- **Skipping tests for "complicated" async code** — most Tier 2 bots. If it's too complicated to test, it's too complicated to ship.

---

## 10. Cross-cutting anti-patterns

- **AI-generated SDK wrappers with `any` types, dynamic imports, guessed constructor params, and "adjust based on actual SDK" comments** — Copy Trading Bot. Compiles but fails on first run. **Our rule**: every SDK integration is driven by reading the SDK source and validating against its test suite / examples.
- **Repurposed bots** — HyperLiquidAlgoBot was a renamed dYdX scalper, leftover `@dydxprotocol/v4-client-js` dependencies, broken entry points. Leftover deps = attack surface + low maintenance discipline. **Our rule**: if we fork, we rip out the old exchange's code immediately, not "someday."
- **`f64::from_bits(1)` / magic-number sentinels** — addressed above. Use the language's null/option/error types.
- **Inference at module import** — redm3-lstm. LSTM's long/short gate is computed **once at `import`** from a stale 2023 CSV with hardcoded `C:/Users/macmw/...` paths, then reused forever by the 900s-scheduled trade loop. **Our rule**: model inference (and any other "expensive decision") runs at decision time, reading the current market — never at import. Modules must be side-effect-free on import.
- **Training/live data distribution mismatch without drift monitor** — redm3-lstm was trained on 2023 OHLC and deployed against 2026 markets with no sanity check. Any ML path in our bot must have a drift monitor (e.g., KS-test on recent window vs training distribution) as a gate before the model's output is allowed to size positions.
- **Regressor collapsed to boolean via `np.sign(y_hat)`** — redm3-lstm. Discards the entire magnitude/confidence signal and jumps to full size on the first positive tick. If we use a regressor, position size scales with predicted return (clipped at a cap), not with a boolean of its sign.
- **Mismatched units in risk thresholds** — redm3-lstm compared `pnl_perc * pos_size` (currency) against `target=0.2` and `-max_loss=0.01` (intended as fractions). Dimensional error. **Enforce unit tags on risk constants** (e.g., Pydantic types `PercentUnit`, `USDUnit`) and reject at startup if dimensions don't match.
- **Identical bid/ask collapsed from L2 level 0** — redm3-lstm assigned `bid = ask = l2[0][0]['px']`. Any L2-derived quote needs paired `bids[0] / asks[0]` access; our L2 parser should return `(bid, ask, spread)` explicitly, never a single mid-ish scalar.
- **High-stars-near-zero-source repos are presumptively hostile** — xlev-hl-bot (79 stars, wallet-drainer). The canonical shape: SEO-padded README is >80% of the repo's total LOC, the install step is a remote-fetch-and-execute (`iwr ... | iex`), there is no auditable source directory, and the README asks for a raw private key in `.env`. **Scouting heuristic for our clone gate**: if a repo has no `src/` or similarly-named source directory AND the ratio of README-to-source line count is >4:1, fail fast and flag as suspected malware. Add to the deny-list after the first such hit. The meta-finding: HL OSS long-tail contains wallet-drainer repos masquerading as bots; stars are not a quality signal on GitHub search.

---

## 10a. Strategy types worth prototyping post-v0 (Phase 5 batch findings)

The Phase 5 expanded-search batch surfaced strategy classes we didn't see in Phases 1–4 and that appear profitable enough to investigate. None are v0 priorities — v0 is grid-on-BTC — but these are the most promising v1+ candidates.

- **Funding-rate arbitrage (perp-spot or perp-perp across venues)** — Nova's funding hub confirms that cross-venue funding rate dispersion is observable and data is easy to collect. HL's funding rates can be 20–100% APY-equivalent in either direction in peak regimes. Substrate: Nova's `Exchange` ABC + APY normalization. Execution: HL perp + any spot (or HL perp + a lower-funding venue's perp). Capital-efficient variant: long funding, short short-funding. Mostly-carry strategy, lower operational risk than directional. **Good candidate for v1.**
- **XEMM with HL as the hedge leg** — XEMM Pacifica-HL confirms the pattern works: make aggressively on a thinner venue (Pacifica), immediately hedge on HL. HL's deep books + maker rebates + fast fills make it an ideal hedge venue. Strategy capture = spread-earned-on-Pacifica minus HL's taker fee (on the hedge). **Needs careful latency budget** (stale quotes = adverse selection) but the infra we saw (5-layer fill detection + hot-WS trading) is the reference implementation. Candidate for v2 once operational maturity is higher.
- **Liquidation-cascade scalping** — freqtrade-titouan has the detection primitives (liquidationMarkPx polling) and we have no bot in the catalog that actually trades on them. When HL cascades, aggressor orders walk the book far past fair value and then snap back within seconds. A TWAP-reverse strategy (sell into cascade bids from the wrong side, unwind on snap-back) is a real opportunity. High ops risk — needs robust reconcile path and tight position sizing.
- **Avellaneda-Stoikov MM with measured intensity** — avellaneda-mm-freqtrade's estimation code is the non-trivial part. The live strategy is broken (q=0) but the research pipeline is solid. A-S with working inventory skew is a strictly-better alternative to grid+trend-pause. **The research code harvest from that bot is probably the highest-leverage v1 upgrade**: replace grid's level-spacing with A-S-computed bid/ask quotes parameterized by inventory.
- **HIP-3 stock-perp specialist** — confirmed gap (no bot in the catalog trades HIP-3). HL's equity perps see lower-sophistication flow and weaker MMs; first-mover advantage is large. Strategy unclear without more research; infra-wise Hummingbot has an HIP-3 enable flag but no bot exercises it. **Research candidate**, not an immediate build target.

## 11. Open research questions (worth addressing before shipping a real bot)

1. **Position-state reconciliation on HL**: event-driven (`userFills` WS) vs snapshot (`clearinghouseState` poll) vs hybrid. Hummingbot uses hybrid and still has lag that triggers the reduce-only bug. What's the right reconciliation cadence to keep lag < fill-to-TP round-trip time?
2. **XEMM on HL**: inventory hedge on a second venue vs skew-based inventory management on HL alone — given HL's maker-taker structure, does external hedging pay for itself? (Untested; Hummingbot XEMM is the only natural testbed among OSS bots.)
3. **Triple Barrier ratio tuning**: is 1:4 SL/TP (Hummingbot default) defensible when entries are maker quotes at spread? Backtest symmetric + multiple asymmetric ratios on real HL fill data.
4. **Regime classification latency**: if we pause quoting in trends, how fast can we classify a trend without false positives? 4h EMA slope is conservative; can we go faster without chopping in on noise?
5. **Grid vs Avellaneda on HL**: Avellaneda-style inventory-aware pricing is richer than grid, but also assumes a diffusion model HL doesn't fit perfectly (jump risk around liquidation cascades). Does it actually beat vanilla grid + trend pause in practice?

---

## 12. Minimum-viable spec (target for v0)

Hard requirements for the custom bot, in priority order:

1. **Key management**: encrypted keyfile (AES-CTR or GCM), testnet default, `LocalAccount`-only in memory, `SecretStr` for all config fields holding secrets.
2. **Config**: Pydantic + YAML + env vars, startup validation, separate testnet/mainnet classes, allowlist for config modifications.
3. **Connector**: official HL SDK base, `AsyncThrottler`, `_NonceManager` (monotonic + locked), hardcoded endpoints, own broker ID, HTTPS/whitelist validation if overrides are supported.
4. **State**: fill-driven, WS + poll belt-and-suspenders, on-disk persistence before act, reconciliation on startup and on timer, WS liveness watchdog.
5. **Strategy**: grid with re-plant-on-fill, vol-adaptive range, trend-regime filter, TripleBarrier exits with tunable (not 1:4) ratios, entry-quality check.
6. **Risk**: live path enforcement (tested against testnet), explicit leverage set at startup, min-notional check per level, `AppError` hierarchy with `retryable` classification, testnet-by-default.
7. **Observability**: SQLite shadow log baked in, structured logging, Docker read-only FS + tight memory cap, healthcheck, Telegram controls with chat_id auth.
8. **Testing**: `aioresponses`/VCR for HTTP, `pytest-asyncio` for async, testnet integration tests for destructive paths, CI runs green before any merge.

Ship v0 with grid-on-BTC-perp only. Add pairs and strategies after steady-state behavior is proven over a multi-week testnet run.
