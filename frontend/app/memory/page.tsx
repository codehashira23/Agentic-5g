"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Brain, Clock, CheckCircle2, XCircle, Loader2, BookOpen, Cpu } from "lucide-react";
import { api } from "@/lib/api/client";
import { keys } from "@/lib/query/keys";
import { Panel } from "@/components/panel";
import { EmptyState } from "@/components/states/empty-state";
import { StatusBadge } from "@/components/status-badge";
import type { WorkflowResponse } from "@/lib/api/types.gen";

// ── helpers ──────────────────────────────────────────────────────────────────
function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const s = Math.floor(diff / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

// ── Summary hook — fetches doc agent narrative for one workflow ───────────────
function useWorkflowSummary(id: string | null) {
  return useQuery<{
    narrative: string;
    outcome: string;
    evidence: string[];
    lessons: string[];
  }>({
    queryKey: ["workflows", id, "summary"],
    queryFn: () => api.get(`/workflows/${id}/summary`),
    enabled: !!id,
    staleTime: 60_000,
  });
}

// ── Episodic memory card ──────────────────────────────────────────────────────
function EpisodicCard({ wf }: { wf: WorkflowResponse }) {
  const [expanded, setExpanded] = useState(false);
  const { data: summary, isLoading } = useWorkflowSummary(
    expanded ? wf.id : null
  );

  const isCompleted = wf.status === "completed";

  return (
    <div
      className={`rounded-lg border p-4 transition-colors cursor-pointer
        ${isCompleted ? "border-ok/30 bg-ok/5" : "border-crit/30 bg-crit/5"}`}
      onClick={() => setExpanded((v) => !v)}
    >
      {/* Header row */}
      <div className="flex items-start gap-3">
        <div className="mt-0.5 shrink-0">
          {isCompleted
            ? <CheckCircle2 className="w-4 h-4 text-ok" />
            : <XCircle className="w-4 h-4 text-crit" />}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-primary truncate">{wf.goal}</p>
          <div className="flex items-center gap-3 mt-1">
            <StatusBadge status={wf.status} />
            <span className="text-xs text-faint flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {timeAgo(wf.created_at)}
            </span>
            <span className="text-xs text-faint font-mono">{wf.id.slice(-8)}</span>
          </div>
        </div>
        <span className="text-xs text-faint shrink-0">{expanded ? "▲" : "▼"}</span>
      </div>

      {/* Expanded: doc agent narrative */}
      {expanded && (
        <div className="mt-3 pt-3 border-t border-border/40">
          {isLoading ? (
            <div className="flex items-center gap-2 text-xs text-faint">
              <Loader2 className="w-3 h-3 animate-spin" />
              Loading summary…
            </div>
          ) : summary?.narrative ? (
            <div className="flex flex-col gap-2">
              <p className="text-xs text-muted leading-relaxed">{summary.narrative}</p>
              {summary.evidence.length > 0 && (
                <div>
                  <p className="text-[10px] text-faint font-semibold uppercase tracking-wider mb-1">
                    Evidence
                  </p>
                  <ul className="flex flex-col gap-0.5">
                    {summary.evidence.map((e, i) => (
                      <li key={i} className="text-xs text-muted pl-2 border-l border-ok/40">
                        {e}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {summary.lessons.length > 0 && (
                <div>
                  <p className="text-[10px] text-faint font-semibold uppercase tracking-wider mb-1">
                    Lessons learned
                  </p>
                  <ul className="flex flex-col gap-0.5">
                    {summary.lessons.map((l, i) => (
                      <li key={i} className="text-xs text-muted pl-2 border-l border-ai/40">
                        {l}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <p className="text-xs text-faint">No summary available for this workflow.</p>
          )}
        </div>
      )}
    </div>
  );
}

// ── Semantic memory — extract facts from rationale text ──────────────────────
function SemanticPanel({ workflows }: { workflows: WorkflowResponse[] }) {
  const completed = workflows.filter((w) => w.status === "completed");

  // Extract semantic facts from workflow goals + outcomes — deduplicated
  const seen = new Set<string>();
  const facts = completed.flatMap((wf) => {
    const facts: string[] = [];
    const g = wf.goal.toLowerCase();
    if (g.includes("deploy") && g.includes("edge")) {
      const match = g.match(/edge[_\s]?\w*/);
      const node = match ? match[0].replace(/\s/, "_") : "edge node";
      facts.push(`Model deployed on ${node} — ${timeAgo(wf.created_at)}`);
    }
    if (g.includes("congestion")) {
      facts.push(`Congestion monitoring configured — ${timeAgo(wf.created_at)}`);
    }
    if (g.includes("fault") || g.includes("recover")) {
      facts.push(`Recovery action executed — ${timeAgo(wf.created_at)}`);
    }
    if (g.includes("load") || g.includes("balance")) {
      facts.push(`Load balancing applied — ${timeAgo(wf.created_at)}`);
    }
    if (facts.length === 0) {
      facts.push(`"${wf.goal.slice(0, 50)}" — ${timeAgo(wf.created_at)}`);
    }
    return facts;
  }).filter((f) => {
    // Deduplicate by fact text prefix (ignore timestamp)
    const key = f.split(" — ")[0].toLowerCase();
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });

  if (facts.length === 0) {
    return (
      <EmptyState message="Semantic facts accumulate as workflows complete. Run Scenario A to populate." />
    );
  }

  return (
    <ul className="flex flex-col gap-2">
      {facts.map((f, i) => (
        <li key={i} className="flex items-start gap-2 text-xs">
          <span className="w-1.5 h-1.5 rounded-full bg-ai mt-1.5 shrink-0" />
          <span className="text-muted">{f}</span>
        </li>
      ))}
    </ul>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function MemoryPage() {
  // Completed workflows — episodic memory
  const { data: completed = [] } = useQuery<WorkflowResponse[]>({
    queryKey: [...keys.workflows({ status: "completed" })],
    queryFn: () => api.get<WorkflowResponse[]>("/workflows?status=completed&limit=20"),
    refetchInterval: 10_000,
  });

  // All recent workflows for stats
  const { data: allWorkflows = [] } = useQuery<WorkflowResponse[]>({
    queryKey: keys.workflows(),
    queryFn: () => api.get<WorkflowResponse[]>("/workflows?limit=50"),
    refetchInterval: 10_000,
  });

  const successCount = allWorkflows.filter((w) => w.status === "completed").length;
  const failedCount = allWorkflows.filter((w) => w.status === "failed").length;
  const { data: running = [] } = useQuery<WorkflowResponse[]>({
    queryKey: [...keys.workflows({ status: "running" })],
    queryFn: () => api.get<WorkflowResponse[]>("/workflows?status=running&limit=5"),
    refetchInterval: 3000,
  });

  // Only show as "active" if started within the last 10 minutes
  const recentRunning = running.filter((w) => {
    const age = Date.now() - new Date(w.created_at).getTime();
    return age < 10 * 60 * 1000; // 10 minutes
  });
  const activeWf = recentRunning[0] ?? null;

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Brain className="w-5 h-5 text-ai" />
        <h1 className="text-lg font-bold text-primary">Memory Viewer</h1>
        <span className="text-xs text-faint ml-2">
          How the AI agents remember and learn from past operations
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* ── Left: Episodic memory ── */}
        <div className="lg:col-span-2 flex flex-col gap-4">
          {/* Working memory — live */}
          <Panel
            title="Working Memory"
            className={activeWf ? "border-ai/30" : ""}
          >
            {activeWf ? (
              <div className="flex items-center gap-3 p-2 rounded-lg bg-ai/10 border border-ai/20">
                <Loader2 className="w-4 h-4 text-ai animate-spin shrink-0" />
                <div>
                  <p className="text-sm font-medium text-primary">{activeWf.goal}</p>
                  <p className="text-xs text-faint mt-0.5">
                    Currently at <span className="text-ai font-semibold capitalize">{activeWf.stage}</span> stage
                    · {timeAgo(activeWf.created_at)}
                  </p>
                </div>
              </div>
            ) : (
              <p className="text-xs text-faint py-2 text-center">
                No active workflow — working memory is clear
              </p>
            )}
          </Panel>

          {/* Episodic memory */}
          <Panel
            title={`Episodic Memory — ${completed.length} recorded operation${completed.length !== 1 ? "s" : ""}`}
          >
            {completed.length === 0 ? (
              <EmptyState message="No completed workflows yet. Submit a goal in the top bar to create the first memory." />
            ) : (
              <div className="flex flex-col gap-3">
                <p className="text-xs text-faint">
                  Click any memory to expand the agent's reasoning and lessons learned.
                </p>
                {completed.map((wf) => (
                  <EpisodicCard key={wf.id} wf={wf} />
                ))}
              </div>
            )}
          </Panel>
        </div>

        {/* ── Right: Semantic memory + stats ── */}
        <div className="flex flex-col gap-4">
          {/* Memory stats */}
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-lg border border-border bg-card p-3 text-center">
              <p className="text-2xl font-bold text-ok">{successCount}</p>
              <p className="text-xs text-faint mt-1">Successful ops</p>
            </div>
            <div className="rounded-lg border border-border bg-card p-3 text-center">
              <p className="text-2xl font-bold text-crit">{failedCount}</p>
              <p className="text-xs text-faint mt-1">Failed ops</p>
            </div>
          </div>

          {/* Semantic memory */}
          <Panel title="Semantic Memory">
            <div className="flex items-center gap-2 mb-3">
              <BookOpen className="w-3.5 h-3.5 text-ai" />
              <span className="text-xs text-faint">Extracted facts from completed operations</span>
            </div>
            <SemanticPanel workflows={completed} />
          </Panel>

          {/* Memory explanation */}
          <Panel title="About Memory">
            <div className="flex flex-col gap-3 text-xs text-muted">
              <div className="flex gap-2">
                <Cpu className="w-3.5 h-3.5 text-ai shrink-0 mt-0.5" />
                <div>
                  <p className="font-semibold text-primary mb-0.5">Working Memory</p>
                  <p>Active context of the currently executing workflow — what the agents are doing right now.</p>
                </div>
              </div>
              <div className="flex gap-2">
                <Clock className="w-3.5 h-3.5 text-ok shrink-0 mt-0.5" />
                <div>
                  <p className="font-semibold text-primary mb-0.5">Episodic Memory</p>
                  <p>Record of past operations — what was attempted, what succeeded, what failed. Agents use this to avoid repeating mistakes.</p>
                </div>
              </div>
              <div className="flex gap-2">
                <Brain className="w-3.5 h-3.5 text-warn shrink-0 mt-0.5" />
                <div>
                  <p className="font-semibold text-primary mb-0.5">Semantic Memory</p>
                  <p>Extracted facts and learned patterns — which nodes respond best to which operations.</p>
                </div>
              </div>
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}
