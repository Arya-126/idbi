"""Sector peer benchmarks.

We rescore every persona in the portfolio once at startup and cache the
per-dimension score distributions per sector. When we score a new (or
recompute an existing) health card, `percentile(sector, dim_key, score)`
answers: "of the peers in this sector, what fraction score at or below this
value?" — which the UI renders as a "Top X% in sector" chip.

If a sector has fewer than 4 peers we return None instead of an unreliable
percentile — better to show nothing than false precision.
"""

from __future__ import annotations

import bisect
from dataclasses import dataclass, field


_MIN_PEERS = 4


@dataclass
class SectorBenchmarks:
    # sector → dim_key → sorted list of scores
    by_sector: dict[str, dict[str, list[int]]] = field(default_factory=dict)

    def register(self, sector: str, dim_scores: dict[str, int]) -> None:
        for dim_key, score in dim_scores.items():
            per_sector = self.by_sector.setdefault(sector, {})
            bisect.insort(per_sector.setdefault(dim_key, []), score)

    def percentile(self, sector: str, dim_key: str, score: int) -> int | None:
        sector_data = self.by_sector.get(sector, {})
        peers = sector_data.get(dim_key, [])
        if len(peers) < _MIN_PEERS:
            return None
        # Fraction of peers ≤ this score. bisect_right gives the count of
        # entries ≤ score when the list is sorted ascending.
        pos = bisect.bisect_right(peers, score)
        pct = round(pos / len(peers) * 100)
        return max(0, min(100, pct))


_BENCHMARKS: SectorBenchmarks | None = None


def _build_benchmarks() -> SectorBenchmarks:
    """Score every registered persona once and index by (sector, dim)."""
    # Deferred imports so this module doesn't force scoring/portfolio at import time.
    from .. import personas as personas_mod
    from ..portfolio import build_portfolio
    from .engine import score_gstin

    build_portfolio()  # ensure sampled personas are registered

    bench = SectorBenchmarks()
    for persona in personas_mod.PERSONAS_BY_GSTIN.values():
        # Use benchmark=False so this call doesn't recurse into itself.
        card = score_gstin(persona.gstin, benchmark=False)
        bench.register(
            persona.sector,
            {d.key: d.score for d in card.dimensions},
        )
    return bench


def get_benchmarks() -> SectorBenchmarks:
    global _BENCHMARKS
    if _BENCHMARKS is None:
        _BENCHMARKS = _build_benchmarks()
    return _BENCHMARKS


def invalidate() -> None:
    global _BENCHMARKS
    _BENCHMARKS = None
