import { InboxIcon } from "lucide-react";

export function EmptyState({ message, action }: { message: string; action?: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 gap-3 text-center">
      <InboxIcon className="w-8 h-8 text-faint" aria-hidden />
      <p className="text-sm text-muted">{message}</p>
      {action}
    </div>
  );
}
