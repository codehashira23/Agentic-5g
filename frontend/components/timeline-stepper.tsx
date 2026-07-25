import { CheckCircle2, Circle, Loader2, XCircle } from "lucide-react";

const STAGES = ["observe", "reason", "plan", "execute", "validate", "complete"] as const;
type Stage = (typeof STAGES)[number];

function stageStatus(current: Stage | string, s: Stage, wfStatus: string) {
  const ci = STAGES.indexOf(current as Stage);
  const si = STAGES.indexOf(s);
  if (wfStatus === "failed" && si === ci) return "failed";
  if (wfStatus === "completed") return "done";
  if (si < ci) return "done";
  if (si === ci) return "active";
  return "pending";
}

export function TimelineStepper({ stage, status }: { stage: string; status: string }) {
  return (
    <ol className="flex items-center" aria-label="Workflow stages">
      {STAGES.map((s, i) => {
        const st = stageStatus(stage, s, status);
        const isDone    = st === "done";
        const isActive  = st === "active";
        const isFailed  = st === "failed";
        const isPending = st === "pending";

        return (
          <li key={s} className="flex items-center flex-1">
            {/* Node */}
            <div className="flex flex-col items-center gap-1">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center border-2 transition-all
                  ${isDone   ? "border-ok   bg-ok/10"   : ""}
                  ${isActive ? "border-ai   bg-ai/10 ring-2 ring-ai/20" : ""}
                  ${isFailed ? "border-crit bg-crit/10" : ""}
                  ${isPending? "border-border bg-card"  : ""}
                `}
              >
                {isDone   && <CheckCircle2 className="w-4 h-4 text-ok" />}
                {isActive && <Loader2 className="w-4 h-4 text-ai animate-spin" />}
                {isFailed && <XCircle className="w-4 h-4 text-crit" />}
                {isPending&& <Circle className="w-4 h-4 text-faint" />}
              </div>
              <span
                className={`text-[10px] font-medium capitalize hidden sm:block
                  ${isDone   ? "text-ok"   : ""}
                  ${isActive ? "text-ai"   : ""}
                  ${isFailed ? "text-crit" : ""}
                  ${isPending? "text-faint": ""}
                `}
              >
                {s}
              </span>
            </div>

            {/* Connector */}
            {i < STAGES.length - 1 && (
              <div
                className={`flex-1 h-0.5 mx-1 rounded-full transition-all
                  ${isDone ? "bg-ok" : "bg-border"}`}
              />
            )}
          </li>
        );
      })}
    </ol>
  );
}
