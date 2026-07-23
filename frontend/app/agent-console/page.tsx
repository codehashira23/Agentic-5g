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

function WorkflowRow({ wf, onClick }: { wf: WorkflowResponse; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-card-hover transition-colors"
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

  const { data: trace = [] } = useQuery({
    queryKey: keys.trace(selectedId ?? ""),
    queryFn: () =>
      api.get<Array<{ stage: string; agent_role: string; rationale: string }>>(
        `/workflows/${selectedId}/trace`,
      ),
    enabled: !!selectedId,
  });

  const eventFeed = useWsStore((s) => s.eventFeed);
  const liveStage = eventFeed.find(
    (e) =>
      e.type === "WORKFLOW_STAGE_CHANGED" &&
      "payload" in e &&
      (e.payload as { workflow_id?: string }).workflow_id === selectedId,
  );

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
                    onClick={() => {
                      const url = new URL(window.location.href);
                      url.searchParams.set("wf", wf.id);
                      window.history.pushState({}, "", url.toString());
                    }}
                  />
                </li>
              ))}
            </ul>
          )}
        </Panel>

        {/* Detail panel */}
        <div className="lg:col-span-2 flex flex-col gap-4">
          {selectedId ? (
            <>
              <Panel title="Lifecycle">
                <TimelineStepper stage="observe" status="running" />
              </Panel>
              <Panel title="Reasoning Trace">
                {trace.length === 0 ? (
                  <EmptyState message="No trace yet." />
                ) : (
                  <ul className="flex flex-col gap-3">
                    {trace.map((t, i) => (
                      <li key={i} className="text-xs border-l-2 border-l-ai pl-3">
                        <p className="font-semibold text-ai capitalize">
                          {t.stage} — {t.agent_role}
                        </p>
                        <p className="text-muted mt-0.5">{t.rationale || "…"}</p>
                      </li>
                    ))}
                  </ul>
                )}
              </Panel>
            </>
          ) : (
            <EmptyState message="Select a workflow to inspect its reasoning." />
          )}
        </div>
      </div>
    </div>
  );
}
