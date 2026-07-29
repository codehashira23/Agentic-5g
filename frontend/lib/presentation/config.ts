/**
 * ============================================================================
 *  Agent5G — Presentation Mode content configuration
 * ============================================================================
 *  This is the SINGLE editable source of truth for every slide's copy, data,
 *  and secret-access settings. Tweak values here and the whole keynote updates.
 *
 *  Nothing in this file is linked from the normal app UI — the presentation is
 *  reachable only via the secret route or the global key combo below.
 * ----------------------------------------------------------------------------
 */

export interface TechItem {
  name: string;
  detail?: string;
}

export interface FeatureItem {
  /** lucide-react icon name (resolved in the slide) */
  icon: string;
  title: string;
  desc: string;
}

export interface WorkflowStep {
  title: string;
  desc: string;
  icon: string;
}

/* ----------------------------------------------------------------------------
 *  Secret access
 * ------------------------------------------------------------------------- */
export const ACCESS = {
  /**
   * URL of the hidden route. The folder on disk is `%5F%5Fpresent` because
   * Next.js treats a literal leading underscore as a private (non-routable)
   * folder — `%5F` is the URL-encoded underscore that restores the segment.
   */
  route: "/__present",
  /** Passphrase for the unlock gate (stored in localStorage once entered). */
  passphrase: "agent5g",
  /**
   * Global key combo: press these keys in sequence (within `hotkeyWindowMs`)
   * from anywhere in the app to jump to the presentation.
   */
  hotkeySequence: ["g", "p"],
  hotkeyWindowMs: 800,
  /** localStorage key used to remember a successful unlock. */
  unlockStorageKey: "a5g_present_unlocked",
} as const;

/* ----------------------------------------------------------------------------
 *  Project meta / branding
 * ------------------------------------------------------------------------- */
export const PROJECT = {
  name: "AGENT5G",
  fullName: "Agent5G",
  tagline: "Agentic AI for 5G Advanced",
  subtitle: "An autonomous operations platform for 5G Advanced Release 20",
  release: "5G Advanced · Release 20",
  event: "Hackathon / Project Showcase",
  year: "2026",
  github: "https://github.com/codehashira23/Agentic-5g",
  /** Wire a real PDF into /public to enable the brochure download button. */
  brochureUrl: "/agent5g-brochure.pdf",
  /** Drop an audio file into /public to enable the background-music toggle. */
  musicUrl: "/presentation-ambient.mp3",
} as const;

/* ----------------------------------------------------------------------------
 *  Team
 * ------------------------------------------------------------------------- */
export const TEAM = {
  members: [
    {
      name: "Divyansh Jaiswal",
      roll: "202311030",
      role: "Solo Developer — Full-stack & AI",
      initials: "DJ",
    },
  ],
  mentor: "Dr. Bhupendra Kumar",
  college: "Indian Institute of Information Technology, Vadodara (IIIT Vadodara ICD)",
  collegeShort: "IIIT Vadodara · ICD",
} as const;

/* ----------------------------------------------------------------------------
 *  Slide content
 * ------------------------------------------------------------------------- */

export const PROBLEM = {
  eyebrow: "The Problem",
  title: "5G Advanced is too complex to run by hand",
  points: [
    {
      icon: "Network",
      title: "Exploding complexity",
      desc: "Dense cells, network slicing, RAN, Core and Edge create millions of interacting parameters no team can tune manually.",
    },
    {
      icon: "TimerReset",
      title: "Reactive operations",
      desc: "Faults are found after they hurt users. Diagnosis and remediation stay slow, manual and human-dependent.",
    },
    {
      icon: "TrendingUp",
      title: "Rising OPEX & energy cost",
      desc: "Round-the-clock monitoring and over-provisioning inflate operating and energy budgets while SLAs tighten.",
    },
    {
      icon: "Boxes",
      title: "Siloed tooling",
      desc: "Metrics, logs, topology and planning live in disconnected tools with no unified intelligence layer.",
    },
  ],
} as const;

export const SOLUTION = {
  eyebrow: "The Solution",
  title: "An agentic AI that runs the network for you",
  statement:
    "Agent5G observes, reasons and acts on the live 5G network through a closed automation loop — turning reactive operations into autonomous ones.",
  pillars: [
    {
      icon: "Bot",
      title: "Autonomous agents",
      desc: "Goal-driven agents detect, diagnose and resolve issues without waiting for a human.",
    },
    {
      icon: "BrainCircuit",
      title: "Reasoning + memory",
      desc: "LLM reasoning grounded by a knowledge graph and long-term memory of past incidents.",
    },
    {
      icon: "Cpu",
      title: "Digital twin safety",
      desc: "Every action is validated on a digital twin before it ever touches the live network.",
    },
  ],
} as const;

export const ARCHITECTURE = {
  eyebrow: "Architecture",
  title: "A layered, closed-loop platform",
  layers: [
    {
      icon: "MonitorSmartphone",
      name: "Experience layer",
      desc: "Next.js 16 dashboard, analytics and agent console",
      tone: "ai",
    },
    {
      icon: "Workflow",
      name: "Agent orchestration",
      desc: "Multi-agent runtime + visual workflow builder",
      tone: "cyan",
    },
    {
      icon: "BrainCircuit",
      name: "Intelligence layer",
      desc: "LLM reasoning · vector memory · knowledge graph",
      tone: "ai",
    },
    {
      icon: "Cpu",
      name: "Network abstraction",
      desc: "Topology · digital twin · simulation engine",
      tone: "cyan",
    },
    {
      icon: "Database",
      name: "Telemetry & data",
      desc: "Real-time metrics, logs and events over WebSocket",
      tone: "ai",
    },
  ],
} as const;

export const FEATURES: { eyebrow: string; title: string; items: FeatureItem[] } = {
  eyebrow: "Features",
  title: "One platform, thirteen intelligent modules",
  items: [
    { icon: "LayoutDashboard", title: "Live Dashboard", desc: "Real-time health, KPIs and network state at a glance." },
    { icon: "BarChart3", title: "Analytics", desc: "Trends, anomalies and predictive insights across the network." },
    { icon: "Bot", title: "Agent Console", desc: "Watch autonomous agents observe, reason and act in real time." },
    { icon: "Workflow", title: "Workflow Builder", desc: "Compose automation flows visually with a node canvas." },
    { icon: "Brain", title: "Memory", desc: "Long-term, retrievable memory of incidents and outcomes." },
    { icon: "Share2", title: "Knowledge Graph", desc: "Relationships between entities power grounded reasoning." },
    { icon: "Network", title: "Topology", desc: "Interactive live map of the RAN, Core and Edge." },
    { icon: "Cpu", title: "Digital Twin", desc: "A safe mirror of the network for what-if validation." },
    { icon: "Play", title: "Simulation", desc: "Run scenarios and stress tests before acting for real." },
    { icon: "Package", title: "Model Manager", desc: "Register, version and route LLM and ML models." },
    { icon: "List", title: "Service Registry", desc: "Discover and track every service in the platform." },
    { icon: "ScrollText", title: "Logs & Observability", desc: "Streaming logs and events with full traceability." },
  ],
};

export const TECH_STACK: {
  eyebrow: string;
  title: string;
  groups: { label: string; icon: string; items: TechItem[] }[];
} = {
  eyebrow: "Technology",
  title: "Built on a modern, type-safe stack",
  groups: [
    {
      label: "Frontend",
      icon: "MonitorSmartphone",
      items: [
        { name: "Next.js 16" },
        { name: "React 19" },
        { name: "TypeScript" },
        { name: "Tailwind CSS v4" },
        { name: "Zustand" },
        { name: "React Query" },
        { name: "Recharts" },
        { name: "React Flow" },
        { name: "Framer Motion" },
      ],
    },
    {
      label: "Backend",
      icon: "Server",
      items: [
        { name: "Python" },
        { name: "FastAPI" },
        { name: "WebSockets" },
        { name: "OpenAPI" },
        { name: "Async I/O" },
      ],
    },
    {
      label: "AI & Intelligence",
      icon: "BrainCircuit",
      items: [
        { name: "LLM agents" },
        { name: "RAG memory" },
        { name: "Knowledge graph" },
        { name: "Digital twin" },
        { name: "Simulation" },
      ],
    },
    {
      label: "Platform & Ops",
      icon: "Rocket",
      items: [
        { name: "Railway" },
        { name: "Nixpacks" },
        { name: "Playwright" },
        { name: "Vitest" },
      ],
    },
  ],
};

export const WORKFLOW: { eyebrow: string; title: string; steps: WorkflowStep[] } = {
  eyebrow: "Workflow",
  title: "The autonomous closed loop",
  steps: [
    { icon: "Radar", title: "Observe", desc: "Ingest live telemetry, metrics, logs and events." },
    { icon: "BrainCircuit", title: "Reason", desc: "Agents analyse with LLM + knowledge graph + memory." },
    { icon: "ClipboardList", title: "Plan", desc: "Generate a remediation or optimisation plan." },
    { icon: "Cpu", title: "Simulate", desc: "Validate the plan on the digital twin first." },
    { icon: "Zap", title: "Act", desc: "Execute the approved change autonomously." },
    { icon: "GraduationCap", title: "Learn", desc: "Store the outcome and improve future decisions." },
  ],
};

export const DEMO = {
  eyebrow: "Live Demo",
  title: "Let's see Agent5G in action",
  script: [
    { icon: "LayoutDashboard", label: "Open the live Dashboard", detail: "network health, KPIs and active agents" },
    { icon: "Bot", label: "Trigger the Agent Console", detail: "watch an agent detect and reason about an anomaly" },
    { icon: "Cpu", label: "Validate on the Digital Twin", detail: "simulate the fix before it goes live" },
    { icon: "Zap", label: "Autonomous remediation", detail: "the loop closes and the KPI recovers" },
  ],
  hint: "Tip: keep the app running on localhost — press Esc to drop out of the deck and back into the live product.",
} as const;

export const AI_FEATURES = {
  eyebrow: "AI Features",
  title: "Intelligence at the core",
  items: [
    { icon: "Bot", title: "Multi-agent orchestration", desc: "Specialised agents collaborate toward operational goals." },
    { icon: "MessagesSquare", title: "Natural-language ops", desc: "Ask the network questions and issue intents in plain English." },
    { icon: "Brain", title: "Retrieval-augmented memory", desc: "Past incidents inform every new decision via RAG." },
    { icon: "Share2", title: "Knowledge-graph reasoning", desc: "Grounded, explainable decisions instead of black-box guesses." },
    { icon: "LineChart", title: "Predictive analytics", desc: "Anomaly detection and forecasting head off failures early." },
    { icon: "ShieldCheck", title: "Twin-verified safety", desc: "Actions are proven safe in simulation before execution." },
  ],
} as const;

export const FUTURE = {
  eyebrow: "Future Scope",
  title: "Where Agent5G goes next",
  items: [
    { icon: "Radio", title: "O-RAN & multi-vendor", desc: "Open, vendor-neutral RAN integration." },
    { icon: "Sparkles", title: "Reinforcement learning", desc: "Self-improving optimisation policies." },
    { icon: "Leaf", title: "Green networking", desc: "Energy-aware, carbon-conscious operations." },
    { icon: "MessagesSquare", title: "Intent-based networking", desc: "Natural language straight to network policy." },
    { icon: "Radar", title: "Federated edge agents", desc: "Distributed autonomy at the network edge." },
    { icon: "Rocket", title: "6G readiness", desc: "A foundation that scales toward 6G." },
  ],
} as const;

export const CLOSING = {
  eyebrow: "Thank You",
  title: "Thank you",
  subtitle: "Questions & discussion welcome",
  qrCaption: "Explore the code",
} as const;

/* ----------------------------------------------------------------------------
 *  Slide registry order (ids map to components in the slide registry)
 * ------------------------------------------------------------------------- */
export const SLIDE_ORDER = [
  "welcome",
  "problem",
  "solution",
  "architecture",
  "features",
  "tech-stack",
  "workflow",
  "demo",
  "ai-features",
  "future",
  "team",
  "thanks",
] as const;

export type SlideId = (typeof SLIDE_ORDER)[number];
