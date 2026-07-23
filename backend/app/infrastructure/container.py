"""
DI Container — the single composition root.

Constructs all infrastructure adapters and application services,
binding domain ports to concrete implementations.
Nothing outside this module should construct adapters directly.

Owning docs: 10-backend.md §7, 03-architecture.md ADR-6
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.application.agents.orchestrator import AgentOrchestrator
from app.application.sel.invoker import ServiceInvoker
from app.application.sel.policy_engine import PolicyEngine
from app.application.sel.registry import ServiceRegistry
from app.application.sel.services.catalog import get_catalog
from app.application.twin_service.scenarios import build_twin_from_scenario
from app.application.twin_service.service import TwinService
from app.application.workflow.engine import WorkflowEngine
from app.infrastructure.bus.bus import InProcessEventBus
from app.infrastructure.db.engine import Database
from app.infrastructure.db.seed import seed as run_seed
from app.infrastructure.llm.client import build_llm
from app.infrastructure.rng.rng import RngService
from app.infrastructure.sim.scheduler import SimScheduler
from app.infrastructure.writer.writer import PersistenceWriter


@dataclass
class Container:
    """Holds all constructed infrastructure + application services."""
    # Infrastructure
    db: Database
    writer: PersistenceWriter
    bus: InProcessEventBus
    rng: RngService
    scheduler: SimScheduler

    # Application services
    registry: ServiceRegistry
    policy_engine: PolicyEngine
    twin_service: TwinService
    invoker: ServiceInvoker
    orchestrator: AgentOrchestrator
    engine: WorkflowEngine

    # Background task handles
    _tasks: list[asyncio.Task] = field(default_factory=list)

    async def start_background_tasks(self) -> None:
        """Start writer, bus, and scheduler background tasks."""
        loop = asyncio.get_event_loop()
        self._tasks.append(loop.create_task(self.writer.run()))
        self._tasks.append(loop.create_task(self.bus.run()))
        self._tasks.append(loop.create_task(self.scheduler.run()))

    async def stop_background_tasks(self) -> None:
        """Gracefully stop all background tasks (flush writer)."""
        self.scheduler.pause()
        await self.writer.close()
        for task in self._tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass
        await self.db.close()


async def build_container(settings: Any | None = None) -> Container:
    """
    Build the full container from settings.
    Used in the lifespan and in tests (with overrides).
    """
    from app.infrastructure.config.settings import Settings
    cfg: Settings = settings or Settings()

    # --- Infrastructure ---
    db = Database(path=cfg.effective_db_path)
    await db.init()

    writer = PersistenceWriter(db)
    bus = InProcessEventBus(persist_fn=None)  # persist via writer directly
    rng = RngService(seed=cfg.sim.default_seed)

    # --- Seed DB ---
    await run_seed(db, writer,
                   scenario=cfg.sim.default_scenario,
                   seed_value=cfg.sim.default_seed)
    # Flush seed writes
    batch = await writer._drain(500)
    if batch:
        await writer._commit(batch)

    # --- LLM client (replay by default → $0, offline) ---
    _llm_mode = cfg.llm.mode
    _llm_provider = cfg.llm.provider
    _llm_model = cfg.llm.model
    print(f"[Agent5G] LLM → mode={_llm_mode}  provider={_llm_provider}  model={_llm_model}", flush=True)
    llm = build_llm(
        mode=_llm_mode,
        fixtures_dir=Path(cfg.llm.fixtures_dir),
        provider=_llm_provider,
        model=_llm_model,
        api_key=cfg.llm.api_key.get_secret_value() if cfg.llm.api_key else "",
        base_url=cfg.llm.base_url or "",
    )

    # --- SEL ---
    registry = ServiceRegistry(db, writer)
    for desc in get_catalog():
        registry.register(desc)
    await registry.persist_all()
    batch = await writer._drain(500)
    if batch:
        await writer._commit(batch)

    policy_engine = PolicyEngine()

    # --- Twin ---
    twin = build_twin_from_scenario(
        cfg.sim.default_scenario, seed=cfg.sim.default_seed
    )
    twin_service = TwinService(twin, rng, bus, writer, db, run_id=1)

    # --- Invoker + orchestrator ---
    invoker = ServiceInvoker(registry, policy_engine, twin_service, bus, writer)
    orchestrator = AgentOrchestrator(llm, invoker, registry, twin_service)
    engine = WorkflowEngine(orchestrator, bus=bus, writer=writer, db=db)

    # --- Scheduler wired to twin ---
    async def _on_tick(evt: Any) -> None:
        await twin_service.on_tick(evt.tick)

    scheduler = SimScheduler(
        tick_ms=cfg.sim.tick_ms,
        on_tick=_on_tick,
    )

    return Container(
        db=db, writer=writer, bus=bus, rng=rng, scheduler=scheduler,
        registry=registry, policy_engine=policy_engine,
        twin_service=twin_service, invoker=invoker,
        orchestrator=orchestrator, engine=engine,
    )
