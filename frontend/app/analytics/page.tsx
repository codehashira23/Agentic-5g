"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ReferenceLine, ResponsiveContainer,
} from "recharts";
import { api } from "@/lib/api/client";
import { Panel } from "@/components/panel";
import { EmptyState } from "@/components/states/empty-state";
import { Skeleton } from "@/components/states/skeleton";

// ─── per-NF-type KPI definitions ──────────────────────────────────────────
const NF_KPIS: Record<string, { value: string; label: string; threshold: number; unit: string; color: string }[]> = {
  UPF: [
    { value: "latency_ms",      label: "Latency",      threshold: 20,   unit: "ms",  color: "#6366f1" },
    { value: "throughput_mbps", label: "Throughput",   threshold: 500,  unit: "Mbps",color: "#10b981" },
    { value: "packet_loss",     label: "Packet Loss",  threshold: 0.01, unit: "",    color: "#f59e0b" },
  ],
  gNB: [
    { value: "prb_utilization", label: "PRB Utilization", threshold: 0.85, unit: "", color: "#8b5cf6" },
  ],
  Edge: [
    { value: "compute_load",    label: "Compute Load", threshold: 0.8,  unit: "",    color: "#06b6d4" },
    { value: "latency_ms",      label: "Latency",      threshold: 15,   unit: "ms",  color: "#6366f1" },
  ],
};

// ─── node catalogue ────────────────────────────────────────────────────────
const NODE_CATALOGUE = [
  { id: "upf_delhi_1",   type: "UPF",  region: "Delhi"  },
  { id: "upf_mumbai_1",  type: "UPF",  region: "Mumbai" },
  { id: "gnb_delhi_1",   type: "gNB",  region: "Delhi"  },
  { id: "gnb_delhi_2",   type: "gNB",  region: "Delhi"  },
  { id: "gnb_mumbai_1",  type: "gNB",  region: "Mumbai" },
  { id: "gnb_mumbai_2",  type: "gNB",  region: "Mumbai" },
  { id: "edge_delhi_1",  type: "Edge", region: "Delhi"  },
  { id: "edge_mumbai_1", type: "Edge", region: "Mumbai" },
];

const REGION_ORDER = ["Delhi", "Mumbai", "Core"];

// ─── single KPI mini-chart ─────────────────────────────────────────────────
function KpiChart({
  nodeId,
  kpi,
}: {
  nodeId: string;
  kpi: { value: string; label: string; threshold: number; unit: string; color: string };
}) {
  const { data = [], isLoading } = useQuery<{ tick: number; value: number }[]>({
    queryKey: ["analytics", "kpi", nodeId, kpi.value],
    queryFn: () =>
      api.get<{ tick: number; value: number }[]>(
        `/analytics/kpis?node_id=${encodeURIComponent(nodeId)}&kpi=${encodeURIComponent(kpi.value)}&limit=80`
      ),
    refetchInterval: 5000,
  });

  if (isLoading) return <Skeleton className="h-40" />;

  const hasData = data.length > 0;
  const latest = hasData ? data[data.length - 1]?.value : null;
  const isBreaching = latest !== null && latest > kpi.threshold;

  return (
    <div className={`rounded-lg border p-3 ${isBreaching ? "border-crit/60 bg-crit/5" : "border-border bg-card"}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold text-muted">{kpi.label}</span>
        {latest !== null && (
          <span className={`text-sm font-mono font-bold ${isBreaching ? "text-crit" : "text-primary"}`}>
            {latest.toFixed(kpi.unit === "ms" ? 1 : 3)}{kpi.unit ? ` ${kpi.unit}` : ""}
          </span>
        )}
      </div>

      {!hasData ? (
        <div className="h-28 flex items-center justify-center">
          <p className="text-xs text-faint">No data — run simulation</p>
        </div>
      ) : (
        <div style={{ height: 110 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis dataKey="tick" tick={{ fill: "#4b5563", fontSize: 9 }} />
              <YAxis tick={{ fill: "#4b5563", fontSize: 9 }} />
              <Tooltip
                contentStyle={{ background: "#151b23", border: "1px solid #1f2937", fontSize: 11 }}
                labelFormatter={(v) => `Tick ${v}`}
                formatter={((v: number) => `${v.toFixed(3)}${kpi.unit ? " " + kpi.unit : ""}`) as any}
              />
              <ReferenceLine
                y={kpi.threshold}
                stroke="#ef4444"
                strokeDasharray="3 2"
                strokeWidth={1}
              />
              <Line
                type="monotone"
                dataKey="value"
                stroke={kpi.color}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 3 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="flex items-center gap-1 mt-1">
        <span className="w-2 h-0.5 inline-block" style={{ background: "#ef4444", borderTop: "1px dashed #ef4444" }} />
        <span className="text-[10px] text-faint">
          Threshold {kpi.threshold}{kpi.unit ? ` ${kpi.unit}` : ""}
        </span>
      </div>
    </div>
  );
}

// ─── main page ─────────────────────────────────────────────────────────────
export default function AnalyticsPage() {
  const [selectedNode, setSelectedNode] = useState("upf_delhi_1");

  // Merge DB nodes with catalogue (DB nodes appear after simulation starts)
  const { data: dbNodes = [] } = useQuery<{ id: string; type: string; region: string }[]>({
    queryKey: ["analytics", "nodes"],
    queryFn: () => api.get("/analytics/nodes"),
    staleTime: 30_000,
  });

  const allNodes = NODE_CATALOGUE.map((n) => {
    const fromDb = dbNodes.find((d) => d.id === n.id);
    return fromDb ?? n;
  });

  const selected = allNodes.find((n) => n.id === selectedNode) ?? allNodes[0];
  const kpis = NF_KPIS[selected?.type ?? "UPF"] ?? [];

  // Group nodes by region for the sidebar
  const byRegion: Record<string, typeof allNodes> = {};
  for (const n of allNodes) {
    if (!byRegion[n.region]) byRegion[n.region] = [];
    byRegion[n.region].push(n);
  }

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-lg font-bold text-primary">Analytics</h1>

      <div className="flex gap-4 items-start">
        {/* ── Node selector sidebar ── */}
        <div className="w-44 flex-shrink-0 flex flex-col gap-3">
          {REGION_ORDER.filter((r) => byRegion[r]).map((region) => (
            <div key={region}>
              <p className="text-[10px] font-semibold text-faint uppercase tracking-wider mb-1 px-1">
                {region}
              </p>
              <div className="flex flex-col gap-1">
                {byRegion[region].map((n) => (
                  <button
                    key={n.id}
                    onClick={() => setSelectedNode(n.id)}
                    className={`text-left px-3 py-2 rounded-lg text-xs transition-colors
                      ${selectedNode === n.id
                        ? "bg-ai/15 border border-ai/40 text-ai"
                        : "bg-card border border-border text-muted hover:border-ai/40 hover:text-primary"
                      }`}
                  >
                    <span className="font-semibold block">{n.type}</span>
                    <span className="font-mono text-[10px] opacity-70 block truncate">{n.id}</span>
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* ── Charts panel ── */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-sm font-bold text-primary">{selected?.id}</span>
            <span className="px-2 py-0.5 rounded bg-card border border-border text-xs text-faint">
              {selected?.type} · {selected?.region}
            </span>
          </div>

          {kpis.length === 0 ? (
            <EmptyState message="No KPI charts defined for this NF type." />
          ) : (
            <div className={`grid gap-4 ${kpis.length === 1 ? "grid-cols-1" : "grid-cols-1 lg:grid-cols-2"}`}>
              {kpis.map((kpi) => (
                <KpiChart key={kpi.value} nodeId={selected.id} kpi={kpi} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
