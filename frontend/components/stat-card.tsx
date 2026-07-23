interface StatCardProps {
  title: string;
  value: string | number;
  unit?: string;
  delta?: string;
  status?: "ok" | "warn" | "crit" | "ai";
}

const STATUS_CLS = {
  ok: "text-ok",
  warn: "text-warn",
  crit: "text-crit",
  ai: "text-ai",
};

export function StatCard({ title, value, unit, delta, status = "ok" }: StatCardProps) {
  return (
    <div className="bg-card border border-border rounded-lg p-4 flex flex-col gap-1">
      <p className="text-xs text-muted uppercase tracking-wide">{title}</p>
      <p className={`text-2xl font-bold tabular-nums ${STATUS_CLS[status]}`}>
        {value}
        {unit && <span className="text-sm font-normal text-muted ml-1">{unit}</span>}
      </p>
      {delta && <p className="text-xs text-muted">{delta}</p>}
    </div>
  );
}
