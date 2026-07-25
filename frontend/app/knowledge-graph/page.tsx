"use client";
import { useState, useCallback, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import ReactFlow, {
  Background,
  Controls,
  type Node,
  type Edge,
  Handle,
  Position,
} from "reactflow";
import "reactflow/dist/style.css";
import { api } from "@/lib/api/client";
import { keys } from "@/lib/query/keys";
import { useWsStore } from "@/lib/ws/store";
import { StatusBadge } from "@/components/status-badge";
import { EmptyState } from "@/components/states/empty-state";
import type { TopologyResponse, WorkflowResponse } from "@/lib/api/types.gen";

// ── NF type colours ──────────────────────────────────────────────────────────
const NF_COLOR: Record<string, string> = {
  NRF:   "#6366f1", // indigo
  AMF:   "#8b5cf6", // violet
  SMF:   "#a78bfa",
  UPF:   "#10b981", // emerald
  PCF:   "#f59e0b", // amber
  UDM:   "#f59e0b",
  NWDAF: "#06b6d4", // cyan
  DCF:   "#06b6d4",
  NEF:   "#3b82f6", // blue
  AF:    "#3b82f6",
  gNB:   "#ec4899", // pink
  Edge:  "#f97316", // orange
};

const STATUS_BORDER: Record<string, string> = {
  ACTIVE:     "#10b981",
  DEGRADED:   "#f59e0b",
  FAILED:     "#ef4444",
  RECOVERING: "#8b5cf6",
  STANDBY:    "#6b7280",
};

// ── Custom KG node ────────────────────────────────────────────────────────────
function KgNode({ data }: { data: { label: string; type: string; status: string; load: number; region: string; selected: boolean } }) {
  const color = NF_COLOR[data.type] ?? "#374151";
  const border = STATUS_BORDER[data.status] ?? "#374151";
  return (
    <div
      style={{
        background: data.selected ? `${color}33` : "rgba(24, 37, 68, 0.92)",
        border: `2px solid ${data.selected ? color : border}`,
        borderRadius: 10,
        padding: "6px 10px",
        minWidth: 100,
        cursor: "pointer",
        transition: "all 0.15s",
        boxShadow: data.selected ? `0 0 12px ${color}55` : "none",
      }}
    >
      <Handle type="target" position={Position.Left} style={{ opacity: 0 }} />
      <div style={{ fontWeight: 700, fontSize: 11, color, marginBottom: 2 }}>{data.type}</div>
      <div style={{ fontSize: 9, color: "#aebdd4", fontFamily: "monospace" }}>{data.label}</div>
      <div style={{ fontSize: 9, color: border, marginTop: 2 }}>{data.status}</div>
      {data.load > 0 && (
        <div style={{ marginTop: 3, height: 3, background: "#2a3c5e", borderRadius: 2, overflow: "hidden" }}>
          <div style={{ width: `${Math.min(data.load * 100, 100)}%`, height: "100%", background: color, borderRadius: 2 }} />
        </div>
      )}
      <Handle type="source" position={Position.Right} style={{ opacity: 0 }} />
    </div>
  );
}

const nodeTypes = { kgNode: KgNode };

// ── Relation edge label colours ──────────────────────────────────────────────
const REL_LABELS: Record<string, string> = {
  N2: "SIGNALS", N3: "ROUTES", N4: "CONTROLS",
  N6: "FORWARDS", N7: "ENFORCES", N8: "AUTHENTICATES",
  "": "CONNECTS",
};

// ── AI-learned relations from completed workflows ────────────────────────────
function extractLearnedRelations(workflows: WorkflowResponse[]): Array<{
  subject: string; relation: string; object: string; wf_id: string; ts: string;
}> {
  const relations: Array<{ subject: string; relation: string; object: string; wf_id: string; ts: string }> = [];
  for (const wf of workflows) {
    if (wf.status !== "completed") continue;
    const g = wf.goal.toLowerCase();
    // Deploy pattern
    if (g.includes("deploy") && g.includes("edge")) {
      const target = g.includes("mumbai") ? "edge_mumbai_1" : "edge_delhi_1";
      const modelMatch = g.match(/(\w+(?:_v\d)?)\s+model/) ?? g.match(/model[:\s]+(\w+)/);
      const model = modelMatch ? modelMatch[1] : "model";
      relations.push({ subject: `${model}_v1`, relation: "DEPLOYED_ON", object: target, wf_id: wf.id, ts: wf.created_at });
      relations.push({ subject: `workflow:${wf.id.slice(-6)}`, relation: "DEPLOYED_TO", object: target, wf_id: wf.id, ts: wf.created_at });
    }
    // Congestion pattern
    if (g.includes("congestion")) {
      const region = g.includes("mumbai") ? "Mumbai" : "Delhi";
      relations.push({ subject: "nwdaf_core_1", relation: "MONITORS_CONGESTION_IN", object: region, wf_id: wf.id, ts: wf.created_at });
    }
    // Load balance pattern
    if (g.includes("load") || g.includes("balance")) {
      relations.push({ subject: "smf_core_1", relation: "REBALANCED", object: "upf_delhi_1", wf_id: wf.id, ts: wf.created_at });
    }
    // Fault recovery
    if (g.includes("recover") || g.includes("fault")) {
      relations.push({ subject: `workflow:${wf.id.slice(-6)}`, relation: "RECOVERED", object: "nrf_core_1", wf_id: wf.id, ts: wf.created_at });
    }
  }
  return relations.slice(0, 20);
}

// ── Entity detail panel ───────────────────────────────────────────────────────
function EntityDetail({
  node,
  links,
  workflows,
  onClose,
}: {
  node: { id: string; type: string; region: string; status: string; load: number } | null;
  links: Array<{ src_id: string; dst_id: string; ref_point: string }>;
  workflows: WorkflowResponse[];
  onClose: () => void;
}) {
  if (!node) return null;

  const connected = links
    .filter((l) => l.src_id === node.id || l.dst_id === node.id)
    .map((l) => ({ id: l.src_id === node.id ? l.dst_id : l.src_id, ref: l.ref_point }));

  const touched = workflows.filter((w) =>
    w.goal.toLowerCase().includes(node.region.toLowerCase()) ||
    w.goal.toLowerCase().includes(node.type.toLowerCase())
  );

  const color = NF_COLOR[node.type] ?? "#374151";

  return (
    <div className="flex flex-col gap-3 h-full overflow-y-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full inline-block" style={{ background: color }} />
            <span className="font-bold text-primary text-sm">{node.id}</span>
          </div>
          <p className="text-xs text-faint mt-0.5">{node.type} · {node.region}</p>
        </div>
        <button onClick={onClose} className="text-faint hover:text-primary text-lg leading-none">×</button>
      </div>

      <StatusBadge status={node.status} />

      {/* Load bar */}
      {node.load > 0 && (
        <div>
          <p className="text-xs text-faint mb-1">Load: {Math.round(node.load * 100)}%</p>
          <div className="h-2 bg-border rounded-full overflow-hidden">
            <div
              className="h-2 rounded-full"
              style={{ width: `${Math.min(node.load * 100, 100)}%`, background: color }}
            />
          </div>
        </div>
      )}

      {/* Connections */}
      {connected.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-faint uppercase tracking-wider mb-2">Connected to</p>
          <ul className="flex flex-col gap-1">
            {connected.map((c) => (
              <li key={c.id} className="flex items-center gap-2 text-xs">
                <span className="text-ai font-mono">{c.id}</span>
                {c.ref && <span className="text-faint px-1.5 py-0.5 rounded bg-card border border-border">{c.ref}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Relevant workflows */}
      {touched.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-faint uppercase tracking-wider mb-2">Related workflows</p>
          <ul className="flex flex-col gap-1.5">
            {touched.slice(0, 5).map((w) => (
              <li key={w.id} className="text-xs">
                <StatusBadge status={w.status} />
                <span className="ml-1.5 text-muted">{w.goal.slice(0, 45)}…</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {touched.length === 0 && connected.length === 0 && (
        <p className="text-xs text-faint">No connections or related workflows yet.</p>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function KnowledgeGraphPage() {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const nfStatusById = useWsStore((s) => s.nfStatusById);

  const { data: topo } = useQuery({
    queryKey: keys.topology(),
    queryFn: () => api.get<TopologyResponse>("/topology"),
    refetchInterval: 10_000,
  });

  const { data: workflows = [] } = useQuery({
    queryKey: keys.workflows(),
    queryFn: () => api.get<WorkflowResponse[]>("/workflows?limit=30"),
    refetchInterval: 15_000,
  });

  // Build React Flow nodes
  const rfNodes: Node[] = useMemo(() => {
    if (!topo) return [];
    return topo.nodes.map((n) => ({
      id: n.id,
      type: "kgNode",
      position: {
        x: n.x && n.x !== 0 ? n.x : 300,
        y: n.y && n.y !== 0 ? n.y : 300,
      },
      data: {
        label: n.id,
        type: n.type,
        status: nfStatusById[n.id] ?? n.status,
        load: n.load,
        region: n.region,
        selected: n.id === selectedNodeId,
      },
    }));
  }, [topo, nfStatusById, selectedNodeId]);

  // Build React Flow edges
  const rfEdges: Edge[] = useMemo(() => {
    if (!topo) return [];
    return topo.links.map((l) => ({
      id: l.id,
      source: l.src_id,
      target: l.dst_id,
      label: REL_LABELS[l.ref_point] ?? l.ref_point,
      style: { stroke: "#4a6294", strokeWidth: 1.5 },
      labelStyle: { fill: "#8698b0", fontSize: 9 },
      animated: false,
    }));
  }, [topo]);

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    setSelectedNodeId((prev) => (prev === node.id ? null : node.id));
  }, []);

  const selectedNode = topo?.nodes.find((n) => n.id === selectedNodeId) ?? null;
  const learnedRelations = useMemo(() => extractLearnedRelations(workflows), [workflows]);

  // Region breakdown
  const regionCounts = useMemo(() => {
    if (!topo) return {};
    return topo.nodes.reduce<Record<string, number>>((acc, n) => {
      acc[n.region] = (acc[n.region] ?? 0) + 1;
      return acc;
    }, {});
  }, [topo]);

  return (
    <div className="flex flex-col gap-4 h-full">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-lg font-bold text-primary">Knowledge Graph</h1>
          <p className="text-xs text-faint mt-0.5">
            Network entity relationships known to the AI agents
          </p>
        </div>
        <div className="flex gap-3">
          {Object.entries(regionCounts).map(([region, count]) => (
            <span key={region} className="px-2 py-1 rounded bg-card border border-border text-xs text-muted">
              {region}: {count} entities
            </span>
          ))}
        </div>
      </div>

      {/* Main content */}
      <div className="flex gap-4 flex-1" style={{ minHeight: 500 }}>
        {/* Graph canvas */}
        <div
          className="flex-1 bg-card border border-border rounded-lg overflow-hidden"
          style={{ minHeight: 480 }}
        >
          {!topo ? (
            <div className="flex items-center justify-center h-full">
              <EmptyState message="Loading network graph…" />
            </div>
          ) : (
            <ReactFlow
              nodes={rfNodes}
              edges={rfEdges}
              nodeTypes={nodeTypes}
              onNodeClick={onNodeClick}
              fitView
              fitViewOptions={{ padding: 0.2 }}
              minZoom={0.3}
              maxZoom={2}
            >
              <Background color="#2a3c5e" gap={20} />
              <Controls />
            </ReactFlow>
          )}
        </div>

        {/* Entity detail panel */}
        {selectedNode && (
          <div className="w-64 shrink-0 bg-card border border-border rounded-lg p-4">
            <EntityDetail
              node={selectedNode}
              links={topo?.links ?? []}
              workflows={workflows}
              onClose={() => setSelectedNodeId(null)}
            />
          </div>
        )}
      </div>

      {/* AI-learned relations strip */}
      <div className="bg-card border border-border rounded-lg p-4">
        <div className="flex items-center gap-2 mb-3">
          <span className="text-xs font-semibold text-ai uppercase tracking-wider">
            AI-Learned Relations
          </span>
          <span className="text-xs text-faint">— extracted from completed workflows</span>
          <span className="ml-auto px-2 py-0.5 rounded bg-ai/10 text-ai text-xs">
            {learnedRelations.length} facts
          </span>
        </div>
        {learnedRelations.length === 0 ? (
          <p className="text-xs text-faint">
            No learned relations yet. Complete a workflow (e.g. Deploy congestion model to Delhi Edge) to see AI-extracted knowledge here.
          </p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {learnedRelations.map((r, i) => (
              <div
                key={i}
                className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-card-hover border border-border text-xs"
                title={`from workflow ${r.wf_id}`}
              >
                <span className="text-primary font-mono">{r.subject}</span>
                <span className="text-ai font-semibold">→ {r.relation} →</span>
                <span className="text-ok font-mono">{r.object}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-3 px-1">
        {Object.entries(NF_COLOR).map(([type, color]) => (
          <span key={type} className="flex items-center gap-1 text-xs text-faint">
            <span className="w-2.5 h-2.5 rounded-sm inline-block" style={{ background: color }} />
            {type}
          </span>
        ))}
      </div>
    </div>
  );
}
