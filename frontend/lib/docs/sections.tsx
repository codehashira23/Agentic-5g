"use client";
/**
 * Section bodies for the hidden /internal documentation.
 * Every section is grounded in the real Agent5G codebase (FastAPI + SQLite +
 * hexagonal layers + deterministic digital-twin sim). Written in an engineering
 * "why / how / when / what-depends" style with interview questions.
 */
import {
  C,
  Callout,
  CodeBlock,
  Diagram,
  FileHeader,
  Flow,
  H2,
  H3,
  InterviewQA,
  KeyValue,
  Lead,
  Li,
  P,
  Pill,
  Table,
  Ul,
} from "@/components/docs/primitives";

/* ============================================================== 1. OVERVIEW */
export function OverviewSection() {
  return (
    <>
      <H2 id="what">What is Agent5G?</H2>
      <Lead>
        Agent5G is an autonomous operations platform for 5G Advanced (Release 20). It runs a
        deterministic <b>digital twin</b> of a 5G core, and a team of cooperating AI agents that
        observe the network, reason about faults, and repair them through a safe, auditable
        closed loop — without a human in the loop.
      </Lead>
      <P>
        The product is a monorepo: a <b>FastAPI</b> Python backend (<C>backend/</C>) that owns the
        simulation, agents and persistence, and a <b>Next.js 16</b> frontend (<C>frontend/</C>) that
        visualises everything in real time. These docs explain the whole system the way the author
        would present it in an interview — top-down architecture first, then layer by layer, then
        the exact files that matter.
      </P>

      <H3 id="stack">Technology at a glance</H3>
      <Table
        head={["Concern", "Choice", "Why"]}
        rows={[
          ["API", "FastAPI + Uvicorn", "Async, typed, auto OpenAPI"],
          ["Validation", "Pydantic v2 + pydantic-settings", "Typed models + env config"],
          ["Database", "SQLite + SQLAlchemy 2.0 (async)", "Zero-ops, deterministic demos"],
          ["AI", "LLM adapters (replay / live)", "$0 offline replay by default"],
          ["Realtime", "WebSocket + in-process event bus", "Live events, decoupled fan-out"],
          ["Frontend", "Next.js 16 · React 19 · TS", "App Router, RSC, fast DX"],
          ["State", "React Query + Zustand", "Server cache + live WS store"],
          ["Styling", "Tailwind v4 tokens", "Black & Gold design system"],
        ]}
      />

      <H2 id="how-to">How to read these docs</H2>
      <Ul>
        <Li>
          Use the <b>sidebar</b> to move between sections, or the <b>Files</b> tab to browse the real
          project tree — documented files are clickable.
        </Li>
        <Li>
          Press <C>/</C> to search, <C>←</C>/<C>→</C> to move section-to-section, and <C>F</C> to enter
          fullscreen <b>Presentation Mode</b> for a slide-style walkthrough.
        </Li>
        <Li>Expandable “Interview questions” blocks appear throughout — click to reveal answers.</Li>
      </Ul>
      <Callout type="tip" title="This page is private">
        <C>/internal</C> is excluded from search engines (noindex + robots.txt) and is never linked
        from the app navigation. It exists purely to present and explain the codebase.
      </Callout>
    </>
  );
}

/* ========================================================== 2. ARCHITECTURE */
export function ArchitectureSection() {
  return (
    <>
      <H2 id="layers">Layered (hexagonal) architecture</H2>
      <P>
        The backend follows clean/ports-and-adapters architecture. Dependencies point{" "}
        <b>inward</b>: the delivery layer depends on the application layer, which depends on the
        pure domain. Infrastructure implements domain <i>ports</i> (Protocols) and is assembled in a
        single composition root.
      </P>
      <Diagram caption="Dependency direction points inward; infrastructure is injected at the edges.">
        {`         ┌───────────────────────────────────────────────┐
         │  app/api        Delivery — FastAPI routers, WS  │
         │                 middleware, error envelope      │
         └───────────────┬───────────────────────────────┘
                         │ depends on
         ┌───────────────▼───────────────────────────────┐
         │  app/application   Use-cases — TwinService,     │
         │                    WorkflowEngine, agents, SEL  │
         └───────────────┬───────────────────────────────┘
                         │ depends on
         ┌───────────────▼───────────────────────────────┐
         │  app/domain     Pure business logic — Twin,     │
         │                 events, ports (NO frameworks)   │
         └───────────────▲───────────────────────────────┘
                         │ implements ports
         ┌───────────────┴───────────────────────────────┐
         │  app/infrastructure   DB, event bus, LLM, sim,  │
         │                       RNG, writer  →  container │
         └────────────────────────────────────────────────┘`}
      </Diagram>

      <H2 id="boundaries">Boundaries are enforced, not just documented</H2>
      <P>
        The layering is not a convention you can accidentally break — it is enforced in CI by{" "}
        <b>import-linter</b> contracts declared in <C>backend/pyproject.toml</C>:
      </P>
      <CodeBlock
        title="backend/pyproject.toml"
        lang="toml"
        code={`[[tool.importlinter.contracts]]
name = "Domain must not import any framework"
type = "forbidden"
source_modules = ["app.domain"]
forbidden_modules = ["fastapi", "sqlalchemy", "langgraph",
                     "app.api", "app.infrastructure"]

[[tool.importlinter.contracts]]
name = "Application must not import delivery layer"
source_modules = ["app.application"]
forbidden_modules = ["app.api"]`}
      />
      <Callout type="info" title="Why this matters">
        Because the domain cannot import SQLAlchemy or FastAPI, the twin and its rules can be unit
        tested with zero I/O, and the persistence or transport can be swapped without touching
        business logic. This is what makes the simulation deterministic and fast to test.
      </Callout>

      <InterviewQA
        items={[
          {
            q: "Why hexagonal architecture for a hackathon project?",
            a: "It keeps the deterministic domain (the twin + events) free of frameworks, so it is trivially unit-testable and reproducible. Adapters (DB, LLM, bus) are injected in one composition root, so the same domain runs identically under tests, replay mode, and live mode.",
          },
          {
            q: "How is the dependency direction actually guaranteed?",
            a: "import-linter runs the two forbidden-import contracts above as part of quality checks. If domain code imports SQLAlchemy or an application module imports the api layer, the check fails.",
          },
        ]}
      />
    </>
  );
}

/* ====================================================== 3. REQUEST LIFECYCLE */
export function RequestLifecycleSection() {
  return (
    <>
      <H2 id="factory">App factory & lifespan</H2>
      <P>
        <C>create_app()</C> in <C>backend/app/main.py</C> builds the FastAPI instance, installs
        middleware and error handlers, and mounts routers. A <C>lifespan</C> context builds the DI
        container once at startup and starts the background tasks (writer, event bus, scheduler),
        then tears them down on shutdown.
      </P>
      <CodeBlock
        title="backend/app/main.py (trimmed)"
        lang="python"
        code={`@asynccontextmanager
async def lifespan(app: FastAPI):
    container = await build_container(app.state.settings)
    app.state.container = container
    await container.start_background_tasks()   # writer, bus, scheduler
    yield
    await container.stop_background_tasks()

def create_app(settings=None) -> FastAPI:
    app = FastAPI(title="Agent5G API", lifespan=lifespan)
    middleware.install(app, cors_origin=app.state.settings.cors_origin)
    errors.install(app)                        # -> ErrorEnvelope
    app.include_router(api_router, prefix="/api/v1")
    app.include_router(ws_router)              # /ws
    return app`}
      />

      <H2 id="pipeline">The request pipeline</H2>
      <Flow
        steps={[
          { label: "HTTP request", sub: "from the Next.js client" },
          { label: "CORS middleware", sub: "localhost + *.railway.app" },
          { label: "Correlation middleware", sub: "X-Correlation-Id + timing" },
          { label: "Router + Depends(get_container)", sub: "DI resolves the container" },
          { label: "Application service", sub: "TwinService / WorkflowEngine / SEL" },
          { label: "Domain + infrastructure", sub: "twin logic, DB reads" },
          { label: "JSON response", sub: "or ErrorEnvelope on failure" },
        ]}
      />
      <P>
        Dependency injection is deliberately tiny: <C>app/api/deps.py</C> exposes a single{" "}
        <C>get_container(request)</C> that returns the container stored on <C>app.state</C>. Every
        route that needs services declares <C>c: Container = Depends(get_container)</C>. There is no
        auth dependency — see <b>Security & Future</b>.
      </P>
      <CodeBlock
        title="backend/app/api/middleware.py — correlation id"
        lang="python"
        code={`class CorrelationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        cid = request.headers.get("X-Correlation-Id", f"req_{uuid4().hex[:8]}")
        request.state.correlation_id = cid
        start = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Correlation-Id"] = cid
        response.headers["X-Response-Time-Ms"] = f"{(time.perf_counter()-start)*1000:.1f}"
        return response`}
      />
      <InterviewQA
        items={[
          {
            q: "Why build the container in lifespan instead of per-request?",
            a: "The container owns long-lived singletons — the async DB engine, the event bus, the sim scheduler and background tasks. They must exist for the whole process, so they are created once at startup and shared via app.state, then injected read-only through Depends.",
          },
          {
            q: "What is the correlation id for?",
            a: "Every request and every domain event carries a correlation_id so a UI action can be traced across the API, the event bus, persisted rows and logs. It is echoed back in a response header for client-side tracing.",
          },
        ]}
      />
    </>
  );
}

/* ========================================================== 4. DOMAIN LAYER */
export function DomainLayerSection() {
  return (
    <>
      <H2 id="twin">The domain is a network, not a database</H2>
      <P>
        <C>app/domain</C> is framework-free business logic. The centrepiece is <C>NetworkTwin</C>{" "}
        (<C>domain/twin/network_twin.py</C>): an in-memory model of a 5G core made of Network
        Functions (AMF, SMF, UPF, NRF, NWDAF, DCF, Edge…), a topology of nodes/links, and KPIs. Its{" "}
        <C>advance(rng, tick)</C> method steps the world forward one tick and returns a list of{" "}
        <C>DomainEvent</C>s.
      </P>
      <Table
        head={["Module", "Responsibility"]}
        rows={[
          [<C key="a">twin/network_twin.py</C>, "The twin aggregate — advance(), snapshot(), apply_command()"],
          [<C key="b">twin/nf/*.py</C>, "Per-NF behaviour (amf, smf, upf, nrf, nwdaf, dcf, edge…)"],
          [<C key="c">twin/events.py</C>, "DomainEvent + NfFailedEvent, WorkflowStageChanged, KPI events"],
          [<C key="d">twin/kpi.py, topology.py</C>, "KPI definitions, node/link graph, regions"],
          [<C key="e">agents/ports.py</C>, "Protocols: MemoryStore, WorkflowRepository, LLMClient, EventBus, Rng"],
          [<C key="f">services/policy.py</C>, "Policy value objects used by the SEL"],
        ]}
      />

      <H2 id="ports">Ports keep the domain pure</H2>
      <P>
        Instead of importing infrastructure, the domain declares <b>ports</b> — Python{" "}
        <C>Protocol</C>s that infrastructure implements. This is the “hexagonal” seam.
      </P>
      <CodeBlock
        title="backend/app/domain/agents/ports.py (shape)"
        lang="python"
        code={`class EventBus(Protocol):
    async def publish(self, event: Any) -> None: ...

class LLMClient(Protocol):
    async def complete(self, prompt: str, **kw) -> str: ...

class Rng(Protocol):
    def for_tick(self, tick: int) -> "Rng": ...`}
      />
      <Callout type="info" title="Determinism by design">
        The twin never calls <C>random</C> directly — it receives a seeded <C>Rng</C> stream per
        tick. Same seed ⇒ same trajectory, which is what makes the golden-trajectory tests
        (<C>backend/tests/determinism</C>) possible.
      </Callout>
    </>
  );
}

/* ===================================================== 5. APPLICATION LAYER */
export function ApplicationLayerSection() {
  return (
    <>
      <H2 id="twin-service">TwinService — the heartbeat</H2>
      <P>
        <C>application/twin_service/service.py</C> connects the pure twin to the outside world. On
        every tick it advances the twin, then splits the resulting events into two persistence
        strategies and publishes everything on the bus.
      </P>
      <CodeBlock
        title="TwinService.on_tick (trimmed)"
        lang="python"
        code={`async def on_tick(self, tick: int):
    stream = self._rng.for_tick(tick)          # deterministic RNG
    events = self._twin.advance(stream, tick)  # domain steps forward
    for evt in events:
        if evt.type == "KPI_UPDATED":
            self._kpi_buffer.append(...)        # write-behind (batched)
        else:
            await self._writer.submit(insert(EventRow)...)  # write-through
    await self._flush_kpis()
    for evt in events:
        await self._bus.publish(evt)            # fan-out to subscribers
    return events`}
      />

      <H2 id="workflow">The 8-stage workflow lifecycle</H2>
      <P>
        <C>application/workflow/engine.py</C> runs an autonomous remediation as a state machine.
        Each stage is persisted to <C>workflows</C> + <C>workflow_trace</C>, and stage transitions
        emit <C>WORKFLOW_*</C> events on the bus.
      </P>
      <Flow
        steps={[
          { label: "observe", sub: "gather twin + KPI state" },
          { label: "reason", sub: "LLM interprets the fault" },
          { label: "plan", sub: "produce an action plan" },
          { label: "execute", sub: "invoke services (loop)", tone: "cyan" },
          { label: "validate", sub: "check success criteria" },
          { label: "complete | retry | rollback", sub: "terminal routing" },
        ]}
      />

      <H2 id="agents">Seven cooperating agents + the SEL</H2>
      <P>
        <C>application/agents/orchestrator.py</C> wires seven roles — observer, planner, executor,
        optimizer, recovery, documentation, memory — each with a scoped tool context. Agents never
        touch the twin directly; they act only through the <b>Service Enablement Layer</b> (SEL):
        a service <C>registry</C>, a <C>policy_engine</C> (guardrails), and an <C>invoker</C> that
        is the single mutation path into the twin.
      </P>
      <P>
        Autonomy is closed by <C>application/recovery/autonomous.py</C>: the container subscribes it
        to <C>NF_FAILED</C> events, so a failed Network Function automatically starts a recovery
        workflow.
      </P>
      <InterviewQA
        items={[
          {
            q: "Why split KPI writes (write-behind) from discrete events (write-through)?",
            a: "KPIs are high-frequency time-series — batching them avoids hammering SQLite. Discrete events (faults, recoveries, workflow transitions) are low-frequency but important for auditability, so they are persisted immediately.",
          },
          {
            q: "How does a fault become an autonomous repair?",
            a: "Injecting a fault publishes NF_FAILED on the bus. AutonomousRecoveryHandler (subscribed with lossless=true) receives it and calls WorkflowEngine.start(), which runs observe→reason→plan→execute→validate and emits WORKFLOW_* events back onto the bus.",
          },
          {
            q: "Why can agents only act through the SEL invoker?",
            a: "It centralises policy checks and gives one auditable mutation path into the twin (invariant TP6). Every action is validated by the policy engine and recorded, so agent behaviour stays safe and traceable.",
          },
        ]}
      />
    </>
  );
}

/* ================================================= 6. SIMULATION & EVENT BUS */
export function SimulationBusSection() {
  return (
    <>
      <H2 id="scheduler">The tick clock</H2>
      <P>
        <C>infrastructure/sim/scheduler.py</C> is a background loop. Every <C>SIM__TICK_MS</C>{" "}
        milliseconds it calls the wired <C>on_tick</C> callback (which is <C>TwinService.on_tick</C>).
        It supports <C>start / pause / step(n) / reset</C> so the UI can drive the simulation.
      </P>
      <Diagram caption="One tick: advance → persist → publish → (autonomous recovery).">
        {`SimScheduler.run()  every tick_ms
      │
      ▼
TwinService.on_tick(tick)
      │  rng.for_tick(tick) → twin.advance() → events[]
      ├──────────────┬───────────────────────────┐
      ▼              ▼                           ▼
 KPI buffer     EventRow insert            bus.publish(evt)
 (write-behind) (write-through)                  │
      └──────► PersistenceWriter ◄────────────────┘
              (single-writer queue → SQLite)      │
                                                  ▼
                                    subscribers (e.g. NF_FAILED
                                    → AutonomousRecoveryHandler)`}
      </Diagram>

      <H2 id="bus">The in-process event bus</H2>
      <P>
        <C>infrastructure/bus/bus.py</C> is a persist-first pub/sub. <C>publish()</C> optionally
        persists, then fans the event out to each subscriber’s bounded async queue; a background{" "}
        <C>run()</C> loop drains those queues and invokes handlers. Critical handlers subscribe with{" "}
        <C>lossless=True</C> so their events are never dropped under back-pressure.
      </P>
      <CodeBlock
        title="bus.publish (trimmed)"
        lang="python"
        code={`async def publish(self, event):
    if self._persist_fn:
        await self._persist_fn(event)          # persist-first
    etype = event.type.value
    for sub in self._subscriptions:
        if not sub.event_types or etype in sub.event_types:
            sub.offer(event)                    # into bounded queue`}
      />

      <H2 id="writer">Why a single-writer queue?</H2>
      <Callout type="warn" title="SQLite writers serialise">
        SQLite allows only one writer at a time. Under a fast tick loop, concurrent inserts throw
        “database is locked”. <C>infrastructure/writer/writer.py</C> funnels <b>all</b> writes
        through one queue and commits them in batches (up to 200), so the sim, agents and API never
        contend for the write lock.
      </Callout>
      <P>
        Reads use short-lived sessions (<C>Database.session()</C>); writes go through{" "}
        <C>writer.submit(WriteOp(...))</C>. Determinism comes from <C>infrastructure/rng/rng.py</C>,
        which derives a per-tick stream from the base seed.
      </P>
      <InterviewQA
        items={[
          {
            q: "Isn't a single writer a bottleneck?",
            a: "For this workload it is the opposite — batching commits amortises fsyncs and removes lock retries. WAL mode plus busy_timeout keeps reads concurrent with the single writer. It trades a tiny bit of write latency for stability and determinism.",
          },
          {
            q: "What happens to events if a subscriber is slow?",
            a: "Each subscriber has its own bounded queue. Non-critical subscribers drop the oldest event under back-pressure; critical ones (lossless=true) block rather than drop, so faults are never lost.",
          },
        ]}
      />
    </>
  );
}

/* ============================================================== 7. DATABASE */
export function DatabaseSection() {
  return (
    <>
      <H2 id="why-sqlite">Why SQLite (and not MongoDB)?</H2>
      <P>
        The platform is a self-contained, reproducible demo. SQLite means zero external services,
        instant startup, and a file you can delete to reset. It is accessed through{" "}
        <b>SQLAlchemy 2.0 async</b> over the <C>aiosqlite</C> driver.
      </P>
      <CodeBlock
        title="infrastructure/db/engine.py — connection PRAGMAs"
        lang="python"
        code={`@event.listens_for(engine.sync_engine, "connect")
def _apply_pragmas(dbapi_conn, _):
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")     # readers don't block the writer
    cur.execute("PRAGMA foreign_keys=ON")      # enforce relationships
    cur.execute("PRAGMA busy_timeout=5000")    # wait, don't fail, on contention
    cur.execute("PRAGMA synchronous=NORMAL")   # fast + safe under WAL
    cur.close()`}
      />

      <H2 id="schema">The 18 tables</H2>
      <P>
        <C>infrastructure/db/models.py</C> declares the schema. ORM rows are kept separate from
        domain entities (repositories translate between them), so the domain stays framework-free.
      </P>
      <Table
        head={["Group", "Tables"]}
        rows={[
          ["Identity", "users (role column, unenforced)"],
          ["Agents & AI", "agents, memory, knowledge_nodes, knowledge_edges, models"],
          ["Services (SEL)", "services, policies, service_calls"],
          ["Network / Twin", "simulation, topology_nodes, topology_links, kpis, events"],
          ["Workflows", "workflows, workflow_steps, workflow_trace"],
          ["Ops", "logs"],
        ]}
      />
      <Callout type="info" title="Two write patterns">
        <b>Write-through</b> for discrete rows (events, workflow steps) — persisted immediately for
        auditability. <b>Write-behind</b> for KPI time-series — buffered and batch-inserted for
        throughput. Both go through the single-writer queue.
      </Callout>
      <InterviewQA
        items={[
          {
            q: "How do you keep ORM models out of the domain?",
            a: "Domain entities are plain dataclasses/Pydantic models in app/domain. SQLAlchemy Row classes live only in infrastructure/db/models.py, and repositories in infrastructure/db/repos map between the two. import-linter forbids the domain from importing sqlalchemy at all.",
          },
          {
            q: "Why does run_id appear on time-series rows?",
            a: "Each simulation run is a context; KPIs and events carry run_id so the analytics endpoints can scope a time-series to one run and so resets don't mix data across runs.",
          },
        ]}
      />
    </>
  );
}

/* ========================================================= 8. LLM & AGENTS */
export function LlmAgentsSection() {
  return (
    <>
      <H2 id="adapters">LLM adapters behind one port</H2>
      <P>
        <C>infrastructure/llm/client.py</C> implements the domain <C>LLMClient</C> port with three
        interchangeable adapters, selected by <C>build_llm()</C> from settings:
      </P>
      <Table
        head={["Adapter", "Mode", "Use"]}
        rows={[
          [<C key="r">ReplayClient</C>, "replay (default)", "Serves recorded JSON fixtures by request hash — offline, $0, deterministic"],
          [<C key="g">GroqClient</C>, "live", "OpenAI-compatible /chat/completions (groq / openrouter / ollama)"],
          [<C key="f">FakeLLM</C>, "tests", "Canned responses for unit tests"],
        ]}
      />
      <CodeBlock
        title="backend/.env — LLM configuration"
        lang="bash"
        code={`LLM__MODE=replay          # replay ($0, offline) | record | live
LLM__PROVIDER=anthropic   # anthropic | gemini | groq | openrouter | ollama
LLM__MODEL=claude-4.8
LLM__API_KEY=             # free-tier key; blank for replay / ollama`}
      />
      <Callout type="tip" title="$0 by default">
        Replay mode makes demos fully offline and reproducible: the same prompt hash always returns
        the same fixture, so a judge sees identical agent reasoning every run with no API key and no
        cost.
      </Callout>

      <H2 id="agent-roles">The agent roles</H2>
      <Table
        head={["Agent", "Job"]}
        rows={[
          ["observer", "Reads twin/KPI state, detects anomalies"],
          ["planner", "Interprets the situation, produces a plan"],
          ["executor", "Runs plan steps via the SEL invoker"],
          ["optimizer", "Proposes tuning to improve KPIs"],
          ["recovery", "Drives fault remediation"],
          ["documentation", "Writes human-readable trace/summaries"],
          ["memory", "Stores/recalls episodic + semantic memory"],
        ]}
      />
      <P>
        Prompts are centralised in <C>application/agents/prompts/registry.py</C>. Each role gets a
        scoped tool set via <C>orchestrator.make_context(role)</C>, so an observer cannot execute
        mutations, etc.
      </P>
      <Callout type="warn" title="Honest note on LangGraph">
        <C>langgraph</C> is declared as a dependency, but the workflow state machine here is
        hand-rolled in <C>application/workflow/engine.py</C>. Treat “LangGraph orchestration” as
        available-but-not-currently-wired.
      </Callout>
    </>
  );
}

/* ==================================================== 9. FRONTEND ARCHITECTURE */
export function FrontendArchSection() {
  return (
    <>
      <H2 id="app-router">App Router shell</H2>
      <P>
        The frontend is Next.js 16 (App Router). <C>app/layout.tsx</C> is the root shell: it loads
        fonts, wraps everything in <C>Providers</C> (React Query), mounts <C>WsInit</C> (the
        WebSocket client) and the hidden <C>SecretHotkey</C>, and renders the persistent{" "}
        <C>NavRail</C> + <C>TopBar</C> around the routed <C>{"{children}"}</C>.
      </P>
      <CodeBlock
        title="app/layout.tsx (trimmed)"
        lang="tsx"
        code={`<Providers>
  <AppErrorBoundary>
    <WsInit />            {/* opens ws://…/ws, feeds the zustand store */}
    <SecretHotkey />      {/* g,p → hidden presentation deck */}
    <NavRail /> <TopBar />
    <main>{children}</main>
  </AppErrorBoundary>
</Providers>`}
      />
      <P>
        There are 13 feature routes under <C>app/</C> (dashboard, analytics, agent-console,
        workflow-builder, memory, knowledge-graph, topology, digital-twin, simulation, model-manager,
        service-registry, logs, settings) plus two hidden routes: <C>%5F%5Fpresent</C> (the keynote
        deck) and this <C>internal</C> docs page.
      </P>

      <H2 id="state">Two kinds of state</H2>
      <Table
        head={["Kind", "Tool", "What it holds"]}
        rows={[
          ["Server cache", "React Query", "REST responses (twin, workflows, analytics) with polling"],
          ["Live state", "Zustand (useWsStore)", "WS connection, tick, alerts, NF status, event feed"],
        ]}
      />
      <P>
        <C>lib/api/client.ts</C> is a tiny typed <C>fetch</C> wrapper (<C>api.get/post/put/del</C>)
        with an <C>ApiError</C> class and a base URL from <C>NEXT_PUBLIC_API_BASE</C>.{" "}
        <C>lib/query/keys.ts</C> centralises query keys so WS events can invalidate exactly the right
        caches.
      </P>
      <InterviewQA
        items={[
          {
            q: "Why both React Query and Zustand?",
            a: "They solve different problems. React Query owns server state — caching, deduping and polling REST endpoints. Zustand owns ephemeral live state pushed over WebSocket (tick, alerts, NF status). Keeping them separate avoids stuffing transient socket data into the query cache.",
          },
          {
            q: "How does a live event refresh a page without a refetch storm?",
            a: "The WS store's apply() reducer calls queryClient.invalidateQueries for just the affected keys (e.g. ['topology'], ['workflows']). Only those queries refetch; everything else stays cached.",
          },
        ]}
      />
    </>
  );
}

/* ============================================================= 10. DATA FLOW */
export function DataFlowSection() {
  return (
    <>
      <H2 id="rest">Flow A — reading dashboard metrics</H2>
      <P>A page mounts, React Query pulls REST endpoints on an interval, and renders cards.</P>
      <Flow
        steps={[
          { label: "DashboardPage", sub: "useQuery(refetchInterval: 3s)" },
          { label: "api.get('/simulation/status')", sub: "lib/api/client.ts" },
          { label: "GET /api/v1/simulation/status", sub: "routers/simulation.py" },
          { label: "TwinService.get_status()", sub: "reads NetworkTwin" },
          { label: "JSON → React Query cache", sub: "{status, tick, nf_count}" },
          { label: "<StatCard/> renders", sub: "UI updates" },
        ]}
      />

      <H2 id="tick">Flow B — a simulation tick reaching the UI</H2>
      <Flow
        steps={[
          { label: "SimScheduler tick", sub: "every tick_ms" },
          { label: "TwinService.on_tick", sub: "advance + persist + publish" },
          { label: "Event bus fan-out", sub: "e.g. NF_FAILED → recovery" },
          { label: "DB rows updated", sub: "events / kpis / simulation" },
          { label: "React Query refetch", sub: "3–5s polling picks up changes", tone: "cyan" },
          { label: "Components re-render", sub: "topology, analytics, workflows" },
        ]}
      />

      <H2 id="ws">Live updates: how they actually work today</H2>
      <Callout type="warn" title="Honest architecture note">
        The WebSocket endpoint (<C>/ws</C>) and a <C>WebSocketHub.broadcast()</C> exist, and the
        frontend store is ready to reduce <C>NF_FAILED</C>, <C>KPI_THRESHOLD_BREACH</C> and{" "}
        <C>WORKFLOW_*</C> events. But <b>no code currently subscribes the hub to the event bus</b>,
        so the server only sends <C>HELLO</C>/<C>PING</C> over the socket. In practice the UI stays
        fresh via React Query <b>polling</b> (3–5s) plus cache invalidation. Wiring the hub to the
        bus (one subscriber in the container) would turn on true push updates — see{" "}
        <b>Security & Future</b>.
      </Callout>
      <P>
        The client side is fully built: <C>lib/ws/ws-init.tsx</C> opens the socket with auto-reconnect
        and routes every message to <C>useWsStore.apply()</C> in <C>lib/ws/store.ts</C>, which
        updates live state and invalidates the matching React Query keys.
      </P>
    </>
  );
}

/* =========================================================== 11. API REFERENCE */
export function ApiReferenceSection() {
  return (
    <>
      <H2 id="rest-endpoints">REST endpoints</H2>
      <P>
        All HTTP routes are mounted under <C>/api/v1</C> (see <C>app/api/routers/__init__.py</C>).
        Every route resolves the container via <C>Depends(get_container)</C>.
      </P>
      <Table
        head={["Method", "Path", "Purpose"]}
        rows={[
          [<Pill key="1" tone="cyan">GET</Pill>, <C key="a">/simulation/status</C>, "Current sim status, tick, seed, nf_count"],
          [<Pill key="2" tone="ai">POST</Pill>, <C key="b">/simulation/start|pause|step|reset</C>, "Control the tick clock"],
          [<Pill key="3" tone="ai">POST</Pill>, <C key="c">/simulation/fault</C>, "Inject a fault → publishes NF_FAILED"],
          [<Pill key="4" tone="cyan">GET</Pill>, <C key="d">/analytics/kpis</C>, "KPI time-series + available KPIs"],
          [<Pill key="5" tone="cyan">GET</Pill>, <C key="e">/twin, /topology</C>, "Twin snapshot, node/link graph"],
          [<Pill key="6" tone="cyan">GET</Pill>, <C key="f">/workflows</C>, "Workflow list + traces"],
          [<Pill key="7" tone="cyan">GET</Pill>, <C key="g">/services, /policies, /models, /logs</C>, "SEL catalog, policies, AIMLE models, logs"],
          [<Pill key="8" tone="cyan">GET</Pill>, <C key="h">/health</C>, "Liveness probe"],
        ]}
      />

      <H2 id="ws-proto">WebSocket</H2>
      <P>
        <C>ws://…/ws</C> — on connect the server sends a <C>HELLO</C> handshake, then keepalive{" "}
        <C>PING</C> every 30s (client may reply <C>{'{"op":"ping"}'}</C> → <C>PONG</C>). Event
        envelopes have the shape below.
      </P>
      <CodeBlock
        title="WS event envelope"
        lang="json"
        code={`{
  "type": "NF_FAILED",
  "event_id": "evt_…",
  "correlation_id": "req_…",
  "ts": "2026-…Z",
  "tick": 128,
  "payload": { "entity_id": "upf-1", "cause": "injected" }
}`}
      />
      <H2 id="errors">Error envelope</H2>
      <P>
        Exceptions are normalised by <C>app/api/errors.py</C> into a consistent JSON body the
        frontend’s <C>ApiError</C> understands.
      </P>
      <CodeBlock
        title="Error response"
        lang="json"
        code={`{ "title": "Not Found", "detail": "…", "status": 404 }`}
      />
    </>
  );
}

/* ============================================================= 12. KEY FILES */
export function KeyFilesSection() {
  return (
    <>
      <H2 id="key-files">The files that matter</H2>
      <P>
        A curated walkthrough of the anchor files. If you understand these twelve, you understand
        the system.
      </P>

      <FileHeader path="backend/app/main.py" tech={["FastAPI"]} />
      <KeyValue
        items={[
          ["Purpose", "Application entry point"],
          ["Responsibility", "create_app() factory + lifespan; installs middleware/errors; mounts routers"],
          ["Imports", "api.routers, api.middleware, api.errors, infrastructure.container"],
          ["Flow", "startup → build_container → start background tasks → serve → shutdown"],
        ]}
      />

      <FileHeader path="backend/app/infrastructure/container.py" tech={["DI"]} />
      <KeyValue
        items={[
          ["Purpose", "The composition root — the ONLY place adapters are assembled"],
          ["Responsibility", "build DB, writer, bus, rng, LLM, SEL, twin_service, orchestrator, engine; seed DB; subscribe recovery to NF_FAILED; wire scheduler"],
          ["Imported by", "main.py (lifespan)"],
          ["Why it matters", "Single source of truth for object wiring; where the WS hub would be subscribed to the bus"],
        ]}
      />

      <FileHeader path="backend/app/application/twin_service/service.py" tech={["Sim"]} />
      <KeyValue
        items={[
          ["Purpose", "Bridge between the pure twin and infrastructure"],
          ["Responsibility", "on_tick(): advance twin → persist (write-through/behind) → publish events; snapshot(); apply_command()"],
          ["Depends on", "NetworkTwin (domain), PersistenceWriter, EventBus, Rng"],
        ]}
      />

      <FileHeader path="backend/app/application/workflow/engine.py" tech={["State machine"]} />
      <KeyValue
        items={[
          ["Purpose", "Run an autonomous remediation as an 8-stage lifecycle"],
          ["Responsibility", "observe→reason→plan→execute→validate→complete/retry/rollback; persist workflow + trace; emit WORKFLOW_* events"],
          ["Imported by", "container.py; AutonomousRecoveryHandler"],
        ]}
      />

      <FileHeader path="backend/app/infrastructure/bus/bus.py" tech={["Pub/Sub"]} />
      <KeyValue
        items={[
          ["Purpose", "In-process event bus"],
          ["Responsibility", "persist-first publish; fan-out to bounded per-subscriber queues; run() dispatch loop; lossless option"],
        ]}
      />

      <FileHeader path="backend/app/infrastructure/writer/writer.py" tech={["SQLite"]} />
      <KeyValue
        items={[
          ["Purpose", "Single-writer persistence queue"],
          ["Responsibility", "serialise ALL writes; batch commit (≤200) to avoid 'database is locked'"],
        ]}
      />

      <FileHeader path="backend/app/infrastructure/db/models.py" tech={["SQLAlchemy"]} />
      <KeyValue
        items={[
          ["Purpose", "The 18-table schema"],
          ["Responsibility", "ORM Row classes with CheckConstraints/indexes; kept separate from domain entities"],
        ]}
      />

      <FileHeader path="backend/app/api/ws/hub.py" tech={["WebSocket"]} />
      <KeyValue
        items={[
          ["Purpose", "Track connected sockets + broadcast envelopes"],
          ["Responsibility", "connect()/disconnect()/broadcast(); HELLO handshake"],
          ["Status", "broadcast() exists but is not yet called by any bus subscriber"],
        ]}
      />

      <FileHeader path="frontend/app/layout.tsx" tech={["Next.js"]} />
      <KeyValue
        items={[
          ["Purpose", "Root shell for every route"],
          ["Responsibility", "fonts, Providers, WsInit, SecretHotkey, NavRail + TopBar around children"],
        ]}
      />

      <FileHeader path="frontend/lib/api/client.ts" tech={["fetch"]} />
      <KeyValue
        items={[
          ["Purpose", "Typed REST client"],
          ["Responsibility", "api.get/post/put/del; ApiError; base = NEXT_PUBLIC_API_BASE"],
          ["Imported by", "every page/hook that calls the backend"],
        ]}
      />

      <FileHeader path="frontend/lib/ws/store.ts" tech={["Zustand"]} />
      <KeyValue
        items={[
          ["Purpose", "Live WebSocket state"],
          ["Responsibility", "apply(event) reduces NF_FAILED/NF_RECOVERED/KPI_THRESHOLD_BREACH/WORKFLOW_*; invalidates React Query keys"],
        ]}
      />

      <FileHeader path="frontend/app/dashboard/page.tsx" tech={["React Query"]} />
      <KeyValue
        items={[
          ["Purpose", "Representative feature page"],
          ["Responsibility", "poll /simulation/status + /twin; read alerts/workflows from the WS store; render StatCards + feeds"],
        ]}
      />
    </>
  );
}

/* ============================================================ 13. DEPLOYMENT */
export function DeploymentSection() {
  return (
    <>
      <H2 id="railway">Deployment on Railway</H2>
      <P>
        Both apps deploy to Railway via <C>nixpacks.toml</C> + <C>railway.json</C>. The backend runs
        Uvicorn; the frontend runs <C>next start</C>. On production the DB path switches to{" "}
        <C>/tmp/agent5g.db</C> (always writable on Railway) via <C>Settings.effective_db_path</C>.
      </P>

      <H2 id="env">Environment variables</H2>
      <Table
        head={["Where", "Variable", "Default / meaning"]}
        rows={[
          ["backend", <C key="1">ENV</C>, "dev | test | demo | production"],
          ["backend", <C key="2">DB_PATH</C>, "data/agent5g.db (→ /tmp on prod)"],
          ["backend", <C key="3">CORS_ORIGIN</C>, "http://localhost:3000 (or comma list / *)"],
          ["backend", <C key="4">LLM__MODE</C>, "replay (default) | record | live"],
          ["backend", <C key="5">SIM__TICK_MS</C>, "1000 — tick interval"],
          ["frontend", <C key="6">NEXT_PUBLIC_API_BASE</C>, "http://localhost:8000/api/v1"],
          ["frontend", <C key="7">NEXT_PUBLIC_WS_URL</C>, "ws://localhost:8000/ws"],
        ]}
      />
      <Callout type="info" title="Secrets never leak">
        API keys use Pydantic <C>SecretStr</C>, so they are never logged or returned by any
        endpoint. The <C>.env</C> file is git-ignored.
      </Callout>
    </>
  );
}

/* ====================================================== 14. SECURITY & FUTURE */
export function SecurityFutureSection() {
  return (
    <>
      <H2 id="posture">Current security posture (honest)</H2>
      <P>This is a demo platform, so the security surface is intentionally small — and worth being precise about.</P>
      <Table
        head={["Area", "Status"]}
        rows={[
          ["Authentication", "None — no login, JWT, cookies or sessions"],
          ["Authorization", "None — users.role exists as data but is not enforced (no RBAC)"],
          ["CORS", "Locked to localhost + *.railway.app (configurable)"],
          ["Secrets", "SecretStr; .env git-ignored; never logged"],
          ["Tracing", "Correlation id on every request + event"],
          ["Input", "Pydantic validates request bodies at the boundary"],
        ]}
      />
      <Callout type="danger" title="Do not expose this publicly as-is">
        Because there is no auth, the control endpoints (start/pause/fault/reset) are open to anyone
        who can reach the API. That is fine for a local/demo deployment behind a private URL, but
        production use needs the auth work below.
      </Callout>

      <H2 id="future">Future improvements</H2>
      <Ul>
        <Li>
          <b>Wire the WebSocket hub to the event bus</b> — one subscriber in <C>container.py</C>{" "}
          calling <C>hub.broadcast(evt)</C> turns polling into true real-time push. The frontend
          already handles the events.
        </Li>
        <Li>
          <b>Add authentication + RBAC</b> — the <C>users</C> table (admin/researcher/viewer) is
          ready; add a JWT/session dependency and gate mutating routes by role.
        </Li>
        <Li><b>Indexes & retention</b> on the high-volume <C>kpis</C>/<C>events</C> tables for long runs.</Li>
        <Li><b>Wire LangGraph</b> (already a dependency) as an alternative workflow runtime.</Li>
        <Li><b>Rate limiting + structured request logging</b> on the API.</Li>
      </Ul>
      <InterviewQA
        items={[
          {
            q: "If you had one more day, what would you do first?",
            a: "Wire the hub to the bus for real push updates — it's the highest-impact, lowest-effort change (a single subscriber), and it removes polling latency across the whole UI. Then add a minimal auth dependency to protect the mutating simulation endpoints.",
          },
        ]}
      />
    </>
  );
}
