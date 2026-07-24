"use client";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { keys } from "@/lib/query/keys";
import { Panel } from "@/components/panel";
import { StatusBadge } from "@/components/status-badge";
import { Skeleton } from "@/components/states/skeleton";
import { ErrorState } from "@/components/states/error-state";
import { EmptyState } from "@/components/states/empty-state";

type NfState = { type: string; region: string; status: string; load: number };

const STATUS_COLOR: Record<string, string> = {
  ACTIVE:     "border-ok/40",
  DEGRADED:   "border-warn/60",
  FAILED:     "border-crit/80",
  RECOVERING: "border-ai/60",
  STANDBY:    "border-border",
};

export default function DigitalTwinPage() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: keys.twin(),
    queryFn: () =>
      api.get<{
        tick: number;
        health_pct: number;
        nf_states: Record<string, NfState>;
      }>("/twin"),
    refetchInterval: 3000,
  });

  if (isLoading)
    return (
      <div className="flex flex-col gap-4">
        <h1 className="text-lg font-bold text-primary">Digital Twin</h1>
        <Skeleton className="h-64" />
      </div>
    );

  if (isError)
    return (
      <div className="flex flex-col gap-4">
        <h1 className="text-lg font-bold text-primary">Digital Twin</h1>
        <ErrorState message="Could not load twin state — is the backend running?" retry={refetch} />
      </div>
    );

  if (!data)
    return (
      <div className="flex flex-col gap-4">
        <h1 className="text-lg font-bold text-primary">Digital Twin</h1>
        <EmptyState message="No twin data yet. Start the simulation first." />
      </div>
    );

  const nfs = Object.entries(data.nf_states);
  const healthyCount = nfs.filter(([, s]) => s.status === "ACTIVE" || s.status === "STANDBY").length;
  const failedCount  = nfs.filter(([, s]) => s.status === "FAILED").length;

  // Group by region
  const byRegion: Record<string, [string, NfState][]> = {};
  for (const [id, state] of nfs) {
    const r = state.region ?? "Unknown";
    if (!byRegion[r]) byRegion[r] = [];
    byRegion[r].push([id, state]);
  }
  const regionOrder = ["Core", "Delhi", "Mumbai", "Bengaluru", "Unknown"];
  const sortedRegions = Object.keys(byRegion).sort(
    (a, b) => (regionOrder.indexOf(a) ?? 99) - (regionOrder.indexOf(b) ?? 99)
  );

  return (
    <div className="flex flex-col gap-4">
      {/* Header summary bar */}
      <div className="flex items-center gap-4 flex-wrap">
        <h1 className="text-lg font-bold text-primary">Digital Twin</h1>
        <span className="px-2 py-0.5 rounded bg-card border border-border text-xs text-muted">
          Tick <span className="text-primary font-mono">{data.tick}</span>
        </span>
        <span className="px-2 py-0.5 rounded bg-ok/10 border border-ok/30 text-xs text-ok">
          {healthyCount} Healthy
        </span>
        {failedCount > 0 && (
          <span className="px-2 py-0.5 rounded bg-crit/10 border border-crit/30 text-xs text-crit">
            {failedCount} Failed
          </span>
        )}
        <span className="ml-auto text-xs text-faint">
          Health {Math.round(data.health_pct * 100)}% · {nfs.length} NFs
        </span>
      </div>

      {/* NFs grouped by region */}
      {sortedRegions.map((region) => (
        <section key={region}>
          <h2 className="text-xs font-semibold text-faint uppercase tracking-wider mb-2 px-1">
            {region} Region
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2">
            {byRegion[region].map(([id, state]) => (
              <div
                key={id}
                className={`bg-card border rounded-lg p-3 text-xs transition-colors
                  ${STATUS_COLOR[state.status] ?? "border-border"}
                  ${state.status === "FAILED" ? "bg-crit/5" : ""}`}
              >
                <p className="font-semibold text-primary text-[11px] mb-0.5">{state.type}</p>
                <p className="font-mono text-faint text-[9px] truncate mb-1.5">{id}</p>
                <StatusBadge status={state.status} />
                {state.load > 0 && (
                  <div className="mt-1.5 h-1 bg-border rounded-full overflow-hidden">
                    <div
                      className={`h-1 rounded-full transition-all ${
                        state.load > 0.85 ? "bg-crit" : state.load > 0.65 ? "bg-warn" : "bg-ai"
                      }`}
                      style={{ width: `${Math.min(state.load * 100, 100)}%` }}
                    />
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
