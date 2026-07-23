"use client";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { keys } from "@/lib/query/keys";
import { Panel } from "@/components/panel";
import { EmptyState } from "@/components/states/empty-state";

export default function LogsPage() {
  const { data } = useQuery({
    queryKey: keys.logs(),
    queryFn: () =>
      api.get<{
        items: Array<{
          id: number;
          ts: string;
          level: string;
          message: string;
          correlation_id?: string;
        }>;
      }>("/logs"),
    refetchInterval: 3000,
  });

  const items = data?.items ?? [];

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-lg font-bold text-primary">Logs</h1>
      <Panel title={`${items.length} entries`}>
        {items.length === 0 ? (
          <EmptyState message="No logs yet." />
        ) : (
          <ul className="flex flex-col gap-1 font-mono text-xs">
            {items.map((log) => (
              <li key={log.id} className="flex gap-3 border-b border-border/30 py-1">
                <span className="text-faint shrink-0">{log.ts?.slice(11, 19)}</span>
                <span
                  className={`shrink-0 ${log.level === "error" ? "text-crit" : log.level === "warn" ? "text-warn" : "text-ok"}`}
                >
                  {log.level?.toUpperCase()}
                </span>
                <span className="text-muted truncate">{log.message}</span>
                {log.correlation_id && (
                  <span className="text-faint shrink-0">{log.correlation_id.slice(-8)}</span>
                )}
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}
