"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Play, Pause, SkipForward, RefreshCw, Zap } from "lucide-react";
import { api } from "@/lib/api/client";
import { keys } from "@/lib/query/keys";
import { Panel } from "@/components/panel";
import { StatusBadge } from "@/components/status-badge";
import { useState } from "react";

export default function SimulationPage() {
  const qc = useQueryClient();
  const [faultNfId, setFaultNfId] = useState("");

  const { data: status } = useQuery({
    queryKey: keys.simStatus(),
    queryFn: () => api.get<{ status: string; tick: number; seed: number }>("/simulation/status"),
    refetchInterval: 2000,
  });

  const mutate = (path: string, body?: object) => () =>
    api.post(path, body ?? {}).then(() => qc.invalidateQueries({ queryKey: keys.simStatus() }));

  const startMut = useMutation({ mutationFn: mutate("/simulation/start") });
  const pauseMut = useMutation({ mutationFn: mutate("/simulation/pause") });
  const stepMut = useMutation({ mutationFn: mutate("/simulation/step", { ticks: 1 }) });
  const resetMut = useMutation({ mutationFn: mutate("/simulation/reset") });
  const faultMut = useMutation({
    mutationFn: () => api.post("/simulation/fault", { nf_id: faultNfId, type: "fail" }),
    onSuccess: () => setFaultNfId(""),
  });

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-lg font-bold text-primary">Simulation</h1>

      <Panel title="Controls">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 mr-4">
            <span className="text-xs text-muted">Status:</span>
            <StatusBadge status={status?.status ?? "stopped"} />
            <span className="text-xs text-faint">tick {status?.tick ?? 0}</span>
          </div>
          <button onClick={() => startMut.mutate()} className="btn-icon" aria-label="Start">
            <Play className="w-4 h-4" />
          </button>
          <button onClick={() => pauseMut.mutate()} className="btn-icon" aria-label="Pause">
            <Pause className="w-4 h-4" />
          </button>
          <button onClick={() => stepMut.mutate()} className="btn-icon" aria-label="Step">
            <SkipForward className="w-4 h-4" />
          </button>
          <button
            onClick={() => resetMut.mutate()}
            className="btn-icon text-warn"
            aria-label="Reset"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </Panel>

      <Panel title="Fault Injection">
        <p className="text-xs text-faint mb-3">
          Inject a failure on any network function. The autonomous recovery agent will detect it and start a recovery workflow automatically.
        </p>
        <div className="flex gap-2 items-center">
          <input
            value={faultNfId}
            onChange={(e) => setFaultNfId(e.target.value)}
            placeholder="NF id — e.g. upf_delhi_1, nrf_core_1, edge_delhi_1"
            className="flex-1 bg-card border border-border rounded px-3 py-1.5 text-sm text-primary placeholder:text-faint focus:outline-none focus:border-crit"
          />
          <button
            onClick={() => faultMut.mutate()}
            disabled={!faultNfId || faultMut.isPending}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-crit/15 text-crit rounded text-sm hover:bg-crit/25 disabled:opacity-40"
            aria-label="Inject fault"
          >
            <Zap className="w-3 h-3" /> Inject Fail
          </button>
        </div>
        {faultMut.isSuccess && (
          <p className="mt-2 text-xs text-ok">
            Fault injected — check Agent Console for the autonomous recovery workflow.
          </p>
        )}
        {faultMut.isError && (
          <p className="mt-2 text-xs text-crit">
            Fault injection failed — NF id not found or simulation not running.
          </p>
        )}
      </Panel>
    </div>
  );
}
