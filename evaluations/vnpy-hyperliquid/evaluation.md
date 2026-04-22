# Evaluation: vnpy-hyperliquid

**Repo**: https://github.com/Macrohegder/vnpy-hyperliquid
**Evaluator**: Claude (osbots research)
**Date**: 2026-04-22
**Tier**: 2

---

## Scope Note

This is a quick-read static eval (~45 min) of a brand-new (0 stars, pushed 2026-04-21) VeighNa (vnpy) gateway plugin for Hyperliquid. Single-file gateway (~1300 LOC) plus tests. No testnet trial. Not a bot/strategy — it's an **exchange adapter** that exposes HL to the vnpy quant framework (CTA strategies, backtesting, etc.). Novelty is the framework-integration pattern.

## A. Security (weight: 40%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| A1 | Key management | 3 | Private key read from `setting["Private Key"]` in `connect()`, stored as instance attr. Not logged on success; error path logs only the exception (fine). Test harness reads from env `HYPERLIQUID_PRIVATE_KEY`. No key rotation / agent-wallet guidance. No unnecessary persistence. |
| A2 | Dependency hygiene | 3 | `requirements.txt` pins minimum versions only (`vnpy>=3.9.0`, `hyperliquid-python-sdk>=0.10.0`, `eth-account>=0.13.0`). No lockfile. dep-audit ran; pyproject present. Uses official HL SDK for signing. |
| A3 | Network surface | 4 | Two endpoints only: `api.hyperliquid.xyz` REST + WS. Proxy host/port supported. No unexpected outbound hosts, no telemetry. |
| A4 | Code transparency | 4 | All logic in one readable file; docs/assessment.md explains architecture and decisions. No obfuscation, no binary blobs. Comments are bilingual (Chinese/English). |
| A5 | Input validation | 3 | `round_hyperliquid_price` enforces HL's 5-sig-fig + szDecimals rule. Wallet init wraps `Account.from_key` in try/except. Some defensive `get_float_value` helpers. Missing: no validation on volume bounds, no guard on mainnet-only `is_mainnet` hard-coded to `True`. |
| | **A average** | **3.4** | |

## B. Functionality (weight: 30%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| B1 | Strategy clarity | N/A→3 | Not a strategy; it's a gateway. Purpose (vnpy adapter) is crystal clear from README/assessment. Score as "framework role clarity". |
| B2 | Backtesting | 3 | No built-in backtest, but `query_history` (candleSnapshot with 3-day chunking) means vnpy's own BacktestingEngine can consume HL data. That's the point of a gateway. |
| B3 | Risk management | 1 | Gateway level: no rate limiting, no position caps, no max notional checks. `reduce_only` hard-coded `False`. Risk is expected to live in the strategy layer (vnpy convention). |
| B4 | Configurability | 3 | Minimal: Private Key + proxy. Symbol naming, cloid generation automatic. No toggle for testnet (`REST_HOST` hard-coded to mainnet). |
| B5 | Monitoring | 3 | `write_log` calls throughout lifecycle (connect, order submit/resting/filled/rejected, cancel, WS connect/disconnect). No metrics/heartbeats beyond the 20s WS ping. |
| | **B average** | **2.6** | |

## C. Engineering Quality (weight: 20%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| C1 | Tests | 2 | Single `tests/test_gateway.py` (637 LOC) is an **end-to-end live harness** requiring a real private key — 10 scenarios (connect, contracts, market, account, position, history, order, cancel, query, optional live fill). No unit tests, no mocks, no CI. |
| C2 | Error handling | 3 | `on_error` / `on_failed` on REST; try/except around order parsing; WS reconnect via timer; fill dedup via `filled_tids`. Missing: no retry/backoff on failed orders, no partial-fill reconciliation against REST. |
| C3 | Documentation | 4 | README bilingual, clear usage snippet. `docs/assessment.md` is a surprisingly thorough ~240-line OKX-vs-HL design doc (REST/WS/signing/precision/account model mapping). Phase log in README. |
| C4 | Code quality | 4 | Clean type hints, dataclass-style maps at module top, single-responsibility methods, consistent naming. Forward-looking perpDex offset handling (builder-deployed dexes at 110000+). |
| C5 | Maintenance | 1 | 0 stars, pushed 2026-04-21 (1 day old). Claims to be "rebuilt from xldistance/vnpy_hyperliquid". Single-author, no issues/PRs yet. Described as "awaiting live validation" (盘后验证 ⏳). |
| | **C average** | **2.8** | |

## D. Hyperliquid Integration (weight: 10%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| D1 | SDK usage | 4 | Uses official `hyperliquid-python-sdk` surgically — only imports signing primitives (`sign_l1_action`, `order_request_to_order_wire`, `order_wires_to_order_action`, `Cloid`, `OrderWire`). Doesn't wrap the high-level `Exchange` class, builds actions itself. Good separation. |
| D2 | Testnet support | 1 | **Mainnet hard-coded**: `REST_HOST = "https://api.hyperliquid.xyz"`, `is_mainnet = REST_HOST == "..."` (tautological). No testnet flag in `default_setting`. Assessment doc explicitly calls this out ("no formal testnet, small mainnet amounts"). |
| D3 | HL features | 4 | Broad coverage: perps (spot acknowledged but excluded), cloid-based cancel (avoids oid race), builder-deployed perp dex support (novel — iterates `perpDexs` and offsets assets at 110000+10000·i), dual fill-dedup (userEvents + userFills via `tid` set), candleSnapshot chunked history, WS channels l2Book/trades/activeAssetCtx/userEvents/orderUpdates/userFills. Missing: batch orders, modify, TP/SL order types. |
| | **D average** | **3.0** | |

---

## Final Score

```
Final = (3.4 * 0.4) + (2.6 * 0.3) + (2.8 * 0.2) + (3.0 * 0.1)
      = 1.36 + 0.78 + 0.56 + 0.30
      = 3.00
```

## Verdict

- [x] 3.0 - 3.9: Worth investigating, needs hardening — **Tier 2 (low end)**

## Summary

A **real gateway, not a skeleton** — all five claimed phases (connect, market data, account/position, trading, OKX parity) are implemented with reasonable care in ~1300 LOC. However, it is 1 day old, 0 stars, has no unit tests (only a live harness needing a mainnet key), hard-codes mainnet, and is single-author unmaintained. The value is the **pattern** — how to wire HL signing into a mature CEX-oriented Python quant framework — not production use.

## Key Findings

### Strengths
- Thoughtful separation: uses official SDK *only* for signing primitives, builds REST actions directly. Avoids the SDK's high-level `Exchange` wrapper, which keeps the adapter layer thin and debuggable.
- Cloid-first order tracking with dedicated `orderid_cloid_map`/`cloid_orderid_map`/`oid_orderid_map` tables and `cancelByCloid` (avoids the classic "cancel by oid before mapping is populated" race).
- Forward-looking multi-perp-dex support: iterates `perpDexs`, computes asset offsets (`110000 + (i-1)*10000`), queries `clearinghouseState` per dex. Most HL bots ignore builder-deployed dexes.
- Dual-channel fill dedup via `filled_tids: set[int]` handles HL's known `userEvents`+`userFills` duplication.
- Accompanying `docs/assessment.md` is a legitimately useful design artifact — explicit OKX↔HL mapping of auth, WS architecture, precision, account model.

### Concerns
- **Mainnet hard-coded.** `REST_HOST`, `WS_HOST`, and `is_mainnet` are constants. No way to flip to testnet without code edits. Directly contradicts project rule #1.
- **No unit tests.** `tests/test_gateway.py` is a live integration harness requiring `HYPERLIQUID_PRIVATE_KEY`. No CI, no mocks, no coverage of the signing/serialization paths.
- Age + adoption risk: 1 day old, 0 stars, single author, "awaiting live validation" per the README's own phase table.
- `is_spot = 10000 <= asset < 110000` heuristic for price rounding is fragile — relies on HL's asset-id convention holding stable; no defensive check.
- `Offset.NONE` hard-coded; `reduce_only=False` hard-coded. Strategies cannot request reduce-only or close-only behavior.
- secret-scan.json flags 11 HIGH/2 MEDIUM — all false positives (variable names like `self.private_key = ""`, doc URLs). Confirms known `scan_secrets.py` noise.

### Recommendations
- If adopting, fork and (1) add a `testnet` flag toggling hosts + `is_mainnet`, (2) parameterize `reduce_only`/offset in `send_order`, (3) add unit tests around `round_hyperliquid_price` and the parse/dedup paths, (4) consider the xldistance upstream as the more battle-tested ancestor.
- Do **not** testnet-trial this gateway as-is until mainnet hard-coding is removed — violates project rules.

---

## Patterns for custom bot

### Framework-integration mapping (HL → vnpy abstraction)

This bot is the cleanest example so far in our catalog of "bolt HL onto a CEX-oriented quant stack." The mapping it codifies is worth harvesting even if we don't use vnpy:

**1. Adapter pattern boundaries (what to wrap vs expose raw)**

| Adapter concern | HL primitive | vnpy abstraction | Pattern |
|---|---|---|---|
| Auth | EIP-712 wallet signature | "API Key/Secret/Passphrase" | Hide behind `connect(setting)`; expose only a "Private Key" field. |
| Symbol | `coin` string + internal `asset` int | `symbol` + `exchange` | Rename: `{COIN}USDC_SWAP_HL`. Collision-avoidance suffix `_HL`. |
| Order type | `tif` ∈ {Gtc, Ioc, Alo} | `OrderType` ∈ {LIMIT, MARKET, FAK, FOK} | Bidirectional dict; MARKET maps to `{"limit":{"tif":"Ioc"}}` with current px. |
| Order ID | dual: `oid` (server) + `cloid` (client) | single `orderid` | **Maintain three maps** (local↔cloid↔oid). Always cancel by cloid. |
| Position | `assetPositions[].szi` (signed) | `PositionData` with `direction`+`volume` | `direction = LONG if szi>0 else SHORT; volume = abs(szi)`. One-way mode only. |
| Account | per-dex `clearinghouseState` | `AccountData` with `accountid` | Emit one `AccountData` per perp dex, keyed `USDC` / `USDC_{DEX}`. |
| Fills | dual-channel: `userEvents` + `userFills` | single `TradeData` stream | Dedupe via `tid` set. |
| Precision | no `pricetick`; 5-sig-fig + `szDecimals` rule | `pricetick: float` | Compute `pricetick = 10**-(6 - szDecimals)` as hint; enforce via round function at send_order time. |

**2. Signing layer minimalism.** Import exactly 5 symbols from `hyperliquid.utils.signing` (`sign_l1_action`, `order_request_to_order_wire`, `order_wires_to_order_action`, `OrderWire`, `Cloid`). Don't wrap SDK's `Exchange` — build the JSON action yourself and POST. This is the pattern I'd want for our custom bot: SDK for crypto, DIY for HTTP.

**3. Cloid generation.** `(ms_timestamp << 16) | (counter & 0xFFFF)` → `Cloid.from_int(...)`. Uniqueness without coordination, cheap ordering, fits in 128 bits.

**4. Reconnect orchestration.** Timer event (`EVENT_TIMER`) increments ping counter; at 20s, pings or reconnects. On `on_connected`, resubscribes *everything* (user channels + market subs from `self.subscribed` dict) and re-queries account/position. Clean, stateful, no external scheduler needed.

**5. Multi-dex asset-space trick.** To handle HL's builder-deployed perp dexes without symbol collision: compute a global asset int via `offset = 110000 + (i-1)*10000` per dex, keep `name_to_dex` map for routing queries. Useful even for non-vnpy bots if we trade across multiple HL perp dexes.

**Idea vs execution note**: The *execution* here is single-author/unvalidated, but the *idea*-level mapping above is high-quality and directly reusable. If we design our own bot around multiple venues, this table is a good template for an HL driver's public contract.

## Tooling gaps

- `scan_secrets.py`: 11/13 findings are regex matches on variable names (`self.private_key = ""`, `private_key: str`) and the string `"Private Key"` in the `default_setting` dict. Same pattern we saw in freqtrade. Recommendation: skip regex "Private key assignment" rule on lines where RHS is an empty string literal, type annotation without value, or a dict-key string.
- `audit_deps.py`: ran; `pyproject.toml` present (package metadata + deps duplicated in requirements.txt) — worth confirming pyproject parsing now that it's a common pattern.
