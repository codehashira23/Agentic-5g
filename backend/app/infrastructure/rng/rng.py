"""
Infrastructure: Seeded RNG service — the sole entropy source (GR4 / TP2).

Implements the Rng port (domain/agents/ports.py).
All randomness in the system flows through here.

Design:
  - A global seed is set once at startup (or on simulation reset).
  - Each simulation tick derives an INDEPENDENT per-tick RngStream from
    hash(seed, tick) so streams are reproducible yet non-overlapping.
  - The RngStream wraps Python's Random with a derived seed, giving
    reproducible .random(), .gauss(), .uniform() calls.

Owning docs: 06-digital-twin.md §13, 10-backend.md §8.5
"""
from __future__ import annotations

import random as _random
from typing import Any


# ---------------------------------------------------------------------------
# RngStream — one per tick, derived from (seed, tick)
# ---------------------------------------------------------------------------
class RngStream:
    """
    A deterministic random stream for one simulation tick.
    Created by RngService.for_tick(); never shared across ticks.
    """

    def __init__(self, seed: int, tick: int) -> None:
        # Derive a stable, unique integer seed from (seed, tick)
        # using Python's built-in hash with a fixed mixing constant.
        derived = seed ^ (tick * 2_654_435_761)  # Knuth multiplicative hash
        derived = (derived + 0x9E3779B9) & 0xFFFF_FFFF
        self._rng = _random.Random(derived)

    def random(self) -> float:
        """Return a float in [0.0, 1.0)."""
        return self._rng.random()

    def gauss(self, mu: float, sigma: float) -> float:
        """Return a Gaussian sample."""
        return self._rng.gauss(mu, sigma)

    def uniform(self, lo: float, hi: float) -> float:
        """Return a uniform sample in [lo, hi)."""
        return self._rng.uniform(lo, hi)

    def randint(self, a: int, b: int) -> int:
        """Return a random integer N such that a <= N <= b."""
        return self._rng.randint(a, b)

    def choice(self, seq: list[Any]) -> Any:
        """Return a random element from a non-empty sequence."""
        return self._rng.choice(seq)


# ---------------------------------------------------------------------------
# RngService — the Rng port implementation
# ---------------------------------------------------------------------------
class RngService:
    """
    Seeded RNG service. Implements the Rng domain port.

    Usage:
        rng = RngService(seed=42)
        stream = rng.for_tick(tick=5)
        value = stream.random()   # deterministic for (seed=42, tick=5)

    Reseed on simulation reset:
        rng.reseed(new_seed)
    """

    def __init__(self, seed: int = 42) -> None:
        self._seed = seed

    @property
    def seed(self) -> int:
        return self._seed

    def for_tick(self, tick: int) -> RngStream:
        """
        Return a per-tick RngStream derived from (seed, tick).
        Same (seed, tick) always produces the same stream (TP2).
        """
        return RngStream(seed=self._seed, tick=tick)

    def reseed(self, seed: int) -> None:
        """Replace the global seed (called on simulation reset)."""
        self._seed = seed
