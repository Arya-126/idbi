"""Observed score snapshots — the honest half of the score-history chart.

Every real card issuance records (gstin, period, composite, band) to a small
JSON file. `_score_history` then overlays these OBSERVED points on top of its
reconstructed approximation, so a firm that has actually been scored twice —
including via the "simulate next month" control — shows real history where it
exists and clearly-approximated history where it doesn't.

File-backed (gitignored) so history survives restarts; production would use a
proper store keyed by scoring runs.
"""

from __future__ import annotations

import json
from pathlib import Path
from threading import Lock

_PATH = Path(__file__).resolve().parent.parent / ".snapshots.json"
_lock = Lock()

# {gstin: {"YYYY-MM": {"score": int, "band": "A"}}}
_data: dict[str, dict[str, dict]] = {}
_loaded = False


def _load() -> None:
    global _data, _loaded
    if _loaded:
        return
    try:
        _data = json.loads(_PATH.read_text(encoding="utf-8"))
    except Exception:
        _data = {}
    _loaded = True


def record(gstin: str, period: str, score: int, band: str) -> None:
    """Upsert one observed point. Same gstin+period overwrites (re-score)."""
    with _lock:
        _load()
        _data.setdefault(gstin, {})[period] = {"score": score, "band": band}
        try:
            _PATH.write_text(json.dumps(_data, indent=0), encoding="utf-8")
        except Exception:
            pass  # persistence is best-effort, never a scoring blocker


def observed(gstin: str) -> dict[str, tuple[int, str]]:
    """period → (score, band) for every observed point of this firm."""
    with _lock:
        _load()
        return {
            p: (v["score"], v["band"]) for p, v in _data.get(gstin, {}).items()
        }
