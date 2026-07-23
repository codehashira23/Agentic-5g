"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Bot,
  Network,
  Cpu,
  Workflow,
  List,
  Share2,
  Brain,
  ScrollText,
  Play,
  BarChart3,
  Package,
  Settings,
} from "lucide-react";

const NAV = [
  {
    group: "Overview",
    items: [
      { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
      { href: "/analytics", label: "Analytics", icon: BarChart3 },
    ],
  },
  {
    group: "Intelligence",
    items: [
      { href: "/agent-console", label: "Agent Console", icon: Bot },
      { href: "/workflow-builder", label: "Workflow Builder", icon: Workflow },
      { href: "/memory", label: "Memory", icon: Brain },
      { href: "/knowledge-graph", label: "Knowledge Graph", icon: Share2 },
    ],
  },
  {
    group: "Network",
    items: [
      { href: "/topology", label: "Topology", icon: Network },
      { href: "/digital-twin", label: "Digital Twin", icon: Cpu },
      { href: "/simulation", label: "Simulation", icon: Play },
      { href: "/model-manager", label: "Model Manager", icon: Package },
    ],
  },
  {
    group: "Platform",
    items: [
      { href: "/service-registry", label: "Service Registry", icon: List },
      { href: "/logs", label: "Logs", icon: ScrollText },
      { href: "/settings", label: "Settings", icon: Settings },
    ],
  },
];

export function NavRail() {
  const pathname = usePathname();
  return (
    <aside className="w-60 min-h-screen bg-panel border-r border-border flex flex-col py-4 gap-1 shrink-0">
      <div className="px-4 mb-4">
        <span className="text-sm font-bold text-ai tracking-wide">Agent5G</span>
      </div>
      {NAV.map((group) => (
        <div key={group.group} className="mb-2">
          <p className="px-4 py-1 text-xs text-faint uppercase tracking-wider">{group.group}</p>
          {group.items.map(({ href, label, icon: Icon }) => {
            const active = pathname === href || pathname.startsWith(href + "/");
            return (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-3 px-4 py-2 text-sm rounded-lg mx-2 transition-colors
                  ${
                    active
                      ? "bg-ai/15 text-ai"
                      : "text-muted hover:bg-card-hover hover:text-primary"
                  }`}
              >
                <Icon className="w-4 h-4 shrink-0" />
                {label}
              </Link>
            );
          })}
        </div>
      ))}
    </aside>
  );
}
