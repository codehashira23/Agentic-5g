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
  Radio,
} from "lucide-react";

const NAV = [
  {
    group: "Overview",
    items: [
      { href: "/dashboard",  label: "Dashboard",  icon: LayoutDashboard },
      { href: "/analytics",  label: "Analytics",  icon: BarChart3 },
    ],
  },
  {
    group: "Intelligence",
    items: [
      { href: "/agent-console",    label: "Agent Console",    icon: Bot },
      { href: "/workflow-builder", label: "Workflow Builder", icon: Workflow },
      { href: "/memory",           label: "Memory",           icon: Brain },
      { href: "/knowledge-graph",  label: "Knowledge Graph",  icon: Share2 },
    ],
  },
  {
    group: "Network",
    items: [
      { href: "/topology",      label: "Topology",      icon: Network },
      { href: "/digital-twin",  label: "Digital Twin",  icon: Cpu },
      { href: "/simulation",    label: "Simulation",    icon: Play },
      { href: "/model-manager", label: "Model Manager", icon: Package },
    ],
  },
  {
    group: "Platform",
    items: [
      { href: "/service-registry", label: "Service Registry", icon: List },
      { href: "/logs",             label: "Logs",             icon: ScrollText },
      { href: "/settings",         label: "Settings",         icon: Settings },
    ],
  },
];

export function NavRail() {
  const pathname = usePathname();
  return (
    <aside className="w-56 min-h-screen bg-panel border-r border-border flex flex-col shrink-0">
      {/* Logo */}
      <div className="px-4 pt-5 pb-4 border-b border-border">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-ai/30 to-cyan/20 border border-ai/40 flex items-center justify-center shrink-0 glow-ai">
            <Radio className="w-4 h-4 text-cyan" />
          </div>
          <div>
            <p className="font-display brand-gradient text-base font-extrabold leading-none tracking-wider">
              AGENT5G
            </p>
            <p className="text-[10px] text-faint mt-1 tracking-widest uppercase">5G Advanced · Rel 20</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-3 px-2 flex flex-col gap-0.5">
        {NAV.map((group, gi) => (
          <div key={group.group} className={gi > 0 ? "mt-3" : ""}>
            <p className="px-3 py-1 text-[10px] text-faint uppercase tracking-widest font-semibold">
              {group.group}
            </p>
            {group.items.map(({ href, label, icon: Icon }) => {
              const active = pathname === href || pathname.startsWith(href + "/");
              return (
                <Link
                  key={href}
                  href={href}
                  className={`flex items-center gap-2.5 px-3 py-2 text-sm rounded-lg transition-all duration-fast
                    ${
                      active
                        ? "bg-ai/15 text-ai font-medium"
                        : "text-muted hover:bg-card-hover hover:text-primary"
                    }`}
                >
                  <Icon
                    className={`w-4 h-4 shrink-0 ${active ? "text-ai" : "text-faint group-hover:text-muted"}`}
                  />
                  {label}
                  {active && (
                    <span className="ml-auto w-1.5 h-1.5 rounded-full bg-ai shrink-0" />
                  )}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-border">
        <p className="text-[10px] text-faint text-center">
          Agentic AI Platform · IIITV 2026
        </p>
      </div>
    </aside>
  );
}
