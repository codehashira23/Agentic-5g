"""Autonomous-recovery harness (offline deterministic mode).

Drives the REAL orchestrator + workflow engine + SEL invoker + persistence with
a deterministic offline LLM (FakeLLM), across many seeded recovery workflows
spanning every fault type the recovery-goal builder handles. Measures:
  - completion rate (workflows reaching a terminal state / COMPLETE)
  - lifecycle stages executed per workflow
  - control-loop wall-clock per workflow (orchestration overhead; excludes any
    live-LLM latency, since the LLM is offline/deterministic here)
  - determinism (same input -> identical logical trajectory)

Temp DB; no live network; reproducible. This file is a throwaway probe.
"""
from __future__ import annotations
import asyncio, os, sys, tempfile, time, json, statistics
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

_tmp = os.path.join(tempfile.gettempdir(), "agent5g_bench.db")
if os.path.exists(_tmp):
    os.remove(_tmp)
os.environ["DB_PATH"] = _tmp
os.environ["ENV"] = "dev"

REPEATS = 4  # per fault type


async def main() -> None:
    import app.infrastructure.container as C
    from app.infrastructure.llm.client import FakeLLM
    C.build_llm = lambda **kw: FakeLLM()  # offline deterministic LLM
    from app.infrastructure.config.settings import Settings
    from app.application.recovery.autonomous import _build_recovery_goal

    container = await C.build_container(Settings())
    twin = container.twin_service._twin

    # one representative instance per recovery-relevant fault type
    want = ["UPF", "NRF", "gNB", "AMF", "SMF", "Edge"]
    picked: dict[str, object] = {}
    for n in twin.topology.nodes.values():
        t = n.nf_type.value
        if t in want and t not in picked:
            picked[t] = n

    def region_of(n) -> str:
        return getattr(n.region, "value", "Core")

    async def run_one(node) -> dict:
        goal = _build_recovery_goal(node.id, node.nf_type.value, region_of(node))
        t0 = time.perf_counter()
        state = await container.engine.start(goal=goal, trigger="autonomous")
        dt = (time.perf_counter() - t0) * 1000.0
        seq = [getattr(tr, "stage", "?") for tr in (state.trace or [])]
        return {
            "type": node.nf_type.value,
            "status": state.status,
            "reached_complete": state.status == "completed",
            "stages": len(set(seq)),
            "sequence": seq,
            "wall_ms": dt,
        }

    # Warm up (exclude first-call/connection overhead from timing).
    await run_one(next(iter(picked.values())))

    trials: list[dict] = []
    for _ in range(REPEATS):
        for node in picked.values():
            trials.append(await run_one(node))

    # Determinism: same fault type twice -> identical logical trajectory.
    a = await run_one(picked["UPF"])
    b = await run_one(picked["UPF"])
    deterministic = (a["sequence"] == b["sequence"] and a["status"] == b["status"])

    walls = [t["wall_ms"] for t in trials]
    n = len(trials)
    completed = sum(1 for t in trials if t["reached_complete"])
    stages = [t["stages"] for t in trials]
    seqs = {tuple(t["sequence"]) for t in trials}

    result = {
        "N": n,
        "fault_types": sorted(picked.keys()),
        "pct_complete": round(100.0 * completed / n, 1),
        "mean_stages": round(statistics.mean(stages), 2),
        "stage_path": sorted({",".join(t["sequence"]) for t in trials}),
        "wall_ms_mean": round(statistics.mean(walls), 1),
        "wall_ms_median": round(statistics.median(walls), 1),
        "wall_ms_stdev": round(statistics.pstdev(walls), 1),
        "per_stage_ms_mean": round(statistics.mean(walls) / max(1, statistics.mean(stages)), 1),
        "deterministic_repeat": deterministic,
        "distinct_trajectories": len(seqs),
    }
    print("RESULT " + json.dumps(result, default=str))

    try:
        await container.stop_background_tasks()
    except Exception:
        pass


asyncio.run(main())
