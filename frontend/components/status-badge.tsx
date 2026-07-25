import { AlertCircle, CheckCircle2, Clock, Minus, Loader2, Zap } from "lucide-react";

const STATUS_MAP: Record<string, { label: string; cls: string; Icon: React.ElementType }> = {
  ACTIVE:     { label: "Active",     cls: "text-ok  bg-ok/10  border border-ok/20",     Icon: CheckCircle2 },
  STANDBY:    { label: "Standby",    cls: "text-info bg-info/10 border border-info/20", Icon: Minus },
  DEGRADED:   { label: "Degraded",   cls: "text-warn bg-warn/10 border border-warn/20", Icon: AlertCircle },
  FAILED:     { label: "Failed",     cls: "text-crit bg-crit/10 border border-crit/20", Icon: AlertCircle },
  RECOVERING: { label: "Recovering", cls: "text-warn bg-warn/10 border border-warn/20", Icon: Clock },
  running:    { label: "Running",    cls: "text-ai   bg-ai/10   border border-ai/20",   Icon: Loader2 },
  completed:  { label: "Done",       cls: "text-ok   bg-ok/10   border border-ok/20",   Icon: CheckCircle2 },
  failed:     { label: "Failed",     cls: "text-crit bg-crit/10 border border-crit/20", Icon: AlertCircle },
  paused:     { label: "Paused",     cls: "text-warn bg-warn/10 border border-warn/20", Icon: Clock },
  stopped:    { label: "Stopped",    cls: "text-faint bg-card    border border-border",  Icon: Minus },
  autonomous: { label: "Auto",       cls: "text-ai   bg-ai/10   border border-ai/20",   Icon: Zap },
};

export function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_MAP[status] ?? {
    label: status,
    cls: "text-faint bg-card border border-border",
    Icon: Minus,
  };
  const { label, cls, Icon } = cfg;
  const isSpinning = status === "running";
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${cls}`}
      aria-label={label}
    >
      <Icon className={`w-3 h-3 shrink-0 ${isSpinning ? "animate-spin" : ""}`} aria-hidden />
      {label}
    </span>
  );
}
