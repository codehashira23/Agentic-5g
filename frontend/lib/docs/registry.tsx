"use client";
import type { ComponentType } from "react";
import {
  Activity,
  Boxes,
  BrainCircuit,
  Database,
  GitBranch,
  Layers,
  type LucideIcon,
  MonitorSmartphone,
  Rocket,
  ScrollText,
  Server,
  ServerCog,
  ShieldCheck,
  Sparkles,
  Waypoints,
} from "lucide-react";
import {
  ApiReferenceSection,
  ApplicationLayerSection,
  ArchitectureSection,
  DatabaseSection,
  DataFlowSection,
  DeploymentSection,
  DomainLayerSection,
  FrontendArchSection,
  KeyFilesSection,
  LlmAgentsSection,
  OverviewSection,
  RequestLifecycleSection,
  SecurityFutureSection,
  SimulationBusSection,
} from "./sections";

export type DocGroup = "Getting Started" | "Backend" | "Frontend" | "Reference";

export interface DocSection {
  id: string;
  title: string;
  group: DocGroup;
  icon: LucideIcon;
  minutes: number;
  Body: ComponentType;
  toc: { id: string; label: string }[];
}

export const GROUP_ORDER: DocGroup[] = ["Getting Started", "Backend", "Frontend", "Reference"];

export const SECTIONS: DocSection[] = [
  {
    id: "overview",
    title: "Overview",
    group: "Getting Started",
    icon: Sparkles,
    minutes: 3,
    Body: OverviewSection,
    toc: [
      { id: "what", label: "What is Agent5G?" },
      { id: "stack", label: "Technology at a glance" },
      { id: "how-to", label: "How to read these docs" },
    ],
  },
  {
    id: "architecture",
    title: "Architecture",
    group: "Getting Started",
    icon: Layers,
    minutes: 4,
    Body: ArchitectureSection,
    toc: [
      { id: "layers", label: "Layered architecture" },
      { id: "boundaries", label: "Enforced boundaries" },
    ],
  },
  {
    id: "request-lifecycle",
    title: "Request Lifecycle",
    group: "Backend",
    icon: Waypoints,
    minutes: 4,
    Body: RequestLifecycleSection,
    toc: [
      { id: "factory", label: "App factory & lifespan" },
      { id: "pipeline", label: "The request pipeline" },
    ],
  },
  {
    id: "domain-layer",
    title: "Domain Layer",
    group: "Backend",
    icon: Boxes,
    minutes: 3,
    Body: DomainLayerSection,
    toc: [
      { id: "twin", label: "The domain is a network" },
      { id: "ports", label: "Ports keep it pure" },
    ],
  },
  {
    id: "application-layer",
    title: "Application Layer",
    group: "Backend",
    icon: ServerCog,
    minutes: 5,
    Body: ApplicationLayerSection,
    toc: [
      { id: "twin-service", label: "TwinService" },
      { id: "workflow", label: "8-stage workflow" },
      { id: "agents", label: "Agents + SEL" },
    ],
  },
  {
    id: "simulation-bus",
    title: "Simulation & Event Bus",
    group: "Backend",
    icon: Activity,
    minutes: 5,
    Body: SimulationBusSection,
    toc: [
      { id: "scheduler", label: "The tick clock" },
      { id: "bus", label: "In-process event bus" },
      { id: "writer", label: "Single-writer queue" },
    ],
  },
  {
    id: "database",
    title: "Database",
    group: "Backend",
    icon: Database,
    minutes: 4,
    Body: DatabaseSection,
    toc: [
      { id: "why-sqlite", label: "Why SQLite" },
      { id: "schema", label: "The 18 tables" },
    ],
  },
  {
    id: "llm-agents",
    title: "LLM & Agents",
    group: "Backend",
    icon: BrainCircuit,
    minutes: 4,
    Body: LlmAgentsSection,
    toc: [
      { id: "adapters", label: "LLM adapters" },
      { id: "agent-roles", label: "The agent roles" },
    ],
  },
  {
    id: "frontend-arch",
    title: "Frontend Architecture",
    group: "Frontend",
    icon: MonitorSmartphone,
    minutes: 4,
    Body: FrontendArchSection,
    toc: [
      { id: "app-router", label: "App Router shell" },
      { id: "state", label: "Two kinds of state" },
    ],
  },
  {
    id: "data-flow",
    title: "Data Flow",
    group: "Frontend",
    icon: GitBranch,
    minutes: 4,
    Body: DataFlowSection,
    toc: [
      { id: "rest", label: "Flow A — REST metrics" },
      { id: "tick", label: "Flow B — a sim tick" },
      { id: "ws", label: "Live updates today" },
    ],
  },
  {
    id: "api-reference",
    title: "API Reference",
    group: "Reference",
    icon: Server,
    minutes: 3,
    Body: ApiReferenceSection,
    toc: [
      { id: "rest-endpoints", label: "REST endpoints" },
      { id: "ws-proto", label: "WebSocket" },
      { id: "errors", label: "Error envelope" },
    ],
  },
  {
    id: "key-files",
    title: "Key Files",
    group: "Reference",
    icon: ScrollText,
    minutes: 5,
    Body: KeyFilesSection,
    toc: [{ id: "key-files", label: "The files that matter" }],
  },
  {
    id: "deployment",
    title: "Deployment",
    group: "Reference",
    icon: Rocket,
    minutes: 2,
    Body: DeploymentSection,
    toc: [
      { id: "railway", label: "Railway" },
      { id: "env", label: "Environment variables" },
    ],
  },
  {
    id: "security-future",
    title: "Security & Future",
    group: "Reference",
    icon: ShieldCheck,
    minutes: 3,
    Body: SecurityFutureSection,
    toc: [
      { id: "posture", label: "Security posture" },
      { id: "future", label: "Future improvements" },
    ],
  },
];

export const SECTION_BY_ID = new Map(SECTIONS.map((s) => [s.id, s]));

/** Exact file → section overrides (the curated anchor files). */
const FILE_OVERRIDES: Record<string, string> = {
  "backend/app/main.py": "request-lifecycle",
  "backend/app/infrastructure/container.py": "key-files",
  "backend/pyproject.toml": "architecture",
  "frontend/app/layout.tsx": "frontend-arch",
  "frontend/app/robots.ts": "security-future",
};

/** Directory-prefix → section rules (first match wins). */
const PREFIX_RULES: [string, string][] = [
  ["backend/app/domain/", "domain-layer"],
  ["backend/app/application/workflow/", "application-layer"],
  ["backend/app/application/twin_service/", "application-layer"],
  ["backend/app/application/agents/", "application-layer"],
  ["backend/app/application/sel/", "application-layer"],
  ["backend/app/application/recovery/", "application-layer"],
  ["backend/app/infrastructure/db/", "database"],
  ["backend/app/infrastructure/bus/", "simulation-bus"],
  ["backend/app/infrastructure/sim/", "simulation-bus"],
  ["backend/app/infrastructure/rng/", "simulation-bus"],
  ["backend/app/infrastructure/writer/", "simulation-bus"],
  ["backend/app/infrastructure/llm/", "llm-agents"],
  ["backend/app/infrastructure/config/", "deployment"],
  ["backend/app/api/ws/", "data-flow"],
  ["backend/app/api/routers/", "api-reference"],
  ["backend/app/api/", "request-lifecycle"],
  ["backend/.env", "deployment"],
  ["backend/nixpacks", "deployment"],
  ["backend/railway", "deployment"],
  ["frontend/lib/ws/", "data-flow"],
  ["frontend/lib/api/", "frontend-arch"],
  ["frontend/lib/query/", "frontend-arch"],
  ["frontend/app/", "frontend-arch"],
  ["frontend/components/shell/", "frontend-arch"],
  ["frontend/nixpacks", "deployment"],
  ["frontend/railway", "deployment"],
];

/** Map a real project path to the most relevant doc section id (or null). */
export function sectionForPath(path: string): string | null {
  if (FILE_OVERRIDES[path]) return FILE_OVERRIDES[path];
  for (const [prefix, id] of PREFIX_RULES) {
    if (path.startsWith(prefix)) return id;
  }
  return null;
}
