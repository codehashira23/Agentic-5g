export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse bg-card-hover rounded ${className}`} aria-hidden />;
}
