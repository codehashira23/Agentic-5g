"""C060: Tests for the seeded RNG service."""
from __future__ import annotations

from app.infrastructure.rng.rng import RngService, RngStream


class TestRngStream:
    def test_random_in_range(self) -> None:
        s = RngStream(seed=42, tick=1)
        for _ in range(100):
            v = s.random()
            assert 0.0 <= v < 1.0

    def test_gauss_returns_float(self) -> None:
        s = RngStream(seed=42, tick=1)
        v = s.gauss(0.0, 1.0)
        assert isinstance(v, float)

    def test_uniform_in_range(self) -> None:
        s = RngStream(seed=42, tick=1)
        for _ in range(50):
            v = s.uniform(5.0, 10.0)
            assert 5.0 <= v < 10.0

    def test_same_seed_tick_same_sequence(self) -> None:
        s1 = RngStream(seed=42, tick=7)
        s2 = RngStream(seed=42, tick=7)
        assert [s1.random() for _ in range(10)] == [s2.random() for _ in range(10)]

    def test_different_ticks_different_sequences(self) -> None:
        s1 = RngStream(seed=42, tick=1)
        s2 = RngStream(seed=42, tick=2)
        vals1 = [s1.random() for _ in range(5)]
        vals2 = [s2.random() for _ in range(5)]
        assert vals1 != vals2

    def test_different_seeds_different_sequences(self) -> None:
        s1 = RngStream(seed=1, tick=1)
        s2 = RngStream(seed=2, tick=1)
        assert s1.random() != s2.random()

    def test_randint_in_range(self) -> None:
        s = RngStream(seed=42, tick=1)
        for _ in range(50):
            v = s.randint(0, 9)
            assert 0 <= v <= 9

    def test_choice_returns_element(self) -> None:
        s = RngStream(seed=42, tick=1)
        items = ["a", "b", "c"]
        assert s.choice(items) in items


class TestRngService:
    def test_default_seed(self) -> None:
        r = RngService()
        assert r.seed == 42

    def test_custom_seed(self) -> None:
        r = RngService(seed=7)
        assert r.seed == 7

    def test_for_tick_returns_stream(self) -> None:
        r = RngService(seed=42)
        s = r.for_tick(tick=1)
        assert isinstance(s, RngStream)

    def test_for_tick_deterministic(self) -> None:
        r = RngService(seed=42)
        v1 = r.for_tick(tick=5).random()
        v2 = r.for_tick(tick=5).random()
        assert v1 == v2

    def test_for_tick_independent_across_ticks(self) -> None:
        r = RngService(seed=42)
        v1 = r.for_tick(tick=1).random()
        v2 = r.for_tick(tick=2).random()
        assert v1 != v2

    def test_reseed_changes_output(self) -> None:
        r = RngService(seed=42)
        v_before = r.for_tick(tick=1).random()
        r.reseed(99)
        v_after = r.for_tick(tick=1).random()
        assert v_before != v_after

    def test_reseed_then_deterministic(self) -> None:
        r = RngService(seed=7)
        v1 = r.for_tick(tick=3).random()
        r.reseed(7)
        v2 = r.for_tick(tick=3).random()
        assert v1 == v2

    def test_satisfies_rng_port(self) -> None:
        from app.domain.agents.ports import Rng
        r = RngService(seed=42)
        assert isinstance(r, Rng)
