"""
Application: Scenario loading and fault injection for the Digital Twin.

Scenarios are named presets that define the initial twin world:
  topology, demand profile, failure config, thresholds, seed.

Owning docs: 06-digital-twin.md §16, 17-deployment.md
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.domain.twin.network_twin import NetworkTwin
from app.domain.twin.profile import Region


@dataclass
class ScenarioConfig:
    """Configuration for a simulation scenario preset."""
    name: str
    seed: int = 42
    regions: tuple[Region, ...] = (Region.DELHI, Region.MUMBAI)
    # Demand multiplier applied on top of the diurnal profile
    demand_multiplier: float = 1.0
    # Scripted faults: list of {tick, nf_id, type}
    scripted_faults: list[dict[str, Any]] = field(default_factory=list)
    description: str = ""


# ---------------------------------------------------------------------------
# Built-in scenario presets
# ---------------------------------------------------------------------------
SCENARIOS: dict[str, ScenarioConfig] = {
    "baseline_healthy": ScenarioConfig(
        name="baseline_healthy",
        seed=42,
        regions=(Region.DELHI, Region.MUMBAI),
        demand_multiplier=1.0,
        description="Small multi-region network, no faults, gentle diurnal demand.",
    ),
    "mumbai_congestion": ScenarioConfig(
        name="mumbai_congestion",
        seed=7,
        regions=(Region.DELHI, Region.MUMBAI),
        demand_multiplier=2.5,  # busy-hour spike drives breach
        description="Demand spike + mobility concentration in Mumbai.",
    ),
    "nrf_failure": ScenarioConfig(
        name="nrf_failure",
        seed=42,
        regions=(Region.DELHI, Region.MUMBAI),
        demand_multiplier=1.0,
        scripted_faults=[{"tick": 5, "nf_id": "nrf_core_1", "type": "fail"}],
        description="Scripted NRF fault at tick 5 — drives Scenario C recovery.",
    ),
    "stress_multi": ScenarioConfig(
        name="stress_multi",
        seed=99,
        regions=(Region.DELHI, Region.MUMBAI),
        demand_multiplier=3.0,
        description="Multiple concurrent stressors for robustness experiments.",
    ),
}


def get_scenario(name: str) -> ScenarioConfig:
    """Return a scenario config by name, or baseline_healthy if not found."""
    return SCENARIOS.get(name, SCENARIOS["baseline_healthy"])


def build_twin_from_scenario(name: str, seed: int | None = None) -> NetworkTwin:
    """Build a NetworkTwin from a named scenario preset."""
    config = get_scenario(name)
    effective_seed = seed if seed is not None else config.seed
    return NetworkTwin.from_baseline(
        seed=effective_seed,
        regions=config.regions,
    )


# ---------------------------------------------------------------------------
# Fault injection
# ---------------------------------------------------------------------------
@dataclass
class FaultSpec:
    """Specification for a fault to inject into the twin."""
    nf_id: str
    fault_type: str = "fail"     # "fail" | "degrade" | "recover"
    kpi: str | None = None       # for "degrade" faults
    delta: float = 0.0           # KPI delta for degrade


def inject_fault(twin: NetworkTwin, spec: FaultSpec) -> dict[str, Any]:
    """
    Apply a fault to the given NF in the twin.
    Returns a result dict describing what was done.
    """
    from app.domain.twin.profile import NFStatus

    nf = twin.get_nf(spec.nf_id)
    if nf is None:
        return {"injected": False, "reason": f"NF '{spec.nf_id}' not found"}

    if spec.fault_type == "fail":
        nf._set_status(NFStatus.FAILED)
        return {"injected": True, "nf_id": spec.nf_id, "type": "fail",
                "new_status": "FAILED"}

    if spec.fault_type == "degrade":
        nf._set_status(NFStatus.DEGRADED)
        return {"injected": True, "nf_id": spec.nf_id, "type": "degrade",
                "new_status": "DEGRADED"}

    if spec.fault_type == "recover":
        nf._set_status(NFStatus.ACTIVE)
        return {"injected": True, "nf_id": spec.nf_id, "type": "recover",
                "new_status": "ACTIVE"}

    return {"injected": False, "reason": f"Unknown fault type '{spec.fault_type}'"}
