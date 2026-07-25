"use client";
import { useWsStore } from "@/lib/ws/store";
import type { WsEvent } from "@/lib/api/types.gen";

function eventStyle(type: string) {
  if (type.includes("FAILED") || type.includes("CRIT"))
    return { bar: "bg-crit", label: "text-crit", bg: "bg-crit/5" };
  if (type.includes("BREACH") || type.includes("WARN"))
    return { bar: "bg-warn", label: "text-warn", bg: "bg-warn/5" };
  if (type.includes("COMPLETED") || type.includes("RECOVERED"))
    return { bar: "bg-ok", label: "text-ok", bg: "bg-ok/5" };
  if (type.includes("WORKFLOW") || type.includes("STAGE"))
    return { bar: "bg-ai", label: "text-ai", bg: "bg-ai/5" };
  if (type.includes("SERVICE") || type.includes("MODEL"))
    return { bar: "bg-info", label: "text-info", bg: "bg-info/5" };
  return { bar: "bg-border", label: "text-faint", bg: "" };
}

function formatType(type: string): string {
  return type
    .replace(/_/g, " ")
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function EventFeed({ maxItems = 20 }: { maxItems?: number }) {
  const feed = useWsStore((s) => s.eventFeed).slice(0, maxItems);

  if (feed.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 gap-2">
        <div className="w-8 h-8 rounded-full bg-card-hover flex items-center justify-center">
          <span className="text-faint text-lg">∅</span>
        </div>
        <p className="text-xs text-faint">No events yet — start the simulation.</p>
      </div>
    );
  }

  return (
    <ul className="flex flex-col gap-0.5" aria-live="polite" aria-label="Live event feed">
      {feed.map((e, i) => {
        const style = eventStyle(e.type);
        const entityId =
          "payload" in e && e.payload && typeof e.payload === "object" && "entity_id" in e.payload
            ? String(e.payload.entity_id)
            : null;
        return (
          <li
            key={i}
            className={`flex items-center gap-2 rounded-lg px-2 py-1.5 text-xs ${style.bg}`}
          >
            <span className={`w-1 h-4 rounded-full shrink-0 ${style.bar}`} />
            <span className={`font-mono font-semibold shrink-0 ${style.label}`}>
              {formatType(e.type)}
            </span>
            {entityId && (
              <span className="text-faint truncate">{entityId}</span>
            )}
            {"tick" in e && (e as { tick?: number }).tick != null && (
              <span className="ml-auto text-faint text-[10px] shrink-0 font-mono">
                t{(e as { tick: number }).tick}
              </span>
            )}
          </li>
        );
      })}
    </ul>
  );
}
