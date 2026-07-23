/**
 * GENERATED — do not hand-edit.
 * Source: GET http://localhost:8000/openapi.json
 * Regenerate: npm run gen:types
 * Owning docs: 09-api.md §7, 11-frontend.md §7
 */

// ---- Common ----
export interface ErrorEnvelope {
  type: string;
  title: string;
  status: number;
  detail?: string;
  correlation_id?: string | null;
  errors?: Array<{ field: string; message: string }>;
}

export interface Paginated<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
}

export interface HealthResponse {
  status: string;
  db: string;
  bus: string;
  llm: string;
  sim: string;
}

// ---- Workflows ----
export interface CreateWorkflowRequest {
  goal: string;
  metadata?: Record<string, unknown>;
}

export interface WorkflowResponse {
  id: string;
  goal: string;
  status: string;
  stage: string;
  created_at: string;
  correlation_id: string;
  trigger: string;
}

export interface TraceEntryResponse {
  stage: string;
  agent_role: string;
  rationale?: string;
  ts?: string;
  tokens_in?: number;
  tokens_out?: number;
  latency_ms?: number;
}

// ---- Services ----
export interface ServiceView {
  name: string;
  kind: string;
  pattern: string;
  owner_nf: string;
  policy_tags: string[];
  spec_ref: string;
  approximates_operation: string;
  idempotent: boolean;
  compensation: string | null;
  description: string;
}

// ---- Twin ----
export interface TwinSnapshot {
  tick: number;
  health_pct: number;
  nf_states: Record<string, NfState>;
}

export interface NfState {
  type: string;
  region: string;
  status: "ACTIVE" | "DEGRADED" | "FAILED" | "RECOVERING" | "STANDBY";
  load: number;
  kpis: Record<string, KpiState>;
}

export interface KpiState {
  current: number;
  smoothed: number;
  breaching: boolean;
}

// ---- Topology ----
export interface TopologyNode {
  id: string;
  type: string;
  region: string;
  status: string;
  load: number;
  x: number;
  y: number;
}

export interface TopologyLink {
  id: string;
  src_id: string;
  dst_id: string;
  ref_point: string;
  latency_ms: number;
  throughput_mbps: number;
}

export interface TopologyResponse {
  nodes: TopologyNode[];
  links: TopologyLink[];
  regions: string[];
}

// ---- Simulation ----
export interface SimStatus {
  status: string;
  tick: number;
  seed: number;
  nf_count: number;
}

// ---- WebSocket Events ----
export type WsEvent =
  | { type: "HELLO"; server_version: string; api: string; schema_version: string; ts: string }
  | { type: "PING" }
  | { type: "PONG" }
  | { type: "KPI_UPDATED"; correlation_id?: string; tick: number; payload: { entity_id: string; kpi: string; value: number } }
  | { type: "KPI_THRESHOLD_BREACH"; correlation_id?: string; tick: number; payload: { entity_id: string; kpi: string; value: number; threshold: number; region: string } }
  | { type: "KPI_THRESHOLD_CLEARED"; correlation_id?: string; tick: number; payload: { entity_id: string; kpi: string; region: string } }
  | { type: "NF_FAILED"; correlation_id?: string; tick: number; payload: { entity_id: string; nf_type: string; cause: string } }
  | { type: "NF_RECOVERED"; correlation_id?: string; tick: number; payload: { entity_id: string; nf_type: string } }
  | { type: "NF_REGISTERED"; correlation_id?: string; tick: number; payload: { entity_id: string; nf_type: string } }
  | { type: "MODEL_DEPLOYED"; correlation_id?: string; tick: number; payload: { model_id: string; target_id: string; region: string } }
  | { type: "MODEL_RETIRED"; correlation_id?: string; tick: number; payload: { model_id: string; target_id: string } }
  | { type: "SERVICE_CALLED"; correlation_id?: string; tick: number; payload: { service_name: string; caller: string } }
  | { type: "SERVICE_RESULT"; correlation_id?: string; tick: number; payload: { service_name: string; status: string; latency_ms: number } }
  | { type: "POLICY_BLOCKED"; correlation_id?: string; tick: number; payload: { service_name: string; policy_id: string; message: string } }
  | { type: "WORKFLOW_STAGE_CHANGED"; correlation_id?: string; tick: number; payload: { workflow_id: string; from_stage: string; to_stage: string; status: string } }
  | { type: "WORKFLOW_COMPLETED"; correlation_id?: string; tick: number; payload: { workflow_id: string; goal: string } }
  | { type: "WORKFLOW_FAILED"; correlation_id?: string; tick: number; payload: { workflow_id: string; error: string } }
  | { type: string; correlation_id?: string; tick: number; payload: Record<string, unknown> };  // fallback
