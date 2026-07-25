"""
Autonomous Recovery Handler — reacts to NF_FAILED events on the event bus.

When a network function fails, this handler automatically starts a recovery
workflow WITHOUT requiring human input. This is the core of "agentic" behaviour:
the system detects faults and responds on its own.

Supported scenarios:
  - UPF failure  → "Load balance away from <upf_id> to alternate UPF"
  - NRF failure  → "Promote standby NRF and re-register all network functions"
  - gNB failure  → "Reroute UE traffic from <gnb_id> to adjacent gNB"
  - Edge failure → "Retire all models on <edge_id> and redeploy to backup edge"
  - Default      → "Recover failed network function <nf_id> in <region>"

Owning docs: 05-agents.md §9, 13-workflow-engine.md §14
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Cooldown: don't trigger recovery for the same NF within this many seconds
# Set to 5s so repeated test injections still trigger recovery
_COOLDOWN_S = 5
_last_triggered: dict[str, float] = {}


def _build_recovery_goal(nf_id: str, nf_type: str, region: str) -> str:
    """
    Build a human-readable recovery goal from the NF failure context.
    The Planner agent uses this goal to generate the recovery plan.
    """
    nf_type_lower = nf_type.lower()

    if nf_type_lower == "upf":
        # Determine alternate UPF region
        alt_region = "Mumbai" if "delhi" in nf_id.lower() else "Delhi"
        return (
            f"UPF {nf_id} has failed in {region}. "
            f"Load balance active sessions to {alt_region} UPF "
            f"and restore network connectivity."
        )
    if nf_type_lower == "nrf":
        return (
            f"NRF {nf_id} has failed. "
            f"Promote standby NRF (nrf_standby_1) and trigger "
            f"re-registration of all affected network functions."
        )
    if nf_type_lower == "gnb":
        return (
            f"gNB {nf_id} has failed in {region}. "
            f"Reroute connected UE sessions to an adjacent gNB "
            f"and restore radio access."
        )
    if nf_type_lower in ("edge", "edgenode"):
        return (
            f"Edge node {nf_id} has failed in {region}. "
            f"Retire all hosted AI models and redeploy to backup edge node."
        )
    if nf_type_lower == "amf":
        return (
            f"AMF {nf_id} has failed in {region}. "
            f"Re-register affected UEs and restore mobility management."
        )
    if nf_type_lower == "smf":
        return (
            f"SMF {nf_id} has failed in {region}. "
            f"Re-establish PDU sessions affected by the SMF failure."
        )
    # Default recovery goal
    return (
        f"Network function {nf_id} ({nf_type}) has failed in {region}. "
        f"Diagnose the failure, apply recovery actions, and restore service."
    )


class AutonomousRecoveryHandler:
    """
    Listens on the event bus for NF_FAILED events and automatically
    starts a recovery workflow via the WorkflowEngine.

    Registered in build_container() after the engine is wired.
    """

    def __init__(self, engine: Any) -> None:
        self._engine = engine

    async def handle(self, event: Any) -> None:
        """
        Called by the event bus when NF_FAILED is published.
        Starts a recovery workflow as a background asyncio task.
        """
        import time

        nf_id: str = getattr(event, "entity_id", "") or ""
        nf_type: str = getattr(event, "nf_type", "") or "NF"
        cause: str = getattr(event, "cause", "unknown") or "unknown"

        if not nf_id:
            logger.warning("AutonomousRecoveryHandler: received NF_FAILED with no entity_id")
            return

        # Extract region from nf_id (e.g. upf_delhi_1 → Delhi)
        region = "Core"
        if "delhi" in nf_id.lower():
            region = "Delhi"
        elif "mumbai" in nf_id.lower():
            region = "Mumbai"
        elif "bengaluru" in nf_id.lower():
            region = "Bengaluru"

        # Cooldown check — don't flood with recovery workflows for the same NF
        now = time.monotonic()
        last = _last_triggered.get(nf_id, 0.0)
        if now - last < _COOLDOWN_S:
            remaining = _COOLDOWN_S - (now - last)
            print(
                f"[AutonomousRecovery] {nf_id} cooldown active — {remaining:.0f}s remaining, skipping",
                flush=True,
            )
            logger.info(
                "AutonomousRecovery: skipping %s — cooldown active (%.0fs remaining)",
                nf_id, remaining,
            )
            return
        _last_triggered[nf_id] = now

        goal = _build_recovery_goal(nf_id, nf_type, region)
        logger.info(
            "AutonomousRecovery: NF_FAILED(%s cause=%s) → starting recovery workflow",
            nf_id, cause,
        )
        print(
            f"[AutonomousRecovery] {nf_id} ({nf_type}) failed → auto-starting recovery",
            flush=True,
        )

        # Fire workflow as background task — don't block the event bus
        asyncio.create_task(
            self._engine.start(
                goal=goal,
                trigger="autonomous",
                correlation_id=None,  # engine will generate a new wf_id
            )
        )
