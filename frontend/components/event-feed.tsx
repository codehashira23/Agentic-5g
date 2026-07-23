"use client";
import { useWsStore } from "@/lib/ws/store";
import type { WsEvent } from "@/lib/api/types.gen";

function eventColor(type: string) {
  if (type.includes("FAILED") || type.includes("CRIT")) return "border-l-crit text-crit";
  if (type.includes("BREACH") || type.includes("WARN")) return "border-l-warn text-warn";
  if (type.includes("COMPLETED") || type.includes("RECOVERED")) return "border-l-ok text-ok";
  if (type.includes("WORKFLOW") || type.includes("SERVICE")) return "border-l-ai text-ai";
  return "border-l-border text-muted";
}

export function EventFeed({ maxItems = 20 }: { maxItems?: number }) {
  const feed = useWsStore((s) => s.eventFeed).slice(0, maxItems);
  if (feed.length === 0) {
    return (
      <p className="text-xs text-faint py-4 text-center">No events yet — start the simulation.</p>
    );
  }
  return (
    <ul className="flex flex-col gap-1" aria-live="polite" aria-label="Live event feed">
      {feed.map((e, i) => (
        <li key={i} className={`border-l-2 pl-2 py-0.5 text-xs ${eventColor(e.type)}`}>
          <span className="font-mono font-medium">{e.type}</span>
          {"payload" in e &&
            e.payload &&
            typeof e.payload === "object" &&
            "entity_id" in e.payload && (
              <span className="ml-1 text-faint">{String(e.payload.entity_id)}</span>
            )}
        </li>
      ))}
    </ul>
  );
}
