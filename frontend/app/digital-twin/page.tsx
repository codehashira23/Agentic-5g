"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Zap, X, Activity } from "lucide-react";
import {
  LineChart, Line, ResponsiveContainer, Tooltip,
} from "recharts";
import { api } from "@/lib/api/client";
import { keys } from "@/lib/query/keys";
import { Panel } from "@/components/panel";
import { StatusBadge } from "@/components/status-badge";
import { Skeleton } from "@/components/states/skeleton";
import { ErrorState } from "@/components/states/error-state";
import { EmptyState } from "@/components/states/empty-state";

// ── Types ─────────────────────────────────────────────────────────────────────
type KpiState = { current: number; smoothed: number; breaching: boolean };
type NfState = {
  type: string;
  region: string;
  status: string;
  load: number;
  kpis?: Record<string, KpiState>;
};
type TwinData = {
  tick: number;
  health_pct: number;
  nf_states: Record<string, NfState>;
};

// ── Status colours ────────────────────────────────────────────────────────────
const STATUS_BORDER: Record<string, string> = {
  ACTIVE:     "border-ok/40",
  DEGRADED:   "border-warn/60",
  FAILED:     "border-crit/80",
  RECOVERING: "border-ai/60",
  STANDBY:    "border-border",
};

// KPIs worth showing prominently
const KEY_KPIS: Record<string, { label: string; unit: string; threshold: number }> = {
  latency_ms:     { label: "Latency",    unit: "ms",  threshold: 20 },
  throughput_mbps:{ label: "Throughput", unit: "Mbps",threshold: 500 },
  packet_loss:    { label: "Pkt Loss",   unit: "",    threshold: 0.01 },
  prb_utilization:{ label: "PRB Util",   unit: "",    threshold: 0.85 },
  compute_load:   { label: "CPU Load",   unit: "",    threshold: 0.8 },
};

// ── KPI Popout ────────────────────────────────────────────────────────────────
function KpiPopout({
  nfId,
  state,
  onClose,
}: {
  nfId: string;
  state: NfState;
  onClose: () => void;
}) {
  const kpis = state.kpis ?? {};
  const relevantKpis = Object.entries(kpis).filter(([k]) => KEY_KPIS[k]);

  return (
    <div className="absolute z-30 top-0 left-full ml-2 w-56 bg-panel border border-border rounded-xl shadow-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <div>
          <p className="text-xs font-bold text-primary">{nfId}</p>
          <p className="text-[10px] text-faint">{state.type} · {state.region}</p>
        </div>
        <button onClick={onClose} className="text-faint hover:text-primary">
          <X className="w-3.5 h-3.5" />
        </button>
      </div>

      {relevantKpis.length === 0 ? (
        <p className="text-xs text-faint">No KPI data for this NF type.</p>
      ) : (
        <div className="flex flex-col gap-2">
          {relevantKpis.map(([kpiName, kpiData]) => {
            const meta = KEY_KPIS[kpiName];
            const val = kpiData.current;
            const breaching = kpiData.breaching;
            return (
              <div key={kpiName}>
                <div className="flex items-center justify-between mb-0.5">
                  <span className="text-[10px] text-faint">{meta.label}</span>
                  <span className={`text-xs font-mono font-bold ${breaching ? "text-crit" : "text-ok"}`}>
                    {val.toFixed(meta.unit === "ms" ? 1 : 3)}{meta.unit ? ` ${meta.unit}` : ""}
                    {breaching && " ⚠"}
                  </span>
                </div>
                <div className="h-1.5 bg-border rounded-full overflow-hidden">
                  <div
                    className={`h-1.5 rounded-full transition-all ${breaching ? "bg-crit" : "bg-ok"}`}
                    style={{
                      width: `${Math.min((val / (meta.threshold * 1.5)) * 100, 100)}%`,
                    }}
                  />
                </div>
                <p className="text-[9px] text-faint mt-0.5">threshold {meta.threshold}{meta.unit}</p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── Sparkline data store (keeps last 15 ticks per NF) ────────────────────────
const sparklineHistory: Record<string, number[]> = {};

function updateSparkline(nfId: string, load: number) {
  if (!sparklineHistory[nfId]) sparklineHistory[nfId] = [];
  sparklineHistory[nfId].push(load);
  if (sparklineHistory[nfId].length > 15) sparklineHistory[nfId].shift();
}

// ── NF Card ───────────────────────────────────────────────────────────────────
function NfCard({
  id,
  state,
  onFault,
}: {
  id: string;
  state: NfState;
  onFault: (id: string) => void;
}) {
  const [showKpi, setShowKpi] = useState(false);

  // Update sparkline on every render
  updateSparkline(id, state.load);
  const sparkData = (sparklineHistory[id] ?? []).map((v, i) => ({ i, v }));

  const kpis = state.kpis ?? {};
  const anyBreaching = Object.values(kpis).some((k) => k.breaching);
  const hasKpis = Object.keys(kpis).some((k) => KEY_KPIS[k]);

  const borderClass = anyBreaching
    ? "border-warn/80 animate-pulse"
    : STATUS_BORDER[state.status] ?? "border-border";
  const bgClass = state.status === "FAILED"
    ? "bg-crit/5"
    : anyBreaching
    ? "bg-warn/5"
    : "";

  return (
    <div className="relative">
      <div
        className={`bg-card border rounded-xl p-3 text-xs transition-all cursor-pointer
          hover:border-ai/40 group ${borderClass} ${bgClass}`}
        onClick={() => hasKpis && setShowKpi((v) => !v)}
      >
        {/* Header */}
        <div className="flex items-start justify-between mb-1">
          <div className="min-w-0">
            <p className="font-bold text-primary text-[11px]">{state.type}</p>
            <p className="font-mono text-faint text-[9px] truncate">{id}</p>
          </div>
          {/* Fault inject button */}
          {state.status === "ACTIVE" || state.status === "DEGRADED" ? (
            <button
              onClick={(e) => { e.stopPropagation(); onFault(id); }}
              className="opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded
                         bg-crit/10 text-crit hover:bg-crit/20"
              title={`Inject fault on ${id}`}
            >
              <Zap className="w-2.5 h-2.5" />
            </button>
          ) : (
            <span className="w-5" />
          )}
        </div>

        {/* Status */}
        <StatusBadge status={state.status} />

        {/* Breaching KPI badge */}
        {anyBreaching && (
          <div className="mt-1 px-1.5 py-0.5 rounded bg-warn/15 text-warn text-[9px] font-semibold">
            KPI BREACH
          </div>
        )}

        {/* Load bar */}
        {state.load > 0 && (
          <div className="mt-2 h-1 bg-border rounded-full overflow-hidden">
            <div
              className={`h-1 rounded-full transition-all ${
                state.load > 0.85 ? "bg-crit" : state.load > 0.65 ? "bg-warn" : "bg-ai"
              }`}
              style={{ width: `${Math.min(state.load * 100, 100)}%` }}
            />
          </div>
        )}

        {/* Sparkline */}
        {sparkData.length > 3 && state.load > 0 && (
          <div className="mt-1.5 h-8 opacity-60">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={sparkData}>
                <Line
                  type="monotone"
                  dataKey="v"
                  stroke={state.load > 0.85 ? "#ef4444" : "#6366f1"}
                  strokeWidth={1.5}
                  dot={false}
                />
                <Tooltip
                  contentStyle={{ background: "rgba(24,37,68,0.96)", border: "1px solid #3d5478", borderRadius: 8, fontSize: 10 }}
                  formatter={((v: number) => `${(v * 100).toFixed(0)}% load`) as any}
                  labelFormatter={() => ""}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* KPI hint */}
        {hasKpis && (
          <div className="mt-1.5 flex items-center gap-1 text-[9px] text-faint">
            <Activity className="w-2.5 h-2.5" />
            <span>{showKpi ? "hide KPIs" : "click for KPIs"}</span>
          </div>
        )}
      </div>

      {/* KPI Popout */}
      {showKpi && hasKpis && (
        <KpiPopout nfId={id} state={state} onClose={() => setShowKpi(false)} />
      )}
    </div>
  );
}

// ── Region stats row ──────────────────────────────────────────────────────────
function RegionStats({ nfs }: { nfs: [string, NfState][] }) {
  const active = nfs.filter(([, s]) => s.status === "ACTIVE").length;
  const failed = nfs.filter(([, s]) => s.status === "FAILED").length;
  const degraded = nfs.filter(([, s]) => s.status === "DEGRADED").length;
  const avgLoad = nfs.reduce((sum, [, s]) => sum + s.load, 0) / Math.max(nfs.length, 1);

  return (
    <div className="flex items-center gap-3 mb-2 px-1">
      <span className="text-xs text-ok">{active} Active</span>
      {degraded > 0 && <span className="text-xs text-warn">{degraded} Degraded</span>}
      {failed > 0 && <span className="text-xs text-crit">{failed} Failed</span>}
      {avgLoad > 0 && (
        <span className="text-xs text-faint ml-auto">
          Avg load {Math.round(avgLoad * 100)}%
        </span>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function DigitalTwinPage() {
  const qc = useQueryClient();

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: keys.twin(),
    queryFn: () => api.get<TwinData>("/twin"),
    refetchInterval: 2000,
  });

  const faultMut = useMutation({
    mutationFn: (nfId: string) =>
      api.post("/simulation/fault", { nf_id: nfId, type: "fail" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.twin() });
      qc.invalidateQueries({ queryKey: keys.topology() });
    },
  });

  if (isLoading)
    return (
      <div className="flex flex-col gap-4">
        <h1 className="text-lg font-bold text-primary">Digital Twin</h1>
        <Skeleton className="h-64" />
      </div>
    );

  if (isError)
    return (
      <div className="flex flex-col gap-4">
        <h1 className="text-lg font-bold text-primary">Digital Twin</h1>
        <ErrorState message="Could not load twin state — is the backend running?" retry={refetch} />
      </div>
    );

  if (!data)
    return (
      <div className="flex flex-col gap-4">
        <h1 className="text-lg font-bold text-primary">Digital Twin</h1>
        <EmptyState message="No twin data yet. Start the simulation first." />
      </div>
    );

  const nfs = Object.entries(data.nf_states);
  const healthyCount = nfs.filter(([, s]) => s.status === "ACTIVE" || s.status === "STANDBY").length;
  const failedCount  = nfs.filter(([, s]) => s.status === "FAILED").length;
  const breachingCount = nfs.filter(([, s]) =>
    Object.values(s.kpis ?? {}).some((k) => k.breaching)
  ).length;

  // Group by region
  const byRegion: Record<string, [string, NfState][]> = {};
  for (const [id, state] of nfs) {
    const r = state.region ?? "Unknown";
    if (!byRegion[r]) byRegion[r] = [];
    byRegion[r].push([id, state]);
  }
  const regionOrder = ["Core", "Delhi", "Mumbai", "Bengaluru", "Unknown"];
  const sortedRegions = Object.keys(byRegion).sort(
    (a, b) => (regionOrder.indexOf(a) ?? 99) - (regionOrder.indexOf(b) ?? 99)
  );

  return (
    <div className="flex flex-col gap-5">
      {/* Header summary bar */}
      <div className="flex items-center gap-3 flex-wrap">
        <h1 className="text-lg font-bold text-primary">Digital Twin</h1>
        <span className="px-2 py-0.5 rounded bg-card border border-border text-xs text-muted">
          Tick <span className="text-primary font-mono font-bold">{data.tick}</span>
        </span>
        <span className="px-2 py-0.5 rounded bg-ok/10 border border-ok/30 text-xs text-ok">
          {healthyCount} Healthy
        </span>
        {failedCount > 0 && (
          <span className="px-2 py-0.5 rounded bg-crit/10 border border-crit/30 text-xs text-crit">
            {failedCount} Failed
          </span>
        )}
        {breachingCount > 0 && (
          <span className="px-2 py-0.5 rounded bg-warn/10 border border-warn/30 text-xs text-warn animate-pulse">
            {breachingCount} KPI Breach
          </span>
        )}
        <span className="ml-auto text-xs text-faint">
          Health {Math.round(data.health_pct * 100)}% · {nfs.length} NFs
        </span>
      </div>

      {/* Fault inject feedback */}
      {faultMut.isPending && (
        <div className="px-3 py-2 rounded-lg bg-crit/10 border border-crit/30 text-xs text-crit">
          Injecting fault…
        </div>
      )}
      {faultMut.isError && (
        <div className="px-3 py-2 rounded-lg bg-crit/10 border border-crit/30 text-xs text-crit">
          Fault injection failed — NF not found or simulation not running.
        </div>
      )}

      {/* NFs grouped by region */}
      {sortedRegions.map((region) => (
        <section key={region}>
          <div className="flex items-center gap-2 mb-1">
            <h2 className="text-xs font-semibold text-faint uppercase tracking-wider px-1">
              {region} Region
            </h2>
          </div>
          <RegionStats nfs={byRegion[region]} />
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2">
            {byRegion[region].map(([id, state]) => (
              <NfCard
                key={id}
                id={id}
                state={state}
                onFault={(nfId) => faultMut.mutate(nfId)}
              />
            ))}
          </div>
        </section>
      ))}

      {/* Legend */}
      <div className="flex flex-wrap gap-4 text-xs text-faint pt-2 border-t border-border">
        <span className="flex items-center gap-1.5">
          <Zap className="w-3 h-3 text-crit" />
          Hover card → click ⚡ to inject fault
        </span>
        <span className="flex items-center gap-1.5">
          <Activity className="w-3 h-3 text-ai" />
          Click card → see live KPIs
        </span>
        <span>Pulsing amber border = KPI threshold breach</span>
      </div>
    </div>
  );
}
