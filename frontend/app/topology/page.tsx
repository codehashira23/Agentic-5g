"use client";
import { useQuery } from "@tanstack/react-query";
import ReactFlow, { Background, Controls, type Node, type Edge } from "reactflow";
import "reactflow/dist/style.css";
import { api } from "@/lib/api/client";
import { keys } from "@/lib/query/keys";
import { useWsStore } from "@/lib/ws/store";
import { ErrorState } from "@/components/states/error-state";
import { Skeleton } from "@/components/states/skeleton";
import type { TopologyResponse } from "@/lib/api/types.gen";

const STATUS_COLOR: Record<string, string> = {
  ACTIVE:     "#10b981",
  STANDBY:    "#3b82f6",
  DEGRADED:   "#f59e0b",
  FAILED:     "#ef4444",
  RECOVERING: "#8b5cf6",
};

const STATUS_LABEL: Record<string, string> = {
  ACTIVE:     "Active",
  STANDBY:    "Standby",
  DEGRADED:   "Degraded",
  FAILED:     "Failed",
  RECOVERING: "Recovering",
};

function toNodes(nodes: TopologyResponse["nodes"], statusMap: Record<string, string>): Node[] {
  return nodes.map((n, i) => {
    const status = statusMap[n.id] ?? n.status;
    const color = STATUS_COLOR[status] ?? "#374151";
    return {
      id: n.id,
      // Use backend coordinates; fall back to grid if 0,0
      position: {
        x: n.x && n.x !== 0 ? n.x : (i % 6) * 180 + 60,
        y: n.y && n.y !== 0 ? n.y : Math.floor(i / 6) * 130 + 60,
      },
      data: { label: n.id, type: n.type, status },
      style: {
        background: "#151b23",
        border: `2px solid ${color}`,
        borderRadius: 8,
        padding: "6px 10px",
        color: "#e5e7eb",
        fontSize: 11,
        minWidth: 110,
      },
      // Custom label: type bold + id small
      type: "default",
    };
  });
}

function toEdges(links: TopologyResponse["links"]): Edge[] {
  return links.map((lk) => ({
    id: lk.id,
    source: lk.src_id,
    target: lk.dst_id,
    label: lk.ref_point || undefined,
    style: { stroke: "#374151" },
    labelStyle: { fill: "#6b7280", fontSize: 10 },
  }));
}

// Colour legend component
function Legend() {
  return (
    <div className="flex flex-wrap gap-4 p-3 border-t border-border bg-card text-xs">
      {Object.entries(STATUS_LABEL).map(([key, label]) => (
        <span key={key} className="flex items-center gap-1.5">
          <span
            className="w-3 h-3 rounded-full inline-block flex-shrink-0"
            style={{ backgroundColor: STATUS_COLOR[key] }}
          />
          <span className="text-muted">{label}</span>
        </span>
      ))}
      <span className="ml-auto text-faint">
        Nodes show NF type · Hover for full ID
      </span>
    </div>
  );
}

export default function TopologyPage() {
  const nfStatusById = useWsStore((s) => s.nfStatusById);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: keys.topology(),
    queryFn: () => api.get<TopologyResponse>("/topology"),
    refetchInterval: 10_000,
  });

  if (isLoading || !data) {
    return (
      <div className="flex flex-col gap-4">
        <h1 className="text-lg font-bold text-primary">Topology</h1>
        <Skeleton className="h-96" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex flex-col gap-4">
        <h1 className="text-lg font-bold text-primary">Topology</h1>
        <ErrorState message="Could not load topology — is the backend running?" retry={refetch} />
      </div>
    );
  }

  // Override node label to show "TYPE\nid" with type prominent
  const nodes = toNodes(data.nodes, nfStatusById).map((n) => ({
    ...n,
    data: {
      ...n.data,
      label: (
        <div className="flex flex-col items-center leading-tight">
          <span className="font-bold text-xs" style={{ color: STATUS_COLOR[n.data.status] ?? "#e5e7eb" }}>
            {n.data.type}
          </span>
          <span className="text-[9px] text-gray-500 font-mono truncate max-w-[90px]">
            {n.data.label}
          </span>
        </div>
      ),
    },
  }));
  const edges = toEdges(data.links);

  return (
    <div className="flex flex-col gap-4 h-full">
      <h1 className="text-lg font-bold text-primary">Topology</h1>
      <div
        className="flex-1 bg-card border border-border rounded-lg overflow-hidden flex flex-col"
        style={{ minHeight: 500 }}
      >
        <div className="flex-1" style={{ minHeight: 460 }}>
          <ReactFlow nodes={nodes} edges={edges} fitView>
            <Background color="#1f2937" />
            <Controls />
          </ReactFlow>
        </div>
        <Legend />
      </div>
    </div>
  );
}
