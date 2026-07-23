"use client";
import { useQuery } from "@tanstack/react-query";
import { useCallback } from "react";
import ReactFlow, { Background, Controls, type Node, type Edge } from "reactflow";
import "reactflow/dist/style.css";
import { api } from "@/lib/api/client";
import { keys } from "@/lib/query/keys";
import { useWsStore } from "@/lib/ws/store";
import { Skeleton } from "@/components/states/skeleton";
import type { TopologyResponse } from "@/lib/api/types.gen";

const STATUS_COLOR: Record<string, string> = {
  ACTIVE: "#10b981",
  STANDBY: "#3b82f6",
  DEGRADED: "#f59e0b",
  FAILED: "#ef4444",
  RECOVERING: "#f59e0b",
};

function toNodes(nodes: TopologyResponse["nodes"], statusMap: Record<string, string>): Node[] {
  return nodes.map((n, i) => ({
    id: n.id,
    position: { x: n.x || (i % 6) * 180 + 60, y: n.y || Math.floor(i / 6) * 130 + 60 },
    data: { label: n.id, type: n.type, status: statusMap[n.id] ?? n.status },
    style: {
      background: "#151b23",
      border: `2px solid ${STATUS_COLOR[statusMap[n.id] ?? n.status] ?? "#1f2937"}`,
      borderRadius: 8,
      padding: "6px 10px",
      color: "#e5e7eb",
      fontSize: 11,
      minWidth: 110,
    },
  }));
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

export default function TopologyPage() {
  const nfStatusById = useWsStore((s) => s.nfStatusById);

  const { data, isLoading } = useQuery({
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

  const nodes = toNodes(data.nodes, nfStatusById);
  const edges = toEdges(data.links);

  return (
    <div className="flex flex-col gap-4 h-full">
      <h1 className="text-lg font-bold text-primary">Topology</h1>
      <div
        className="flex-1 bg-card border border-border rounded-lg overflow-hidden"
        style={{ minHeight: 500 }}
      >
        <ReactFlow nodes={nodes} edges={edges} fitView>
          <Background color="#1f2937" />
          <Controls />
        </ReactFlow>
      </div>
    </div>
  );
}
