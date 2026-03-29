# Build Notes: hyperliquid-python-sdk

**Date**: 2026-03-29

---

## Build System

- **Package manager**: Poetry (pyproject.toml + poetry.lock)
- **Python**: ^3.9 (supports 3.9 through 3.13)
- **Build backend**: `poetry.core.masonry.api`

## Runtime Dependencies (5 total)

| Package | Version Range | Purpose |
|---------|---------------|---------|
| eth-utils | >=2.1.0,<6.0.0 | Ethereum utility functions (keccak, hex) |
| eth-account | >=0.10.0,<0.14.0 | EIP-712 signing, account management |
| websocket-client | ^1.5.1 | WebSocket subscriptions |
| requests | ^2.31.0 | HTTP REST API calls |
| msgpack | ^1.0.5 | Action serialization for hashing |

Minimal, focused dependency tree. All well-established libraries.

## Dev Dependencies

pytest, pytest-recording (VCR cassettes), mypy, pre-commit, safety, coverage, pytest-cov, vcrpy, types-requests, lz4.

## CI/CD

- `.github/workflows/ci.yml` — test runner
- `.github/workflows/lint.yml` — linting
- `.pre-commit-config.yaml` — pre-commit hooks

## Test Suite

- `tests/signing_test.py` — signature generation/verification test vectors
- `tests/info_test.py` — API info endpoint tests using VCR cassettes (recorded HTTP responses)
- Test framework: pytest with `--record-mode=once` (VCR)
- Coverage configured: `--cov=hyperliquid`

## Docker Build

Not attempted in Docker sandbox — this is a library SDK, not an executable bot. It doesn't have a Dockerfile or entrypoint. The SDK is installed as a pip dependency by bots that use it.

To test install:
```bash
pip install hyperliquid-python-sdk  # from PyPI
# or
pip install -e .  # from cloned source
```

## Notes

- No Dockerfile needed — this is a library, not a standalone application
- Poetry lockfile is committed, ensuring reproducible installs
- The `Makefile` likely has targets for lint/test/build (standard Poetry project)
