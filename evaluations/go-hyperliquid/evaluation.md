# Evaluation: go-hyperliquid (Unofficial Go SDK)

**Repo**: https://github.com/sonirico/go-hyperliquid
**Evaluator**: Claude (automated)
**Date**: 2026-04-19
**Tier**: Reference / infra axis (not a bot, not official)
**Stars**: 106 | **License**: MIT

---

## Rubric Adaptation (SDK, not a bot)

This is a Go client library, not a trading bot. The standard rubric assumes a bot; we adapt as follows:

- **A1 Key management** — scored on how the SDK *expects* callers to pass keys, and whether it leaks them.
- **B1 Strategy clarity** — replaced by **API coverage** (REST + WS surface).
- **B2 Backtesting** — **N/A**, excluded from average.
- **B3 Risk management** — **N/A** (delegated to caller), excluded from average.
- **D1 SDK usage** — **N/A** (this *is* the SDK), excluded from average.

Averages are computed over scored sub-criteria only (N/A dropped, consistent with the Python SDK baseline eval).

---

## A. Security (weight: 40%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| A1 | Key management | 4 | Key passed in as `*ecdsa.PrivateKey` via `crypto.HexToECDSA` — never read from disk by the SDK itself, never logged, never sent on the wire (only r/s/v derived via `go-ethereum/crypto.Sign`). Pluggable `L1ActionSigner`/`UserSignedActionSigner`/`AgentSigner` interfaces (`opt.go:88-107`) mean callers can keep the key in an HSM/KMS and never hand raw bytes to the SDK — better design than the Python SDK for production hardening. Not 5 because example code in README embeds `crypto.HexToECDSA("your-private-key")` with no keystore/encrypted-file helper. |
| A2 | Dependency hygiene | 3 | `go.mod` pins Go 1.25.3 and has 11 direct deps, all reputable (`go-ethereum`, `gorilla/websocket`, `vmihailenco/msgpack`, `mailru/easyjson`, `valyala/fastjson`). `audit_deps.py` found no Go manifest support (tool gap — findings: `{"languages": [], "vulnerability_count": 0}`). Manual review: transitive deps pull in `gnark-crypto`, `ProjectZKM/Ziren` (zk runtime, via go-ethereum), `blst` — large surface via go-ethereum but unavoidable for EIP-712. Two `sonirico/vago*` packages are author-owned utility libs (supply-chain consideration). No `govulncheck` artifact checked in. |
| A3 | Network surface | 4 | Three hardcoded URLs: `MainnetAPIURL`, `TestnetAPIURL`, `LocalAPIURL` (`client.go:18-20`). WS client whitelists only `api.hyperliquid.xyz` and `api.hyperliquid-testnet.xyz` for automatic `wss://...ws/` path rewriting (`ws.go:55-74`) — any other host forces callers to supply a full ws URI. No telemetry. Custom `http.Client` injection supported. |
| A4 | Code transparency | 5 | All source Go, readable. MIT license. No obfuscation. Large generated files (`*_easyjson.go`) are standard codegen, not obfuscation. Public `go-ethereum`, `gorilla/websocket` upstream. No SECURITY.md though. |
| A5 | Input validation | 3 | `actionHash` rejects negative nonces and `expiresAfter` via panic (`signing.go:334,351`). `SignAgent` rejects negative nonce (returns error). `hashStructLenient` does careful typed conversion for `uint64` fields (handles `int64`, `float64`, `json.Number`, string). No client-side order-size / notional bounds. No rate-limit primitive. Secret scan found 3 CRITICAL hits — all were false positives (tx hashes and VCR fixtures misidentified as private keys) plus an `.env.testnet` containing what *looks* like a leaked 64-hex testnet key — worth confirming it's not live. |
| | **A average** | **3.8** | |

## B. Functionality (weight: 30%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| B1 | API coverage (adapted) | 5 | 57 `Exchange` methods across orders/cancels/others (bulk orders, modify, schedule-cancel, TPSL, market-open/close with slippage, leverage, isolated margin, vault transfers, USD/spot/class transfers, bridge withdraw, agent approval, builder fees, big blocks, spot deploy, perp deploy, validator ops, multi-sig, token delegation, sub-accounts, referral). 14 WS subscription types (trades, l2Book, candles, allMids, bbo, activeAssetCtx, webData2/3, clearinghouseState, openOrders, userFills, orderUpdates, notification, twapStates). README claims full Python SDK parity — consistent with what's in the tree. |
| B2 | Backtesting | N/A | SDK |
| B3 | Risk management | N/A | SDK (delegated) |
| B4 | Configurability | 5 | Clean functional-options pattern throughout (`opt.go`): `ClientOpt`, `ExchangeOpt`, `InfoOpt`, `WsOpt` via generic `Opt[T any]`. Options: debug mode, custom `http.Client`, custom `websocket.Dialer`, ws read timeout, perp dex name, and — notably — `ExchangeOptL1Signer`/`ExchangeOptUserSignedSigner`/`ExchangeOptAgentSigner` for pluggable signing backends (HSM/KMS-friendly). `.env.testnet` + `godotenv` dep suggests env-file convention in examples. Testnet is per-constructor (baseURL), not per-call — same as Python SDK. |
| B5 | Observability | 3 | Uses `sonirico/vago/lol` structured logger with zerolog backend (`WithLevel`, `WithEnv`, structured `Fields`). Debug mode on client/exchange/info/ws logs full requests + responses. No metrics/tracing hooks, no built-in Prometheus, no OpenTelemetry. `Exchange.executeAction` has no hooks for latency measurement — callers would have to wrap the HTTP client. |
| | **B average** | **4.33** | (B1+B4+B5 / 3) |

## C. Engineering Quality (weight: 20%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| C1 | Tests | 4 | 15 `*_test.go` files in root + 10 example tests. `signing_test.go` has explicit cross-language test vectors (hex strings comparing Go output to Python SDK output). VCR-style cassettes in `testdata/*.yaml` (50+ YAML fixtures) via `go-vcr/v4`. `types_msgpack_order_test.go` + `types_msgpack_test.go` specifically verify Python-compatible msgpack wire format. Coveralls badge in README. No live-integration test runner in CI. |
| C2 | Error handling | 3 | Typed `APIError` (code + msg) and `ValidationError` returned from `client.post` (`client.go:99-108`). `IsWalletDoesNotExistError` helper for one known recoverable class. **Gap vs our design goal**: no distinction between transient (429/5xx/net) and structural (4xx) errors, no retry/backoff primitive on the REST client. WS reconnect does exist (exponential backoff capped at 1 min, `ws.go:335-353`) — good. Some paths `panic` on encoding failures (`actionHash` for marshal errors or negative nonce) — questionable for a library. |
| C3 | Documentation | 3 | README has quick-start + feature checklist + roadmap. Godoc comments on exported funcs (most of them). `CONTRIBUTING.md` exists. `examples/` directory with WS and order examples. No dedicated docs site beyond pkg.go.dev. |
| C4 | Code quality | 4 | Idiomatic Go: functional options, interface-based signer injection, `context.Context` plumbed through all blocking ops, `sync.RWMutex` + `atomic.Int64` for WS state, `closeOnce` on shutdown. `easyjson`-generated marshalers for hot JSON paths, `msgpack/v5` + `fastjson` + `vmihailenco/msgpack`. Makefile with `ci-full`, `ci-test`, `install-tools`. Go Report Card badge. Some low-quality smells: `println`/commented debug blocks scattered in `exchange.go` and `signing.go`, and `NewWebsocketClient` calls `log.Fatalf` on a bad URL (bad for a library). |
| C5 | Maintenance | 3 | 1 primary contributor (sonirico / "Marquitos") with ~20 secondary contributors listed. CI workflows + coveralls. **Caveat**: the cloned repo shows a single squashed commit on this checkout, so history depth is hard to judge locally — README mentions ongoing work. 106 stars modest but growing. Last commit on our clone is 2026-04-07 (12 days old) — active. Open question: bus factor of 1 primary author. |
| | **C average** | **3.4** | |

## D. Hyperliquid Integration (weight: 10%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| D1 | SDK usage | N/A | This IS the SDK |
| D2 | Testnet support | 4 | `TestnetAPIURL` constant; `isMainnet` derived from `client.baseURL == MainnetAPIURL` inside `executeAction` (`exchange.go:160`). Defaults to mainnet if no baseURL given (`client.go:34-36`) — same safety issue as Python SDK. `signatureChainId` `0x66eee` and hardcoded signing chainId `1337` / `421614` match Python SDK exactly. Testnet vs mainnet is a per-client setting, not per-call — fine for separation, no risk of mixing. |
| D3 | HL features | 5 | Full coverage: perps, spot, vaults, subaccounts, agent approval, builder fees (approve + routing), multi-sig, TPSL (native trigger orders), schedule-cancel, big blocks, staking/token delegation, USD/spot/class transfers, bridge withdraw, HIP-3 perp deploy (`PerpDeploy*` fixtures in testdata), spot deploy, validator/consensus layer. Matches Python SDK feature-for-feature per README, confirmed by file listing. |
| | **D average** | **4.5** | (D2+D3 / 2) |

---

## Final Score

```
Final = (A_avg * 0.4) + (B_avg * 0.3) + (C_avg * 0.2) + (D_avg * 0.1)
      = (3.8   * 0.4) + (4.33  * 0.3) + (3.4   * 0.2) + (4.5   * 0.1)
      = 1.52  + 1.30  + 0.68  + 0.45
      = 3.95
```

## Verdict

- [ ] >= 4.0: Strong candidate for testnet trials
- [x] 3.0 - 3.9: Worth investigating, needs hardening (just below 4.0)
- [ ] 2.0 - 2.9: Reference only
- [ ] < 2.0: Avoid

Scores 0.22 above the Python SDK baseline (3.73). Higher B from clean options/pluggable signer, higher D from parity, roughly equal A/C. Borderline strong candidate — the missing 0.05 is entirely from no retry primitive and a 1-author maintenance risk.

## Summary

Well-engineered unofficial Go port of the Python SDK. Signing implementation is unusually careful: explicit msgpack str16→str8 conversion (`signing.go:33-257`) with a structure-aware walker to avoid corrupting non-string bytes that happen to contain `0xda`, and `hashStructLenient` that filters extra fields to match Python's `eth_account` behavior. Cross-language test vectors in `signing_test.go` guard against drift. WebSocket has real reconnect + exponential backoff + read-timeout + ping loop — strictly better than the Python SDK's daemon-thread approach. Pluggable signer interfaces open the door to HSM/KMS without forking. API coverage matches Python SDK.

## Key Findings

### Strengths
- **Signing parity work is exceptional** — commented references to Python behavior, msgpack str16→str8 converter, `hashStructLenient` for EIP-712 field filtering. This is the *best* artifact for understanding HL wire-format edge cases the Python SDK's dynamism hides.
- **WS has production patterns the Python SDK lacks**: 50s ping, 90s read-deadline (exceeds ping so pongs don't false-timeout), exponential backoff reconnect capped at 60s, automatic resubscribe on reconnect, thread-safe subscriber registry with `uniqSubscriber` dedup.
- **Pluggable signer interfaces** (`L1ActionSigner`/`UserSignedActionSigner`/`AgentSigner`) — cleanest HSM/KMS integration path of any HL SDK we've looked at.
- Functional options generics (`Opt[T any]`) — tidy, ergonomic, trivially composable.
- Typed `APIError`, structured logging via `vago/lol`, `context.Context` everywhere.

### Concerns
- No retry/backoff primitive on REST client — transient 5xx/429 surface directly to caller. We'd have to add our own.
- No structural-vs-transient error classification (only `IsWalletDoesNotExistError`). Matches our known design gap; we'd still need to build a classifier.
- `NewWebsocketClient` `log.Fatalf` on bad URL — library killing the process is wrong, should return error.
- Some `panic` in signing paths on encoding failure / negative nonce — acceptable but brittle.
- Defaults to **mainnet** when baseURL empty (`client.go:34-36`) — same footgun as Python SDK.
- **Bus factor ≈ 1** (sonirico is primary, others drive-by). Must judge long-term maintenance against that.
- `.env.testnet` in-repo contains a 64-char hex string (`HL_PRIVATE_KEY=a002...3699`) — should be confirmed to be a burner testnet key and ideally moved to `.env.testnet.example`.
- Dep audit tool has no Go support — manual review only; no automated `govulncheck` in CI.

### Recommendations
- **For our v1+ custom bot**: Go is a reasonable port target — the reconnect and signer-injection patterns here are directly reusable. However, latency wins from Go are marginal against what we've seen as HL's actual tail (WS drops ~1/10min on testnet, REST ~50-150ms). Don't port for performance; port only if the team prefers Go ergonomically.
- **Immediate use**: read `signing.go` as the canonical reference for msgpack+EIP-712 wire format. The `convertStr16ToStr8` walker and the `hashStructLenient` helper are gotchas our Python-based bot would never encounter but would silently break on if we ever handcraft a signature.
- **Reuse patterns from ws.go**: the `pingInterval < readTimeout` invariant and exponential-backoff reconnect should anchor our own WS layer.
- If we adopt this SDK, wrap it: add retry middleware on `client.post`, add transient/structural error classifier, default baseURL to testnet, replace `log.Fatalf` paths, and pass our own `L1ActionSigner` backed by whatever key storage we land on.
