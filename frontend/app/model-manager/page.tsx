"use client";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { keys } from "@/lib/query/keys";
import { Panel } from "@/components/panel";
import { EmptyState } from "@/components/states/empty-state";

export default function ModelManagerPage() {
  const { data: models = [] } = useQuery({
    queryKey: keys.models(),
    queryFn: () =>
      api.get<Array<{ id: string; name?: string; state: string; target?: string }>>("/models"),
    refetchInterval: 5000,
  });
  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-lg font-bold text-primary">Model Manager</h1>
      <Panel title={`${models.length} model instances`}>
        {models.length === 0 ? (
          <EmptyState message="No models deployed. Try Scenario A — Deploy congestion model to Delhi Edge." />
        ) : (
          <ul className="flex flex-col gap-2 text-xs">
            {models.map((m) => (
              <li key={m.id} className="flex items-center gap-3 border-b border-border/30 pb-1">
                <span className="font-mono text-ai">{m.id}</span>
                <span className="text-muted">{m.name ?? "—"}</span>
                <span
                  className={`px-1.5 py-0.5 rounded ${m.state === "deployed" ? "bg-ok/15 text-ok" : "bg-faint/10 text-faint"}`}
                >
                  {m.state}
                </span>
                {m.target && <span className="text-faint">→ {m.target}</span>}
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}
