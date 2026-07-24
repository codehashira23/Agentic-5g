"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ReferenceLine, ResponsiveContainer, Legend,
} from "recharts";
import { api } from "@/lib/api/client";
import { Panel } from "@/components/panel";
import { EmptyState } from "@/components/states/empty-state";
import { Skeleton } from "@/components/states/skeleton";

const KPI_OPTIONS = [
  { value: "latency_ms",       label: "Latency (ms)",       threshold: 20,  unit: "ms"  },
  { value: "throughput_gbps",  label: "Throughput (Gbps)",  threshold: 0.5, unit: "Gbps" },
  { value: "packet_loss_pct",  label: "Packet Loss (%)",    threshold: 1,   unit: "%"   },
  { value: "prb_utilization",  label: "PRB Utilization",    threshold: 0.85,unit: ""    },
  { value: "cpu_util_pct",     label: "CPU Utilization (%)",threshold: 80,  unit: "%"   },
];

interface KpiPoint { tick: number; value: number; ts: string }
interface KpiNode  { id: string; type: string; region: string }

export default function AnalyticsPage() {
  const [selectedNode, setSelectedNode] = useState("upf_delhi_1");
  const [selectedKpi,  setSelectedKpi]  = useState("latency_ms");

  const kpiMeta = KPI_OPTIONS.find((k) => k.value === selectedKpi) ?? KPI_OPTIONS[0];

  // Load available nodes
  const { data: nodes = [] } = useQuery<KpiNode[]>({
    queryKey: ["analytics", "nodes"],
    queryFn: () => api.get<KpiNode[]>("/analytics/nodes"),
    staleTime: 30_000,
  });

  // Load KPI data
  const { data: kpis = [], isLoading, isError } = useQuery<KpiPoint[]>({
    queryKey: ["analytics", "kpis", selectedNode, selectedKpi],
    queryFn: () =>
      api.get<KpiPoint[]>(
        `/analytics/kpis?node_id=${encodeURIComponent(selectedNode)}&kpi=${encodeURIComponent(selectedKpi)}&limit=120`
      ),
    refetchInterval: 5000,
    enabled: !!selectedNode,
  });

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-lg font-bold text-primary">Analytics</h1>

      {/* Controls */}
      <div className="flex flex-wrap gap-3 items-center">
        <div className="flex flex-col gap-1">
          <label className="text-xs text-faint">Node</label>
          <select
            value={selectedNode}
            onChange={(e) => setSelectedNode(e.target.value)}
            className="bg-card border border-border rounded px-2 py-1.5 text-sm text-primary
                       focus:outline-none focus:border-ai min-w-[180px]"
          >
            {nodes.length === 0 && (
              <option value="upf_delhi_1">upf_delhi_1</option>
            )}
            {nodes.map((n) => (
              <option key={n.id} value={n.id}>
                {n.id} ({n.type} · {n.region})
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-xs text-faint">KPI</label>
          <select
            value={selectedKpi}
            onChange={(e) => setSelectedKpi(e.target.value)}
            className="bg-card border border-border rounded px-2 py-1.5 text-sm text-primary
                       focus:outline-none focus:border-ai min-w-[200px]"
          >
            {KPI_OPTIONS.map((k) => (
              <option key={k.value} value={k.value}>{k.label}</option>
            ))}
          </select>
        </div>

        <div className="ml-auto text-xs text-faint self-end pb-1.5">
          {kpis.length > 0
            ? `${kpis.length} samples · last tick ${kpis[kpis.length - 1]?.tick ?? "—"}`
            : "Start simulation to generate data"}
        </div>
      </div>

      {/* Chart */}
      <Panel title={`${kpiMeta.label} — ${selectedNode}`}>
        {isLoading ? (
          <Skeleton className="h-64" />
        ) : isError ? (
          <EmptyState message="Could not load KPI data — is the backend running?" />
        ) : kpis.length === 0 ? (
          <EmptyState message="No data yet — start the simulation on the Simulation page, then come back." />
        ) : (
          <div style={{ width: "100%", height: 300 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={kpis} margin={{ top: 8, right: 16, left: 0, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                <XAxis
                  dataKey="tick"
                  tick={{ fill: "#6b7280", fontSize: 11 }}
                  label={{ value: "Tick", position: "insideBottomRight", offset: -4, fill: "#6b7280", fontSize: 11 }}
                />
                <YAxis
                  tick={{ fill: "#6b7280", fontSize: 11 }}
                  label={{ value: kpiMeta.unit, angle: -90, position: "insideLeft", fill: "#6b7280", fontSize: 11 }}
                />
                <Tooltip
                  contentStyle={{ background: "#151b23", border: "1px solid #1f2937", fontSize: 12 }}
                  labelFormatter={(v) => `Tick ${v}`}
                  formatter={((v: number) => `${v.toFixed(3)} ${kpiMeta.unit}`) as any}
                />
                <Legend wrapperStyle={{ fontSize: 12, color: "#9ca3af" }} />
                {/* Threshold reference line */}
                <ReferenceLine
                  y={kpiMeta.threshold}
                  stroke="#ef4444"
                  strokeDasharray="4 2"
                  label={{ value: `Threshold ${kpiMeta.threshold}${kpiMeta.unit}`, fill: "#ef4444", fontSize: 10 }}
                />
                <Line
                  type="monotone"
                  dataKey="value"
                  name={kpiMeta.label}
                  stroke="#6366f1"
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4, fill: "#6366f1" }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </Panel>
    </div>
  );
}
