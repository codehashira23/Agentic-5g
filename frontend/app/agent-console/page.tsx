"use client";
import { Suspense } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api/client";
import { keys } from "@/lib/query/keys";
import { useWsStore } from "@/lib/ws/store";
import { Panel } from "@/components/panel";
import { StatusBadge } from "@/components/status-badge";
import { TimelineStepper } from "@/components/timeline-stepper";
import { EmptyState } from "@/components/states/empty-state";
import type { WorkflowResponse } from "@/lib/api/types.gen";

function WorkflowRow({ wf, selected, onClick }: { wf: WorkflowResponse; selected: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`w-full text-left flex items-center gap-3 px-3 py-2 rounded-lg transition-colors
        ${selected ? "bg-ai/10 border border-ai/30" : "hover:bg-card-hover"}`}
    >
      <StatusBadge status={wf.status} />
      <span className="flex-1 text-sm text-primary truncate">{wf.goal}</span>
      <span className="text-xs text-faint font-mono">{wf.id.slice(-6)}</span>
    </button>
  );
}

export default function AgentConsolePage() {
  return (
    <Suspense fallback={<div className="p-6 text-muted text-sm">Loading…</div>}>
      <AgentConsoleInner />
    </Suspense>
  );
}

function AgentConsoleInner() {
  const searchParams = useSearchParams();
  const selectedId = searchParams.get("wf");

  const { data: workflows = [] } = useQuery({
    queryKey: keys.workflows(),
    queryFn: () => api.get<WorkflowResponse[]>("/workflows"),
    refetchInterval: 3000,
  });

  // Find the selected workflow to get its real stage and status
  const selectedWf = workflows.find((w) => w.id === selectedId) ?? null;

  const { data: trace = [] } = useQuery({
    queryKey: keys.trace(selectedId ?? ""),
    queryFn: () =>
      api.get<Array<{ stage: string; agent_role: string; rationale: string; ts: string }>>(
        `/workflows/${selectedId}/trace`,
      ),
    enabled: !!selectedId,
    // Refetch trace when workflow completes
    refetchInterval: selectedWf?.status === "running" ? 2000 : false,
  });

  function selectWorkflow(id: string) {
    const url = new URL(window.location.href);
    url.searchParams.set("wf", id);
    window.history.pushState({}, "", url.toString());
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-lg font-bold text-primary">Agent Console</h1>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Workflow list */}
        <Panel title="Workflows" className="lg:col-span-1">
          {workflows.length === 0 ? (
            <EmptyState message="No workflows yet — submit an intent above." />
          ) : (
            <ul className="flex flex-col gap-1">
              {workflows.map((wf) => (
                <li key={wf.id}>
                  <WorkflowRow
                    wf={wf}
                    selected={wf.id === selectedId}
                    onClick={() => selectWorkflow(wf.id)}
                  />
                </li>
              ))}
            </ul>
          )}
        </Panel>

        {/* Detail panel */}
        <div className="lg:col-span-2 flex flex-col gap-4">
          {selectedWf ? (
            <>
              <Panel title="Lifecycle">
                {/* Use real stage + status from the workflow row */}
                <TimelineStepper
                  stage={selectedWf.stage ?? "observe"}
                  status={selectedWf.status ?? "running"}
                />
                <div className="mt-3 flex items-center gap-2">
                  <StatusBadge status={selectedWf.status} />
                  <span className="text-xs text-faint font-mono">{selectedWf.id}</span>
                  <span className="text-xs text-muted truncate ml-auto">{selectedWf.goal}</span>
                </div>
              </Panel>
              <Panel title="Reasoning Trace">
                {trace.length === 0 ? (
                  <EmptyState message={
                    selectedWf.status === "running"
                      ? "Agents are working — trace will appear here as each stage completes."
                      : "No trace recorded for this workflow."
                  } />
                ) : (
                  <ul className="flex flex-col gap-3">
                    {trace.map((t, i) => (
                      <li key={i} className="text-xs border-l-2 border-l-ai pl-3">
                        <div className="flex items-center gap-2 mb-0.5">
                          <span className="font-semibold text-ai capitalize">{t.stage}</span>
                          {t.agent_role && (
                            <span className="text-faint">— {t.agent_role}</span>
                          )}
                          {t.ts && (
                            <span className="text-faint ml-auto font-mono">
                              {new Date(t.ts).toLocaleTimeString()}
                            </span>
                          )}
                        </div>
                        <p className="text-muted leading-relaxed">{t.rationale || "…"}</p>
                      </li>
                    ))}
                  </ul>
                )}
              </Panel>
            </>
          ) : selectedId ? (
            <EmptyState message="Loading workflow…" />
          ) : (
            <EmptyState message="Select a workflow to inspect its reasoning." />
          )}
        </div>
      </div>
    </div>
  );
}
