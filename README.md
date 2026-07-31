<div align="center">

# 🛰️ Agent5G

### Agentic AI Service Enablement Platform for 5G Advanced (Release 20)

An autonomous, closed-loop multi-agent system that **observes** a simulated 5G core network, **reasons** over telemetry with an LLM, and **safely acts** to self-heal and optimize — all from a real-time operations dashboard.

[![Live Demo](https://img.shields.io/badge/🚀_Live_Demo-agentic5g.up.railway.app-6C47FF?style=for-the-badge)](https://agentic5g.up.railway.app)
[![GitHub](https://img.shields.io/badge/💻_Source-codehashira23%2FAgentic--5g-181717?style=for-the-badge&logo=github)](https://github.com/codehashira23/Agentic-5g)

<br/>

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-agents-1C3C3C)
![Next.js](https://img.shields.io/badge/Next.js-16-000000?logo=nextdotjs&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-strict-3178C6?logo=typescript&logoColor=white)
![Tests](https://img.shields.io/badge/tests-575_passing-brightgreen)
![Railway](https://img.shields.io/badge/deployed-Railway-0B0D0E?logo=railway&logoColor=white)

</div>

---

## 🤔 What is this?

Agent5G is a **digital twin of a 5G core** (AMF, SMF, UPF, NRF, NWDAF, gNB, and more) paired with an **agentic AI control loop**. The agent continuously watches network KPIs, uses LLM reasoning to plan remediation, and executes actions through a **safety policy engine** that blocks anything unsafe — no human in the loop required.

## 🔄 The agent loop

```mermaid
flowchart LR
    O[👁️ Observe<br/>telemetry & KPIs] --> R[🧠 Reason<br/>LLM analysis]
    R --> P[🗺️ Plan<br/>remediation]
    P --> A[⚙️ Act<br/>via safety gate]
    A --> V[✅ Verify<br/>outcome]
    V --> O
```

## ✨ Features

- 🤖 **Multi-agent orchestration** — full observe → reason → plan → act → verify cycle coordinated with LangGraph.
- 🛰️ **5G digital twin** — 9 simulated core network functions with KPIs, faults, events, and topology.
- 🛡️ **Safety-first autonomy** — a policy engine validates every action against hard & soft constraints before execution.
- 🎯 **Deterministic & offline** — seeded RNG + an LLM replay layer make demos and tests reproducible at **$0 cost**.
- 🌐 **11 REST routers + live WebSocket** — health, topology, twin, workflows, simulation, analytics, logs, services, policies, models, settings.
- 📊 **13-page operations console** — Agent Console, Topology, Digital Twin, Analytics, Simulation, Logs, Service Registry, Model Manager, Knowledge Graph, Memory, Workflow Builder, Settings, Dashboard.

## 🧱 Tech stack

| Layer | Technologies |
|-------|-------------|
| **Backend** | Python 3.11 · FastAPI · Pydantic v2 · SQLAlchemy 2.0 (async) · LangGraph · WebSockets · Groq / Llama 3.1 |
| **Frontend** | Next.js 16 · React 19 · TypeScript · TailwindCSS v4 · React Flow · Recharts · Zustand · TanStack Query |
| **Quality** | pytest (575 tests) · ruff · mypy · import-linter · Vitest · Playwright |
| **Architecture** | Clean/hexagonal (`domain → application → infrastructure → api`) with enforced layer boundaries |
| **DevOps** | Deployed on Railway (nixpacks) · auto-generated OpenAPI types shared with the frontend |

## ⚡ Quick start

> **Prerequisites:** Python 3.11+ and Node.js 20+. The default LLM mode is `replay` — fully offline, no API key, **$0**.

```powershell
# 1. One-time setup (venv, deps, .env files)
.\scripts\setup.ps1

# 2. Start the backend        (Terminal 1)
.\scripts\run-backend.ps1

# 3. Start the frontend       (Terminal 2)
.\scripts\run-frontend.ps1
```

Then open **http://localhost:3000** — API docs live at **http://localhost:8000/docs**.

## 📂 Project structure

```
Agentic-5g/
├── backend/     # FastAPI + LangGraph agent (clean architecture)
│   └── app/     # domain · application · infrastructure · api
├── frontend/    # Next.js 16 operations dashboard
├── data/        # simulation scenarios
├── scripts/     # setup & run helpers (PowerShell)
└── learning/    # research notes & system docs
```

## 🏗️ Architecture & design

These diagrams are a Mermaid rendering of the full pack in [`planning/diagrams.tex`](planning/diagrams.tex) (LaTeX/TikZ source). The proposed authentication flow from that pack is intentionally left out here — it is future work, not part of the current build.

**System architecture**

```mermaid
flowchart TB
    User(["Network Operator / Researcher<br/>(web browser)"])

    subgraph FE["Frontend — Next.js 16 · React 19 · TypeScript"]
        direction LR
        Pages["13 pages<br/>(App Router)"]
        Query["TanStack Query<br/>(poll + cache)"]
        Store["Zustand<br/>(WS live store)"]
        Viz["React Flow<br/>+ Recharts"]
    end

    subgraph BE["Backend — Python 3.11 · FastAPI (clean / hexagonal)"]
        API["api/ — 11 REST routers + WebSocket, middleware, deps"]
        APP["application/ — orchestrator, 7 agents, workflow engine, SEL, twin service, recovery"]
        DOM["domain/ — digital twin (13 NF types), KPIs, events, ports"]
        INFRA["infrastructure/ — event bus, SQLite, LLM adapters, seeded RNG, writer queue, container"]
        API --> APP --> DOM
        INFRA -.->|"implements ports"| DOM
    end

    DB[("SQLite agent5g.db<br/>(18 tables)")]
    LLM["Groq API — Llama 3.1<br/>(replay / live / record / fake)"]

    User --> FE
    FE <-->|"HTTPS REST + WebSocket"| API
    INFRA -.->|"persist"| DB
    INFRA -.->|"LLM calls"| LLM
```

<sub>Two processes (console + backend), four inward-depending backend layers, and two external dependencies — a seeded SQLite store and a Groq-hosted LLM reached through a provider-agnostic port.</sub>

<details>
<summary><b>🧩 Component &amp; module structure</b></summary>

<br/>

**Component view**

```mermaid
flowchart TB
    Console["Operations Console<br/>(13 pages)"]
    Routers["REST Routers<br/>(11 groups)"]
    WSHub["WebSocket Hub"]
    Orch["Agent Orchestrator<br/>(LangGraph)"]
    Agents["7 Agents<br/>observer · planner · executor<br/>optimizer · recovery · documentation · memory"]
    Policy["Policy Engine<br/>(hard + soft rules)"]
    Engine["Workflow Engine<br/>(staged loop)"]
    SEL["Service Enablement Layer<br/>(invoker)"]
    LLMAd["LLM Adapter<br/>(Groq, 4 modes)"]
    TwinSvc["Twin Service<br/>(tick loop)"]
    Recov["Autonomous<br/>Recovery Handler"]
    Twin["Digital Twin<br/>(18 nodes, KPIs)"]
    Bus["Event Bus<br/>(pub/sub)"]
    Writer["Writer Queue<br/>(single writer)"]
    DB[("SQLite DB<br/>(18 tables)")]

    Console <--> Routers
    Console <--> WSHub
    Routers --> Orch
    Orch --> Agents
    Orch --> Engine
    Agents --> LLMAd
    Engine --> SEL
    SEL --> Policy
    Engine --> TwinSvc
    TwinSvc --> Twin
    Recov --> Engine
    Twin --> Bus
    Bus --> Recov
    Bus --> Writer
    Writer --> DB
    SEL -->|"apply action"| Twin
    Bus -->|"stream events"| WSHub
```

<sub>The orchestrator drives the workflow engine; every mutation passes the Service Enablement Layer and its policy engine; the event bus fans domain events out to the console, the writer queue, and autonomous recovery.</sub>

**Module dependency graph**

```mermaid
flowchart TB
    subgraph Delivery["Delivery"]
        R["api/routers<br/>(11 groups)"]
        WS["api/ws"]
        MW["api/schemas + middleware"]
    end
    subgraph Application["Application"]
        TS["application/twin_service"]
        AG["application/agents<br/>(+ orchestrator)"]
        RC["application/recovery"]
        WF["application/workflow<br/>(engine)"]
        SL["application/sel<br/>(invoker, policy)"]
    end
    subgraph Domain["Domain"]
        DS["domain/services"]
        TW["domain/twin<br/>(NFs, KPIs, events)"]
        PO["domain/ports<br/>(interfaces)"]
    end
    subgraph Infrastructure["Infrastructure"]
        LL["infra/llm"]
        DBm["infra/db<br/>(+ writer)"]
        BUSm["infra/bus"]
        RNGm["infra/rng"]
        CON["infra/container<br/>(composition root)"]
    end

    R --> AG
    R --> WF
    WS --> WF
    RC --> WF
    WF --> SL
    AG --> TW
    WF --> TW
    SL --> TW
    TS --> TW
    DS --> TW
    LL -.->|"implements"| PO
    DBm -.->|"implements"| PO
    BUSm -.->|"implements"| PO
    RNGm -.->|"implements"| PO
```

<sub>Solid arrows are inward compile-time dependencies; dashed arrows are infrastructure adapters implementing the domain's ports. These boundaries are machine-checked by import-linter.</sub>

**Technology stack (by layer)**

```mermaid
flowchart TB
    L1["Frontend / Presentation<br/>Next.js 16 · React 19 · TypeScript · TailwindCSS v4 · React Flow · Recharts · Zustand · TanStack Query"]
    L2["Transport / API<br/>REST (OpenAPI-generated types) · WebSocket (live events)"]
    L3["Application / Backend<br/>Python 3.11 · FastAPI · Uvicorn (ASGI) · LangGraph · Pydantic v2"]
    L4["Domain<br/>framework-free 5G model — digital twin · KPIs · events · ports"]
    L5["Persistence<br/>SQLAlchemy 2.0 (async) · aiosqlite · SQLite (single-writer queue)"]
    L6["AI / LLM<br/>Groq API · Llama 3.1 — modes: replay / live / record / fake"]
    L7["Quality<br/>pytest (575) · ruff · mypy · import-linter · Vitest · Playwright"]
    L8["Deployment<br/>Railway (nixpacks) · $0 running cost"]

    L1 --> L2 --> L3 --> L4 --> L5 --> L6 --> L7 --> L8
```

</details>

<details>
<summary><b>⚙️ Runtime &amp; behaviour</b></summary>

<br/>

**Request processing pipeline**

```mermaid
flowchart TB
    S(["Client HTTP request"])
    ASGI["Uvicorn (ASGI) accepts request"]
    MW["Middleware — CORS, correlation-id, timing"]
    Route["Route match (api/routers)"]
    Deps["Dependency injection — container, DB session"]
    Valid{"Pydantic body valid?"}
    Err[/"422 / 4xx error"/]
    App["Application use-case / service"]
    Core["Domain + infrastructure — twin, SEL, repositories"]
    Ser["Serialize response schema"]
    Out(["JSON response (+ correlation-id)"])

    S --> ASGI --> MW --> Route --> Deps --> Valid
    Valid -->|"yes"| App
    Valid -->|"no"| Err
    App --> Core --> Ser --> Out
    Err -.-> Out
```

<sub>Malformed requests short-circuit to a structured error; valid requests flow through the application and domain layers before serialization.</sub>

**API communication**

```mermaid
flowchart LR
    subgraph FEc["Frontend Console"]
        RQ["TanStack Query<br/>(poll + cache)"]
        WSC["WebSocket client<br/>(Zustand store)"]
    end
    subgraph BEc["FastAPI Backend"]
        REST["11 REST routers<br/>health · topology · twin · workflows · simulation · analytics · logs · services · policies · models · settings"]
        WSH["WebSocket hub (/ws)"]
    end

    RQ -->|"GET/POST (every few s)"| REST
    REST -->|"JSON"| RQ
    WSH -.->|"push events (NF_FAILED, stage_changed, …)"| WSC
    WSC -.->|"open once"| WSH
```

<sub>REST is polled and cached on the client; a single persistent WebSocket pushes server-initiated events so the UI reacts the instant the network changes.</sub>

**Sequence — autonomous recovery**

```mermaid
sequenceDiagram
    autonumber
    participant UI as Browser (UI)
    participant Twin as Twin / API
    participant Bus as Event Bus
    participant Rec as Recovery Handler
    participant Agents as Agent Loop (7 agents)
    participant SEL as SEL (invoker + policy)
    participant Store as Persist + WS

    UI->>Twin: POST /simulation/fault
    Note over Twin: mark NF FAILED
    Twin->>Bus: publish NF_FAILED
    Bus->>Store: persist + WS push
    Store-->>UI: node turns red
    Bus->>Rec: NF_FAILED
    Rec->>Agents: start workflow (autonomous goal)
    Agents->>Twin: Observe snapshot
    Twin-->>Agents: network state
    Note over Agents: Reason + Plan
    Agents->>SEL: invoke upf.loadbalance.apply
    Note over SEL: policy check → allow
    SEL->>Twin: apply command
    Twin-->>SEL: ok
    SEL-->>Agents: result
    Agents->>Twin: Validate snapshot
    Agents->>Store: stream stages + trace
    Store-->>UI: live stepper updates
```

<sub>After the fault is injected, the loop runs observe → reason → plan → act → verify on its own; the only mutation (apply command) happens after the policy engine allows it.</sub>

**Activity — workflow lifecycle**

```mermaid
flowchart TB
    Start((Start)) --> Obs["Observe — read twin snapshot"]
    Obs --> Rea["Reason — interpret goal"]
    Rea --> Pla["Plan — ordered actions"]
    Pla --> Gate{"Policy allows action?"}
    Gate -->|"block"| Refuse["Record refusal;<br/>choose alternative"]
    Refuse --> Pla
    Gate -->|"allow"| Exe["Execute — invoke via SEL"]
    Exe --> Val["Validate — re-observe"]
    Val --> Ok{"Outcome?"}
    Ok -->|"success"| Comp["Complete — write summary"]
    Ok -->|"failed"| RB["Rollback — compensate"]
    Ok -->|"retry"| Exe
    RB --> Comp
    Comp --> Done((End))
```

<sub>The plan is gated action-by-action by the policy engine; validation either completes, retries the execute step, or triggers a compensating rollback.</sub>

**Data-flow diagram (Level 1)**

```mermaid
flowchart LR
    OP(["Operator / Researcher"])
    LLM(["LLM Provider (Groq)"])
    P2(("P2<br/>Run Workflow"))
    P3(("P3<br/>Enforce Policy"))
    P1(("P1<br/>Simulate Twin"))
    P4(("P4<br/>Persist &amp; Stream"))
    D1[("D1: topology, kpis, events, simulation")]
    D2[("D2: workflows, steps, trace, service_calls")]
    D3[("D3: memory, knowledge_*")]
    D4[("D4: policies, services, agents, users")]

    OP -->|"goal / fault"| P2
    P2 <-->|"reason"| LLM
    P2 -->|"action"| P3
    P3 -->|"apply"| P1
    P1 -->|"KPIs, events"| D1
    P1 -->|"snapshot"| P2
    P2 -->|"trace"| D2
    P3 -->|"calls"| D2
    P2 -->|"learn"| D3
    D4 -->|"rules"| P3
    P2 -->|"events"| P4
    P4 -->|"live updates"| OP
    P4 -.-> D2
```

<sub>The workflow process (P2) reasons with the LLM and proposes actions to the policy process (P3), which alone may apply changes to the twin (P1); a persist/stream process (P4) records events and drives the live console.</sub>

**State — network-function operational states**

```mermaid
stateDiagram-v2
    [*] --> STANDBY
    STANDBY --> ACTIVE: promote
    ACTIVE --> DEGRADED: KPI breach
    DEGRADED --> ACTIVE: KPI recovers
    DEGRADED --> FAILED: fault
    ACTIVE --> FAILED: fault injected
    FAILED --> RECOVERING: recovery starts
    RECOVERING --> ACTIVE: recovered
```

**State — workflow status states**

```mermaid
stateDiagram-v2
    [*] --> running
    running --> paused: pause
    paused --> running: resume
    running --> completed: all stages ok
    running --> failed: unrecoverable
    running --> cancelled: operator cancels
    completed --> [*]
    failed --> [*]
    cancelled --> [*]
```

<sub>A network function cycles through operational states; injected or emergent faults drive it to FAILED, from which a recovery workflow returns it to ACTIVE. A workflow runs until it completes, fails, or is cancelled, and may be paused and resumed.</sub>

</details>

<details>
<summary><b>🗄️ Data &amp; deployment</b></summary>

<br/>

**Database ER diagram (18 tables)**

```mermaid
erDiagram
    users {
        string id PK
        string username
        string role
    }
    agents {
        string role PK
        int enabled
    }
    services {
        string name PK
        string kind
        string owner_nf
    }
    policies {
        string id PK
        string severity
        string decision
    }
    simulation {
        int id PK
        string scenario
        int seed
        int tick
    }
    topology_nodes {
        string id PK
        string type
        string region
        string status
    }
    topology_links {
        string id PK
        string src_id FK
        string dst_id FK
    }
    kpis {
        int id PK
        string node_id FK
        int run_id FK
        float value
    }
    events {
        int id PK
        string type
        int run_id FK
    }
    workflows {
        string id PK
        string goal
        string trigger
        string status
        string created_by FK
    }
    workflow_steps {
        string id PK
        string workflow_id FK
        string service_name FK
        string status
    }
    workflow_trace {
        int id PK
        string workflow_id FK
        string stage
        string agent_role
    }
    logs {
        int id PK
        string level
        string correlation_id
    }
    memory {
        string id PK
        string scope
        string workflow_id FK
    }
    knowledge_nodes {
        string id PK
        string entity_type
        string label
    }
    knowledge_edges {
        int id PK
        string src_id FK
        string dst_id FK
        string provenance_workflow_id FK
    }
    models {
        string id PK
        string name
        string state
        string target_node_id FK
    }
    service_calls {
        int id PK
        string workflow_id FK
        string service_name FK
        string policy_id FK
        string status
    }

    users ||--o{ workflows : "creates"
    workflows ||--o{ workflow_steps : "has"
    services ||--o{ workflow_steps : "invoked by"
    workflows ||--o{ service_calls : "logs"
    services ||--o{ service_calls : "called in"
    policies ||--o{ service_calls : "decides"
    workflows ||--o{ workflow_trace : "records"
    workflows ||--o{ memory : "produces"
    simulation ||--o{ kpis : "context"
    topology_nodes ||--o{ kpis : "measured on"
    topology_nodes ||--o{ topology_links : "source"
    topology_nodes ||--o{ topology_links : "target"
    simulation ||--o{ events : "context"
    topology_nodes ||--o{ models : "hosts"
    knowledge_nodes ||--o{ knowledge_edges : "source"
    knowledge_nodes ||--o{ knowledge_edges : "target"
    workflows ||--o{ knowledge_edges : "provenance"
```

<sub>Italic-style FK columns point from the referencing table to its parent. <code>workflows</code> is the hub for operational tables, while <code>topology_nodes</code> anchors the twin's time series.</sub>

**Deployment topology**

```mermaid
flowchart LR
    Browser(["User Workstation<br/>Web Browser (Next.js SPA)"])

    subgraph Railway["Railway Cloud (free tier)"]
        FE["«container» Frontend Service<br/>Next.js 16 server (nixpacks)"]
        BE["«container» Backend Service<br/>Uvicorn + FastAPI (nixpacks)"]
        DBa[("«artifact» SQLite<br/>/tmp/agent5g.db")]
    end

    Groq["«external service» Groq API<br/>Llama 3.1 (OpenAI-compatible)"]

    Browser -->|"HTTPS (UI)"| FE
    Browser <-->|"HTTPS REST + WSS"| BE
    BE <-->|"HTTPS"| Groq
    BE -.->|"file I/O"| DBa
```

<sub>The browser loads the Next.js console and calls the FastAPI backend directly over REST and a secure WebSocket; the backend persists to an ephemeral SQLite file and consults a Groq-hosted LLM.</sub>

</details>

<details>
<summary><b>🧭 Product &amp; project view</b></summary>

<br/>

**Use-case view**

```mermaid
flowchart LR
    Operator(["Network Operator<br/>/ Researcher"])
    RecoveryActor(["Recovery Handler<br/>(system)"])
    LLMActor(["LLM Provider<br/>(Groq)"])

    subgraph Platform["Agent5G Platform"]
        UC1(["Submit operation goal"])
        UC2(["Monitor workflow (console)"])
        UC3(["Inject fault"])
        UC4(["View topology / twin"])
        UC5(["View analytics / KPIs"])
        UC6(["Browse audit logs"])
        UC7(["Manage models / services / policies"])
        UC8(["Control simulation (start/pause/step)"])
        UC9(["Run agentic workflow"])
        UC10(["Autonomously recover"])
        UC11(["Enforce safety policy"])
        UC12(["Reason via LLM"])
    end

    Operator --- UC1
    Operator --- UC2
    Operator --- UC3
    Operator --- UC4
    Operator --- UC5
    Operator --- UC6
    Operator --- UC7
    Operator --- UC8
    RecoveryActor --- UC10
    LLMActor --- UC12

    UC1 -.->|"include"| UC9
    UC10 -.->|"include"| UC9
    UC9 -.->|"include"| UC11
    UC9 -.->|"include"| UC12
```

<sub>Human operators use the console; the recovery handler is a system actor that triggers autonomous workflows; every workflow includes safety enforcement and LLM reasoning.</sub>

**Project workflow (capstone)**

```mermaid
flowchart TB
    Goal[/"User goal (typed)"/]
    Fault[/"Autonomous fault (NF_FAILED)"/]
    Obs["Observe"]
    Rea["Reason"]
    Pla["Plan"]
    Act["Act"]
    Ver["Verify"]
    SEL{{"SEL (safety gate)"}}
    Twin[("Digital Twin<br/>world state — 18 nodes, KPIs")]
    Out[/"Persist to DB &amp; stream to console<br/>(every stage)"/]

    Goal --> Obs
    Fault --> Obs
    Obs --> Rea --> Pla --> Act --> Ver --> Obs
    Twin -->|"read"| Obs
    Twin -->|"read"| Ver
    Act --> SEL -->|"mutate"| Twin
    Act -.-> Out
    Ver -.-> Out
```

<sub>A goal or an autonomous fault enters at Observe; only the safety-gated Act step mutates the twin; Verify closes the loop. The twin is the world, the agents are the mind, the SEL is the hands, and every step is recorded and streamed.</sub>

</details>

## 🎬 Demo scenarios

1. **Proactive model deployment** — the agent pushes an ML model to an edge node ahead of predicted demand.
2. **Autonomous congestion mitigation** — detects a KPI breach and executes a mitigation plan end-to-end.
3. **NRF fault detection & self-healing** — spots a service-registry failure and recovers the network automatically.

## 📊 By the numbers

`575` tests · `13` dashboard pages · `11` API routers + WebSocket · `9` 5G network functions · `3` live autonomous scenarios · `4` LLM modes (replay / live / record / fake)

## 🔗 Links

- 🚀 **Live platform:** https://agentic5g.up.railway.app
- 💻 **GitHub:** https://github.com/codehashira23/Agentic-5g

<br/>
<sub>Built as a summer research project on autonomous network operations for 5G Advanced / 6G.</sub>
</div>
