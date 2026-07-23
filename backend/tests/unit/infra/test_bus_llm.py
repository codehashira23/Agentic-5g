"""C065 + C066: Tests for the event bus and LLM client."""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from app.infrastructure.bus.bus import InProcessEventBus, Subscription
from app.infrastructure.llm.client import (
    FakeLLM,
    MissingFixtureError,
    ReplayClient,
    build_llm,
)


# ===========================================================================
# Event Bus (C065)
# ===========================================================================
class TestInProcessEventBus:
    def _make_event(self, event_type: str) -> object:
        class E:
            type = event_type
        return E()

    async def test_subscribe_and_publish(self) -> None:
        bus = InProcessEventBus()
        received: list[object] = []

        async def handler(e: object) -> None:
            received.append(e)

        sub = bus.subscribe(["NF_FAILED"], handler)
        event = self._make_event("NF_FAILED")
        await bus.publish(event)
        # Drain the subscriber queue directly
        while not sub.queue.empty():
            e = sub.queue.get_nowait()
            await handler(e)
        assert len(received) == 1

    async def test_type_filter_ignores_other_types(self) -> None:
        bus = InProcessEventBus()
        received: list[object] = []

        async def handler(e: object) -> None:
            received.append(e)

        bus.subscribe(["NF_FAILED"], handler)
        await bus.publish(self._make_event("KPI_UPDATED"))
        assert bus._subscriptions[0].queue.empty()

    async def test_empty_type_list_subscribes_all(self) -> None:
        bus = InProcessEventBus()
        received: list[object] = []

        async def handler(e: object) -> None:
            received.append(e)

        sub = bus.subscribe([], handler)
        await bus.publish(self._make_event("ANY_EVENT"))
        assert not sub.queue.empty()

    async def test_subscriber_count(self) -> None:
        bus = InProcessEventBus()
        async def h(e: object) -> None: ...
        bus.subscribe(["X"], h)
        bus.subscribe(["Y"], h)
        assert bus.subscriber_count == 2

    async def test_cancel_removes_subscription(self) -> None:
        bus = InProcessEventBus()
        async def h(e: object) -> None: ...
        sub = bus.subscribe(["X"], h)
        sub.cancel()
        await bus.publish(self._make_event("X"))
        assert sub.queue.empty()

    async def test_persist_fn_called_before_fanout(self) -> None:
        order: list[str] = []

        async def persist(e: object) -> None:
            order.append("persist")

        async def handler(e: object) -> None:
            order.append("handler")

        bus = InProcessEventBus(persist_fn=persist)
        sub = bus.subscribe([], handler)
        await bus.publish(self._make_event("X"))
        assert order[0] == "persist"

    async def test_drop_oldest_when_full(self) -> None:
        bus = InProcessEventBus()
        async def h(e: object) -> None: ...
        sub = bus.subscribe([], h, queue_size=2)
        for i in range(5):
            sub.offer(self._make_event(f"E{i}"))
        # Should have the 2 most recent events
        assert sub.queue.qsize() <= 2

    def test_satisfies_port(self) -> None:
        bus = InProcessEventBus()
        assert bus.satisfies_port()

    async def test_clear_subscriptions(self) -> None:
        bus = InProcessEventBus()
        async def h(e: object) -> None: ...
        bus.subscribe(["X"], h)
        bus.clear_subscriptions()
        assert bus.subscriber_count == 0


# ===========================================================================
# FakeLLM (C066)
# ===========================================================================
class TestFakeLLM:
    async def test_default_response(self) -> None:
        fake = FakeLLM()
        result = await fake.tool_call("sys", [], [])
        assert "rationale" in result

    async def test_set_response_returned_in_order(self) -> None:
        fake = FakeLLM()
        fake.set_response({"rationale": "first", "verdict": "pass"})
        fake.set_response({"rationale": "second", "verdict": "fail"})
        r1 = await fake.tool_call("s", [], [])
        r2 = await fake.tool_call("s", [], [])
        assert r1["verdict"] == "pass"
        assert r2["verdict"] == "fail"

    async def test_call_count_tracked(self) -> None:
        fake = FakeLLM()
        await fake.complete("s", [])
        await fake.tool_call("s", [], [])
        assert fake.call_count == 2

    def test_satisfies_port(self) -> None:
        fake = FakeLLM()
        assert fake.satisfies_port()


# ===========================================================================
# ReplayClient (C066)
# ===========================================================================
class TestReplayClient:
    async def test_missing_fixture_raises(self, tmp_path: Path) -> None:
        client = ReplayClient(fixtures_dir=tmp_path)
        with pytest.raises(MissingFixtureError):
            await client.tool_call("sys", [], [])

    async def test_save_and_load_fixture(self, tmp_path: Path) -> None:
        client = ReplayClient(fixtures_dir=tmp_path)
        response = {"rationale": "deployed", "status": "ok"}
        key = client._hash("sys", [], [], "")
        client.save_fixture(key, response)
        loaded = await client.tool_call("sys", [], [])
        assert loaded["rationale"] == "deployed"

    async def test_same_inputs_same_hash(self, tmp_path: Path) -> None:
        client = ReplayClient(fixtures_dir=tmp_path)
        h1 = client._hash("sys", [{"role": "user", "content": "hi"}], [], "model")
        h2 = client._hash("sys", [{"role": "user", "content": "hi"}], [], "model")
        assert h1 == h2

    async def test_different_inputs_different_hash(self, tmp_path: Path) -> None:
        client = ReplayClient(fixtures_dir=tmp_path)
        h1 = client._hash("sys_a", [], [], "")
        h2 = client._hash("sys_b", [], [], "")
        assert h1 != h2

    def test_satisfies_port(self, tmp_path: Path) -> None:
        client = ReplayClient(fixtures_dir=tmp_path)
        assert client.satisfies_port()


class TestBuildLLM:
    def test_build_fake(self) -> None:
        llm = build_llm(mode="fake")
        assert isinstance(llm, FakeLLM)

    def test_build_replay(self, tmp_path: Path) -> None:
        llm = build_llm(mode="replay", fixtures_dir=tmp_path)
        assert isinstance(llm, ReplayClient)

    def test_build_default_is_replay(self, tmp_path: Path) -> None:
        llm = build_llm(fixtures_dir=tmp_path)
        assert isinstance(llm, ReplayClient)
