/**
 * Icon resolver for the presentation deck.
 * Content config references lucide icons by name; this maps those names to
 * components so slides can stay data-driven. Brand icons (GitHub) were removed
 * from lucide, so a small inline SVG is provided.
 */
import {
  Activity,
  Antenna,
  Aperture,
  ArrowRight,
  BarChart3,
  Blocks,
  Bot,
  Boxes,
  Brain,
  BrainCircuit,
  ClipboardList,
  Cpu,
  Database,
  Download,
  GraduationCap,
  Layers,
  Layers3,
  LayoutDashboard,
  Leaf,
  LineChart,
  List,
  MessagesSquare,
  MonitorSmartphone,
  Network,
  Orbit,
  Package,
  Play,
  Radar,
  Radio,
  Rocket,
  ScrollText,
  Server,
  ServerCog,
  Share2,
  ShieldCheck,
  Signal,
  Sparkles,
  TimerReset,
  TrendingUp,
  Waypoints,
  Workflow,
  Zap,
  type LucideIcon,
  type LucideProps,
} from "lucide-react";

export type IconProps = LucideProps;

/** Inline GitHub mark (lucide dropped brand icons in 1.x). */
export function GithubIcon({ size = 24, className }: { size?: number | string; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="currentColor"
      className={className}
      aria-hidden
    >
      <path d="M12 .5C5.37.5 0 5.87 0 12.5c0 5.3 3.44 9.8 8.21 11.39.6.11.82-.26.82-.58l-.01-2.05c-3.34.73-4.04-1.61-4.04-1.61-.55-1.39-1.34-1.76-1.34-1.76-1.09-.75.08-.73.08-.73 1.2.09 1.84 1.24 1.84 1.24 1.07 1.84 2.81 1.31 3.5 1 .11-.78.42-1.31.76-1.61-2.67-.3-5.47-1.34-5.47-5.95 0-1.31.47-2.39 1.24-3.23-.13-.3-.54-1.52.11-3.18 0 0 1.01-.32 3.3 1.23a11.5 11.5 0 0 1 3-.4c1.02 0 2.05.14 3 .4 2.28-1.55 3.29-1.23 3.29-1.23.66 1.66.25 2.88.12 3.18.77.84 1.24 1.92 1.24 3.23 0 4.62-2.81 5.64-5.49 5.94.43.37.81 1.1.81 2.22l-.01 3.29c0 .32.22.7.83.58A12.01 12.01 0 0 0 24 12.5C24 5.87 18.63.5 12 .5Z" />
    </svg>
  );
}

const MAP: Record<string, LucideIcon> = {
  Activity,
  Antenna,
  Aperture,
  ArrowRight,
  BarChart3,
  Blocks,
  Bot,
  Boxes,
  Brain,
  BrainCircuit,
  ClipboardList,
  Cpu,
  Database,
  Download,
  GraduationCap,
  Layers,
  Layers3,
  LayoutDashboard,
  Leaf,
  LineChart,
  List,
  MessagesSquare,
  MonitorSmartphone,
  Network,
  Orbit,
  Package,
  Play,
  Radar,
  Radio,
  Rocket,
  ScrollText,
  Server,
  ServerCog,
  Share2,
  ShieldCheck,
  Signal,
  Sparkles,
  TimerReset,
  TrendingUp,
  Waypoints,
  Workflow,
  Zap,
  // Inline SVG stands in for the removed lucide brand icon.
  Github: GithubIcon as unknown as LucideIcon,
};

/** Data-driven icon: `<Icon name="Bot" className="w-6 h-6" />`. */
export function Icon({ name, ...props }: { name: string } & IconProps) {
  const Cmp = MAP[name] ?? Sparkles;
  return <Cmp {...props} />;
}
