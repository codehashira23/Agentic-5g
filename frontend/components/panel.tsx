interface PanelProps {
  title?: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}

export function Panel({ title, actions, children, className = "" }: PanelProps) {
  return (
    <div className={`bg-card border border-border rounded-lg overflow-hidden ${className}`}>
      {(title || actions) && (
        <div className="flex items-center justify-between px-4 py-3 border-b border-border">
          {title && <h3 className="text-sm font-semibold text-primary">{title}</h3>}
          {actions && <div className="flex items-center gap-2">{actions}</div>}
        </div>
      )}
      <div className="p-4">{children}</div>
    </div>
  );
}
