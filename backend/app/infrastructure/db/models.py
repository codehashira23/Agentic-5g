"""
Infrastructure: SQLAlchemy ORM models for all 18 database tables.

Matches the schema in 12-database.md exactly.
ORM classes are kept SEPARATE from domain entities (BD-2) — repositories
translate between them, keeping the domain framework-free.

Key conventions (12-database.md §4):
  - Primary keys: string ids where semantically meaningful; INTEGER autoincrement
    for pure append tables (events, kpis, logs, service_calls, workflow_trace).
  - Timestamps: ISO-8601 UTC TEXT.
  - Enums: TEXT with CheckConstraint.
  - JSON payloads: TEXT (validated by Pydantic at the application boundary).
  - Correlation: operational rows carry correlation_id (DP2).
  - Run context: time-series rows carry run_id FK → simulation (DP7).

Owning docs: 12-database.md §6
"""
from __future__ import annotations

from sqlalchemy import (
    CheckConstraint,
    Column,
    Float,
    ForeignKey,
    Index,
    Integer,
    Text,
)

from app.infrastructure.db.engine import Base


# ---------------------------------------------------------------------------
# 1. users
# ---------------------------------------------------------------------------
class UserRow(Base):
    __tablename__ = "users"

    id = Column(Text, primary_key=True)          # user_{uuid}
    username = Column(Text, nullable=False, unique=True)
    display_name = Column(Text)
    role = Column(
        Text,
        CheckConstraint("role IN ('admin','researcher','viewer')"),
        nullable=False,
        default="researcher",
    )
    created_at = Column(Text, nullable=False)


# ---------------------------------------------------------------------------
# 2. agents
# ---------------------------------------------------------------------------
class AgentRow(Base):
    __tablename__ = "agents"

    role = Column(
        Text,
        CheckConstraint(
            "role IN ('planner','executor','observer','optimizer',"
            "'recovery','documentation','memory')"
        ),
        primary_key=True,
    )
    description = Column(Text, nullable=False)
    tools_json = Column(Text, default="[]")
    memory_scopes_json = Column(Text, default="[]")
    enabled = Column(Integer, nullable=False, default=1)
    created_at = Column(Text)


# ---------------------------------------------------------------------------
# 3. services
# ---------------------------------------------------------------------------
class ServiceRow(Base):
    __tablename__ = "services"

    name = Column(Text, primary_key=True)        # {nf}.{domain}.{action}
    kind = Column(
        Text,
        CheckConstraint("kind IN ('read','action','control')"),
        nullable=False,
    )
    pattern = Column(
        Text,
        CheckConstraint("pattern IN ('request_response','subscribe_notify')"),
        nullable=False,
        default="request_response",
    )
    owner_nf = Column(Text, nullable=False)
    input_schema_json = Column(Text, default="{}")
    output_schema_json = Column(Text, default="{}")
    policy_tags_json = Column(Text, default="[]")
    spec_ref = Column(Text, default="")
    approximates_operation = Column(Text, default="")
    idempotent = Column(Integer, default=1)
    compensation = Column(Text)
    description = Column(Text, default="")
    registered_at = Column(Text)


# ---------------------------------------------------------------------------
# 4. policies
# ---------------------------------------------------------------------------
class PolicyRow(Base):
    __tablename__ = "policies"

    id = Column(Text, primary_key=True)          # PLC-1 … PLC-6, custom
    name = Column(Text, nullable=False)
    enabled = Column(Integer, nullable=False, default=1)
    severity = Column(
        Text,
        CheckConstraint("severity IN ('low','medium','high','critical')"),
        nullable=False,
        default="high",
    )
    match_json = Column(Text, default="{}")
    condition_ref = Column(Text, nullable=False)
    decision = Column(
        Text,
        CheckConstraint("decision IN ('allow','block','require_confirmation')"),
        nullable=False,
        default="block",
    )
    message = Column(Text, default="")
    builtin = Column(Integer, nullable=False, default=0)
    updated_at = Column(Text)


# ---------------------------------------------------------------------------
# 5. simulation — one row per run (seed + scenario + status)
# ---------------------------------------------------------------------------
class SimulationRow(Base):
    __tablename__ = "simulation"

    id = Column(Integer, primary_key=True, autoincrement=True)   # run_id
    scenario = Column(Text, nullable=False)
    seed = Column(Integer, nullable=False)
    status = Column(
        Text,
        CheckConstraint("status IN ('running','paused','stopped','reset')"),
        nullable=False,
        default="stopped",
    )
    tick = Column(Integer, nullable=False, default=0)
    tick_ms = Column(Integer, nullable=False, default=1000)
    snapshot_json = Column(Text)
    started_at = Column(Text)
    ended_at = Column(Text)


# ---------------------------------------------------------------------------
# 6. topology_nodes
# ---------------------------------------------------------------------------
class TopologyNodeRow(Base):
    __tablename__ = "topology_nodes"

    id = Column(Text, primary_key=True)          # upf_delhi_1 etc.
    type = Column(Text, nullable=False)          # NFType value
    region = Column(Text, nullable=False)
    status = Column(
        Text,
        CheckConstraint(
            "status IN ('ACTIVE','DEGRADED','FAILED','RECOVERING','STANDBY')"
        ),
        nullable=False,
        default="ACTIVE",
    )
    load = Column(Float, nullable=False, default=0.0)
    x = Column(Float, default=0.0)
    y = Column(Float, default=0.0)
    state_json = Column(Text, default="{}")
    services_json = Column(Text, default="[]")
    updated_at = Column(Text)
    tick = Column(Integer, default=0)


# ---------------------------------------------------------------------------
# 7. topology_links
# ---------------------------------------------------------------------------
class TopologyLinkRow(Base):
    __tablename__ = "topology_links"

    id = Column(Text, primary_key=True)
    src_id = Column(Text, ForeignKey("topology_nodes.id"), nullable=False)
    dst_id = Column(Text, ForeignKey("topology_nodes.id"), nullable=False)
    ref_point = Column(Text, default="")
    throughput_mbps = Column(Float, default=0.0)
    latency_ms = Column(Float, default=0.0)
    utilization = Column(Float, default=0.0)
    updated_at = Column(Text)


# ---------------------------------------------------------------------------
# 8. kpis — append-only, write-behind batched (DP4)
# ---------------------------------------------------------------------------
class KpiRow(Base):
    __tablename__ = "kpis"

    id = Column(Integer, primary_key=True, autoincrement=True)
    node_id = Column(Text, ForeignKey("topology_nodes.id"), nullable=False)
    kpi = Column(Text, nullable=False)
    value = Column(Float, nullable=False)
    tick = Column(Integer, nullable=False)
    run_id = Column(Integer, ForeignKey("simulation.id"))
    ts = Column(Text, nullable=False)

    __table_args__ = (
        Index("ix_kpis_node_kpi_tick", "node_id", "kpi", "tick"),
        Index("ix_kpis_run", "run_id"),
    )


# ---------------------------------------------------------------------------
# 9. events — append-only, write-through (lossless for critical events)
# ---------------------------------------------------------------------------
class EventRow(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(Text, nullable=False)
    correlation_id = Column(Text)
    entity_id = Column(Text)
    payload_json = Column(Text, default="{}")
    tick = Column(Integer, default=0)
    run_id = Column(Integer, ForeignKey("simulation.id"))
    ts = Column(Text, nullable=False)

    __table_args__ = (
        Index("ix_events_type_ts", "type", "ts"),
        Index("ix_events_correlation", "correlation_id"),
        Index("ix_events_entity", "entity_id"),
        Index("ix_events_run", "run_id"),
    )


# ---------------------------------------------------------------------------
# 10. workflows
# ---------------------------------------------------------------------------
class WorkflowRow(Base):
    __tablename__ = "workflows"

    id = Column(Text, primary_key=True)          # wf_{uuid}
    correlation_id = Column(Text, nullable=False)
    goal = Column(Text, nullable=False)
    trigger = Column(
        Text,
        CheckConstraint("trigger IN ('user','observer','template')"),
        nullable=False,
        default="user",
    )
    status = Column(
        Text,
        CheckConstraint(
            "status IN ('running','completed','failed','cancelled','paused')"
        ),
        nullable=False,
        default="running",
    )
    stage = Column(Text, nullable=False, default="observe")
    attempts = Column(Integer, nullable=False, default=0)
    seed = Column(Integer)
    scenario = Column(Text)
    config_json = Column(Text, default="{}")
    summary_json = Column(Text)
    error = Column(Text)
    created_by = Column(Text, ForeignKey("users.id"))
    created_at = Column(Text, nullable=False)
    updated_at = Column(Text, nullable=False)
    completed_at = Column(Text)

    __table_args__ = (
        Index("ix_workflows_status_created", "status", "created_at"),
        Index("ix_workflows_correlation", "correlation_id"),
    )


# ---------------------------------------------------------------------------
# 11. workflow_steps
# ---------------------------------------------------------------------------
class WorkflowStepRow(Base):
    __tablename__ = "workflow_steps"

    id = Column(Text, primary_key=True)          # {wf_id}_s{n}
    workflow_id = Column(Text, ForeignKey("workflows.id"), nullable=False)
    correlation_id = Column(Text)
    index = Column(Integer, nullable=False)
    service_name = Column(Text, ForeignKey("services.name"))
    args_json = Column(Text, default="{}")
    success_criterion = Column(Text, default="")
    status = Column(
        Text,
        CheckConstraint(
            "status IN ('pending','running','succeeded','failed','compensated')"
        ),
        nullable=False,
        default="pending",
    )
    result_json = Column(Text, default="{}")
    compensation = Column(Text)
    attempts = Column(Integer, nullable=False, default=0)
    created_at = Column(Text)
    updated_at = Column(Text)

    __table_args__ = (
        Index("ix_wf_steps_workflow", "workflow_id"),
    )


# ---------------------------------------------------------------------------
# 12. workflow_trace — append-only reasoning record
# ---------------------------------------------------------------------------
class WorkflowTraceRow(Base):
    __tablename__ = "workflow_trace"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(Text, ForeignKey("workflows.id"), nullable=False)
    correlation_id = Column(Text)
    stage = Column(Text, nullable=False)
    agent_role = Column(Text)  # soft ref to agents.role, no hard FK
    rationale = Column(Text)
    structured_json = Column(Text, default="{}")
    tokens_in = Column(Integer, default=0)
    tokens_out = Column(Integer, default=0)
    latency_ms = Column(Float, default=0.0)
    prompt_version = Column(Text, default="")
    ts = Column(Text, nullable=False)

    __table_args__ = (
        Index("ix_trace_workflow_ts", "workflow_id", "ts"),
    )


# ---------------------------------------------------------------------------
# 13. logs — structured application logs
# ---------------------------------------------------------------------------
class LogRow(Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts = Column(Text, nullable=False)
    level = Column(
        Text,
        CheckConstraint("level IN ('debug','info','warn','error')"),
        nullable=False,
        default="info",
    )
    type = Column(Text)
    correlation_id = Column(Text)
    nf = Column(Text)
    service = Column(Text)
    message = Column(Text, nullable=False)
    payload_json = Column(Text, default="{}")

    __table_args__ = (
        Index("ix_logs_ts", "ts"),
        Index("ix_logs_correlation", "correlation_id"),
        Index("ix_logs_level_type", "level", "type"),
    )


# ---------------------------------------------------------------------------
# 14. memory
# ---------------------------------------------------------------------------
class MemoryRow(Base):
    __tablename__ = "memory"

    id = Column(Text, primary_key=True)          # mem_{uuid}
    scope = Column(
        Text,
        CheckConstraint("scope IN ('working','episodic','semantic')"),
        nullable=False,
    )
    content_json = Column(Text, default="{}")
    summary = Column(Text, nullable=False)
    workflow_id = Column(Text, ForeignKey("workflows.id"))
    created_by_agent = Column(Text, default="memory")  # soft ref, no FK
    embedding_json = Column(Text)
    weight = Column(Float, nullable=False, default=1.0)
    created_at = Column(Text, nullable=False)
    expires_at = Column(Text)

    __table_args__ = (
        Index("ix_memory_scope", "scope"),
        Index("ix_memory_workflow", "workflow_id"),
    )


# ---------------------------------------------------------------------------
# 15. knowledge_nodes
# ---------------------------------------------------------------------------
class KnowledgeNodeRow(Base):
    __tablename__ = "knowledge_nodes"

    id = Column(Text, primary_key=True)          # nf:upf_delhi_1 etc.
    entity_type = Column(Text, nullable=False)
    label = Column(Text, nullable=False)
    props_json = Column(Text, default="{}")
    first_seen_at = Column(Text)
    updated_at = Column(Text)


# ---------------------------------------------------------------------------
# 16. knowledge_edges
# ---------------------------------------------------------------------------
class KnowledgeEdgeRow(Base):
    __tablename__ = "knowledge_edges"

    id = Column(Integer, primary_key=True, autoincrement=True)
    src_id = Column(Text, ForeignKey("knowledge_nodes.id"), nullable=False)
    dst_id = Column(Text, ForeignKey("knowledge_nodes.id"), nullable=False)
    relation = Column(Text, nullable=False)
    props_json = Column(Text, default="{}")
    provenance_workflow_id = Column(Text, ForeignKey("workflows.id"))
    created_at = Column(Text)

    __table_args__ = (
        Index("ix_kedges_src", "src_id"),
        Index("ix_kedges_dst", "dst_id"),
        Index("ix_kedges_relation", "relation"),
    )


# ---------------------------------------------------------------------------
# 17. models (AIMLE model instances)
# ---------------------------------------------------------------------------
class ModelRow(Base):
    __tablename__ = "models"

    id = Column(Text, primary_key=True)          # model_{uuid}
    name = Column(Text, nullable=False)
    version = Column(Text, default="1.0")
    state = Column(
        Text,
        CheckConstraint(
            "state IN ('registered','trained','validated',"
            "'deployed','monitored','retired')"
        ),
        nullable=False,
        default="registered",
    )
    target_node_id = Column(Text, ForeignKey("topology_nodes.id"))
    metrics_json = Column(Text, default="{}")
    created_at = Column(Text, nullable=False)
    updated_at = Column(Text, nullable=False)


# ---------------------------------------------------------------------------
# 18. service_calls — append-only SEL invocation log
# ---------------------------------------------------------------------------
class ServiceCallRow(Base):
    __tablename__ = "service_calls"

    id = Column(Integer, primary_key=True, autoincrement=True)
    correlation_id = Column(Text)
    workflow_id = Column(Text, ForeignKey("workflows.id"))
    service_name = Column(Text, ForeignKey("services.name"))
    caller = Column(Text)
    status = Column(
        Text,
        CheckConstraint(
            "status IN ('ok','blocked','error','requires_confirmation')"
        ),
        nullable=False,
        default="ok",
    )
    args_json = Column(Text, default="{}")
    result_json = Column(Text, default="{}")
    policy_id = Column(Text, ForeignKey("policies.id"))
    latency_ms = Column(Float, default=0.0)
    ts = Column(Text, nullable=False)

    __table_args__ = (
        Index("ix_calls_correlation", "correlation_id"),
        Index("ix_calls_service", "service_name"),
        Index("ix_calls_status", "status"),
        Index("ix_calls_ts", "ts"),
    )
