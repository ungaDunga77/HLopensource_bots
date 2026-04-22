# Evaluation: hypersdk (infinitefield)

**Repo**: https://github.com/infinitefield/hypersdk
**Evaluator**: claude
**Date**: 2026-04-19
**Tier**: 2 (community Rust SDK; 138 stars; MPL-2.0)

> **Note on rubric adaptation.** This is an SDK, not a bot. The rubric is adapted:
> - A (Security, 40%) — key handling at constructor boundary, cargo deps, network surface, code transparency, input validation.
> - B (Functionality, 30%) — B1 = API coverage; B2 (backtesting) N/A; B3 (risk mgmt) N/A; B4 = configurability; B5 = observability.
> - C (Engineering, 20%) — tests, error handling, docs, code quality, maintenance. Rust-specific focus: `unsafe`, `unwrap`/`expect`/`panic!` on production paths, error-type design.
> - D (HL Integration, 10%) — D1 (SDK usage) N/A (*is* the SDK); D2 testnet; D3 HL feature coverage.
>
> Final weights unchanged (0.4 / 0.3 / 0.2 / 0.1).

---

## A. Security (weight: 40%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| A1 | Key handling (constructor pattern) | 5 | SDK itself never touches keys: signing methods take `&S: Signer` (alloy trait). Key ownership stays with caller. `PrivateKeySigner` is re-exported from `alloy::signers::local`, i.e. a vetted, audited crate. Example `credentials.rs` supports three ingestion patterns cleanly: `--private-key` CLI, Foundry keystore (with `rpassword` prompt fallback), or `PRIVATE_KEY` env via dotenv. No key logging, no ambient key access, no writing keys anywhere. Agent-wallet workflow supported via `approve_agent` + `multisig_approve_agent` examples. |
| A2 | Dependency hygiene | 3 | 19 runtime deps, all mainstream and well-maintained: alloy 1.5, reqwest 0.13, tokio 1, serde 1, rust_decimal 1.39, chrono 0.4, rmp-serde 1. WebSocket lib `yawc 0.3` is niche (zero-copy, performance-focused) — lower ecosystem review surface than `tokio-tungstenite` but actively maintained. No `Cargo.lock` committed (normal for libraries but means downstream consumers resolve versions afresh). No pinning to git SHAs. `anyhow` used broadly alongside the structured `Error` type — mild tension. |
| A3 | Network surface | 5 | Two endpoints: HTTPS `api.hyperliquid.xyz` (+ testnet) and `wss://api.hyperliquid.xyz/ws`. `reqwest` with `rustls` feature flag (no OpenSSL). 10-second request timeout hardcoded. `websocket_no_tls()` helper exists but is opt-in and documented as "testing/local" only. No proxy, telemetry, or third-party calls. |
| A4 | Code transparency | 5 | Zero `unsafe` blocks across entire crate. Fully open source (MPL-2.0). No obfuscation, no vendored binaries (only JSON ABIs for EVM contracts, which are standard). Code reads as a direct, documented wrapper around the HL REST/WS wire format. |
| A5 | Input validation | 4 | Strong type-level validation: prices/sizes are `rust_decimal::Decimal` (not f64 — rejects float drift); addresses are `alloy::Address` (parse-time checksum); order-side / TIF / grouping are enums; nonces are `u64`. `PriceTick::tick_for`/`round`/`round_by_side` enforce HL's 5-sig-fig + max-decimal tick rules and return `Option<Decimal>` rather than panicking. `Error::InvalidOrder { message }` variant exists for exchange-side rejections. What's missing: no client-side min-notional check (the recurring $10 gotcha) — caller must enforce. |
| | **A average** | **4.4** | |

## B. Functionality (weight: 30%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| B1 | API coverage | 5 | Very broad. HTTP client exposes ~50+ methods: perps/spot meta, `clearinghouse_state`, `user_balances`, `user_fees`, `open_orders`, `all_mids`, `funding_history`, `vault_details`, `user_vault_equities`, `api_agents`, `multi_sig_config`, outcome markets (HIP-4), HIP-3 list, plus trading: `place`, batch cancel/modify, `schedule_cancel`, `update_leverage`, `approve_agent`, `usd_send`, `spot_send`, `send_asset`, EVM transfers, vault transfer, subaccounts, priority-fee bidding. WS covers trades, L2Book, candles, allMids, userEvents, userFills, userFundings, orderUpdates, userTwapSliceFills, userTwapHistory, activeAssetData, webData2. 26 hypercore examples + morpho/uniswap EVM examples. |
| B2 | Backtesting | N/A | N/A (SDK) |
| B3 | Risk management | N/A | N/A (SDK) |
| B4 | Configurability | 4 | `Client::new(Chain)` + `.with_url(Url)` + `.with_http_client(...)` builder methods allow custom endpoints and shared reqwest clients. `NonceHandler` is thread-safe and configurable. WS reconnect constants (initial 500ms, cap 5s, max missed pongs 2) are `const` in `ws.rs` — not runtime-tunable without a fork. No global config object, which is actually a plus (less hidden state). |
| B5 | Observability | 3 | Uses `log` crate facade — consumers can wire any backend (e.g. `simple_logger` in examples). WS logs connect/disconnect/reconnect attempts, re-subscription, missed pongs, parse failures. HTTP error bodies are included in the `anyhow!("decode failed: ...; body={text}")` messages (useful for debugging). No built-in metrics (counters, histograms) and no tracing spans — just log lines. |
| | **B average (B1+B4+B5)/3** | **4.0** | |

## C. Engineering Quality (weight: 20%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| C1 | Tests | 4 | 62 `#[test]` / `#[tokio::test]` attributes across 6 files. Notable: signature roundtrip tests (`test_sign_usd_transfer_action` checks an exact byte-for-byte signature against a known-good hex; `test_recover_usd_send` and `test_recover_batch_order` verify signer recovery from sigs); serde roundtrip tests for every WS payload variant (Candle, UserEvents::Funding, UserEvents::NonUserCancel, ActiveAssetData, UserTwapSliceFills, UserTwapHistory, WebData2); candle interval parser tests; tick-rounding tests. Some tests require network (hit real mainnet) but are gated as `#[tokio::test]`. No integration test harness separate from unit tests. |
| C2 | Error handling (structural) | 5 | This is the standout area. `hypercore::Error` is a proper structured enum with 9 variants: `Network(reqwest::Error)`, `Api(String)`, `Json(serde_json::Error)`, `Signing(SignerError)`, `InvalidOrder { message }`, `WebSocket(String)`, `InvalidAddress(String)`, `Timeout`, `Other(String)`. Key feature: `is_retryable()`, `is_network_error()`, `is_api_error()` helper methods classify transient vs permanent — exactly the structural/transient split we want. `From` impls route `reqwest::Error` with `is_timeout()` to `Error::Timeout`. `std::error::Error::source()` correctly threaded. Generic `ActionError<T>` for batch failures preserves which IDs failed. **Zero `unwrap()` / `expect()` / `panic!()` on production paths** in `ws.rs`, none in `signing.rs`, and the two in `mod.rs:1000/1034` are inside tests (`#[test] mod` blocks). Only non-test unwraps in the crate are on `Url::parse` of compile-time-constant strings (`"https://api.hyperliquid.xyz".parse().unwrap()`) — i.e. infallible by construction. Zero `unsafe`. HTTP methods currently return `anyhow::Result<T>` (not `Result<T, Error>`) — mild inconsistency with the structured `Error` above, but `anyhow::Error` can wrap `Error` via the `From<anyhow::Error>` impl. |
| C3 | Documentation | 5 | Crate-level rustdoc with quick-start for queries, orders, WS. Per-module docs, per-type docs, per-method docs, most with `no_run` doctest examples. README explains architectural decisions: *why* `impl Future` instead of `async fn` (tokio::spawn ergonomics), *why* `rust_decimal`, *why* `yawc`. `CHANGELOG.md` follows Keep-a-Changelog. `docs.rs` configured with `all-features = true`. |
| C4 | Code quality / idiomatic Rust | 4 | Idiomatic alloy usage for EIP-712 (the `solidity::Agent` struct derives `SolStruct`, uses `eip712_signing_hash(&CORE_MAINNET_EIP712_DOMAIN)` — this is the *correct* alloy-native path, not a hand-rolled ABI encoder). `impl Future<Output=...> + Send + 'static` pattern (documented rationale) makes methods spawn-friendly. Thread-safe `NonceHandler` uses `AtomicU64` with `fetch_max` + `fetch_add`. Nicely small `ws.rs` state machine: exponential backoff (500ms→5s cap, reset on success), missed-pong liveness (2-pong threshold, 5s interval), `HashSet<Subscription>` state preserved across reconnects and auto-replayed. Minor: some method bodies are long (http.rs is 2482 lines — could be split). One `.unwrap()` in `Client::new` for reqwest builder (infallible in practice but stylistically unclean). |
| C5 | Maintenance | 4 | Active. v0.2.9 released; CHANGELOG shows regular Jan 2026 releases (v0.1.5→v0.2.x). New features landing (HIP-3, HIP-4 outcome markets, new WS channels). Single author (`Dario <dario@infinitefieldtrading.com>`) — bus-factor risk. MPL-2.0 is a reasonable license. |
| | **C average** | **4.4** | |

## D. Hyperliquid Integration (weight: 10%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| D1 | SDK usage | N/A | N/A (is the SDK) |
| D2 | Testnet support | 5 | First-class. `hypercore::testnet()`, `hypercore::testnet_ws()`, `testnet_url()`, `testnet_websocket_url()`. `Chain::Testnet` enum variant threaded through all signing (agent source `"b"` vs `"a"`, testnet chain ID `0x66eee` vs `0xa4b1`). No `#[cfg(feature = ...)]` gating — switching is a runtime choice, which is what we want. |
| D3 | HL features covered | 5 | HyperCore: perps, spot, orders (all TIF + trigger/stop), batch cancel/modify, cloids, schedule-cancel, leverage update, USDC/asset sends, EVM↔HL transfers, subaccounts, vaults, multisig, priority-fee auction, HIP-3 (multi-DEX perps), HIP-4 (outcome/prediction markets). HyperEVM: Morpho (APY queries, market/vault events), Uniswap V3 (pools created, prjx flows, price math). Multisig signature-collection protocol implemented end-to-end with both RMP-based and EIP-712-typed-data action routing (`multisig_collect_signatures` dispatches on `inner_action.typed_data_multisig(...)`). |
| | **D average (D2+D3)/2** | **5.0** | |

---

## Final Score

```
Final = (A_avg * 0.4) + (B_avg * 0.3) + (C_avg * 0.2) + (D_avg * 0.1)
      = (4.4  * 0.4) + (4.0  * 0.3) + (4.4  * 0.2) + (5.0  * 0.1)
      = 1.76 + 1.20 + 0.88 + 0.50
      = 4.34
```

## Verdict

- [x] >= 4.0: Strong candidate for testnet trials
- [ ] 3.0 - 3.9: Worth investigating, needs hardening
- [ ] 2.0 - 2.9: Reference only
- [ ] < 2.0: Avoid

## Summary

Mature, idiomatic, well-documented Rust SDK for Hyperliquid. API coverage matches or exceeds the official `hyperliquid-dex/hyperliquid-rust-sdk` on surface area (HIP-3, HIP-4, full multisig, EVM integrations). The EIP-712 signing path uses alloy's `SolStruct::eip712_signing_hash` — same wire format as the Python SDK — with signature-roundtrip unit tests validating exact bytes. Error handling and WebSocket design are of notably high quality. Primary risk is single-author bus factor, not code quality.

## Key Findings

### Strengths

- **Structured error type with retry classification.** `hypercore::Error` enum splits Network/Timeout/WebSocket (retryable) from Api/InvalidOrder/InvalidAddress/Signing (permanent). `is_retryable()` / `is_network_error()` / `is_api_error()` helpers. `ActionError<T>` preserves which order IDs failed in a batch. Directly addresses the anti-pattern we saw in Market Maker Novus (stringly-typed errors, no transient classification).
- **WebSocket resilience baked in.** `ws.rs` implements: exponential backoff with cap (500ms→5s), reset-on-success, missed-pong liveness detector (2 × 5s), state-preserving resubscription via `HashSet<Subscription>`, clean separation into `Connection` / `ConnectionHandle` / `ConnectionStream` so subs can be managed from a different task than the event loop. 5-second ping interval, 10-second connect timeout. Contrasts sharply with Market Maker Novus's bare reconnect loop.
- **Zero `unsafe`, zero production-path panics.** All `unwrap()` / `expect()` occurrences are either in `#[test]` modules, doctest examples, or on compile-time-constant `Url::parse` calls (infallible). The type system does the work: `rust_decimal::Decimal` for money, `alloy::Address` for keys/addresses, enums for order side / TIF / grouping / chain.
- **Type-safe EIP-712 via alloy.** `solidity::Agent` derives `SolStruct`; signing uses `signer.sign_typed_data(&agent, &CORE_MAINNET_EIP712_DOMAIN)`. Tests assert exact signature hex against known-good values and also verify `recover()` roundtrips — the kind of cross-check that would have caught signing bugs we saw elsewhere.
- **Key isolation at the trait boundary.** Signing methods take `&S: Signer` — the SDK never owns or sees raw key material. Example credentials loader supports keystore + password prompt, CLI arg, and env var, picking the safest available path.
- **First-class testnet.** Runtime `Chain` enum (not feature flag), with correct per-chain EIP-712 domain, agent source char, and chain ID. `hypercore::testnet()` is a one-liner.
- **Broad API coverage.** HIP-3 (multi-DEX), HIP-4 outcome markets, multisig w/ EIP-712 + RMP action dispatch, subaccounts, vaults, priority-fee auction, HyperEVM (Morpho, Uniswap V3). Explicit price-tick rounding (`PriceTick::round_by_side` with conservative/aggressive maker/taker semantics) is a nicety most SDKs omit.

### Concerns

- **Dual error types.** HTTP methods currently return `anyhow::Result<T>`, not `Result<T, hypercore::Error>`. The structured `Error` type exists and has great classification methods, but callers of the HTTP client have to downcast via `err.downcast_ref::<Error>()` to get at them. A consumer bot should wrap the client or wait for the (likely) migration to the structured error.
- **No `Cargo.lock` committed.** Library convention, but downstream consumers need to pin/`cargo update` carefully; transitive updates in alloy/reqwest could drift the signing path.
- **Single author / bus factor.** One maintainer (`dario@infinitefieldtrading.com`). 138 stars suggests a user base, but no multi-maintainer review.
- **Secret scanner false positives.** `secret-scan.json` flags 13 CRITICAL "private keys" — all are `abi/*.json` files where 64-char hex byte sequences appear inside Solidity ABI JSON. One real 64-hex value is a *throwaway test private key* in `signing.rs:228` (deliberately committed so signature-roundtrip tests are deterministic — standard practice, low risk). No production secrets present.
- **Niche WebSocket lib.** `yawc` is zero-copy and fast but less reviewed than `tokio-tungstenite`. For a long-lived production bot, a WS library swap is non-trivial.
- **No built-in metrics / tracing.** Only `log` facade. A production bot would want to wrap the client with its own `tracing` spans.
- **`Client::new` panics if reqwest builder fails** (`.unwrap()` on `reqwest::Client::builder().build()`). In practice infallible with this feature set, but not hygienic — a `try_new` variant would be safer.

### Recommendations

1. **Adopt this SDK (or the official HL Rust SDK) for any Rust-based bot work.** Against our custom-bot reference point, this is substantially above what we'd write from scratch and roughly on par with (arguably broader than) the official `hyperliquid-dex/hyperliquid-rust-sdk`. Either is viable; this one has stronger error-type design and more complete multisig + HIP-3/HIP-4 coverage. If risk-averse, go official; if surface-area-hungry, go infinitefield.
2. **Contrast with Market Maker Novus as a teaching case.** Novus had unchecked `unwrap()` in fill-parsing paths, stringly-typed errors, and a bare reconnect loop. This SDK shows the idiomatic Rust alternatives directly: structured `Error` enum w/ retry classification; `Option<Decimal>` return for fallible math; `HashSet<Subscription>` resubscribe state; missed-pong liveness. Good design reference for our own bot, even if we end up writing it in Python.
3. **For our custom bot design:** port three patterns explicitly — (a) the `is_retryable()` / `is_network_error()` / `is_api_error()` classification API on errors, (b) the state-preserving WS reconnect loop with ping/missed-pong liveness, (c) the `PriceTick::round_by_side(side, price, conservative)` abstraction for maker-vs-taker tick rounding. These are the three recurring bug classes across the bots we've reviewed.
4. **If using as-is:** wrap HTTP calls to convert `anyhow::Error` → `hypercore::Error` at the boundary so retry logic can consume the structured error; add your own `tracing` spans; supply your own min-notional check before calling `place()`.
