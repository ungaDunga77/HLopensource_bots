# Build Notes: Passivbot

**Date**: 2026-04-01

---

## Build System

- **Package manager**: pip (requirements.txt → includes live, full, dev, rust)
- **Python**: 3.12 (minimum, required by numba)
- **Rust**: Required for optimizer extension (passivbot-rust/, built via maturin)
- **Build command**: `pip install -r requirements.txt && cd passivbot-rust && maturin build --release && pip install target/wheels/*.whl && pip install -e .`
- **Run command**: `python src/main.py`

## Runtime Dependencies (live trading, 12 total)

| Package | Version | Purpose |
|---------|---------|---------|
| maturin | 1.5.1 | Rust extension builder |
| python-dateutil | 2.9.0.post0 | Date/time utilities |
| numba | 0.59.1 | JIT compiler (backtesting acceleration) |
| pandas | 2.2.2 | Data manipulation |
| numpy | 1.26.4 | Numerical computing |
| ccxt | 4.5.22 | Exchange API abstraction (7 exchanges) |
| hjson | 3.0.2 | Config file parser (JSON superset) |
| prettytable | 3.11.0 | CLI output formatting |
| sortedcontainers | 2.4.0 | Sorted data structures |
| portalocker | 3.2.0 | File locking |
| tqdm | 4.66.5 | Progress bars |
| openpyxl | 3.1.5 | Excel file support |

## Additional Dependencies (backtester/optimizer, 13 total)

matplotlib, colorama, pyecharts, deap (evolutionary algorithms), aiohttp, websockets, msgpack, plotly, dash, dash-bootstrap-components, psutil, requests, dictdiffer

## Dev Dependencies (5 total)

prospector, mkdocs, mkdocs-material, pymdown-extensions, PyYAML

## Rust Dependencies (10 total)

pyo3 0.21.2 (Python FFI), ndarray 0.15.6, numpy 0.21.0, memmap 0.7.0 (deprecated, use memmap2), serde 1.0 + serde_json 1.0, num_enum 0.7, strum 0.26, log 0.4

## Project Structure

```
passivbot/
├── src/                            # Python source (40 modules)
│   ├── main.py                     # Entry point
│   ├── passivbot.py                # Core bot logic (6,757 lines)
│   ├── config_utils.py             # Config loading/validation (3,019 lines)
│   ├── pure_funcs.py               # Pure calculation functions
│   ├── procedures.py               # Startup procedures, key loading
│   ├── logging_setup.py            # Log config with CCXT suppression
│   ├── rust_utils.py               # Rust build/import bridge
│   ├── custom_endpoint_overrides.py # URL rewriting system
│   ├── exchanges/                  # Exchange connectors
│   │   ├── ccxt_bot.py             # Base CCXT bot class
│   │   ├── hyperliquid.py          # Hyperliquid connector
│   │   ├── binance.py, bybit.py, bitget.py, okx.py, gateio.py, kucoin.py, paradex.py
│   │   └── (each exchange ~200-800 lines)
│   ├── backtest.py, optimize.py    # Backtester + optimizer
│   ├── optimization/               # Optimization utilities
│   ├── downloader.py               # Historical data fetcher
│   ├── fill_events_manager.py      # Trade fill tracking
│   └── tools/                      # CLI utilities
├── passivbot-rust/                 # Rust optimizer (cdylib via pyo3)
│   ├── Cargo.toml
│   └── src/                        # Rust source
├── configs/                        # Configuration templates
├── tests/                          # Test suite (78 files)
├── pytests/                        # Additional tests (2 files)
├── tests/exchanges/                # Exchange-specific tests (8 files)
├── docs/                           # MkDocs documentation
├── notebooks/                      # Jupyter analysis
├── scripts/                        # Utility scripts
├── api-keys.json.example           # Credential template
├── broker_codes.hjson              # Exchange affiliate codes
├── Dockerfile, Dockerfile_live     # Production Docker configs
└── docker-compose.yml              # Production compose
```

## Tests

**Result**: 851 passed, 22 failed, 118 skipped (991 collected from 88 test files)

- **Passed (851)**: Config validation, order logic, grid calculations, risk management (TWEL/WEL), fill events, exchange mocks, optimization, candlestick processing
- **Failed (22)**: All due to read-only filesystem in our Docker sandbox (`os.makedirs("caches")` in candlestick_manager.py). These would pass on a writable filesystem. Not actual test bugs.
- **Skipped (118)**: Tests requiring exchange connectivity or specific environment config
- **Rust extension**: Loads successfully (`import passivbot_rust` works)

**Test quality**: Good coverage of core trading logic. Tests use mocks for exchange interactions, asyncio for async code. Parametrized tests for edge cases. Notable test files:
- `test_twel_enforcer.py` — wallet exposure limit enforcement
- `test_entries_sizing.py` — position sizing validation
- `test_orchestrator_integration.py` — end-to-end with mock exchange
- `test_config_*.py` — 15+ config validation files

**CI**: GitHub Actions workflow exists but is a **no-op** (`run: 'true'`). Tests are not run in CI.

## Docker Build

- **Custom Dockerfile**: `sandbox/Dockerfile.passivbot` (Python 3.12 + Rust toolchain + maturin)
- **Build time**: ~5 minutes (Rust compilation is the bottleneck)
- **Image size**: ~2GB (includes Rust toolchain + all Python deps)
- **Security hardening**: Non-root user, read-only filesystem (via docker run flags)
- **Passivbot's own Dockerfiles**: Not used (designed for production, lack our security controls)

## Notes

- v7.8.5 (latest, installed from editable source)
- Rust extension builds cleanly via maturin
- All 12 live trading deps + 13 full deps installed without errors
- `memmap` 0.7.0 in Cargo.toml is deprecated (replaced by `memmap2` in the ecosystem), but functional
- HJSON used for config (JSON superset — more permissive parsing, supports comments)
- License: Unlicense (public domain)
- CLAUDE.md exists but delegates to AGENTS.md
