"use client";
import dynamic from "next/dynamic";
import type { ComponentType } from "react";
import type { SlideId } from "@/lib/presentation/config";

/** Branded fallback shown while a slide chunk loads. */
function SlideLoader() {
  return (
    <div className="flex h-full w-full items-center justify-center">
      <span className="pv-spin h-9 w-9 rounded-full border-2 border-ai/30 border-t-ai" />
    </div>
  );
}

export interface SlideMeta {
  id: SlideId;
  title: string;
  notes: string;
  Component: ComponentType;
  /** Eagerly fetch this slide's chunk (used to preload neighbours). */
  preload: () => Promise<unknown>;
}

/**
 * Slide registry. Each slide is code-split via `next/dynamic` (import paths are
 * written inline so the bundler can match chunks). The deck preloads the
 * previous/next slide so transitions never flash.
 */
export const SLIDES: Record<SlideId, SlideMeta> = {
  welcome: {
    id: "welcome",
    title: "Welcome",
    notes:
      "Set the stage: Agent5G is agentic AI for 5G Advanced Release 20. One line — we make the network run itself. Enter fullscreen and go.",
    Component: dynamic(() => import("./slides/welcome-slide"), { loading: SlideLoader }),
    preload: () => import("./slides/welcome-slide"),
  },
  problem: {
    id: "problem",
    title: "Problem",
    notes:
      "5G Advanced is too complex for manual operations. Emphasise scale, reactive firefighting, rising OPEX/energy and tool silos.",
    Component: dynamic(() => import("./slides/problem-slide"), { loading: SlideLoader }),
    preload: () => import("./slides/problem-slide"),
  },
  solution: {
    id: "solution",
    title: "Solution",
    notes:
      "Agent5G closes the loop: observe, reason, act. Highlight autonomous agents, reasoning grounded by memory + knowledge graph, and digital-twin safety.",
    Component: dynamic(() => import("./slides/solution-slide"), { loading: SlideLoader }),
    preload: () => import("./slides/solution-slide"),
  },
  architecture: {
    id: "architecture",
    title: "Architecture",
    notes:
      "Walk the layers top-down: experience, agent orchestration, intelligence, network abstraction, telemetry. Telemetry rises, actions flow back down.",
    Component: dynamic(() => import("./slides/architecture-slide"), { loading: SlideLoader }),
    preload: () => import("./slides/architecture-slide"),
  },
  features: {
    id: "features",
    title: "Features",
    notes:
      "Thirteen modules, one platform. Don't read them all — point at Agent Console, Digital Twin and Knowledge Graph as differentiators.",
    Component: dynamic(() => import("./slides/features-slide"), { loading: SlideLoader }),
    preload: () => import("./slides/features-slide"),
  },
  "tech-stack": {
    id: "tech-stack",
    title: "Tech Stack",
    notes:
      "Type-safe, modern stack. Next.js 16 + React 19 front end; Python + FastAPI backend over WebSockets; LLM agents, RAG memory, knowledge graph; deployed on Railway.",
    Component: dynamic(() => import("./slides/tech-stack-slide"), { loading: SlideLoader }),
    preload: () => import("./slides/tech-stack-slide"),
  },
  workflow: {
    id: "workflow",
    title: "Workflow",
    notes:
      "The autonomous closed loop: Observe → Reason → Plan → Simulate → Act → Learn. Stress that simulation on the twin gates every action.",
    Component: dynamic(() => import("./slides/workflow-slide"), { loading: SlideLoader }),
    preload: () => import("./slides/workflow-slide"),
  },
  demo: {
    id: "demo",
    title: "Live Demo",
    notes:
      "Switch to the live app (Esc drops out of the deck) or load the embedded dashboard. Show an agent detecting an anomaly and remediating it.",
    Component: dynamic(() => import("./slides/demo-slide"), { loading: SlideLoader }),
    preload: () => import("./slides/demo-slide"),
  },
  "ai-features": {
    id: "ai-features",
    title: "AI Features",
    notes:
      "Intelligence at the core: multi-agent orchestration, natural-language ops, RAG memory, knowledge-graph reasoning, predictive analytics, twin-verified safety.",
    Component: dynamic(() => import("./slides/ai-features-slide"), { loading: SlideLoader }),
    preload: () => import("./slides/ai-features-slide"),
  },
  future: {
    id: "future",
    title: "Future Scope",
    notes:
      "Where it goes next: O-RAN/multi-vendor, reinforcement learning, green networking, intent-based networking, federated edge agents, 6G readiness.",
    Component: dynamic(() => import("./slides/future-slide"), { loading: SlideLoader }),
    preload: () => import("./slides/future-slide"),
  },
  team: {
    id: "team",
    title: "Team",
    notes: "Solo build by Divyansh Jaiswal (202311030), mentored by Dr. Bhupendra Kumar at IIIT Vadodara ICD.",
    Component: dynamic(() => import("./slides/team-slide"), { loading: SlideLoader }),
    preload: () => import("./slides/team-slide"),
  },
  thanks: {
    id: "thanks",
    title: "Thank You",
    notes: "Thank the judges. Scan the QR for the repo, offer the brochure, and invite questions.",
    Component: dynamic(() => import("./slides/thanks-slide"), { loading: SlideLoader }),
    preload: () => import("./slides/thanks-slide"),
  },
};
