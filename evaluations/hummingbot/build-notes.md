# Build Notes: Hummingbot (HL Connector)

**Date**: 2026-04-01

---

## Build System

- **Package manager**: Conda (`setup/environment.yml`) + pip (`setup/pip_packages.txt`) + setuptools (`setup.py`)
- **Python**: 3.13 (via Conda)
- **Cython**: Required for core framework classes (order book, clock, strategy base, etc.)
- **Build command**: `conda env create -f setup/environment.yml && conda run -n hummingbot python setup.py build_ext --inplace -j 8`
- **Docker base**: `continuumio/miniconda3:latest`
- **Custom Dockerfile**: `sandbox/Dockerfile.hummingbot` (created for this evaluation)

## HL Connector Dependencies (6 direct)

| Package | Version | Purpose |
|---------|---------|---------|
| eth-account | >=0.13.0 | EIP-712 signing, `Account.from_key()` |
| msgpack-python | (unpinned) | Action hash serialization |
| aiohttp | >=3.8.5 | HTTP REST + WebSocket (via platform) |
| pydantic | >=2 | Config validation, SecretStr |
| cryptography | >=41.0.2 | Crypto primitives (via eth-account) |
| safe-pysha3 | (unpinned) | Keccak hashing (via eth_utils) |

## Platform Dependencies (34 total install_requires)

Notable platform-only deps not needed for HL:
- `injective-py` (Injective chain connector)
- `xrpl-py>=4.4.0` (XRPL connector)
- `web3` (EVM gateway connectors)
- `bip-utils` (HD wallet derivation)
- `numba>=0.61.2` (JIT compilation for strategies)
- `TA-Lib>=0.6.4` (technical analysis, requires C library)
- `scipy>=1.11.1` (numerical optimization)

Pinning style: version ranges (`>=`), not exact pins. Resolution depends on Conda solver.

## Project Structure (HL Connector Only)

```
hummingbot/connector/
├── exchange/hyperliquid/              # Spot connector (9 files, 824 lines exchange class)
│   ├── __init__.py
│   ├── hyperliquid_auth.py            # EIP-712 signing + NonceManager (300 lines)
│   ├── hyperliquid_constants.py       # Endpoints, rate limits (104 lines)
│   ├── hyperliquid_exchange.py        # Main exchange class (824 lines)
│   ├── hyperliquid_utils.py           # Config maps + SecretStr (209 lines)
│   ├── hyperliquid_web_utils.py       # URL builders, wire formatting (164 lines)
│   ├── hyperliquid_api_order_book_data_source.py
│   ├── hyperliquid_api_user_stream_data_source.py
│   └── hyperliquid_order_book.py
│
└── derivative/hyperliquid_perpetual/  # Perp connector (11 files, 1234 lines derivative class)
    ├── __init__.py
    ├── dummy.pxd                      # Empty Cython stub (2 lines)
    ├── dummy.pyx                      # Empty Cython stub (2 lines)
    ├── hyperliquid_perpetual_auth.py  # EIP-712 signing, no NonceManager (204 lines)
    ├── hyperliquid_perpetual_constants.py  # Endpoints, rate limits (126 lines)
    ├── hyperliquid_perpetual_derivative.py # Main derivative class + HIP-3 (1234 lines)
    ├── hyperliquid_perpetual_utils.py      # Config maps + SecretStr (209 lines)
    ├── hyperliquid_perpetual_web_utils.py  # URL builders, wire formatting (164 lines)
    ├── hyperliquid_perpetual_api_order_book_data_source.py
    └── hyperliquid_perpetual_user_stream_data_source.py

Also relevant:
├── core/rate_oracle/sources/          # HL rate oracle sources (2 files)
└── data_feed/candles_feed/            # HL candle feeds (spot + perp, 6 files)
```

Total HL source: ~2,058 lines in exchange classes + ~1,600 lines in supporting files = ~3,660 lines.
Full Hummingbot codebase: 562 MB, ~100k+ lines. HL connector is <1% of codebase.

## Test Results

**274 tests, 274 passed, 0 failed, 4 warnings, 9.15 seconds**

| Test File | Tests | Status |
|-----------|-------|--------|
| `test_hyperliquid_exchange.py` | ~50 | All pass |
| `test_hyperliquid_auth.py` | ~5 | All pass |
| `test_hyperliquid_api_order_book_data_source.py` | ~15 | All pass |
| `test_hyperliquid_user_stream_data_source.py` | ~5 | All pass |
| `test_hyperliquid_utils.py` | ~5 | All pass |
| `test_hyperliquid_web_utils.py` | ~3 | All pass |
| `test_hyperliquid_order_book.py` | ~3 | All pass |
| `test_hyperliquid_perpetual_derivative.py` | ~170 | All pass |
| `test_hyperliquid_perpetual_auth.py` | ~3 | All pass |
| `test_hyperliquid_perpetual_api_order_book_data_source.py` | ~15 | All pass |
| `test_hyperliquid_perpetual_user_stream_data_source.py` | ~5 | All pass |
| `test_hyperliquid_perpetual_utils.py` | ~15 | All pass |
| `test_hyperliquid_perpetual_web_utils.py` | ~5 | All pass |

Perp connector has significantly more tests (especially `test_hyperliquid_perpetual_derivative.py` at 3,565 lines) covering HIP-3 markets, leverage, positions, trading rules.

Warnings: 4 — all Pydantic deprecation warnings from unrelated foxbit connector and a test loop deprecation. No HL-related warnings.

## Docker Build

- **Dockerfile**: `sandbox/Dockerfile.hummingbot` (custom, based on Hummingbot's own Dockerfile)
- **Base**: `continuumio/miniconda3:latest`
- **Build steps**: apt deps → Conda env create → pip packages → copy source → Cython build → copy tests → non-root user
- **Build time**: ~8-10 minutes (Conda solve + Cython compilation dominant)
- **Image size**: ~3-4 GB (Conda + full platform dependencies)
- **Test execution**: `--network=none --tmpfs /tmp --memory=2g`
- **Security**: non-root `botuser`, network isolation, tmpfs for writes
