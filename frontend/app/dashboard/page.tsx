"use client";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { keys } from "@/lib/query/keys";
import { useWsStore } from "@/lib/ws/store";
import { StatCard } from "@/components/stat-card";
import { Panel } from "@/components/panel";
import { EventFeed } from "@/components/event-feed";
import { Skeleton } from "@/components/states/skeleton";

export default function DashboardPage() {
  const { data: health } = useQuery({
    queryKey: keys.simStatus(),
    queryFn: () =>
      api.get<{ status: string; tick: number; health_pct?: number }>("/simulation/status"),
    refetchInterval: 5000,
  });

  const activeWorkflows = useWsStore((s) => s.activeWorkflows);
  const alerts = useWsStore((s) => s.alerts);
  const health_pct = useWsStore((s) => s.health_pct);

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-lg font-bold text-primary">Dashboard</h1>

      {/* Stat row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {health ? (
          <>
            <StatCard title="Active Workflows" value={activeWorkflows} status="ai" />
            <StatCard
              title="NF Health"
              value={`${Math.round(health_pct * 100)}%`}
              status={health_pct > 0.8 ? "ok" : health_pct > 0.5 ? "warn" : "crit"}
            />
            <StatCard title="Sim Tick" value={health.tick ?? 0} status="ok" />
            <StatCard
              title="Open Alerts"
              value={alerts.length}
              status={alerts.length === 0 ? "ok" : "warn"}
            />
          </>
        ) : (
          Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-20" />)
        )}
      </div>

      {/* Live events */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Panel title="Live Events">
          <EventFeed maxItems={15} />
        </Panel>
        <Panel title="Alerts">
          {alerts.length === 0 ? (
            <p className="text-xs text-faint py-4 text-center">No active alerts</p>
          ) : (
            <ul className="flex flex-col gap-2">
              {alerts.slice(0, 10).map((a) => (
                <li key={a.id} className="text-xs border-l-2 border-l-warn pl-2 text-warn">
                  {a.message}
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>
    </div>
  );
}
