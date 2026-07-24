"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Copy, Check } from "lucide-react";
import { api } from "@/lib/api/client";
import { keys } from "@/lib/query/keys";
import { Panel } from "@/components/panel";
import { Skeleton } from "@/components/states/skeleton";
import { EmptyState } from "@/components/states/empty-state";
import type { ServiceView } from "@/lib/api/types.gen";

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  function copy() {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  }
  return (
    <button
      onClick={copy}
      className="ml-1 p-0.5 rounded hover:bg-card-hover transition-colors text-faint hover:text-primary"
      title="Copy spec ref"
    >
      {copied ? <Check className="w-3 h-3 text-ok" /> : <Copy className="w-3 h-3" />}
    </button>
  );
}

export default function ServiceRegistryPage() {
  const [search, setSearch] = useState("");

  const { data: services = [], isLoading } = useQuery({
    queryKey: keys.services(),
    queryFn: () => api.get<ServiceView[]>("/services"),
  });

  const q = search.trim().toLowerCase();
  const filtered = q
    ? services.filter(
        (s) =>
          s.name.toLowerCase().includes(q) ||
          (s.owner_nf ?? "").toLowerCase().includes(q) ||
          (s.kind ?? "").toLowerCase().includes(q) ||
          (s.spec_ref ?? "").toLowerCase().includes(q),
      )
    : services;

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-lg font-bold text-primary">Service Registry</h1>

      {/* Search bar */}
      <input
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="Search by name, owner NF, kind, or spec ref…"
        className="w-full bg-card border border-border rounded-lg px-3 py-2 text-sm
                   text-primary placeholder:text-faint focus:outline-none focus:border-ai"
      />

      <Panel title={`${filtered.length} of ${services.length} services`}>
        {isLoading ? (
          <Skeleton className="h-40" />
        ) : filtered.length === 0 ? (
          <EmptyState message={q ? `No services matching "${q}"` : "No services registered."} />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead>
                <tr className="border-b border-border text-faint">
                  <th className="pb-2 pr-4 font-medium">Name</th>
                  <th className="pb-2 pr-4 font-medium">Kind</th>
                  <th className="pb-2 pr-4 font-medium">Owner NF</th>
                  <th className="pb-2 pr-4 font-medium">Spec Ref</th>
                  <th className="pb-2 font-medium">Compensation</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((s) => (
                  <tr key={s.name} className="border-b border-border/50 hover:bg-card-hover">
                    <td className="py-1.5 pr-4 font-mono text-ai">{s.name}</td>
                    <td className="py-1.5 pr-4">
                      <span
                        className={`px-1.5 py-0.5 rounded text-xs ${
                          s.kind === "action"
                            ? "bg-warn/15 text-warn"
                            : s.kind === "control"
                            ? "bg-crit/15 text-crit"
                            : "bg-ok/15 text-ok"
                        }`}
                      >
                        {s.kind}
                      </span>
                    </td>
                    <td className="py-1.5 pr-4 text-muted">{s.owner_nf}</td>
                    <td className="py-1.5 pr-4 text-faint">
                      <span className="flex items-center gap-0.5">
                        <span className="truncate max-w-[160px]">{s.spec_ref || "—"}</span>
                        {s.spec_ref && <CopyButton text={s.spec_ref} />}
                      </span>
                    </td>
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
