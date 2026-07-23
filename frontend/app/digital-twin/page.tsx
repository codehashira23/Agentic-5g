"use client";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { keys } from "@/lib/query/keys";
import { Panel } from "@/components/panel";
import { StatusBadge } from "@/components/status-badge";
import { Skeleton } from "@/components/states/skeleton";
import { ErrorState } from "@/components/states/error-state";
import { EmptyState } from "@/components/states/empty-state";

export default function DigitalTwinPage() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: keys.twin(),
    queryFn: () =>
      api.get<{
        tick: number;
        health_pct: number;
        nf_states: Record<string, { type: string; region: string; status: string; load: number }>;
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

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-lg font-bold text-primary">Digital Twin — Tick {data.tick}</h1>
      <Panel
        title={`${nfs.length} Network Functions — Health ${Math.round(data.health_pct * 100)}%`}
      >
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          {nfs.map(([id, state]) => (
            <div key={id} className="bg-card-hover rounded-lg p-3 text-xs">
              <p className="font-mono font-medium text-primary truncate">{id}</p>
              <p className="text-faint">
                {state.type} · {state.region}
              </p>
              <StatusBadge status={state.status} />
              <div className="mt-1 h-1 bg-border rounded-full overflow-hidden">
                <div
                  className="h-1 bg-ai rounded-full transition-all"
                  style={{ width: `${state.load * 100}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}
