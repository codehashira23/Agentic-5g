interface SectionTitleProps {
  children: React.ReactNode;
  /** Optional icon shown before the label */
  icon?: React.ReactNode;
  className?: string;
}

/**
 * Small uppercase gradient section label — for grouping content within a page.
 * e.g. <SectionTitle>Delhi Region</SectionTitle>
 */
export function SectionTitle({ children, icon, className = "" }: SectionTitleProps) {
  return (
    <div className={`flex items-center gap-1.5 mb-2 ${className}`}>
      {icon && <span className="text-ai">{icon}</span>}
      <span className="section-eyebrow brand-gradient">{children}</span>
    </div>
  );
}
