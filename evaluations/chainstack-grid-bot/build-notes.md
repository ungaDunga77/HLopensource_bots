# Build Notes: Chainstack Grid Bot

**Date**: 2026-03-29

---

## Build System

- **Package manager**: uv (pyproject.toml + uv.lock)
- **Python**: 3.13 (.python-version)
- **Build command**: `uv sync`
- **Run command**: `uv run src/run_bot.py [config.yaml]`

## Runtime Dependencies (8 total)

| Package | Version | Purpose |
|---------|---------|---------|
| hyperliquid-python-sdk | >=0.20.0 | Official HL SDK (REST + signing) |
| eth-account | >=0.10.0 | Ethereum wallet/signing |
| pyyaml | >=6.0 | YAML config parsing |
| typing-extensions | >=4.0 | Type hint backports |
| psutil | >=7.0.0 | System resource monitoring |
| httpx | >=0.28.1 | HTTP client (endpoint health checks) |
| python-dotenv | >=1.1.1 | .env file loading |
| websockets | >=15.0.1 | WebSocket market data feed |

## Project Structure

Clean SOLID architecture:
- `src/interfaces/` — abstract contracts (ExchangeAdapter, TradingStrategy)
- `src/exchanges/hyperliquid/` — HL-specific adapter implementation
- `src/strategies/grid/` — grid trading logic
- `src/core/` — engine, config, key management, risk management, endpoint routing
- `src/utils/` — events, exceptions
- `learning_examples/` — standalone educational scripts (6 categories)
- `bots/` — YAML bot configs

## Tests

No test suite. No pytest config. The bot's CLAUDE.md mentions "test driven development" and "testing requirements" but no tests exist in the repo.

## Docker Build

Not attempted — will use our sandbox Dockerfile.python. The bot has no Dockerfile of its own.

## Notes

- Uses `uv` instead of pip/poetry — our audit_deps.py flagged for manual review (pyproject.toml, not requirements.txt)
- The `learning_examples/` directory is a nice addition — 15+ standalone scripts teaching HL API usage
- `AGENTS.md` and `CLAUDE.md` present — this repo was partly built with AI assistance
- License: Apache-2.0
