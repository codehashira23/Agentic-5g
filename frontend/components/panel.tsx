interface PanelProps {
  title?: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  /** Optional left-border accent colour class e.g. "border-l-4 border-l-ai" */
  accent?: string;
}

export function Panel({ title, actions, children, className = "", accent }: PanelProps) {
  return (
    <div
      className={`bg-card backdrop-blur-xl border border-border rounded-xl overflow-hidden shadow-1 ${accent ?? ""} ${className}`}
    >
      {(title || actions) && (
        <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-white/[0.02]">
          {title && (
            <h3 className="text-sm font-semibold text-primary tracking-tight">{title}</h3>
          )}
          {actions && (
            <div className="flex items-center gap-2">{actions}</div>
          )}
        </div>
      )}
      <div className="p-4">{children}</div>
    </div>
  );
}
