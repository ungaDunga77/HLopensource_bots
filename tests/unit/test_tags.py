from __future__ import annotations

from osbot.strategy.tags import OrderIntent, OrderIntentTracker, OrderTag


def test_cloid_is_0x_prefixed_32_hex_chars() -> None:
    tag = OrderTag(strategy_id=1, intent=OrderIntent.OPEN_GRID, level=3)
    cloid = tag.to_cloid()
    assert cloid.startswith("0x")
    assert len(cloid) == 2 + 32
    int(cloid, 16)


def test_cloids_are_unique_across_calls() -> None:
    tag = OrderTag(strategy_id=1, intent=OrderIntent.OPEN_GRID, level=0)
    cloids = {tag.to_cloid() for _ in range(100)}
    assert len(cloids) == 100


def test_tracker_roundtrip() -> None:
    t = OrderIntentTracker()
    t.register("local-1", "0xabc")
    t.bind_oid("0xabc", "oid-42")
    assert t.local_to_cloid["local-1"] == "0xabc"
    assert t.cloid_to_oid["0xabc"] == "oid-42"
    assert t.oid_to_cloid["oid-42"] == "0xabc"
    t.forget("0xabc")
    assert "0xabc" not in t.cloid_to_local
    assert "local-1" not in t.local_to_cloid
    assert "oid-42" not in t.oid_to_cloid
