"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Zap, Radio, Shield, Brain, Play, CheckCircle2,
  XCircle, Loader2, ChevronRight, Clock,
} from "lucide-react";
import { api } from "@/lib/api/client";
import { keys } from "@/lib/query/keys";
import { Panel } from "@/components/panel";
import { StatusBadge } from "@/components/status-badge";
import type { WorkflowResponse } from "@/lib/api/types.gen";

// ── Scenario definitions ──────────────────────────────────────────────────────
const SCENARIOS = [
  {
    id: "scenario-a",
    title: "Scenario A — Model Deployment",
    subtitle: "AI deploys a congestion detection model to Delhi Edge",
    goal: "Deploy congestion detection model to Delhi Edge",
    icon: Brain,
    color: "#6366f1",
    bgColor: "bg-[#6366f1]/10",
    borderColor: "border-[#6366f1]/30",
    steps: ["Observe Delhi network state", "Plan model deployment", "Deploy to edge_delhi_1 via AIMLE", "Validate deployment success"],
    expectedOutcome: "congestion_v1 deployed and active on edge_delhi_1",
    trigger: "user",
  },
  {
    id: "scenario-b",
    title: "Scenario B — UPF Recovery",
    subtitle: "AI detects UPF failure and load-balances to Mumbai",
    goal: "UPF upf_delhi_1 has failed in Delhi. Load balance active sessions to Mumbai UPF and restore network connectivity.",
    icon: Zap,
    color: "#f59e0b",
    bgColor: "bg-[#f59e0b]/10",
    borderColor: "border-[#f59e0b]/30",
    steps: ["Observe Delhi UPF failure", "Reason about load balancing", "Apply load balance to Mumbai UPF", "Validate connectivity restored"],
    expectedOutcome: "Sessions load-balanced from upf_delhi_1 to upf_mumbai_1",
    trigger: "user",
  },
  {
    id: "scenario-c",
    title: "Scenario C — NRF Recovery",
    subtitle: "AI promotes standby NRF when primary NRF fails",
    goal: "NRF nrf_core_1 has failed. Promote standby NRF (nrf_standby_1) and trigger re-registration of all affected network functions.",
    icon: Shield,
    color: "#ef4444",
    bgColor: "bg-[#ef4444]/10",
    borderColor: "border-[#ef4444]/30",
    steps: ["Observe NRF failure in Core", "Plan standby promotion", "Promote nrf_standby_1 to active", "Re-register affected NFs"],
    expectedOutcome: "nrf_standby_1 promoted and all NFs re-registered",
    trigger: "user",
  },
  {
    id: "scenario-d",
    title: "Scenario D — Mumbai Deployment",
    subtitle: "AI deploys traffic prediction model to Mumbai Edge",
    goal: "Deploy traffic prediction model to Mumbai Edge",
    icon: Radio,
    color: "#10b981",
    bgColor: "bg-[#10b981]/10",
    borderColor: "border-[#10b981]/30",
    steps: ["Observe Mumbai network state", "Plan model deployment", "Deploy to edge_mumbai_1 via AIMLE", "Validate deployment success"],
    expectedOutcome: "traffic_v1 deployed and active on edge_mumbai_1",
    trigger: "user",
  },
];

const STAGES = ["observe", "reason", "plan", "execute", "validate", "complete"];

// ── Stage progress bar ────────────────────────────────────────────────────────
function StageProgress({ currentStage, status }: { currentStage: string; status: string }) {
  const currentIdx = STAGES.indexOf(currentStage);
  return (
    <div className="flex items-center gap-1 mt-3">
      {STAGES.map((stage, i) => {
        const isDone = i < currentIdx || status === "completed";
        const isCurrent = i === currentIdx && status === "running";
        const isFailed = status === "failed" && i === currentIdx;
        return (
          <div key={stage} className="flex items-center gap-1 flex-1">
            <div className={`flex-1 h-1.5 rounded-full transition-all ${
              isDone ? "bg-ok" :
              isFailed ? "bg-crit" :
              isCurrent ? "bg-ai animate-pulse" :
              "bg-border"
            }`} />
            {i < STAGES.length - 1 && (
              <ChevronRight className={`w-2.5 h-2.5 shrink-0 ${isDone ? "text-ok" : "text-faint"}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Running workflow card ─────────────────────────────────────────────────────
function RunningWorkflowCard({
  wf,
  scenarioColor,
}: {
  wf: WorkflowResponse;
  scenarioColor: string;
}) {
  type TraceEntry = { stage: string; agent_role: string; rationale: string; ts: string };

  const { data: trace = [] } = useQuery<TraceEntry[]>({
    queryKey: keys.trace(wf.id),
    queryFn: () => api.get<TraceEntry[]>(`/workflows/${wf.id}/trace`),
    refetchInterval: wf.status === "running" ? 2000 : 5000,
    staleTime: 0,
  });

  const isRunning = wf.status === "running";
  const isDone = wf.status === "completed";
  const isFailed = wf.status === "failed";

  return (
    <div className="border border-border rounded-xl p-4 bg-card flex flex-col gap-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {isRunning && <Loader2 className="w-4 h-4 animate-spin" style={{ color: scenarioColor }} />}
          {isDone && <CheckCircle2 className="w-4 h-4 text-ok" />}
          {isFailed && <XCircle className="w-4 h-4 text-crit" />}
          <StatusBadge status={wf.status} />
          <span className="text-xs font-mono text-faint">{wf.id.slice(-8)}</span>
        </div>
        <span className="text-xs text-faint flex items-center gap-1">
          <Clock className="w-3 h-3" />
          {new Date(wf.created_at).toLocaleTimeString()}
        </span>
      </div>

      {/* Stage progress */}
      <div>
        <div className="flex items-center justify-between mb-1">
          {STAGES.map((s) => (
            <span
              key={s}
              className={`text-[9px] capitalize font-medium ${
                wf.stage === s ? "text-ai" :
                STAGES.indexOf(s) < STAGES.indexOf(wf.stage) || isDone ? "text-ok" :
                "text-faint"
              }`}
            >
              {s}
            </span>
          ))}
        </div>
        <StageProgress currentStage={wf.stage} status={wf.status} />
      </div>

      {/* Latest trace entry */}
      {trace.length > 0 && (
        <div className="border-l-2 pl-3" style={{ borderColor: scenarioColor }}>
          <p className="text-[10px] font-semibold uppercase tracking-wider mb-0.5"
            style={{ color: scenarioColor }}>
            {trace[trace.length - 1].stage} — {trace[trace.length - 1].agent_role}
          </p>
          <p className="text-xs text-muted leading-relaxed">
            {trace[trace.length - 1].rationale?.slice(0, 200) || "…"}
          </p>
        </div>
      )}

      {/* Full trace when done */}
      {isDone && trace.length > 1 && (
        <details className="mt-1">
          <summary className="text-xs text-ai cursor-pointer hover:text-primary">
            View full reasoning trace ({trace.length} entries)
          </summary>
          <ul className="mt-2 flex flex-col gap-2">
            {trace.map((t, i) => (
              <li key={i} className="text-xs border-l-2 border-border pl-2">
                <span className="font-semibold text-ai capitalize">{t.stage}</span>
                <span className="text-faint"> — {t.agent_role}</span>
                <p className="text-muted mt-0.5">{t.rationale?.slice(0, 150) || "—"}</p>
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}

// ── Scenario card ─────────────────────────────────────────────────────────────
function ScenarioCard({
  scenario,
  onLaunch,
  isLaunching,
  activeWf,
}: {
  scenario: typeof SCENARIOS[0];
  onLaunch: () => void;
  isLaunching: boolean;
  activeWf: WorkflowResponse | null;
}) {
  const Icon = scenario.icon;

  return (
    <div className={`border rounded-xl p-5 flex flex-col gap-4 transition-all
      ${scenario.bgColor} ${scenario.borderColor}`}>
      {/* Header */}
      <div className="flex items-start gap-3">
        <div className="p-2 rounded-lg shrink-0" style={{ background: `${scenario.color}22` }}>
          <Icon className="w-5 h-5" style={{ color: scenario.color }} />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-bold text-primary">{scenario.title}</h3>
          <p className="text-xs text-muted mt-0.5">{scenario.subtitle}</p>
        </div>
      </div>

      {/* Steps */}
      <div className="flex flex-col gap-1.5">
        {scenario.steps.map((step, i) => (
          <div key={i} className="flex items-start gap-2 text-xs text-muted">
            <span className="w-4 h-4 rounded-full flex items-center justify-center shrink-0 mt-0.5
                           text-[10px] font-bold"
              style={{ background: `${scenario.color}33`, color: scenario.color }}>
              {i + 1}
            </span>
            {step}
          </div>
        ))}
      </div>

      {/* Expected outcome */}
      <div className="rounded-lg p-2.5 text-xs text-muted bg-card border border-border">
        <span className="font-semibold text-faint">Expected: </span>
        {scenario.expectedOutcome}
      </div>

      {/* Launch button */}
      <button
        onClick={onLaunch}
        disabled={isLaunching || activeWf?.status === "running"}
        className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm
                   font-semibold transition-all disabled:opacity-40 disabled:cursor-not-allowed"
        style={{
          background: `${scenario.color}22`,
          color: scenario.color,
          border: `1px solid ${scenario.color}44`,
        }}
      >
        {isLaunching ? (
          <><Loader2 className="w-4 h-4 animate-spin" /> Launching…</>
        ) : activeWf?.status === "running" ? (
          <><Loader2 className="w-4 h-4 animate-spin" /> Running…</>
        ) : (
          <><Play className="w-4 h-4" /> Launch Scenario</>
        )}
      </button>

      {/* Active workflow for this scenario */}
      {activeWf && (
        <RunningWorkflowCard wf={activeWf} scenarioColor={scenario.color} />
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function WorkflowBuilderPage() {
  const qc = useQueryClient();
  // Track which scenario launched which workflow
  const [scenarioWfMap, setScenarioWfMap] = useState<Record<string, string>>({});
  const [launchingId, setLaunchingId] = useState<string | null>(null);

  // Recent workflows to match back to scenarios
  const { data: workflows = [] } = useQuery<WorkflowResponse[]>({
    queryKey: keys.workflows(),
    queryFn: () => api.get<WorkflowResponse[]>("/workflows?limit=20"),
    refetchInterval: 3000,
  });

  const launchMut = useMutation({
    mutationFn: ({ goal }: { goal: string }) =>
      api.post<WorkflowResponse>("/workflows", { goal }),
    onSuccess: (wf, { goal }) => {
      // Find which scenario this was for
      const scenario = SCENARIOS.find((s) => s.goal === goal);
      if (scenario) {
        setScenarioWfMap((prev) => ({ ...prev, [scenario.id]: wf.id }));
      }
      setLaunchingId(null);
      qc.invalidateQueries({ queryKey: keys.workflows() });
    },
    onError: () => setLaunchingId(null),
  });

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div>
        <h1 className="text-lg font-bold text-primary">Workflow Builder</h1>
        <p className="text-xs text-faint mt-1">
          Launch pre-built 5G AI scenarios. Each scenario runs the full
          Observe → Reason → Plan → Execute → Validate → Complete lifecycle.
        </p>
      </div>

      {/* How it works banner */}
      <div className="flex items-center gap-6 p-4 rounded-xl bg-ai/5 border border-ai/20">
        {STAGES.map((stage, i) => (
          <div key={stage} className="flex items-center gap-2">
            <span className="text-xs font-semibold text-ai capitalize">{stage}</span>
            {i < STAGES.length - 1 && <ChevronRight className="w-3 h-3 text-faint shrink-0" />}
          </div>
        ))}
        <span className="ml-auto text-xs text-faint">Powered by Groq · llama-3.1-8b-instant</span>
      </div>

      {/* Scenario grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {SCENARIOS.map((scenario) => {
          const wfId = scenarioWfMap[scenario.id];
          const activeWf = wfId
            ? workflows.find((w) => w.id === wfId) ?? null
            : null;

          return (
            <ScenarioCard
              key={scenario.id}
              scenario={scenario}
              isLaunching={launchingId === scenario.id}
              activeWf={activeWf}
              onLaunch={() => {
                setLaunchingId(scenario.id);
                launchMut.mutate({ goal: scenario.goal });
              }}
            />
          );
        })}
      </div>

      {/* Recent runs */}
      {workflows.filter((w) => !Object.values(scenarioWfMap).includes(w.id)).length > 0 && (
        <Panel title="Other Recent Workflows">
          <div className="flex flex-col gap-2">
            {workflows
              .filter((w) => !Object.values(scenarioWfMap).includes(w.id))
              .slice(0, 5)
              .map((wf) => (
                <div key={wf.id} className="flex items-center gap-3 text-xs py-1.5 border-b border-border/50">
                  <StatusBadge status={wf.status} />
                  <span className="flex-1 text-muted truncate">{wf.goal}</span>
                  <span className="font-mono text-faint">{wf.id.slice(-8)}</span>
                </div>
              ))}
          </div>
        </Panel>
      )}
    </div>
  );
}
