"use client";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { keys } from "@/lib/query/keys";
import { Panel } from "@/components/panel";

export default function SettingsPage() {
  const { data } = useQuery({
    queryKey: keys.settings(),
    queryFn: () => api.get<Record<string, unknown>>("/settings"),
  });
  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-lg font-bold text-primary">Settings</h1>
      <Panel title="Effective configuration">
        <pre className="text-xs text-muted bg-card-hover rounded p-3 overflow-auto">
          {data ? JSON.stringify(data, null, 2) : "Loading…"}
        </pre>
      </Panel>
    </div>
  );
}
