"""Forager-style pair selection (stub). Disabled in v0, wired in v1."""

from __future__ import annotations


class ForagerSelector:
    """Scanner side of scanner/executor split (senpi-skills pattern). v1."""

    def rank(self) -> list[str]:
        raise NotImplementedError("Forager disabled in v0")
