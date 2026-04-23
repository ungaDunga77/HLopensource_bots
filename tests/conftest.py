"""Shared pytest fixtures.

VCR harness adapted from the Hyperliquid Python SDK's test scaffolding
(MIT-licensed, see https://github.com/hyperliquid-dex/hyperliquid-python-sdk).
Vendored here with attribution per design notes §4 — cassettes live in
`tests/cassettes/` and replay HTTP for integration tests without hitting testnet.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
import vcr

CASSETTE_DIR = Path(__file__).parent / "cassettes"


@pytest.fixture
def vcr_cassette(request: pytest.FixtureRequest) -> Iterator[vcr.cassette.Cassette]:
    """Per-test VCR cassette named after the test function.

    Record mode: `once` — if the cassette file is missing, hits the network and
    writes it; if it exists, replays strictly (any new request raises).
    """
    name = f"{request.node.name}.yaml"
    my_vcr = vcr.VCR(
        cassette_library_dir=str(CASSETTE_DIR),
        record_mode="once",
        filter_headers=["authorization", "cookie"],
        filter_query_parameters=["signature"],
    )
    with my_vcr.use_cassette(name) as cassette:
        yield cassette
