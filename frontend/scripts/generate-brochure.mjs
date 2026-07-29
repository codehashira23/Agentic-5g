/**
 * Generates the Agent5G project brochure at `public/agent5g-brochure.pdf`.
 *
 * Produces a branded, multi-section A4 PDF (gold-on-black) with selectable
 * text and vector shapes, so it opens anywhere and imports cleanly into tools
 * like Canva for redesign. Re-run any time with: `npm run gen:brochure`.
 *
 * Content mirrors lib/presentation/config.ts. This script is intentionally
 * self-contained (plain Node ESM) so it needs no TypeScript/Next tooling.
 */
import { PDFDocument, StandardFonts, rgb } from "pdf-lib";
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT = join(__dirname, "..", "public", "agent5g-brochure.pdf");

/* ------------------------------------------------------------------ content */
const DATA = {
  name: "AGENT5G",
  tagline: "Agentic AI for 5G Advanced",
  subtitle: "An autonomous operations platform for 5G Advanced Release 20",
  release: "5G Advanced · Release 20",
  event: "Project Showcase · 2026",
  github: "https://github.com/codehashira23/Agentic-5g",
  problem: [
    ["Exploding complexity", "Dense cells, slicing, RAN, Core and Edge create millions of interacting parameters no team can tune by hand."],
    ["Reactive operations", "Faults are found after they hurt users; diagnosis and remediation stay slow and human-dependent."],
    ["Rising OPEX & energy cost", "Round-the-clock monitoring and over-provisioning inflate operating and energy budgets while SLAs tighten."],
    ["Siloed tooling", "Metrics, logs, topology and planning live in disconnected tools with no unified intelligence layer."],
  ],
  solutionStatement:
    "Agent5G observes, reasons and acts on the live 5G network through a closed automation loop - turning reactive operations into autonomous ones.",
  solution: [
    ["Autonomous agents", "Goal-driven agents detect, diagnose and resolve issues without waiting for a human."],
    ["Reasoning + memory", "LLM reasoning grounded by a knowledge graph and long-term memory of past incidents."],
    ["Digital twin safety", "Every action is validated on a digital twin before it ever touches the live network."],
  ],
  features: [
    "Live Dashboard", "Analytics", "Agent Console", "Workflow Builder",
    "Memory", "Knowledge Graph", "Topology", "Digital Twin",
    "Simulation", "Model Manager", "Service Registry", "Logs & Observability",
  ],
  workflow: [
    ["Observe", "Ingest live telemetry, metrics, logs and events."],
    ["Reason", "Agents analyse with LLM + knowledge graph + memory."],
    ["Plan", "Generate a remediation or optimisation plan."],
    ["Simulate", "Validate the plan on the digital twin first."],
    ["Act", "Execute the approved change autonomously."],
    ["Learn", "Store the outcome and improve future decisions."],
  ],
  tech: [
    ["Frontend", "Next.js 16 · React 19 · TypeScript · Tailwind CSS v4 · Zustand · React Query · Recharts · React Flow · Framer Motion"],
    ["Backend", "Python · FastAPI · WebSockets · OpenAPI · Async I/O"],
    ["AI & Intelligence", "LLM agents · RAG memory · Knowledge graph · Digital twin · Simulation"],
    ["Platform & Ops", "Railway · Nixpacks · Playwright · Vitest"],
  ],
  ai: [
    ["Multi-agent orchestration", "Specialised agents collaborate toward operational goals."],
    ["Natural-language ops", "Ask the network questions and issue intents in plain English."],
    ["Retrieval-augmented memory", "Past incidents inform every new decision via RAG."],
    ["Knowledge-graph reasoning", "Grounded, explainable decisions instead of black-box guesses."],
    ["Predictive analytics", "Anomaly detection and forecasting head off failures early."],
    ["Twin-verified safety", "Actions are proven safe in simulation before execution."],
  ],
  future: [
    "O-RAN & multi-vendor RAN integration",
    "Reinforcement learning for self-improving optimisation",
    "Energy-aware green networking",
    "Intent-based networking (language to policy)",
    "Federated edge agents",
    "6G readiness",
  ],
  team: {
    member: "Divyansh Jaiswal",
    roll: "202311030",
    role: "Solo Developer - Full-stack & AI",
    mentor: "Dr. Bhupendra Kumar",
    college: "Indian Institute of Information Technology, Vadodara (IIIT Vadodara ICD)",
  },
};

/* ------------------------------------------------------------------- layout */
const PAGE_W = 595.28;
const PAGE_H = 841.89;
const MARGIN = 46;
const CONTENT_W = PAGE_W - MARGIN * 2;
const FOOTER_Y = 34;
const BOTTOM = FOOTER_Y + 22;

const BLACK = rgb(0, 0, 0);
const GOLD = rgb(0.988, 0.639, 0.067);
const WHITE = rgb(0.961, 0.973, 0.988);
const MUTED = rgb(0.737, 0.796, 0.878);
const FAINT = rgb(0.525, 0.596, 0.69);
const LINE = rgb(0.165, 0.235, 0.369);
const CARD = rgb(0.055, 0.078, 0.125);

/** Replace non-WinAnsi punctuation so StandardFonts never choke. */
function s(str) {
  return String(str)
    .replace(/[\u2014\u2013]/g, "-")
    .replace(/[\u2018\u2019]/g, "'")
    .replace(/[\u201C\u201D]/g, '"')
    .replace(/\u2026/g, "...");
}

async function main() {
  const doc = await PDFDocument.create();
  doc.setTitle("Agent5G - Project Brochure");
  doc.setAuthor("Divyansh Jaiswal");
  doc.setSubject("Agentic AI for 5G Advanced Release 20");

  const reg = await doc.embedFont(StandardFonts.Helvetica);
  const bold = await doc.embedFont(StandardFonts.HelveticaBold);

  let page;
  let y;

  const drawFooter = () => {
    page.drawRectangle({ x: MARGIN, y: FOOTER_Y + 14, width: CONTENT_W, height: 0.6, color: LINE });
    page.drawText(s(DATA.github), { x: MARGIN, y: FOOTER_Y, size: 8, font: reg, color: FAINT });
    const right = "Agent5G · IIIT Vadodara ICD · 2026";
    const w = reg.widthOfTextAtSize(right, 8);
    page.drawText(right, { x: PAGE_W - MARGIN - w, y: FOOTER_Y, size: 8, font: reg, color: FAINT });
  };

  const addPage = () => {
    if (page) drawFooter();
    page = doc.addPage([PAGE_W, PAGE_H]);
    page.drawRectangle({ x: 0, y: 0, width: PAGE_W, height: PAGE_H, color: BLACK });
    page.drawRectangle({ x: 0, y: PAGE_H - 5, width: PAGE_W, height: 5, color: GOLD });
    y = PAGE_H - MARGIN - 6;
  };

  const ensure = (space) => {
    if (y - space < BOTTOM) addPage();
  };

  const wrap = (str, font, size, maxWidth) => {
    const words = s(str).split(/\s+/);
    const lines = [];
    let line = "";
    for (const word of words) {
      const test = line ? `${line} ${word}` : word;
      if (font.widthOfTextAtSize(test, size) > maxWidth && line) {
        lines.push(line);
        line = word;
      } else {
        line = test;
      }
    }
    if (line) lines.push(line);
    return lines;
  };

  const paragraph = (str, { size = 10, font = reg, color = WHITE, x = MARGIN, lh = 1.4, gap = 6, maxWidth = CONTENT_W } = {}) => {
    for (const ln of wrap(str, font, size, maxWidth)) {
      ensure(size * lh);
      page.drawText(ln, { x, y: y - size, size, font, color });
      y -= size * lh;
    }
    y -= gap;
  };

  const eyebrow = (str) => {
    ensure(30);
    y -= 8;
    page.drawText(s(str).toUpperCase(), { x: MARGIN, y: y - 9, size: 9.5, font: bold, color: GOLD });
    y -= 13;
    page.drawRectangle({ x: MARGIN, y: y - 1, width: 28, height: 2, color: GOLD });
    y -= 12;
  };

  const bullet = (title, desc, { numbered = null } = {}) => {
    ensure(16);
    const marker = numbered != null ? `${numbered}` : "•";
    page.drawText(marker, { x: MARGIN, y: y - 10, size: 10.5, font: bold, color: GOLD });
    const tx = MARGIN + 16;
    page.drawText(s(title), { x: tx, y: y - 10, size: 10.5, font: bold, color: WHITE });
    y -= 14;
    if (desc) {
      paragraph(desc, { x: tx, size: 9.5, color: MUTED, maxWidth: CONTENT_W - 16, lh: 1.32, gap: 7 });
    } else {
      y -= 3;
    }
  };

  /* ----------------------------------------------------------- page 1 header */
  addPage();
  page.drawText(s(DATA.name), { x: MARGIN, y: y - 32, size: 34, font: bold, color: GOLD });
  y -= 44;
  page.drawText(s(DATA.tagline), { x: MARGIN, y: y - 14, size: 14, font: bold, color: WHITE });
  y -= 22;
  paragraph(DATA.subtitle, { size: 10.5, color: MUTED, gap: 10 });
  page.drawRectangle({ x: MARGIN, y: y, width: CONTENT_W, height: 1, color: LINE });
  y -= 14;
  page.drawText(s(`${DATA.release}    |    ${DATA.event}`), { x: MARGIN, y: y - 9, size: 9, font: reg, color: FAINT });
  y -= 20;

  /* ------------------------------------------------------------- narrative */
  eyebrow("The Problem");
  for (const [t, d] of DATA.problem) bullet(t, d);

  eyebrow("The Solution");
  paragraph(DATA.solutionStatement, { size: 10.5, color: WHITE, gap: 8 });
  for (const [t, d] of DATA.solution) bullet(t, d);

  eyebrow("Key Features");
  paragraph(DATA.features.join("   ·   "), { size: 10, color: MUTED, lh: 1.5, gap: 6 });

  eyebrow("How It Works");
  DATA.workflow.forEach(([t, d], i) => bullet(t, d, { numbered: i + 1 }));

  eyebrow("Technology Stack");
  for (const [label, items] of DATA.tech) {
    ensure(16);
    page.drawText(s(label), { x: MARGIN, y: y - 10, size: 10, font: bold, color: GOLD });
    y -= 13;
    paragraph(items, { size: 9.5, color: MUTED, lh: 1.35, gap: 8 });
  }

  eyebrow("AI Features");
  for (const [t, d] of DATA.ai) bullet(t, d);

  eyebrow("Future Scope");
  for (const f of DATA.future) bullet(f, null);

  /* ------------------------------------------------------------------ team */
  eyebrow("Team");
  ensure(60);
  page.drawRectangle({ x: MARGIN, y: y - 52, width: CONTENT_W, height: 52, color: CARD, borderColor: LINE, borderWidth: 0.8 });
  page.drawText(s(DATA.team.member), { x: MARGIN + 14, y: y - 20, size: 13, font: bold, color: WHITE });
  page.drawText(s(`${DATA.team.roll}  ·  ${DATA.team.role}`), { x: MARGIN + 14, y: y - 34, size: 9.5, font: reg, color: GOLD });
  page.drawText(s(`Mentor: ${DATA.team.mentor}`), { x: MARGIN + 14, y: y - 46, size: 9, font: reg, color: MUTED });
  y -= 60;
  paragraph(DATA.team.college, { size: 9, color: FAINT, gap: 4 });

  drawFooter();

  const bytes = await doc.save();
  mkdirSync(dirname(OUT), { recursive: true });
  writeFileSync(OUT, bytes);
  console.log(`Brochure written: ${OUT} (${(bytes.length / 1024).toFixed(1)} KB, ${doc.getPageCount()} page(s))`);
}

main().catch((err) => {
  console.error("Failed to generate brochure:", err);
  process.exit(1);
});
