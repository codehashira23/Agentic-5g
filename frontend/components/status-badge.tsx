import { AlertCircle, CheckCircle2, Clock, Minus } from "lucide-react";

const STATUS_MAP: Record<string, { label: string; cls: string; Icon: React.ElementType }> = {
  ACTIVE: { label: "Active", cls: "text-ok bg-ok-bg", Icon: CheckCircle2 },
  STANDBY: { label: "Standby", cls: "text-info bg-info-bg", Icon: Minus },
  DEGRADED: { label: "Degraded", cls: "text-warn bg-warn-bg", Icon: AlertCircle },
  FAILED: { label: "Failed", cls: "text-crit bg-crit-bg", Icon: AlertCircle },
  RECOVERING: { label: "Recovering", cls: "text-warn bg-warn-bg", Icon: Clock },
  running: { label: "Running", cls: "text-ok bg-ok-bg", Icon: CheckCircle2 },
  completed: { label: "Done", cls: "text-info bg-info-bg", Icon: CheckCircle2 },
  failed: { label: "Failed", cls: "text-crit bg-crit-bg", Icon: AlertCircle },
  paused: { label: "Paused", cls: "text-warn bg-warn-bg", Icon: Clock },
};

export function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_MAP[status] ?? { label: status, cls: "text-faint bg-card", Icon: Minus };
  const { label, cls, Icon } = cfg;
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${cls}`}
      aria-label={label}
    >
      <Icon className="w-3 h-3" aria-hidden />
      {label}
    </span>
  );
}
