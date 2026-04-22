# Lessons Learned

## Security Findings

- **SDK key management is solid**: Official SDK never logs, serializes, or transmits the private key. Only EIP-712 signature (r,s,v) is sent. Bots should follow this pattern — pass `LocalAccount` to Exchange constructor, never reference the raw key again.
- **SDK defaults to mainnet**: `API.__init__` defaults to `MAINNET_API_URL` if no base_url provided. Bots should override this to default to testnet.

## Good Patterns

- **TypedDict-based type system** (SDK): All API request/response types defined as TypedDict with Literal unions. Gives mypy strict checking without runtime overhead. Good pattern for bots to follow.
- **Signature-only auth** (SDK): EIP-712 typed data signing with phantom agent pattern. Key never leaves the local signing function.
- **Config file + keystore options** (SDK): `config.json` for simple usage, encrypted keystore with password prompt for production. Bots should support both.
- **VCR cassette testing** (SDK): Records HTTP responses for deterministic tests without hitting live API. Good pattern for bot test suites.
- **YAML config with validation** (Chainstack): Comprehensive dataclass-based config with cross-validation, range checking, and documented defaults. Good pattern — better than raw .env for complex bot configurations.
- **Endpoint routing with health checks** (Chainstack): Smart routing between Chainstack and public endpoints with fallback. Forces exchange/signing operations through public API (required by HL protocol). Good separation of read vs write endpoints.
- **Testnet-first design** (Chainstack): Separate testnet/mainnet key paths, config defaults to testnet, docs emphasize testnet. This is the pattern all bots should follow.

## Bad Patterns

- **No client-side rate limiting** (SDK): SDK doesn't enforce rate limits. Bots need to implement their own or risk getting throttled.
- **No WebSocket reconnection** (SDK): `WebsocketManager` runs as daemon thread with no reconnection logic. Bots using WebSocket subscriptions must handle disconnects themselves.
- **BTC precision hardcoded** (Chainstack): Price rounded to whole dollars (wrong — should be 2 decimals), size to 5 decimals, min size to 0.0001. All hardcoded for BTC only. Bots should query market metadata from SDK (`info.meta()`) for szDecimals and proper precision.
- **Order fill tracking gap** (Chainstack): Engine places limit orders but assumes immediate execution without verifying fills. Grid strategies need actual fill tracking to know when to place counter-orders.

## HL-Specific Gotchas

- **Mainnet/testnet is URL-based**: SDK determines environment by comparing `base_url == MAINNET_API_URL`. The signing chain differs: `"a"` for mainnet, `"b"` for testnet in phantom agent source field; `"Mainnet"`/`"Testnet"` in user-signed actions.
- **Asset IDs**: Perp assets start at 0, spot assets at 10000, builder-deployed perps at 110000+. The SDK handles this mapping internally via `coin_to_asset` dict.
- **Order wire format**: Orders use compact wire format (`a`=asset, `b`=isBuy, `p`=price, `s`=size, `r`=reduceOnly, `t`=type, `c`=cloid). Prices/sizes sent as strings via `float_to_wire()`.
- **Market orders are IOC limits**: `market_open()` calculates a slippage-adjusted limit price and sends as `{"limit": {"tif": "Ioc"}}`. Default slippage is 5%.
- **WebSocket userEvents/orderUpdates can't multiplex**: SDK raises NotImplementedError if you subscribe to these channels multiple times (messages don't include user identifier).

## CCXT-Based Bot Patterns (Passivbot)

- **CCXT abstraction trades HL-native features for multi-exchange support**: Passivbot uses CCXT for all 7 exchanges. This means no direct use of the official HL SDK, no native testnet flag, and no access to HL-specific features (agent wallets, vault creation). Trade-off is acceptable for multi-exchange bots but limits HL integration depth.
- **Custom endpoint override is an attack surface**: Passivbot's `custom_endpoint_overrides.py` allows URL rewriting without scheme or domain validation. Any bot that supports proxy/custom endpoints should validate HTTPS and maintain a domain whitelist.
- **CCXT debug logging can leak credentials**: CCXT logs full request/response payloads at DEBUG level. Passivbot correctly suppresses CCXT to WARNING by default (`logging_setup.py`). Any CCXT-based bot should do the same.
- **Plaintext JSON credential files are common but weak**: Passivbot uses `api-keys.json` (plaintext). Chainstack uses env vars + key files. Env vars are more secure for containerized deployments. Bots should support both.
- **Balance hysteresis prevents order oscillation**: Passivbot "snaps" balance values to prevent rapid recalculations from small balance changes. Good pattern for any bot doing position sizing based on wallet balance.
- **Config whitelist protection**: Passivbot's `apply_allowed_modifications()` only allows explicitly whitelisted config fields to be modified. Prevents injection of arbitrary config sections. Good pattern for bots with complex configs.

## Tooling Notes

- **scan_secrets.py regex is noisy on env var reads**: Patterns like `private_key = os.getenv(...)` and `if not private_key:` trigger HIGH. These are safe env var lookups, not hardcoded secrets. Consider adding an `os.getenv`/`os.environ` exclusion filter.
- **audit_deps.py needs pyproject.toml support**: Chainstack bot uses `pyproject.toml` instead of `requirements.txt`. Currently flags for manual review but doesn't extract/audit deps from it.
- **trufflehog v2 (pip) output is messy**: ANSI color codes in output, separator-based parsing is fragile. Works but v3 (Go binary) would be cleaner if needed.
- **URL whitelist needs tuning**: Non-whitelisted URL check flags benign domains (apache.org, chainstack docs, gitbook). Could maintain a broader safe-domains list.
- **Smoke test on Chainstack Grid Bot passed**: clone_bot.sh -> scan_secrets.py -> audit_deps.py pipeline works end-to-end. Zero CRITICAL findings, zero vulnerabilities.
- **clone_bot.sh hard gate too aggressive for SDKs**: The 64-char hex regex (`0x[a-fA-F0-9]{64}`) matches EIP-712 signature components (r, s values), transaction hashes, and EVM bytecode — all legitimate content in blockchain SDKs. The gate deleted the official SDK clone on false positives. Needs exclusions for `tests/`, `examples/`, and known signature field names.
- **scan_secrets.py regex equally noisy on SDKs**: 1058 false positives on the official SDK (signing test vectors, VCR cassettes with tx hashes, EVM bytecode). The regex scanner needs context-aware filtering for blockchain codebases.
- **clone_bot.sh bypassed for Passivbot (same reason as SDK)**: Manual `git clone --depth 1` used. This is the 2nd time — confirms the hard gate needs fixing for crypto codebases.
- **Passivbot scan_secrets.py results**: 0 CRITICAL, 26 HIGH (all false positives), 118 MEDIUM (URLs in tests/docs). Manageable triage.
- **audit_deps.py correctly handled multiple requirements files**: Passivbot has requirements-live.txt, requirements-full.txt, requirements-dev.txt, requirements-rust.txt. Tool audited all of them. Separate live vs full distinction is useful — live deps had 0 vulns.
- **Custom Dockerfile needed for Python+Rust bots**: `sandbox/Dockerfile.passivbot` created to handle Rust toolchain + maturin + our security hardening. Standard `Dockerfile.python` insufficient for mixed-language projects.
- **Read-only filesystem causes test failures**: 22 of 991 Passivbot tests failed due to `os.makedirs("caches")` on read-only FS. Expected behavior from our security hardening. These should be counted as environment-specific, not actual failures.
- **clone_bot.sh bypassed for Hummingbot (3rd time)**: Same false-positive issue as SDK and Passivbot. Confirm fix needed — consider making it a soft gate with manual override, or adding exclusions for test/, signing constants, and blockchain hex patterns.
- **scan_secrets.py needs path-scoping option**: Hummingbot is 562 MB. Full scan would timeout or produce thousands of false positives. Ran scoped scans on HL directories only. Add `--scope` flag for large repos.
- **Custom Dockerfile needed for Conda+Cython bots**: `sandbox/Dockerfile.hummingbot` created using `continuumio/miniconda3` base, Conda env create, Cython build. Build time ~8-10 min, image ~3-4 GB. Standard `Dockerfile.python` insufficient for Conda-based projects.

## Direct HL Connector Patterns (Hummingbot)

- **Dual connector pattern (spot + perp)**: Hummingbot separates spot (`exchange/hyperliquid/`) from perp (`derivative/hyperliquid_perpetual/`) with different base classes. Auth, utils, and web_utils are duplicated between them — near-identical code. This duplication should be checked for consistency; divergence was found in nonce management (spot has NonceManager, perp does not).
- **Custom EIP-712 signing is deeper than CCXT abstraction**: Both Hummingbot and Passivbot implement their own HL API layer. Passivbot does it via CCXT; Hummingbot does it directly with custom signing. Hummingbot's approach enables HL-native features (vault, HIP-3, testnet, API wallets) that CCXT cannot provide.
- **Encrypted credential storage is possible**: Hummingbot uses AES-CTR encrypted keyfiles via `eth_keyfile` (password-protected). This is significantly better than Passivbot's plaintext `api-keys.json` or raw `.env` files. Bots targeting production should implement similar encryption.
- **Thread-safe nonce management matters**: Spot auth's `_NonceManager` (threading.Lock + monotonic increment) prevents nonce collisions under concurrent signing. Perp auth lacks this — potential for rejected orders. Any bot doing concurrent order signing should implement nonce management.
- **HIP-3 asset ID mapping**: Builder-deployed perp DEXs start at asset ID 110000. Each DEX gets an offset of 10000 (first=110000, second=120000). Asset IDs are base offset + array index from the `allPerpMetas` response. The `:` in coin names (e.g., `xyz:AAPL`) indicates HIP-3 markets.
- **MD5 for order IDs is acceptable**: Hummingbot hashes client order IDs via MD5 to produce `0x` hex format for HL's cloid field. Not a cryptographic use — collision probability negligible at practical order volumes. Official SDK uses UUID4 hex.

## Tier 2 Bot Patterns

- **GTC limits as "market orders" are dangerous**: HyperLiquidAlgoBot sends market-like orders as `tif: "Gtc"` with +-0.5% price offset. If not filled immediately, these orders persist on the book indefinitely. Always use `tif: "Ioc"` (Immediate-or-Cancel) for market-like behavior. The official SDK does this correctly via `market_open()`.
- **Repurposed bots are common and risky**: HyperLiquidAlgoBot is a renamed dYdX bot — package.json still says "dydx-scalping-bot", unused `@dydxprotocol/v4-client-js` in dependencies, entry point `src/index.ts` doesn't exist. Leftover dependencies increase attack surface and signal low maintenance discipline.
- **Backtesting-only risk management is a false sense of security**: HyperLiquidAlgoBot has a sophisticated RiskManager class (Kelly criterion, anti-martingale, pyramiding, volatility adjustment) but only uses it in backtesting. The live controller.js doesn't import it at all — live trading has no stop loss and no max position enforcement. Always verify risk management is wired into the live trading path.
- **Inconsistent testnet flags across functions break safety guarantees**: HyperLiquidAlgoBot's `getCandles()` hardcodes `testnet: false`, `getUserOpenPositions()` hardcodes `testnet: true`, and `trade.js` uses an env var. This means live trading could mix mainnet data with testnet account state. Testnet handling should be centralized in one config source.
- **`hyperliquid` npm package (unofficial)**: Community SDK for JavaScript. Works for basic operations (orders, candles, user state, WebSocket). Not the official Hyperliquid Python SDK. Acceptable for JS projects but has less ecosystem support.
- **Custom EIP-712 signing can silently produce invalid payloads**: Copy Trader (MaxIsOntoSomething) implements its own EIP-712 signing with `chainId: 1337` and uses `"a": wallet_address` (should be asset index) and `"c": symbol` (not a standard HL API field) in order actions. The HL API would reject these silently. Bots rolling their own signing should validate against the official SDK's wire format.
- **Hardcoded dry_run=True is safe but masks broken live paths**: Copy Trader always creates the executor with `dry_run=True` regardless of the `SIMULATED_TRADING` setting. This prevents accidental live trading but also means the live code path is never exercised and can accumulate bugs unnoticed (as it did here — wrong API payload format).
- **Dockerfile COPY .env bakes credentials into image layers**: Copy Trader's `Dockerfile` includes `COPY .env .env`, which persists credentials in the Docker image even if overridden at runtime via docker-compose volume mount. Use `env_file` or `--env-file` in docker-compose instead.
- **Pydantic + env vars is a good config pattern**: Copy Trader uses Pydantic BaseModel for structured config with env var overrides. Better than raw `.env` for type validation and defaults. Good complement to Chainstack's YAML + dataclass pattern.
- **Telegram bot with chat_id auth is adequate for personal use**: Copy Trader restricts Telegram commands to a single `allowed_chat_id`. Simple but effective for single-user bots. The pause/resume/stop controls via Telegram are a good operational pattern.
- **Copy trading bots need entry quality checks**: Copy Trader checks price deviation between target entry and current market price before copying. If the price has moved >5% (configurable), it skips the copy. Prevents entering at significantly worse prices when there's latency between detection and execution.
- **Speculative SDK integration signals AI-generated code**: Copy Trading Bot (gamma-trade-lab) wraps `@nktkas/hyperliquid` with `any` types, dynamic imports, guessed constructor params, and comments like "adjust based on actual SDK." The code compiles but would fail on first run. When evaluating bots, check that SDK wrappers match the actual SDK API surface — guessed APIs are a strong signal that the code was never tested.
- **Wrong `.env.example` reveals copy-paste projects**: Copy Trading Bot ships a `.env.example` with Solana, Twitter, Discord, GROQ, and Redis keys — none used by the bot. This is a copy-paste artifact from a different project. Always compare `.env.example` contents against actual `process.env` / `os.getenv` usage in the code.
- **Gitignoring lock files is a security anti-pattern**: Copy Trading Bot gitignores `package-lock.json`. This means every `npm install` resolves fresh versions from `^` ranges, making builds non-reproducible and vulnerable to supply chain attacks on transitive dependencies. Lock files must be committed.
- **Unit mismatch in position size capping**: Copy Trading Bot's `capPositionSize` compares raw base-unit size against equity-in-USD percentage. This dimensional error either over-constrains (high-price assets) or under-constrains (low-price assets). Position size caps should compare notional values (size * price) against equity limits.
- **Zod + dotenv is a strong config pattern for TypeScript bots**: Copy Trading Bot validates all env vars through a Zod schema with transforms (string -> number/boolean), defaults, and range constraints. Catches misconfig at startup rather than at runtime. Good complement to the Python patterns: Pydantic (Copy Trader) and YAML + dataclass (Chainstack).
- **Custom error hierarchies with retryable classification**: Copy Trading Bot defines `AppError` with a `retryable` flag, then categorizes errors (SDK, Network, WebSocket, Trading, Validation, Config, RateLimit, Account). The `retryWithBackoff` utility checks `error.retryable` before retrying. Good pattern for bots with multiple failure modes — prevents retrying validation errors while correctly retrying network errors.
- **Storing private keys in databases multiplies attack surface**: Grid Bot (SrDebiasi) stores private keys as `VARCHAR(255)` in PostgreSQL, exposed via an unauthenticated API with wildcard CORS. A database compromise, SQL injection, or any network access to the API yields all keys. Keys should be encrypted at rest (see Rust Bot's AES-256-GCM pattern) or kept in env vars / vault systems — never in application databases.
- **Fire-and-forget DB updates cause order-tracking drift**: Grid Bot uses `void updateTradeOrder().catch(...)` — in-memory state is updated before the DB write completes. On process restart, the DB may lack orders that exist on the exchange. Trading bots must persist state before acting on it, or implement periodic reconciliation against exchange state.
- **Web dashboards need authentication even on localhost**: Grid Bot (Fastify) and Market Maker (actix-web) both serve unauthenticated APIs with `origin: true` / `allow_any_origin()` CORS. Any browser tab on the same machine (or network, if port is exposed) can place orders and upload private keys. If a dashboard is needed, add JWT auth at minimum.
- **EIP-712 agent approval is the best key pattern for HL bots**: Rust Bot (0xNoSystem) generates agent keys server-side, encrypted with AES-256-GCM. Users approve via EIP-712 signature with their wallet (Metamask). The server never sees the user's main private key. This is more secure than any .env-based approach and aligns with Hyperliquid's native agent wallet system.
- **Rhai scripting DSL for user strategies is powerful but needs sandboxing**: Rust Bot lets users write trading logic in Rhai scripts. The sandbox limits operations (100k), depth (64), string size (4KB), array size (1024). But `eval()` may remain accessible in stdlib. Any bot offering user-written strategies must audit the scripting engine's stdlib, disable dangerous functions, and test resource exhaustion.
- **`panic!()` in exchange data handlers will crash the bot on unexpected API responses**: Market Maker (Novus) has `panic!("THIS IS INSANE")` in liquidation parsing and `panic!("ASSET ISN'T TRADABLE")` on missing assets. Exchange APIs can return unexpected values during outages, migrations, or new feature rollouts. Always use `Result<T, E>` / error returns in exchange handlers, never `panic!()`.
- **`f64::from_bits(1)` as a sentinel value is an anti-pattern**: Market Maker uses this instead of `Option<f64>` for uninitialized prices. It produces a tiny non-zero value (~5e-324) that can silently corrupt calculations. Use `Option`, `f64::NAN`, or dedicated error types.
- **GitHub language detection is unreliable for crypto bots**: Three of seven Tier 2 bots had incorrect language in the catalog based on repo metadata: Grid Bot (listed Python, was JS/Node), Market Maker (listed unknown, was Rust), Drift Arb (listed Rust, was Python). Always clone and inspect — don't trust GitHub's language badge.
- **Cross-exchange arbitrage is not truly atomic**: Drift Arb places two independent async orders. Even with rollback logic, there's a window where one leg fills and the other hasn't. Fill detection via position polling (1s intervals, 10s timeout) may lag blockchain state. The execution engine design (snapshot → submit both → poll → rollback if partial) is sound but requires tight timing guarantees that async REST APIs can't provide.
- **Pydantic + YAML + env var separation is the best config pattern seen**: Drift Arb uses YAML for strategy parameters (checked in), env vars for secrets (never checked in), and Pydantic for validation at startup. This is the cleanest config architecture across all 11 bots evaluated. Better than raw .env (most bots), YAML without validation (Chainstack), or Zod-only (Copy Trading Bot).
- **pytest with async mocks is feasible for trading bots**: Drift Arb's 637 lines of tests prove that even small trading bots can have meaningful test coverage. Key patterns: mock connectors returning canned order books, mock execution engine verifying rollback behavior, pytest-asyncio for async operations. The other six Tier 2 bots having zero tests is a choice, not a constraint.
- **Deleted repos can be recovered from forks**: Market Maker (Novus) repo returned 404, but the GitHub API still exposed metadata via the org endpoint, and 18 forks contained the complete codebase. When a repo disappears, check forks before writing it off.

## Phase 4 Testnet Trial Lessons

- **HL testnet faucet requires mainnet activation**: The official drip at `app.hyperliquid-testnet.xyz/drip` returns generic "Something went wrong" unless the address has bridged ≥ $5 USDC to the HL mainnet bridge on Arbitrum. Documented requirement, unhelpful error message.
- **Agent (API) wallets have their own addresses**: When users create an HL agent wallet via the API menu, they get a separate keypair. The agent's address holds $0 — funds stay in the master (MetaMask) wallet it was approved for. Bots that call `Info()`/`Exchange()` without `account_address` override will query balances at the agent address and see $0. Chainstack bot has this limitation.
- **SDK 0.22.0 has a testnet spot_meta bug**: `Info.__init__` and `Exchange.__init__` crash on testnet with `IndexError: list index out of range` because the spot universe references token indices that don't exist in the tokens list. Workaround: pass `spot_meta={"universe": [], "tokens": []}` to skip spot-asset mapping. Should be upstreamed.
- **HL min notional is $10 and strict**: Bot-side precision math must produce orders ≥ $10 notional at every grid level. HL rejects with `"Order must have minimum value of $10. asset=N"`. Grid bots sizing = allocation / levels; higher-priced levels get smaller rounded sizes and hit the floor first. Verify: (size_BTC × price_USD) ≥ 10 for every level.
- **uv in Docker pattern**: `pip install uv && uv sync --frozen --no-dev` in the install step, then `ENV PATH="/app/.venv/bin:${PATH}"`. Do not use `uv run` at CMD — the PATH export makes plain `python` resolve to the venv. Harmless for non-uv bots (dir doesn't exist).
- **Docker Compose interpolates all services**: Even when targeting one service, compose validates `${VAR:?...}` interpolation for every service in the file. Workaround: pass `BOT_NAME=dummy BOT_PATH=bots/dummy` for bot-specific services that don't use those vars.
- **Don't store bot patches in `bots/`**: `bots/` is gitignored and ephemeral. Patches to cloned code are lost on re-clone. Either (a) upstream the fix, (b) keep a patch file in `evaluations/<bot>/patches/`, or (c) bake patches into a bot-specific Dockerfile.
- **Config via bind-mount works well**: Mount `evaluations/<bot>/testnet-config.yaml` → `/app/config.yaml:ro` keeps configs version-controlled and bot code unmodified. Use this pattern for all bot testnet runs.
- **Private key vs address confusion**: Private key is 32 bytes / 64 hex chars; address is 20 bytes / 40 hex chars. `eth_account` gives a helpful error when 20 bytes are passed. Users occasionally paste the address thinking it's the key — first-time setup friction.

## Chainstack Grid Bot — 25h Testnet Trial (2026-04-15 → 2026-04-16)

Lessons from the first full testnet trial. Detailed report at `evaluations/chainstack-grid-bot/shadow/report-20260416-final.md`.

**What the bot got wrong (design defects observed in live data)**

- **Fake fill detection** (`engine.py:394-399`): engine calls `on_trade_executed` immediately after `place_order()` returns. Bot's `total_trades` counter is actually "orders submitted." Observed 5 reported vs 2 real fills over 25h. Any grid bot MUST reconcile against `info.user_fills` on a timer and/or subscribe to the WS `userFills` channel.
- **Placeholder P&L formula** (`basic_grid.py:253-257`): `profit = 0.01 × sell_notional` for every SELL signal. Unrelated to actual buy/sell pairing, ignores fees, funding, partial fills, unrealized. Always compute P&L from `closedPnL - fee` fields on real fills, never from submitted-order metadata.
- **Broken close-position path** (`adapter.py:450`): calls `self.exchange.order(order_request_dict)` but SDK signature is positional. `TypeError` every time. Combined with `limit_px: None` (invalid on HL — no true market orders). Risk manager fires correctly, fails to enforce. The code path has apparently never been exercised end-to-end. **Any trading bot's close-position / stop-loss paths must have integration tests against testnet.**
- **Grid never re-plants filled levels**: After 2 buys filled, those 2 price levels went idle permanently. The strategy only reconstructs the grid on rebalance (threshold-based). In sideways markets, this means the grid shrinks to zero. A correct grid bot re-places the opposite-side order at the same level on every fill — that's literally the "grid" mechanic.
- **No trend filter**: Pure grid bots bleed in trending markets. Observed position-price correlation of −0.52 over 25h (accumulating longs as price fell, which is the grid working as designed but also the problem — no regime detection). A reference price / EMA filter that pauses buys in a confirmed downtrend would have cut drawdown substantially.
- **Range too wide for vol regime**: Config had ±5% grid width; realized p99 1h excursion was 2.23%. Configured grid was ~5× wider than the realized vol envelope, guaranteeing low fill rate. A grid bot should size range from realized σ (e.g., `range_pct ≈ k × σ_1h` with k=3–6), not from user guesses.

**What the bot got right (worth keeping)**

- **WebSocket + polling as belt-and-suspenders**: WS for `allMids`, periodic polling for account/orders/fills. Survived a ~30s HL 502 outage cleanly.
- **YAML config with documented defaults and cross-validation**: Edits are cheap and safe. Better than any `.env`-only pattern.
- **Docker-friendly, read-only FS, 512 MB cap**: Used only 77 MB flat over 25h with 0.08% CPU. Whatever we build should fit the same envelope.
- **Endpoint router abstraction**: Clean separation of info vs exchange endpoints with health checks.

**What we'd do differently in our own bot**

- **Fill reconciliation as a first-class feature**: Every strategy action keyed off exchange-confirmed fills (from `userFills` WS or `user_fills` poll), never off submission. In-memory grid state is derived, not authoritative.
- **Re-plant on fill**: On buy fill at level N, immediately place a sell at level N+1 (and vice versa). No need to rebalance the whole grid.
- **Real P&L accounting**: Sum `closedPnL - fee` from actual fills; mark open inventory to market; report both realized and unrealized. Never a placeholder.
- **Real risk enforcement tested against testnet before merge**: If close-position isn't exercised in CI, it WILL be broken when needed. Implement it as an IOC limit (HL has no true market) with slippage-adjusted price, not `None`.
- **Regime awareness**: Trend filter (e.g., 4h EMA slope) that pauses adds to inventory in strong trends. Grid works great in the ~60% of time markets are range-bound; bleeds in the other 40%. Knowing which regime we're in is worth more than any parameter tuning.
- **Vol-adaptive range**: Recompute `range_pct` from rolling realized σ every N minutes. Static YAML ranges are a trap.
- **Shadow observability for free**: Build the equivalent of `tools/shadow_collector.py` into the bot itself — SQLite log of mids, fills, equity, grid state — because the data is invaluable for post-mortem and you'll regret not having it.

**Testnet trial infrastructure lessons**

- **Shadow data collection is essential for evaluating bots**: The bot's own reporting (`Total trades`, `total_profit`) was fictional. Without our out-of-process `tools/shadow_collector.py` against HL `user_fills`, we'd have no way to score realized P&L or fill rate. **Every future testnet trial should run with shadow collection attached.** The tool is bot-agnostic — only `--bot-container` changes.
- **Bot-log parsing needs the full `ts - logger - LEVEL - msg` format**: Loose regex that just looked for `LEVEL` without accounting for the logger-name field left the `level` column NULL on every row. Full format: `^(ts)\s*-\s*(logger)\s*-\s*(LEVEL)\s*-\s*(msg)$`.
- **WS silent death is real**: A SDK WS subscription can stop firing callbacks without any observable error. Add a liveness watchdog that warns if no callback has fired for >5min.
- **Grid bots on low-vol BTC produce 2 fills in 25h**: Budget for multi-day trials, not hours. Or use higher-vol assets / tighter grids to get faster data.

## Passivbot V5 (HL perp testnet, 2026-04-18 → 2026-04-19, 30.5h total)

**Trial window (both segments are weekend trading)**:
- **Segment 1**: Sat 2026-04-18 01:40 UTC → Sat 07:11 UTC (5.5h, crashed on HL 502)
- **Segment 2**: Sat 2026-04-18 13:21 UTC → Sun 2026-04-19 14:07 UTC (25h, stopped manually)
- **No weekday data**. Crypto runs 24/7 but maker fill rates and realized vol are measurably lower on weekends — results should be treated as a *weekend-regime* sample, not a general steady-state estimate.

Config: BTC long only, 1x leverage, TWEL 50% (~$100 max exposure), grid strategy from `configs/examples/btc_long.json` with testnet overrides (`evaluations/passivbot/testnet-config.json`). Agent-wallet auth via patched connector. Shadow DB: `evaluations/passivbot/shadow/trial-20260418-0149.db`.

**Required patch to run at all**: Passivbot has no testnet support upstream. Added `set_sandbox_mode(True)` call gated on `api-keys.json` `use_testnet: true` field (~8 lines, `evaluations/passivbot/patches/001-testnet-support.patch`). The fact that this is a ~10-minute fix not upstreamed despite CCXT's built-in HL sandbox support (which flips both the URL and the EIP-712 `source` field from `"a"` to `"b"`) is itself a finding about the bot's HL-integration priorities.

**What the 30.5h data showed (combined both segments)**:

- **Final account**: $201.79 → $201.85 after a forced flatten at stop time. **Net +$0.06** as measured; **+$0.34 if we credit the counterfactual** where the last open long would have closed at its grid target ($76,786) instead of being force-closed at market ($75,980, −$0.23 realized on that position).
- **16 fills total** (7 completed round-trips, 9 opens, 7 closes); 15 maker / 1 taker.
- **Fees**: $0.048 = 1.71 bps of notional, consuming ~14% of gross round-trip PnL. Close to HL mainnet maker rate (1.5 bps). Not a profitability constraint.
- **Churn**: 49 orders posted, 3:1 cancel-to-fill. Free on HL, no throttling.
- **Naive annualized**: 8.7% as-measured, ~16% counterfactual. **Weekend-only sample**, both numbers should be treated with wide error bars.

**Segments behaved very differently**:

- **Segment 1 (Sat 04:14–06:22 active, 2h8m of trading in 5.5h uptime)** — BTC oscillated $77,547–$78,000 in the grid sweet spot. **6 clean round-trips, all profitable, +$0.258 net (11.5 bps on notional, $0.047/hour uptime)**. The "ideal regime" for grid. 62% idle.
- **Segment 2 (Sat 13:23 → Sun 14:07, 25h uptime, 99 min of active trading)** — BTC drifted down 1.7% from $76,405 to $75,980 over the window. **Only 1 round-trip + 1 unwound-at-loss position, +$0.037 net from fills, ~93% idle**. Representative of the "drift regime" where grid gets stuck accumulating a one-sided long into falling price.

**What the 5.5h segment-1 data showed**:

- **Patient entry**: 2h27m of no orders after startup while the bot waited for BTC to reach `EMA * (1 - entry_initial_ema_dist)` trigger. First order placed at 02:07 UTC as BTC dipped to $77,716. Good discipline — no forced fills.
- **Grid activation**: When BTC hit ~$77,568 at 04:14, bot filled 3 entries totaling 0.00052 BTC in <20s, then cycled through 5 round-trips in ~80s: buys at 77,547–77,568 / sells at 77,750–77,770. **Classic grid scalping behavior, exactly as designed.**
- **Fills**: 13 new fills (42 orders posted, 33 cancelled/replaced). Realized PnL **+$0.29 USDT** on a $201.79 account over ~5.5h. Gross edge ~26 bps per round-trip, net after fees similar to Hummingbot's ~12 bps.
- **Deeper grid legs never triggered**: entries at $74,558 (-4%) and $70,464 (-9%) sat dormant because BTC stayed in the $76–78k range. This is grid working correctly — they're safety nets, not primary.
- **Reposts dominate order churn**: 33 cancels vs 13 fills. Bot continuously repositions entry/close orders as EMAs and price shift, even when spread movement is tiny (`Δp=0.0013%`, `Δq=46.2%` style reposts). Rate-limit friendly (no throttling observed), but noisy. A more conservative `price_distance_threshold` or repost hysteresis would reduce this.

**Robustness finding — Passivbot does not survive HL 502 outages**:

- 06:56 UTC: HL testnet returned `502 Bad Gateway` from nginx on `POST /info`.
- Bot threw `ccxt.base.errors.ExchangeNotAvailable` in the main execution loop.
- Error handler caught and "retried" but repeatedly re-fetched through the same `_get_positions_and_balance_cached` wrapper that re-raised the cached exception (`hyperliquid.py:417 raise self._hl_cached_result`) — the cached-result pattern **poisoned every subsequent call for the window of the outage**.
- 200+ identical error traces in 14 minutes, then the container exited with code 0 at 07:10.
- **Compare to Chainstack Grid Bot**: survived a ~30s HL 502 during its 25h trial cleanly. Passivbot is less resilient.
- Upstream fix direction: either (a) invalidate the cached error on TTL expiry shorter than the backoff, (b) add explicit 5xx retry-with-backoff at the CCXT wrapper layer, or (c) catch `ExchangeNotAvailable` in the main loop and sleep 30s instead of exiting. The current path conflates "auth failure" (permanent) with "5xx" (transient) under the same `ExchangeNotAvailable` class.

**Operational gotchas**:

- **Image-copied source means runtime patches need bind-mounts**: the Phase 3 `bot-passivbot:latest` image was built with `COPY bots/passivbot /app/`, so our `set_sandbox_mode` patch lives in the gitignored workspace tree but isn't in the image. Compose bind-mount `../bots/passivbot/src/exchanges/hyperliquid.py:/app/src/exchanges/hyperliquid.py:ro` fixes this without a 10-minute Rust rebuild.
- **Passivbot needs writable `caches/` and `backtests/` dirs even in live mode** — initial run crashed with `PermissionError` because non-root `botuser` couldn't write under root-owned `/app`. Bind-mount host dirs pre-chowned to uid 1000 to fix.
- **148 historical fills were auto-loaded at startup** from the 4-day HL user-fills history. Good reconciliation pattern — Passivbot's `FillEventsManager` queries `/userFills` at boot and catches up. But: these fills were from the Hummingbot trials, not Passivbot's. The bot happily attributed them into its own PnL tracking (`pnl=+2.63 USDT`). **Fill attribution is by account, not by bot instance** — expected but worth noting if you ever run multiple bots serially on the same account.
- **TWEL / `total_wallet_exposure_limit` terminology is dangerous**: the `btc_long.json` example ships with TWEL **4.36** (436% notional vs balance, implying ~4–5x leverage equivalent). Without understanding that field, a fresh user running "the example config" would silently be 4x leveraged. Our config uses 0.5 (50%) which is the correct "conservative" setting.
- **Log cadence is deliberately quiet**: health summary every 15 min, unstuck status every 5 min. Silence is not a hang; don't restart on perceived hung loops.

**Entry/exit tags are self-documenting and useful for post-hoc analysis**: every order carries a `tag` like `entry_initial_normal_long`, `entry_grid_normal_long`, `entry_grid_cropped_long`, `close_grid_long`, `close_trailing_long`, `unstuck_close_long`. This makes reconstructing bot intent from fills straightforward. Adopt this pattern.

---

## Passivbot Forager Trial (HL perp testnet, 2026-04-19 → 2026-04-20, 20.75h)

**Forager mode is the reason to run Passivbot.** 10-coin approved pool, `n_positions: 1`, long-only, same per-trade sizing as the static BTC trial. Net +$2.40 in 20.75h vs BTC's +$0.06 in 30.5h — **58× the per-hour return** on matched sizing. The delta is entirely from coin selection: ETH's log_range EMA (16-span) was 2–4× BTC's for almost the whole window, so forager parked on ETH and harvested a tight grid cycle.

**Selection mechanics observed**:
- Ranking cycle runs every ~5 min on two EMAs: volume (365-span) and log_range (16-span).
- `[mode] added long.X: normal (forager slot 1/1)` + `[mode] removed long.Y: graceful_stop` is the full swap atomic in logs.
- `auto_gs: true` prevents swap-while-in-position — outgoing coin only retires once its position closes. This is why the bot held ETH continuously for 18h before rotating.
- Finally saw 6 ETH↔BTC rotations in a 40-min window at T+19h when log_range scores converged.

**Selection-vs-execution tension**: 0 of 88 fills were on BTC despite 3 rotations **to** BTC. Price never touched the entry ladder before the bot rotated back. On a 5-min ranking cadence with ~60s entry-order retire cycles, short rotations produce no fills on the new coin. Implication: forager's per-coin-contribution is highly bimodal — the "chosen" coin gets most/all fills; late rotations are near-free swaps.

**DCA grid recovery worked exactly as designed** (the Martingale scenario): ETH dropped 4% and hit the $2272 grid level, position scaled to 49% WEL ($21 → $42 notional) with averaged entry $2308.61. The averaged pile closed at $2316–$2319 over the next ~40 min for a combined +$0.47. This is the strategy's core value proposition; confirmed it delivers on real HL order flow.

**Reduce-only race reproduces at ~0.1/hour**. Same defect as Trial #1: 2 `InvalidOrder: Reduce only order would increase position` errors in 20h, both self-recovered via the close-grid replace logic. The defect rate is low enough that the 10-errors-per-hour circuit breaker has plenty of headroom in normal conditions but could be eroded in a high-frequency regime.

**WS reconnect cadence is a steady ~1/10min on HL testnet**. 113 reconnects in 20h. Every one 1s-recovered via CCXT Pro with zero trading impact. Pattern is too regular to be instability — it's an HL testnet keepalive/idle-timeout. Don't alert on it. Worth confirming whether mainnet exhibits the same cadence.

**Scaled projection**: $1000-account-equivalent ≈ +$11.90 in 20h (+1.19%), or roughly **+$13.8/day / +$413/month** if the ETH volatility regime holds. This is testnet with no real-depth slippage; treat as optimistic.

**Pending Trial #3**: enable shorts, raise `n_positions` to 3–5, keep the 10-coin pool. Question to answer: does multi-position forager compound the single-coin selection gain, or does TWEL competition dilute it?

---

## Passivbot Full Forager Trial (HL perp testnet, 2026-04-20 → 2026-04-21, 15.9h)

**Full forager config — 3L + 1S, both sides enabled, same 10-coin pool.** Net +$0.96 (+0.47%) in 15.9h → **+$0.060/h, roughly half of single-position forager's +$0.116/h.** Multi-position + shorts did not compound the gain; it diluted it. The full-feature config also surfaced a new Passivbot defect (below) that makes high-concurrent-position configurations impractical to run on HL as shipped.

**Critical defect: insufficient-margin restart loop.** When Passivbot holds all its configured slots full AND tries to maintain the full DCA ladder per position, its internal margin calculation disagrees with HL's. HL rejects the DCA orders as `InsufficientFunds: Insufficient margin to place order. asset=N`. The 10-errors-per-hour circuit breaker trips in ~4 min, triggers `RestartBotException`, bot restarts, immediately hits the same error cascade, restarts again. Observed: 20+ internal restarts + 2 container-level restarts in ~3.5 hours, during which the bot posted 0 fills and accumulated unrealized drawdown. Only reduce-only (close_grid) orders succeeded, because they don't consume margin. **Root cause (inferred): Passivbot computes per-position WE against a snapshotted balance and doesn't account for cross-margin overlap across open positions at order submission time.** `filter_by_min_effective_cost: true` worsens this by bumping entry sizes to meet HL's $10 minimum, which can push combined exposure above available margin once all slots fill simultaneously.

**Safe Passivbot-on-HL config: keep `long.n_positions + short.n_positions ≤ 2`**, or reduce TWEL below 0.5 combined. Single-position forager (Trial #2 config) is the sweet spot: best per-hour return across three trials, zero defects triggered. The shipped Passivbot documentation doesn't mention this boundary.

**Short code path is functional in isolation.** 47 short fills across ETH (45) + BTC (2 rotations). Same PnL profile as longs (~+$0.032 per $12 notional). No short-specific bugs — the mechanics of entry_grid_normal_short / close_grid_short / entry_grid_cropped_short all fire correctly. **Recommendation when running shorts**: mirror the long params rather than using the shipped short template (which ships effectively disabled with `entry_initial_qty_pct: 0.004`).

**Cross-side forager deadlock**: observed ~3h stretch at T+7h where bot held an underwater BTC short while 3 long slots sat idle because BTC's log_range (short-side ranking signal) exceeded all long candidates' log_range scores. The long side never promoted a candidate to `normal` mode. Multi-position forager with `auto_gs: true` can starve one side indefinitely when the market's volatility profile favors the other. Not a bug — a direct consequence of independent per-side ranking + `auto_gs` refusing to rotate in-position slots.

**Fill rate is higher with multi-position** (101 fills in 15.9h vs 88 in 20.75h → 6.4 fills/h vs 4.2 fills/h) but **notional churned is lower** ($1,051 vs $1,538), which means each position is smaller and each round-trip captures less profit. With per-position WE sliced 3× smaller for Trial #3 longs (0.75 TWEL / 3 slots = 0.25 WE per slot vs Trial #2's 0.5 WE per single slot), individual wins dropped from ~$0.053 to ~$0.027.

**Coin diversity worked, but the "best coin" still dominated**: 6 coins filled (vs 1 in Trial #2), but ETH alone had 78 of 101 fills (77%). The non-ETH coins contributed $0.27 of $1.35 total PnL (20%). Forager's selection logic does rotate, but ETH's volatility profile was so dominant over the trial window that the diversification effect was marginal.

**Docker `restart: unless-stopped` masks internal instability.** Trial #3 showed that Passivbot's `RestartBotException` + Docker restart policy create a *soft-recovery* loop — the bot thrashes internally but stays technically "running" as far as container status is concerned. Container uptime alone is a poor health signal for Passivbot; monitor the `[health] uptime=` log line (which resets on internal restart) or `errors=N/10` trend instead.

**Agent-wallet gotcha for wrap-up scripts.** Passivbot's `api-keys.json` for testnet contains an agent private key (the wallet address derived from the private key is DIFFERENT from the `wallet_address` field which is the main account). To operate on the account via the HL SDK, construct `Exchange(agent_wallet, account_address=main_addr, ...)` — the main address holds funds, the agent key just signs. The `check_testnet.py` script also derives its own wallet from `.env` which uses a different testnet account entirely (main-testnet address `0x3BaC...458C`), so its account-state output is for a different wallet than Passivbot trades under. Keep these mental models separate.

---

## Hummingbot V2 `pmm_simple` controller (HL perp testnet, 2026-04-17 → 2026-04-18)

Config: BTC-USD, $80 notional budget across 2 spread levels (10/30 bps each side), 1x leverage, SL 200 bps (MARKET), TP 50 bps (LIMIT), time_limit 1800s, refresh 60s. Shadow DB: `trial-v2-20260417-1908.db`. Bot log: `logs_testnet-config.log`.

**What the data showed (first 5.5h, after which executor slots poisoned themselves):**

- 134 fills (68 buys / 66 sells), 24/hr, all BTC-USD, avg trade $16.78 notional
- Total notional churned: $2,248; gross edge captured: ~14 bps on notional
- Fees paid: $0.44 (~2 bps); realized PnL (matched round-trips): **$2.15**
- Net inventory: −0.002 BTC (short drift from stuck executors), MTM −$158 at close
- Total PnL incl. inventory MTM: $3.06, or ~14 bps on notional
- Price regime: 122 bps intraday range — friendly, not a stress test

Extrapolation to a $1,000 account at same rotation rate: ~$117/day gross ceiling in a good regime. After realistic haircuts (mainnet adverse selection ~50–70% of gross, real HL maker fees 3 bps RT vs 2 bps observed, inventory drift, executor-bug throttle): expected **$3–10/day steady-state, −$30 to −$200 on trending days**. Strategy mechanically works; account size + single-pair PMM is the binding constraint, not fee math.

**V2 PositionExecutor ↔ HL connector position-sync bug**:

- After ~5.5h, 15,303 `Reduce only order would increase position. asset=3` rejections and 5,006 `Take profit order failed` events; multiple executors hit `Retrying 10/10` and stopped reopening → bot "alive" but not placing new orders.
- Root cause: V2 `pmm_simple` submits take-profits as reduce-only LIMIT orders. Hummingbot's internal position state lags HL's actual state (settlement delay between fill event and position-snapshot refresh). When the executor thinks it's long and submits a reduce-only SELL, HL's view is already flat (or the opposite sign) → rejection.
- V2 masks the V1 nonce-collision bug via retry, but this reduce-only lag is a new, V2-specific defect introduced by the TripleBarrier exit logic.
- Upstream fix direction: reconcile executor position state against HL's `clearinghouseState` before every reduce-only submit, or retry reduce-only rejections by re-querying position first, or allow TP as a regular LIMIT when reduce-only would fail.

**MQTT bridge noise**: Hummingbot tries to connect to a local MQTT broker every 10s by default. 14 MB of log file is mostly "Reconnecting in 5.0 seconds". Disable via `mqtt_bridge.mqtt_autostart: False` in `conf_client.yml` or run with `--no-mqtt` equivalent. Not a bug, but operationally noisy.

**Triple Barrier (`stop_loss: 0.02`, `take_profit: 0.005`) is asymmetric 1:4 risk/reward** — needs ~80% TP-hit rate just to break even on matched exits. For a PMM where entries are maker quotes at the spread, this is generally defensible (spread capture should hit TP far more often than SL), but the asymmetry is not obviously correct and deserves sensitivity analysis before any mainnet use.

**Leverage default**: Hummingbot does not call `set_leverage()` on startup — inherits whatever HL account has (we pre-set 1x manually). V2 `leverage` field in the YAML only affects local budget sizing, not exchange-side leverage. **Safety concern**: fresh deployments can silently run at cross-20x if the account was left that way.

**Strategy coverage gap**: We tested V1 `simple_pmm` (smoke only, bug-surface) and V2 `pmm_simple` (5.5h trial, this run). Hummingbot ships ~15 other strategies applicable to HL — `perpetual_market_making` (V1), `avellaneda_market_making` (V1), `cross_exchange_market_making` (V1), V2 controllers `pmm_dynamic`, `dman_v3`, `bollinger_v1`, `macd_bb_v1`, `supertrend_v1`, `stat_arb`, `xemm_multiple_levels`. Current data supports a verdict on the *bot* and *the PMM family*, not on the strategy framework as a whole. XEMM in particular is unexplored and would have a very different risk profile (hedges inventory externally).

**Verdict**: Scale headline ("lots of trades, tiny P&L") is a *capital* story, not a *strategy* story. Engineering verdict on Hummingbot-on-HL is "works with documented defects" — the V1 nonce collision and V2 position-sync bug are both real and both have clear upstream fixes.

---

## Hummingbot (simple_pmm script, HL perp testnet, 2026-04-17)

**Upstream bugs blocking startup** — all in `bots/hummingbot/hummingbot/connector/derivative/hyperliquid_perpetual/hyperliquid_perpetual_derivative.py` unless noted:

- **`split(':')` crash on HIP-3 symbols with >1 colon** (line 983). `deployer, base = full_symbol.split(':')` raises `ValueError: too many values to unpack`. Fix: `split(':', 1)`. Blocks trading-rules init → connector never ready.
- **Duplicate-symbol handling uses case-sensitive check but stores uppercased value** (lines 987-991). Causes `bidict.ValueDuplicationError` when two DEX markets collide after `.upper()`. Original `_resolve_trading_pair_symbols_duplicate` has the same case mismatch and compounds the bug.
- **HIP-3 DEX market fetch path is a minefield**. We disabled it entirely (`enable_hip3_markets` default `True` → `False`). Multiple additional bugs lurk here; for single-market perp trading it is not needed.
- **Sample `scripts/simple_pmm.py` uses `OrderCandidate` on a perpetual exchange** — budget checker crashes with `AttributeError: 'OrderCandidate' object has no attribute 'position_close'`. Fix: `PerpetualOrderCandidate(..., leverage=Decimal("1"), position_close=False)`.
- **Nonce-collision bug in order submission**: Hummingbot uses the current millisecond as the nonce. When buy+sell are dispatched in the same ms (normal for symmetric PMM), the second one fails with `Invalid nonce: duplicate nonce`. Observed ~50% rejection rate. Did not patch — documented as finding.

**Config traps**:

- `order_amount` on BTC-USD HL perp quantizes to zero if you set < `10^-szDecimals`. For BTC (szDecimals=5) the floor is 0.00001 BTC, but practically you need ≥ `min_notional_size / price` ≈ $10 / $78k ≈ 0.00013. Use 0.001+ with buffer.
- Default Hummingbot PMM does **not** call `set_leverage()`. HL will apply whatever account-level leverage is configured (was 20x cross on our account by default). A market-making strategy should force 1-3x, not ride exchange defaults.

**HL account / funding gotchas (specific to agent-wallet setups)**:

- **Agent wallets cannot transfer funds between spot and perp.** `usdClassTransfer` signed by the agent returns "Must deposit before performing actions". That action is master-only. Trial setup requires either (a) master moves funds via UI, or (b) master signs a one-shot transfer.
- **Unified Account Mode is transparent to the legacy `clearinghouseState` endpoint.** Even with unified on, perp `accountValue` reads 0 if no explicit transfer has been made. Hummingbot queries `clearinghouseState` for collateral → budget checker sees $0 → quantizes order to zero. Must disable unified OR do an explicit spot→perp transfer.
- **An address can exist on both mainnet and testnet.** A key labelled `HYPERLIQUID_TESTNET_PRIVATE_KEY` is indistinguishable from a mainnet key to the wallet layer — the only signal is where funds live. Always verify with a balance probe on both networks before using, and keep testnet key rotation disciplined.

**Strategy-quality finding (`simple_pmm.py` as a PMM)**:

- It's a pedagogical example, not a production strategy. No inventory skew handling, no volatility-adaptive spreads, no leverage control, fixed 30s refresh (picked off by toxic flow). Hummingbot *does* ship better (`pure_market_making`, `avellaneda_market_making`, v2 controllers) — so a fair evaluation of the engine needs at least one of those, not `simple_pmm`.
- Observed in a ~30-minute smoke run: accumulated a one-sided short position (classic PMM drift when price moves against inventory), realized -$0.02 after flatten. Data on one-sided fill behavior captured in shadow DB `trial-20260417-1818.db`.

**Operational**:

- **Rebuilds are cheap once conda env is cached.** First build ~10-15 min; subsequent rebuilds after a `.py` edit are seconds. Don't be afraid to iterate.
- **Hot-patching `.py` files via `docker cp` + `docker restart`** works for quick probes (e.g. adding a debug log), but always bake into the image for real runs — containers get recreated and hot-patches vanish.
- **When a bot stays "not ready" with no error**, patch the readiness log line to dump `status_dict` keys. Silent-hang connectors are common.

---

## Freqtrade-titouan Trial A (HL perp testnet, 2026-04-21 → 2026-04-22, ~24h)

**External-close path works; signal-driven entries on HL testnet are hard to fill with passive limits.**

**The target-test — `_handle_external_close` — fire-validated.** Force-closed Freqtrade's tracked Trade id=1 via the HL SDK (`market_close`). Freqtrade detected the missing position within 10 seconds: logged `Not enough BTC in wallet to exit` (benign), then `LIMIT_SELL fulfilled ... Marking Trade(id=1) as closed as the trade is fulfilled and found no open orders for it`. SQLAlchemy rollback+refresh kept the DB consistent — no phantom open-trade row. **This is the pattern we're adopting verbatim for our custom bot's position-reconciliation layer.**

**Testnet enablement pattern: override `_init_ccxt` in the HL exchange subclass to call `set_sandbox_mode(True)` when `exchange.use_testnet=true`.** Same patch shape as Passivbot. `set_sandbox_mode` flips both the URL AND the EIP-712 `source` field (`"a"` → `"b"`), so it's the single-call right way to do this. Putting the call in `additional_exchange_init` is too late — markets get loaded from mainnet first. Must override `_init_ccxt`.

**Freqtrade's market boot is slow on HL: ~4.5 min per container start** because `fetch_market_leverage_tiers` makes ~500 sequential REST calls across all HL perp markets. The fork exposes a `_ft_has['uses_leverage_tiers'] = False` flag in its HL module — but Freqtrade core never reads it. Upstream PR candidate. For our bot: skip per-market leverage tier loading entirely; HL's cross/isolated margin model doesn't need it.

**Config schema strictness bites when disabling optional sections.** Freqtrade's JSON schema requires all sub-fields of `telegram` and `api_server` even when `enabled: false`. Couldn't just write `{"enabled": false}` — had to omit the section entirely. Worth knowing if we ever ship a Pydantic config for our bot: either `exclude_unset=True` at serialization or accept missing required fields when the parent `enabled=False`.

**HL testnet WS cadence reconfirmed: ~2 `continuously_async_watch_ohlcv` errors per 30-min window.** All self-recover in <2s via Freqtrade's built-in reconnect. Now seen in three different frameworks (Hummingbot, Passivbot, Freqtrade) → firmly testnet-side behavior, not bot-defect. Production WS layer must tolerate this cadence without alerting.

**Passive limit entries in a trending market don't fill.** Phase 2 of the trial (moderate RSI<45 + EMA_fast > EMA_slow strategy) fired 1 entry signal in 12h of uptrending BTC. The limit at `entry_pricing.price_side: same` (best-bid) hit the 5-min `unfilledtimeout` before crossing → cancelled. This is a Freqtrade-on-HL pairing issue, not a fork defect: on 5-min candles with passive limits, directional markets fill poorly. A real production Freqtrade setup on HL would need `price_side: other` (cross the spread) or a longer unfilledtimeout — both have costs. Our custom bot will replant limits against the opposite side of the book to avoid this.

**`no-new-privileges:true` + Freqtrade's sudo-chown entrypoint.** The Freqtrade Dockerfile's entrypoint tries `sudo chown` to fix bind-mount ownership. Our hardened sandbox blocks this with `no-new-privileges: true` in compose, producing a warning but no hard failure. The real cost is the leverage-tiers cache in `user_data/` never persists across container restarts, forcing the 4.5-min boot every time. Either pre-chown host-side or accept the cost. We accepted it — two boots over the 24h trial.

**Fill summary (whole trial, Phase 1 + 2):** 6 fills (3 opens + 3 closes), closedPnl +$0.099, fees $0.017 (2.50 bps of $68 notional, 67% maker). Net equity change: +$0.080. Data volume is small — strategy was built as a smoke test, not a profit measurement — so treat the PnL as a sanity check, not a signal.

**What we learned about the fork's claimed features, live:**
- ✅ `_handle_external_close` works.
- ⏳ `fetch_liquidation_fills` (liquidation detection) — code inspection only; couldn't generate a real cascade on testnet.
- ⏳ `TrendRegularityFilter` — requires a strategy that USES it, and no such strategy ships with the fork; code-inspection-validated only.
- ⏳ Custom hyperopt loss + 6 Optuna samplers — backtesting-only, not live-observable.
- ⏳ Liquidation-price closed-form formula — code-validated; to fire-validate, we'd need to push a position near liquidation on testnet, which requires extreme leverage.

**The fork's score stands at 3.75.** Trial confirmed the patterns we want to adopt and surfaced operational knowledge (boot time, config quirks, passive-limit fill issues) that will inform our own bot's design.
