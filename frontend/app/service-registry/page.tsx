"use client";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { keys } from "@/lib/query/keys";
import { Panel } from "@/components/panel";
import { Skeleton } from "@/components/states/skeleton";
import { EmptyState } from "@/components/states/empty-state";
import type { ServiceView } from "@/lib/api/types.gen";

export default function ServiceRegistryPage() {
  const { data: services = [], isLoading } = useQuery({
    queryKey: keys.services(),
    queryFn: () => api.get<ServiceView[]>("/services"),
  });

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-lg font-bold text-primary">Service Registry</h1>
      <Panel title={`${services.length} registered services`}>
        {isLoading ? (
          <Skeleton className="h-40" />
        ) : services.length === 0 ? (
          <EmptyState message="No services registered." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead>
                <tr className="border-b border-border text-faint">
                  <th className="pb-2 pr-4 font-medium">Name</th>
                  <th className="pb-2 pr-4 font-medium">Kind</th>
                  <th className="pb-2 pr-4 font-medium">Owner</th>
                  <th className="pb-2 pr-4 font-medium">Spec ref</th>
                  <th className="pb-2 font-medium">Compensation</th>
                </tr>
              </thead>
              <tbody>
                {services.map((s) => (
                  <tr key={s.name} className="border-b border-border/50 hover:bg-card-hover">
                    <td className="py-1.5 pr-4 font-mono text-ai">{s.name}</td>
                    <td className="py-1.5 pr-4">
                      <span
                        className={`px-1.5 py-0.5 rounded text-xs ${s.kind === "action" ? "bg-warn/15 text-warn" : "bg-ok/15 text-ok"}`}
                      >
                        {s.kind}
                      </span>
                    </td>
                    <td className="py-1.5 pr-4 text-muted">{s.owner_nf}</td>
                    <td className="py-1.5 pr-4 text-faint">{s.spec_ref || "—"}</td>
                    <td className="py-1.5 text-faint font-mono">{s.compensation || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  );
}
