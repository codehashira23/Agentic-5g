interface StatCardProps {
  title: string;
  value: string | number;
  unit?: string;
  delta?: string;
  status?: "ok" | "warn" | "crit" | "ai";
  icon?: React.ReactNode;
}

const STATUS_CONFIG = {
  ok:   { value: "text-ok",   bg: "from-ok/5",   border: "border-ok/20"   },
  warn: { value: "text-warn", bg: "from-warn/5",  border: "border-warn/20" },
  crit: { value: "text-crit", bg: "from-crit/5",  border: "border-crit/20" },
  ai:   { value: "text-ai",   bg: "from-ai/5",    border: "border-ai/20"   },
};

export function StatCard({ title, value, unit, delta, status = "ok", icon }: StatCardProps) {
  const cfg = STATUS_CONFIG[status];
  return (
    <div
      className={`relative bg-gradient-to-br ${cfg.bg} to-card backdrop-blur-xl border ${cfg.border}
                  rounded-xl p-4 flex flex-col gap-2 overflow-hidden shadow-1`}
    >
      {/* Background decoration */}
      <div className="absolute top-0 right-0 w-24 h-24 rounded-full opacity-5 -translate-y-8 translate-x-8"
           style={{ background: `var(--color-${status === "ai" ? "ai" : status})` }} />

      <div className="flex items-start justify-between gap-2">
        <p className="text-xs font-medium text-muted uppercase tracking-widest leading-none">
          {title}
        </p>
        {icon && (
          <span className={`${cfg.value} opacity-60`}>{icon}</span>
        )}
      </div>

      <p className={`text-2xl font-bold tabular-nums leading-none ${cfg.value}`}>
        {value}
        {unit && (
          <span className="text-sm font-normal text-muted ml-1">{unit}</span>
        )}
      </p>

      {delta && (
        <p className="text-xs text-muted leading-none">{delta}</p>
      )}
    </div>
  );
}
