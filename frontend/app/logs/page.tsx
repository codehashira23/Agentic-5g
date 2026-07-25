"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Activity, Zap, Workflow, Server,
  ChevronDown, ChevronRight, Search, X,
  AlertTriangle, CheckCircle2, Info, Clock,
} from "lucide-react";
import { api } from "@/lib/api/client";
import { StatCard } from "@/components/stat-card";
import { Panel } from "@/components/panel";
import { EmptyState } from "@/components/states/empty-state";
import { Skeleton } from "@/components/states/skeleton";
import type { WorkflowResponse } from "@/lib/api/types.gen";

// ── Types ─────────────────────────────────────────────────────────────────────
type EventItem = {
  id: number; type: string; ts: string;
  entity_id?: string; correlation_id?: string;
  payload_json?: string; tick?: number;
};
type ServiceCallItem = {
  id: number; service_name: string; caller: string;
  status: string; latency_ms: number; ts: string;
  correlation_id?: string;
};
type LogStats = {
  event_count: number; service_call_count: number;
  workflow_count: number; fault_count: number;
};

// ── Event helpers ─────────────────────────────────────────────────────────────
const EVENT_TYPE_GROUPS: Record<string, string[]> = {
  faults:    ["NF_FAILED", "NF_DEREGISTERED"],
  recovered: ["NF_RECOVERED", "NF_REGISTERED"],
  kpi:       ["KPI_THRESHOLD_BREACH", "KPI_THRESHOLD_CLEARED", "KPI_UPDATED"],
  workflow:  ["WORKFLOW_STAGE_CHANGED", "WORKFLOW_COMPLETED", "WORKFLOW_FAILED"],
  service:   ["SERVICE_CALLED", "SERVICE_RESULT", "POLICY_BLOCKED"],
  model:     ["MODEL_DEPLOYED", "MODEL_RETIRED"],
};

function eventStyle(type: string) {
  if (EVENT_TYPE_GROUPS.faults.includes(type))
    return { bar: "bg-crit", label: "text-crit", bg: "bg-crit/5 hover:bg-crit/8", icon: AlertTriangle, iconCls: "text-crit" };
  if (EVENT_TYPE_GROUPS.recovered.includes(type))
    return { bar: "bg-ok", label: "text-ok", bg: "bg-ok/5 hover:bg-ok/8", icon: CheckCircle2, iconCls: "text-ok" };
  if (EVENT_TYPE_GROUPS.kpi.includes(type))
    return { bar: "bg-warn", label: "text-warn", bg: "bg-warn/5 hover:bg-warn/8", icon: Activity, iconCls: "text-warn" };
  if (EVENT_TYPE_GROUPS.workflow.includes(type))
    return { bar: "bg-ai", label: "text-ai", bg: "bg-ai/5 hover:bg-ai/8", icon: Workflow, iconCls: "text-ai" };
  if (EVENT_TYPE_GROUPS.service.includes(type))
    return { bar: "bg-info", label: "text-info", bg: "bg-info/5 hover:bg-info/8", icon: Server, iconCls: "text-info" };
  return { bar: "bg-border", label: "text-muted", bg: "hover:bg-card-hover", icon: Info, iconCls: "text-faint" };
}

function formatEventType(type: string): string {
  return type.replace(/_/g, " ").toLowerCase().replace(/\b\w/g, c => c.toUpperCase());
}

function formatTime(iso: string): string {
  try { return new Date(iso).toLocaleTimeString(); } catch { return iso; }
}

function svcStatusColor(status: string): string {
  if (status === "ok") return "text-ok bg-ok/10 border-ok/20";
  if (status === "blocked") return "text-warn bg-warn/10 border-warn/20";
  return "text-crit bg-crit/10 border-crit/20";
}

// ── Expandable event row ──────────────────────────────────────────────────────
function EventRow({
  event,
  onFilterCid,
}: {
  event: EventItem;
  onFilterCid: (cid: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const style = eventStyle(event.type);
  const Icon = style.icon;
  let payload: Record<string, unknown> = {};
  try { payload = JSON.parse(event.payload_json || "{}"); } catch { /* ignore */ }

  return (
    <div className={`rounded-lg border border-transparent transition-colors ${style.bg}`}>
      <button
        className="w-full flex items-center gap-3 px-3 py-2 text-left"
        onClick={() => setOpen(v => !v)}
      >
        <span className={`w-1 h-8 rounded-full shrink-0 ${style.bar}`} />
        <Icon className={`w-3.5 h-3.5 shrink-0 ${style.iconCls}`} />
        <span className={`text-xs font-semibold shrink-0 min-w-[180px] ${style.label}`}>
          {formatEventType(event.type)}
        </span>
        {event.entity_id && (
          <span className="text-xs text-faint font-mono">{event.entity_id}</span>
        )}
        <span className="ml-auto flex items-center gap-2 shrink-0">
          {event.tick != null && (
            <span className="text-[10px] text-faint font-mono">t{event.tick}</span>
          )}
          <span className="text-[10px] text-faint">{formatTime(event.ts)}</span>
          {event.correlation_id && (
            <button
              onClick={(e) => { e.stopPropagation(); onFilterCid(event.correlation_id!); }}
              className="text-[10px] text-ai font-mono hover:underline"
              title="Filter by this workflow"
            >
              {event.correlation_id.slice(-8)}
            </button>
          )}
          {open ? <ChevronDown className="w-3 h-3 text-faint" /> : <ChevronRight className="w-3 h-3 text-faint" />}
        </span>
      </button>

      {open && Object.keys(payload).length > 0 && (
        <div className="px-8 pb-3">
          <pre className="text-[10px] text-muted bg-card border border-border rounded-lg p-3 overflow-x-auto">
            {JSON.stringify(payload, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
const FILTER_GROUPS = [
  { key: "all",       label: "All Events" },
  { key: "faults",    label: "Faults" },
  { key: "workflow",  label: "Workflows" },
  { key: "kpi",       label: "KPI" },
  { key: "service",   label: "Service Calls" },
  { key: "model",     label: "Models" },
];

type Tab = "events" | "service-calls" | "workflow-trace";

export default function LogsPage() {
  const [tab, setTab] = useState<Tab>("events");
  const [filterGroup, setFilterGroup] = useState("all");
  const [correlationId, setCorrelationId] = useState("");
  const [searchText, setSearchText] = useState("");
  const [selectedWfId, setSelectedWfId] = useState("");

  // Stats
  const { data: stats } = useQuery<LogStats>({
    queryKey: ["logs", "stats"],
    queryFn: () => api.get<LogStats>("/logs/stats"),
    refetchInterval: 10_000,
  });

  // Domain events
  const { data: eventsData, isLoading: eventsLoading } = useQuery<{ items: EventItem[]; total: number }>({
    queryKey: ["logs", "events", correlationId],
    queryFn: () => api.get<{ items: EventItem[]; total: number }>(
      `/logs/events?limit=200${correlationId ? `&correlation_id=${encodeURIComponent(correlationId)}` : ""}`
    ),
    refetchInterval: 5000,
    enabled: tab === "events",
  });

  // Service calls
  const { data: callsData, isLoading: callsLoading } = useQuery<{ items: ServiceCallItem[]; total: number }>({
    queryKey: ["logs", "service-calls", correlationId],
    queryFn: () => api.get<{ items: ServiceCallItem[]; total: number }>(
      `/logs/service-calls?limit=100${correlationId ? `&correlation_id=${encodeURIComponent(correlationId)}` : ""}`
    ),
    refetchInterval: 5000,
    enabled: tab === "service-calls",
  });

  // Workflows for trace picker
  const { data: workflows = [] } = useQuery<WorkflowResponse[]>({
    queryKey: ["workflows"],
    queryFn: () => api.get<WorkflowResponse[]>("/workflows?limit=20"),
    enabled: tab === "workflow-trace",
  });

  // Workflow trace
  const { data: traceData } = useQuery<Array<{ stage: string; agent_role: string; rationale: string; ts: string }>>({
    queryKey: ["workflows", selectedWfId, "trace"],
    queryFn: () => api.get(`/workflows/${selectedWfId}/trace`),
    enabled: !!selectedWfId && tab === "workflow-trace",
    staleTime: 0,
  });

  // Filter events
  const allEvents = eventsData?.items ?? [];
  const filteredEvents = allEvents.filter(e => {
    const typeGroups = EVENT_TYPE_GROUPS[filterGroup as keyof typeof EVENT_TYPE_GROUPS];
    const matchesGroup = filterGroup === "all" || (typeGroups && typeGroups.includes(e.type));
    const matchesSearch = !searchText || e.type.toLowerCase().includes(searchText.toLowerCase())
      || (e.entity_id ?? "").toLowerCase().includes(searchText.toLowerCase())
      || (e.correlation_id ?? "").toLowerCase().includes(searchText.toLowerCase());
    return matchesGroup && matchesSearch;
  });

  const allCalls = callsData?.items ?? [];
  const filteredCalls = allCalls.filter(c =>
    !searchText ||
    c.service_name.toLowerCase().includes(searchText.toLowerCase()) ||
    (c.caller ?? "").toLowerCase().includes(searchText.toLowerCase()) ||
    (c.correlation_id ?? "").toLowerCase().includes(searchText.toLowerCase())
  );

  return (
    <div className="flex flex-col gap-5">
      {/* Header */}
      <div>
        <h1 className="text-lg font-bold text-primary">Logs</h1>
        <p className="text-xs text-faint mt-0.5">
          Audit trail for all AI agent decisions, service calls, and network events
        </p>
      </div>

      {/* Stats bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatCard
          title="Domain Events"
          value={stats?.event_count ?? 0}
          status="ai"
          icon={<Activity className="w-4 h-4" />}
        />
        <StatCard
          title="Service Calls"
          value={stats?.service_call_count ?? 0}
          status="ok"
          icon={<Server className="w-4 h-4" />}
        />
        <StatCard
          title="Workflows"
          value={stats?.workflow_count ?? 0}
          status="ai"
          icon={<Workflow className="w-4 h-4" />}
        />
        <StatCard
          title="Fault Events"
          value={stats?.fault_count ?? 0}
          status={stats?.fault_count ? "crit" : "ok"}
          icon={<Zap className="w-4 h-4" />}
        />
      </div>

      {/* Filter bar */}
      <div className="flex flex-wrap gap-2 items-center">
        {/* Correlation ID filter */}
        <div className="flex items-center gap-1 flex-1 min-w-[200px] bg-card border border-border rounded-lg px-3 py-1.5">
          <Search className="w-3.5 h-3.5 text-faint shrink-0" />
          <input
            value={correlationId}
            onChange={e => setCorrelationId(e.target.value)}
            placeholder="Filter by workflow ID…"
            className="flex-1 bg-transparent text-sm text-primary placeholder:text-faint outline-none font-mono"
          />
          {correlationId && (
            <button onClick={() => setCorrelationId("")} className="text-faint hover:text-primary">
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* Search */}
        <div className="flex items-center gap-1 flex-1 min-w-[160px] bg-card border border-border rounded-lg px-3 py-1.5">
          <Search className="w-3.5 h-3.5 text-faint shrink-0" />
          <input
            value={searchText}
            onChange={e => setSearchText(e.target.value)}
            placeholder="Search events…"
            className="flex-1 bg-transparent text-sm text-primary placeholder:text-faint outline-none"
          />
          {searchText && (
            <button onClick={() => setSearchText("")} className="text-faint hover:text-primary">
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-border">
        {(["events", "service-calls", "workflow-trace"] as Tab[]).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-xs font-medium capitalize transition-colors border-b-2 -mb-px
              ${tab === t ? "border-ai text-ai" : "border-transparent text-muted hover:text-primary"}`}
          >
            {t === "events" ? "Domain Events" : t === "service-calls" ? "Service Calls" : "Workflow Trace"}
          </button>
        ))}
      </div>

      {/* Domain Events tab */}
      {tab === "events" && (
        <div className="flex flex-col gap-3">
          {/* Type filter pills */}
          <div className="flex flex-wrap gap-1.5">
            {FILTER_GROUPS.map(g => (
              <button
                key={g.key}
                onClick={() => setFilterGroup(g.key)}
                className={`px-3 py-1 rounded-full text-xs font-medium transition-colors
                  ${filterGroup === g.key
                    ? "bg-ai/15 text-ai border border-ai/30"
                    : "bg-card border border-border text-muted hover:text-primary"}`}
              >
                {g.label}
                {g.key !== "all" && (
                  <span className="ml-1 opacity-60">
                    {allEvents.filter(e => (EVENT_TYPE_GROUPS[g.key] ?? []).includes(e.type)).length}
                  </span>
                )}
              </button>
            ))}
          </div>

          <Panel title={`${filteredEvents.length} events${correlationId ? ` · ${correlationId.slice(0, 14)}…` : ""}`}>
            {eventsLoading ? (
              <Skeleton className="h-40" />
            ) : filteredEvents.length === 0 ? (
              <EmptyState message="No events yet — start the simulation or run a workflow." />
            ) : (
              <div className="flex flex-col gap-0.5 max-h-[520px] overflow-y-auto">
                {filteredEvents.map(event => (
                  <EventRow
                    key={event.id}
                    event={event}
                    onFilterCid={(cid) => setCorrelationId(cid)}
                  />
                ))}
              </div>
            )}
          </Panel>
        </div>
      )}

      {/* Service Calls tab */}
      {tab === "service-calls" && (
        <Panel title={`${filteredCalls.length} service calls`}>
          {callsLoading ? (
            <Skeleton className="h-40" />
          ) : filteredCalls.length === 0 ? (
            <EmptyState message="No service calls yet — run a workflow to see AI agent actions here." />
          ) : (
            <div className="overflow-x-auto max-h-[520px] overflow-y-auto">
              <table className="w-full text-xs">
                <thead className="sticky top-0 bg-card">
                  <tr className="border-b border-border">
                    <th className="text-left py-2 pr-4 text-faint font-medium">Service</th>
                    <th className="text-left py-2 pr-4 text-faint font-medium">Caller</th>
                    <th className="text-left py-2 pr-4 text-faint font-medium">Status</th>
                    <th className="text-left py-2 pr-4 text-faint font-medium">Latency</th>
                    <th className="text-left py-2 pr-4 text-faint font-medium">Workflow</th>
                    <th className="text-left py-2 text-faint font-medium">Time</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredCalls.map(call => (
                    <tr key={call.id} className="border-b border-border/40 hover:bg-card-hover">
                      <td className="py-2 pr-4 font-mono text-ai">{call.service_name}</td>
                      <td className="py-2 pr-4 text-muted">{call.caller}</td>
                      <td className="py-2 pr-4">
                        <span className={`px-1.5 py-0.5 rounded border text-[10px] font-medium ${svcStatusColor(call.status)}`}>
                          {call.status}
                        </span>
                      </td>
                      <td className="py-2 pr-4 font-mono text-muted">{call.latency_ms}ms</td>
                      <td className="py-2 pr-4">
                        {call.correlation_id && (
                          <button
                            onClick={() => setCorrelationId(call.correlation_id!)}
                            className="font-mono text-ai hover:underline"
                          >
                            {call.correlation_id.slice(-8)}
                          </button>
                        )}
                      </td>
                      <td className="py-2 text-faint">{formatTime(call.ts)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Panel>
      )}

      {/* Workflow Trace tab */}
      {tab === "workflow-trace" && (
        <div className="flex flex-col gap-4">
          {/* Workflow picker */}
          <div className="flex items-center gap-3">
            <select
              value={selectedWfId}
              onChange={e => setSelectedWfId(e.target.value)}
              className="flex-1 bg-card border border-border rounded-lg px-3 py-2 text-sm text-primary
                         focus:outline-none focus:border-ai"
            >
              <option value="">— Select a workflow —</option>
              {workflows.map(wf => (
                <option key={wf.id} value={wf.id}>
                  [{wf.status.toUpperCase()}] {wf.goal.slice(0, 55)}… · {wf.id.slice(-8)}
                </option>
              ))}
            </select>
            {correlationId && (
              <button
                onClick={() => {
                  const wf = workflows.find(w => w.id === correlationId || w.id.endsWith(correlationId));
                  if (wf) setSelectedWfId(wf.id);
                }}
                className="text-xs text-ai hover:underline whitespace-nowrap"
              >
                Load filtered ID
              </button>
            )}
          </div>

          <Panel title={selectedWfId ? `Reasoning trace — ${selectedWfId.slice(-8)}` : "Select a workflow above"}>
            {!selectedWfId ? (
              <EmptyState message="Pick a workflow to see the AI reasoning trace." />
            ) : !traceData ? (
              <Skeleton className="h-40" />
            ) : traceData.length === 0 ? (
              <EmptyState message="No trace recorded for this workflow." />
            ) : (
              <ol className="flex flex-col gap-4">
                {traceData.map((entry, i) => (
                  <li key={i} className="flex gap-3">
                    <div className="flex flex-col items-center">
                      <div className="w-6 h-6 rounded-full bg-ai/15 border border-ai/30 flex items-center justify-center
                                      text-[10px] font-bold text-ai shrink-0">
                        {i + 1}
                      </div>
                      {i < traceData.length - 1 && <div className="w-px flex-1 bg-border mt-1" />}
                    </div>
                    <div className="flex-1 pb-3">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-bold text-ai capitalize">{entry.stage}</span>
                        <span className="text-xs text-faint">— {entry.agent_role}</span>
                        {entry.ts && (
                          <span className="ml-auto text-[10px] text-faint font-mono">
                            {formatTime(entry.ts)}
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-muted leading-relaxed">
                        {entry.rationale || "—"}
                      </p>
                    </div>
                  </li>
                ))}
              </ol>
            )}
          </Panel>
        </div>
      )}
    </div>
  );
}
