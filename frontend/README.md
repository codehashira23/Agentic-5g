<div align="center">

# 🛰️ Agent5G — Frontend

### Real-time operations console for Agentic AI on 5G Advanced (Release 20)

The Next.js dashboard that visualizes the Agent5G control loop: it streams live
network telemetry over WebSockets, renders topology, twins and analytics, and
lets you watch autonomous agents **observe → reason → plan → act → verify**.

![Next.js](https://img.shields.io/badge/Next.js-16-000000?logo=nextdotjs&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-strict-3178C6?logo=typescript&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-v4-06B6D4?logo=tailwindcss&logoColor=white)
![Node](https://img.shields.io/badge/Node-20-339933?logo=nodedotjs&logoColor=white)

</div>

> This package is the **frontend** of the larger Agent5G platform. It talks to
> the FastAPI + LangGraph backend over REST and WebSockets. For the full-stack
> overview and one-command setup, see the [root README](../README.md).

---

## 🤔 What is this?

Agent5G's frontend is a single-page operations platform for a simulated 5G core.
It is a **read-and-react control surface**: REST queries hydrate each page,
while a persistent WebSocket pushes live events (faults, KPI breaches, workflow
stage changes) that instantly invalidate the relevant caches so the UI stays in
sync with the network. Landing on `/` redirects to `/dashboard`.

## 🧱 Tech stack

| Layer         | Technologies                                                                 |
| ------------- | ---------------------------------------------------------------------------- |
| **Framework** | Next.js 16 (App Router) · React 19 · TypeScript (strict)                     |
| **Styling**   | Tailwind CSS v4 · custom fonts (Space Grotesk · Orbitron · Geist Mono)       |
| **Data**      | TanStack Query (server state) · Zustand (live WS state) · typed fetch client |
| **Realtime**  | Native WebSocket with auto-reconnect + query-cache invalidation              |
| **Visuals**   | React Flow (topology/workflows) · Recharts (analytics) · Framer Motion       |
| **Extras**    | lucide-react icons · canvas-confetti · qrcode.react · pdf-lib (brochure)     |
| **Tooling**   | ESLint · Prettier · Vitest (+ Testing Library) · Playwright (e2e)            |
| **Types**     | OpenAPI types auto-generated from the backend into `lib/api/types.gen.ts`    |

## ✅ Prerequisites

- **Node.js 20** (see `.node-version`)
- The **Agent5G backend** running locally for live data (REST on
  `http://localhost:8000`, WebSocket on `ws://localhost:8000/ws`). The UI still
  loads without it — pages show empty/error states and the socket retries.

## ⚡ Getting started

```bash
# 1. Install dependencies
npm install

# 2. Configure environment
cp .env.local.example .env.local   # Windows: copy .env.local.example .env.local

# 3. Start the dev server
npm run dev
```

Open **http://localhost:3000** — you'll be redirected to the dashboard.

### Environment variables

Copy `.env.local.example` to `.env.local` and adjust as needed. Both are
`NEXT_PUBLIC_*` values, inlined at build time; the client falls back to the
localhost defaults below if they're missing.

| Variable               | Description           | Default                        |
| ---------------------- | --------------------- | ------------------------------ |
| `NEXT_PUBLIC_API_BASE` | Backend REST base URL | `http://localhost:8000/api/v1` |
| `NEXT_PUBLIC_WS_URL`   | Backend WebSocket URL | `ws://localhost:8000/ws`       |

## 📜 Available scripts

| Script                 | What it does                                                              |
| ---------------------- | ------------------------------------------------------------------------- |
| `npm run dev`          | Start the Next.js dev server (http://localhost:3000)                      |
| `npm run build`        | Production build                                                          |
| `npm start`            | Serve the production build                                                |
| `npm run lint`         | Lint with ESLint                                                          |
| `npm run typecheck`    | Type-check with `tsc --noEmit`                                            |
| `npm test`             | Run the Vitest unit/component suite once                                  |
| `npm run test:watch`   | Run Vitest in watch mode                                                  |
| `npm run format`       | Format the repo with Prettier                                             |
| `npm run format:check` | Check formatting without writing                                          |
| `npm run gen:types`    | Regenerate `lib/api/types.gen.ts` from the backend's `/openapi.json`      |
| `npm run gen:brochure` | Build the branded project PDF at `public/agent5g-brochure.pdf`            |
| `npm run gen:doctree`  | Snapshot the project tree into `lib/docs/project-tree.ts` (for /internal) |

> **e2e tests:** Playwright specs live in `e2e/`. Run them with
> `npx playwright test` against a running app (`E2E_BASE_URL` overrides the
> target, default `http://localhost:3000`).

## 📂 Project structure

```
frontend/
├── app/                    # App Router — one folder per route (13 pages)
│   ├── layout.tsx          # Root shell: fonts, providers, nav rail, top bar, WS init
│   ├── page.tsx            # "/" → redirects to /dashboard
│   ├── dashboard/          # Overview: live health, KPIs, agents
│   ├── analytics/          # Trends, anomalies, predictive charts
│   ├── agent-console/      # Watch agents observe → reason → act
│   ├── workflow-builder/   # Visual automation canvas (React Flow)
│   ├── memory/             # Long-term incident memory
│   ├── knowledge-graph/    # Entity relationship graph
│   ├── topology/           # Live RAN/Core/Edge map
│   ├── digital-twin/       # What-if mirror of the network
│   ├── simulation/         # Scenario + stress testing
│   ├── model-manager/      # Register/version LLM & ML models
│   ├── service-registry/   # Service discovery
│   ├── logs/               # Streaming logs & events
│   ├── settings/           # Platform settings
│   ├── internal/           # Hidden: internal docs walkthrough (see below)
│   └── %5F%5Fpresent/      # Hidden: presentation deck at /__present (see below)
├── components/             # UI building blocks
│   ├── shell/              # nav-rail + top-bar (app chrome)
│   ├── docs/               # /internal docs UI
│   ├── presentation/       # Slide deck components
│   ├── states/             # Loading / empty / error states
│   └── *.tsx               # panel, stat-card, status-badge, event-feed, etc.
├── lib/
│   ├── api/                # Typed fetch client + generated OpenAPI types
│   ├── query/              # TanStack Query client + query keys
│   ├── ws/                 # WebSocket store (Zustand) + connection init
│   ├── docs/               # Data for the /internal docs page
│   └── presentation/       # Deck config, motion, fullscreen/idle hooks
├── e2e/                    # Playwright scenario specs (A/B/C)
├── test/                   # Vitest setup + unit/component tests
├── scripts/                # Node ESM generators (brochure, doc tree)
└── public/                 # Static assets
```

## 🏗️ Architecture notes

**Data flow.** Server state comes from the backend via a small typed fetch
wrapper (`lib/api/client.ts`) that throws a structured `ApiError` and is consumed
through TanStack Query. Request/response shapes are **not hand-written** — they're
generated from the backend's OpenAPI schema (`npm run gen:types`), so the UI stays
in lockstep with the API.

**Realtime.** `lib/ws/ws-init.tsx` opens a WebSocket on app mount and reconnects
automatically (3s backoff). Incoming events land in a Zustand store
(`lib/ws/store.ts`) that keeps the connection status, an event feed and alerts,
and — critically — **invalidates the matching React Query caches** (e.g. `twin`,
`topology`, `workflows`) so affected pages refetch the instant the network state
changes.

**Path alias.** `@/*` maps to the project root, so imports read as
`@/components/...` and `@/lib/...`.

## 🕹️ Hidden features

Two routes are intentionally unlinked from the UI and reachable only via secret
key combos (typed anywhere outside a text field, within ~800ms):

- **Presentation deck** — press `g` then `p` (or visit `/__present`). A
  full-screen keynote; all copy lives in `lib/presentation/config.ts`. Unlock
  passphrase: `agent5g`.
- **Internal docs** — press `g` then `d` (or visit `/internal`). A walkthrough of
  the real project tree generated by `npm run gen:doctree`.

## 🧪 Testing

- **Unit / component:** [Vitest](https://vitest.dev) + Testing Library in a jsdom
  environment (`vitest.config.ts`, setup in `test/setup.ts`). Run `npm test`.
- **End-to-end:** [Playwright](https://playwright.dev) specs in `e2e/`
  (`playwright.config.ts`), targeting Chromium. Run `npx playwright test`.

## 🚀 Deployment

Deployed on [Railway](https://railway.app) using **Nixpacks**. The build installs
with `npm ci`, runs `npm run build`, and starts with
`npm start -- --port $PORT` (see `nixpacks.toml` and `railway.json`). Set
`NEXT_PUBLIC_API_BASE` and `NEXT_PUBLIC_WS_URL` to your deployed backend before
building, since they're baked in at build time.

## 🔗 Links

- 📦 **Full-stack overview:** [root README](../README.md)
- 🚀 **Live platform:** https://agentic5g.up.railway.app
- 💻 **GitHub:** https://github.com/codehashira23/Agentic-5g
