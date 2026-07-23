import { AlertTriangle } from "lucide-react";

export function ErrorState({ message, retry }: { message: string; retry?: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 gap-3">
      <AlertTriangle className="w-8 h-8 text-crit" aria-hidden />
      <p className="text-sm text-muted">{message}</p>
      {retry && (
        <button onClick={retry} className="text-xs text-ai underline">
          Retry
        </button>
      )}
    </div>
  );
}
