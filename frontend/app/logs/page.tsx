"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { keys } from "@/lib/query/keys";
import { Panel } from "@/components/panel";
import { EmptyState } from "@/components/states/empty-state";

const LEVEL_COLOR: Record<string, string> = {
  error: "text-crit",
  warn:  "text-warn",
  info:  "text-ok",
  debug: "text-faint",
};

type LogItem = {
  id: number;
  ts: string;
  level: string;
  message: string;
  correlation_id?: string;
  type?: string;
  source?: "log" | "event";
};

export default function LogsPage() {
  const [correlationId, setCorrelationId] = useState("");
  const [tab, setTab] = useState<"logs" | "events">("events");

  const queryUrl = correlationId.trim()
    ? `/${tab}?correlation_id=${encodeURIComponent(correlationId.trim())}`
    : `/${tab}`;

  const { data } = useQuery({
    queryKey: keys.logs(correlationId.trim() || undefined),
    queryFn: () =>
      api.get<{ items: LogItem[] }>(queryUrl),
    refetchInterval: 3000,
  });

  const items = data?.items ?? [];

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-lg font-bold text-primary">Logs</h1>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-border">
        {(["events", "logs"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-1.5 text-xs capitalize transition-colors
              ${tab === t
                ? "border-b-2 border-ai text-ai"
                : "text-muted hover:text-primary"}`}
          >
            {t === "events" ? "Domain Events" : "App Logs"}
          </button>
        ))}
      </div>

      {/* Filter bar */}
      <div className="flex items-center gap-2">
        <input
          value={correlationId}
          onChange={(e) => setCorrelationId(e.target.value)}
          placeholder="Filter by workflow ID — e.g. wf_a1b2c3d4"
          className="flex-1 bg-card border border-border rounded-lg px-3 py-1.5 text-sm
                     text-primary placeholder:text-faint focus:outline-none focus:border-ai
                     font-mono"
        />
        {correlationId && (
          <button
            onClick={() => setCorrelationId("")}
            className="px-3 py-1.5 rounded-lg bg-card border border-border text-xs text-muted
                       hover:text-primary transition-colors"
          >
            Clear
          </button>
        )}
      </div>

      <Panel
        title={`${items.length} ${tab === "events" ? "domain events" : "app logs"}${correlationId ? ` · ${correlationId.slice(0, 14)}…` : ""}`}
      >
        {items.length === 0 ? (
          <EmptyState
            message={
              correlationId
                ? "No entries for this correlation ID."
                : tab === "events"
                ? "No events yet — start the simulation or submit a workflow."
                : "No app logs yet — submit a workflow to generate entries."
            }
          />
        ) : (
          <ul className="flex flex-col gap-0.5 font-mono text-xs max-h-[600px] overflow-y-auto">
            {items.map((log) => (
              <li
                key={log.id}
                className="flex gap-3 border-b border-border/20 py-1.5 hover:bg-card-hover px-1 rounded"
              >
                <span className="text-faint shrink-0 tabular-nums">
                  {log.ts?.slice(11, 23) ?? "—"}
                </span>
                {tab === "logs" ? (
                  <span className={`shrink-0 w-10 ${LEVEL_COLOR[log.level] ?? "text-muted"}`}>
                    {log.level?.toUpperCase().slice(0, 4)}
                  </span>
                ) : null}
                {log.type && (
                  <span className="text-ai shrink-0 max-w-[180px] truncate">{log.type}</span>
                )}
                <span className="text-muted flex-1 truncate">{log.message}</span>
                {log.correlation_id && (
                  <span
                    className="text-faint shrink-0 cursor-pointer hover:text-ai transition-colors"
                    title={log.correlation_id}
                    onClick={() => setCorrelationId(log.correlation_id!)}
                  >
                    {log.correlation_id.slice(-10)}
                  </span>
                )}
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}
