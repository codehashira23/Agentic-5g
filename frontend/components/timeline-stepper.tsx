import { CheckCircle2, Circle, Loader2, XCircle } from "lucide-react";

const STAGES = ["observe", "reason", "plan", "execute", "validate", "complete"] as const;
type Stage = (typeof STAGES)[number];

function stageStatus(current: Stage | string, s: Stage, wfStatus: string) {
  const ci = STAGES.indexOf(current as Stage);
  const si = STAGES.indexOf(s);
  if (wfStatus === "failed" && si === ci) return "failed";
  if (si < ci) return "done";
  if (si === ci) return "active";
  return "pending";
}

export function TimelineStepper({ stage, status }: { stage: string; status: string }) {
  return (
    <ol className="flex items-center gap-0 text-xs" aria-label="Workflow stages">
      {STAGES.map((s, i) => {
        const st = stageStatus(stage, s, status);
        return (
          <li key={s} className="flex items-center">
            <span
              className={`flex flex-col items-center gap-0.5
              ${
                st === "done"
                  ? "text-ok"
                  : st === "active"
                    ? "text-ai"
                    : st === "failed"
                      ? "text-crit"
                      : "text-faint"
              }`}
            >
              {st === "done" ? (
                <CheckCircle2 className="w-4 h-4" />
              ) : st === "active" ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : st === "failed" ? (
                <XCircle className="w-4 h-4" />
              ) : (
                <Circle className="w-4 h-4" />
              )}
              <span className="hidden sm:block capitalize">{s}</span>
            </span>
            {i < STAGES.length - 1 && (
              <span className={`w-6 h-px mx-1 ${st === "done" ? "bg-ok" : "bg-border"}`} />
            )}
          </li>
        );
      })}
    </ol>
  );
}
