# Commit Plan — Building Agent5G Slowly, One Small Commit at a Time

> **Purpose:** a granular, ordered list of **small, non-breaking commits**. Each commit touches only a few files, leaves the repository in a **working state** (installs / lints / typechecks / tests pass for what exists), and is **verified before moving on**. Build slowly: do one commit, confirm it's green, then proceed.
> **Toolchain:** **pip + venv** (Python), **npm** (Node), Windows 11 / PowerShell.
> **Follows:** the phases and Two-Day Delivery Plan in `15-kiro-rules.md` §4/§4.1, broken into micro-commits.
> **LLM:** default `replay` (offline, $0). No paid services (CST-1).

---

## How to use this file

1. Do the commits **in order**. Do not skip ahead.
2. Each commit lists: **files**, **what it does**, and a **verify** step (the gate). Only commit when verify passes.
3. Use the exact **commit message** given (Conventional Commits). Keep commits focused.
4. If a commit breaks something, **fix or revert** before the next one — never build on a red state.
5. Check the box when done. Track progress here.

**Commit message format:** `type(scope): summary` — types: `chore`, `feat`, `test`, `docs`, `refactor`, `fix`, `build`.

**Per-commit verify baseline** (run what applies to the files you touched):
- Backend: `.venv\Scripts\activate` then `ruff check .`, `mypy app`, `pytest -q`
- Frontend: `npm run lint`, `npx tsc --noEmit`, `npm test` (once tests exist)
- Nothing should error for code that exists.

---

## Phase 0 — Repository & Git bootstrap

- [x] **C001** `chore: initialize git repository and base structure`
  - Repo already initialized on branch `main` with one commit ("init repo for agentic 5g"). Clean working tree.
  - `.gitignore` confirmed tracking `planning/`, `.env`, `data/*.db`, `node_modules/`, `.venv/`.
  - Verified: `git status` clean; `.gitignore` committed.

- [x] **C002** `chore: confirm docs/ intentionally ignored (planning-only)`
  - Decision: `docs/` stays in `.gitignore` — it is local design/planning material. Only code ships in the repo.
  - No files to stage. Nothing to commit.
  - Verified: `git ls-files docs/` returns empty (correct).

---

## Phase 1 — Backend scaffolding (pip + venv)

- [x] **C010** `build: add backend package skeleton and pyproject`
  - Files: `backend/pyproject.toml`, `backend/app/__init__.py`, `backend/app/domain/__init__.py`,
    `backend/app/application/__init__.py`, `backend/app/infrastructure/__init__.py`,
    `backend/app/api/__init__.py`, `backend/tests/__init__.py` + sub-package `__init__.py` files.
  - `pyproject.toml`: project metadata, `requires-python>=3.11`, all pinned deps, ruff/mypy/pytest/import-linter config.
  - Verified: `pip install -e ".[dev]"` succeeded; all packages installed.

- [x] **C011** `chore: configure ruff, mypy, and pytest`
  - Configured inside `pyproject.toml` (tool sections). `asyncio_default_fixture_loop_scope = "function"` silences the deprecation warning.
  - Verified: `ruff check .` → All checks passed; `mypy app` → no issues (5 files); `pytest -q` → no tests ran (correct).

- [x] **C012** `chore: add import-linter layer contracts`
  - Two contracts in `pyproject.toml`: domain must not import fastapi/sqlalchemy/langgraph/app.api/app.infrastructure; application must not import app.api.
  - Verified: `lint-imports` → 2 kept, 0 broken. **Gate G1 PASSED.**

- [x] **C013** `feat: minimal FastAPI app with /health`
  - Files: `app/main.py` (create_app + `/health` returning `{"status":"ok"}`).
  - Verified: `ruff` ✅ · `mypy` ✅ (6 files) · `GET /health` → `{"status":"ok"}` ✅
  - Commit: `feat: minimal FastAPI app with /health endpoint`

- [x] **C014** `test: health endpoint integration test`
  - Files: `tests/integration/test_health.py` (2 tests via httpx AsyncClient + ASGITransport).
  - Verified: `pytest -q` → 2 passed · `ruff` ✅ · `mypy` ✅ · `lint-imports` ✅
  - Commit: `test: add health endpoint integration test`

- [x] **C015** `chore: add .env.example and typed Settings`
  - Files: `backend/.env.example`, `app/infrastructure/config/settings.py`,
    `app/infrastructure/config/__init__.py`, `tests/unit/infra/test_settings.py`.
  - Verified: 13 tests pass · defaults correct · `SecretStr` masks API key · env overrides work · `ruff` ✅ · `mypy` ✅ · `lint-imports` ✅ (15 files, 8 deps)
  - Commit: `chore: add .env.example and typed Settings`

---

## Phase 1b — Frontend scaffolding (npm)

- [x] **C020** `build: scaffold Next.js app (TypeScript strict)`
  - Files: entire `frontend/` created by `create-next-app@latest` with `--ts --eslint --app --tailwind`.
  - `package.json` updated: name → `agent5g-frontend`, added `typecheck` and `gen:types` scripts.
  - `tsconfig.json`: `"strict": true` confirmed.
  - Verified: `npm run build` ✅ · `npm run typecheck` ✅ · `npm run lint` ✅
  - Commit: `build: scaffold Next.js app with TypeScript strict`

- [x] **C021** `chore: configure ESLint/Prettier and typecheck script`
  - Files: `eslint.config.mjs` (added `eslint-config-prettier` last), `.prettierrc` (100-char, double-quotes, trailing-commas, LF), `.prettierignore`, `package.json` (`format`, `format:check` scripts added).
  - Installed: `prettier`, `eslint-config-prettier` (dev deps).
  - Verified: `npm run lint` ✅ · `npm run typecheck` ✅ · `npm run format:check` ✅ · `npm run build` ✅
  - Commit: `chore: configure ESLint, Prettier, and typecheck script`

- [x] **C022** `chore: add frontend .env.local.example and design tokens`
  - Files: `.env.local.example` (`NEXT_PUBLIC_API_BASE`, `NEXT_PUBLIC_WS_URL`),
    `app/globals.css` (full dark-first token set from `04-ui.md §5` — surfaces, borders, typography,
    semantic status colours ok/warn/crit/ai, radius, motion durations, shadows, reduced-motion respect),
    `app/layout.tsx` (updated metadata + `bg-base text-primary` applied to body).
  - Tailwind v4 CSS-based config — no `tailwind.config.ts` needed; tokens mapped via `@theme inline`.
  - Verified: `npm run format:check` ✅ · `npm run lint` ✅ · `npm run typecheck` ✅ · `npm run build` ✅
  - Commit: `chore: add env example and dark-theme design tokens`

---

## Phase 1c — Windows run scripts

- [x] **C030** `chore: add Windows run/setup scripts`
  - Files: `scripts/setup.ps1` (prereq check + venv + pip + npm + env copy),
    `scripts/run-backend.ps1` (uvicorn 127.0.0.1 only, `-Prod`/`-Port` params),
    `scripts/run-frontend.ps1` (next dev/build+start, `-Prod`/`-Port` params),
    `scripts/seed.ps1` (idempotent DB seed, forwards to seed module when available),
    `scripts/reset.ps1` (guarded DB reset with `-Force` flag, updates .env seed/scenario),
    `scripts/backup.ps1` (timestamped DB copy to `data/backups/`),
    `scripts/demo-setup.ps1` (forces `ENV=demo LLM__MODE=replay`, resets to baseline, one-command pre-demo).
  - Verified: all 7 scripts present · backend boots via script path (127.0.0.1:8000, `{"status":"ok"}`) ✅
  - Commit: `chore: add Windows setup and run scripts`

> **Gate G1 (end of Phase 1):** both apps boot; lint/typecheck clean; `/health` ok. ✅ Backend side PASSED. Frontend pending C020-C030.

---

## Phase 2 — Backend domain (pure Pydantic, no frameworks)

Build the domain in tiny slices. Each is unit-tested. (Owning docs: `06`, `07`, `08`, `05`.)

- [x] **C040** `feat(domain): NF enums and value objects`
  - Files: `app/domain/twin/__init__.py`, `app/domain/twin/profile.py`
    (`NFType` 13 values · `NFStatus` 5 values · `Region` 4 values · `NFProfile` frozen Pydantic model),
    `tests/unit/twin/__init__.py`, `tests/unit/twin/test_profile.py` (19 tests).
  - Also fixed pre-existing settings test isolation bug (reads real `.env`; now uses `_env_file=None`).
  - Verified: 34 passed · `ruff` ✅ · `mypy` ✅ (10 files) · `lint-imports` ✅ (18 files, 11 deps)
  - Commit: `feat(domain): add NF enums, status, and NFProfile`

- [x] **C041** `feat(domain): KPI value objects`
  - Files: `app/domain/twin/kpi.py`
    (`KpiName` 10 values · `KpiSample` frozen immutable sample · `KpiSet` with EMA smoothing,
    physical clamping floor/ceil, hysteresis breach detection, factory helpers),
    `tests/unit/twin/test_kpi.py` (29 tests).
  - Verified: 63 total passed · `ruff` ✅ · `mypy` ✅ (11 files) · `lint-imports` ✅ (20 files)
  - Commit: `feat(domain): add KpiSet with threshold hysteresis`

- [x] **C042** `feat(domain): domain events`
  - Files: `app/domain/twin/events.py`
    (`EventType` 21 values · `DomainEvent` base with `to_envelope()` · 21 typed event classes),
    `tests/unit/twin/test_events.py` (37 tests).
  - Verified: 100 total passed · `ruff` ✅ · `mypy` ✅ (12 files) · `lint-imports` ✅ (22 files)
  - Commit: `feat(domain): add domain event types and envelope`

- [x] **C043** `feat(domain): NetworkFunction base + advance contract`
  - Files: `app/domain/twin/entities.py`
    (`RngStream` protocol · `AdvanceContext` frozen Pydantic · `NetworkFunction` abstract base
    with `advance()`, `handle()`, protected helpers `_set_status/_set_load/_set_kpi/_get_kpi`),
    `tests/unit/twin/test_entities_base.py` (38 tests incl. FakeRng, StubNF, event-emission cycle).
  - Verified: 138 total passed · `ruff` ✅ · `mypy` ✅ (13 files) · `lint-imports` ✅ (24 files)
  - Commit: `feat(domain): add NetworkFunction base and advance contract`

- [x] **C044** `feat(domain): NRF entity`
  - Files: `app/domain/twin/nf/__init__.py`, `app/domain/twin/nf/nrf.py`
    (register · deregister with PLC-1 invariant · discover with type/region/status filters ·
    list · advance KPI/stochastic-failure/auto-recovery · standby promotion),
    `tests/unit/twin/test_nrf.py` (34 tests).
  - Verified: 172 total passed · `ruff` ✅ · `mypy` ✅ (15 files) · `lint-imports` ✅ (26 files)
  - Commit: `feat(domain): add NRF entity with registration/discovery`

- [x] **C045** `feat(domain): AMF/SMF/UPF entities`
  - Files: `app/domain/twin/nf/amf.py` (ue register/deregister/context · advance KPI/failure/recovery),
    `app/domain/twin/nf/smf.py` (session create/modify/release/list · advance),
    `app/domain/twin/nf/upf.py` (session install/remove · loadbalance.apply · metrics.get ·
    M/M/1 latency model · 3 KPIs with thresholds),
    `tests/unit/twin/test_amf_smf_upf.py` (47 tests).
  - Verified: 219 total passed · `ruff` ✅ · `mypc0y` ✅ (18 files) · `lint-imports` ✅ (29 files)
  - Commit: `feat(domain): add AMF, SMF, UPF entities`

- [x] **C046** `feat(domain): NWDAF, DCF, Edge, and remaining NFs`
  - Files: `nf/nwdaf.py` (analytics subscriptions · AIMLE model deploy/retire/status · accuracy KPI improves with deployed models),
    `nf/dcf.py` (data collection subscribe/query/history · ADRF-like sample store · DataCollectedEvent),
    `nf/edge.py` (AIMLE model deploy · latency drops with each hosted model · M/M/1-lite KPIs),
    `nf/remaining.py` (PCF · UDM with 200 synthetic-only subscribers · NEF · AF · GNB with PRB/handover · UE with attach/mobility),
    `tests/unit/twin/test_remaining_nfs.py` (51 tests — NWDAF + Edge thorough, rest smoke).
  - Verified: 270 total passed · `ruff` ✅ · `mypy` ✅ (22 files) · `lint-imports` ✅ (33 files)
  - Commit: `feat(domain): add NWDAF, DCF, Edge, and remaining NFs`

- [ ] **C047** `feat(domain): topology and NetworkTwin aggregate`
  - Files: `app/domain/twin/topology.py`, `NetworkTwin` in `entities.py`
    (snapshot + advance iterating sorted ids), tests.
  - Verify: deterministic advance over a small twin.
  - Commit: `feat(domain): add topology and NetworkTwin aggregate`

- [ ] **C048** `feat(domain): service descriptor and policy models`
  - Files: `app/domain/services/models.py` (`ServiceDescriptor`, `ServiceKind`, `Pattern`, `ServiceResult`),
    `app/domain/services/policy.py` (`Policy`, `PolicyDecision`), tests.
  - Commit: `feat(domain): add ServiceDescriptor, ServiceResult, and Policy models`

- [ ] **C049** `feat(domain): agent structured I/O and memory models`
  - Files: `app/domain/agents/models.py` (Interpretation, Plan, Step, StepResult, Observation,
    Validation, OptimizationProposal, RecoveryPlan, WorkflowSummary, MemoryWrite, KnowledgeDelta),
    `app/domain/agents/memory.py`, tests.
  - Commit: `feat(domain): add agent structured I/O and memory models`

- [x] **C050** `feat(domain): port interfaces`
  - Files: `app/domain/twin/ports.py` (`TwinRepository`),
    `app/domain/services/ports.py` (`ServiceRegistry`, `PolicyStore`),
    `app/domain/agents/ports.py` (`MemoryStore`, `WorkflowRepository`, `LLMClient`, `Rng`, `EventBus`),
    `tests/unit/agents/test_ports.py` (15 tests — Protocol conformance + rejection + no-framework-leak).
  - Verified: 414 total passed · `ruff` ✅ · `mypy` ✅ (33 files) · `lint-imports` ✅ (45 files, 128 deps, 2 contracts kept)
  - **GATE G2 PASSED** ✅

> **Gate G2 summary:** Domain layer complete and clean.
> - `ruff check` → All checks passed
> - `mypy app` → Success: no issues in 33 source files
> - `pytest -q` → **414 passed**
> - `lint-imports` → 45 files, 128 dependencies · **Domain must not import any framework: KEPT** · **Application must not import delivery layer: KEPT**
> - Zero framework imports in `domain/`
  - Commit: `feat(domain): add port interfaces (repositories, bus, llm, rng)`

> **Gate G2:** domain unit tests pass; import-linter clean; zero framework imports in `domain/`.

---

## Phase 3 — Infrastructure adapters

- [ ] **C060** `feat(infra): seeded RNG service`
  - Files: `app/infrastructure/rng/rng.py`, `tests/unit/infra/test_rng.py`.
  - Verify: `for_tick(seed, tick)` reproducible; independent per tick.
  - Commit: `feat(infra): add seeded, tick-derived RNG service`

- [ ] **C061** `feat(infra): async SQLite engine + PRAGMAs`
  - Files: `app/infrastructure/db/engine.py`
    (async engine, WAL/foreign_keys/busy_timeout, session factory).
  - Verify: engine connects to a temp DB in a test.
  - Commit: `feat(infra): add async SQLite engine with PRAGMAs`

- [ ] **C062** `feat(infra): ORM models for core tables`
  - Files: `app/infrastructure/db/models.py`
    (`simulation`, `topology_nodes`, `topology_links`, `kpis`, `events`, `services`, `policies`).
  - Verify: `Database.init()` creates tables in a test DB.
  - Commit: `feat(infra): add ORM models for twin/services/events tables`

- [ ] **C063** `feat(infra): ORM models for workflow/agent/memory tables`
  - Files: extend `models.py`
    (`workflows`, `workflow_steps`, `workflow_trace`, `logs`, `memory`,
    `knowledge_nodes`, `knowledge_edges`, `models`, `service_calls`, `users`, `agents`).
  - Verify: all 18 tables create; FKs enforced.
  - Commit: `feat(infra): add ORM models for workflows, memory, and logs`

- [ ] **C064** `feat(infra): single-writer persistence queue`
  - Files: `app/infrastructure/writer/writer.py`, test.
  - Verify: submit/flush commits; drain-on-close loses nothing.
  - Commit: `feat(infra): add single-writer persistence queue`

- [ ] **C065** `feat(infra): in-process event bus (persist-first)`
  - Files: `app/infrastructure/bus/bus.py`, test.
  - Verify: publish persists then fans out; bounded subscriber queue.
  - Commit: `feat(infra): add in-process persist-first event bus`

- [ ] **C066** `feat(infra): LLMClient with replay mode`
  - Files: `app/infrastructure/llm/client.py`
    (Protocol + `ReplayClient` + `build_llm` returning replay by default),
    `tests/fixtures/llm/` seed, test.
  - Verify: replay serves a fixture by request hash; missing fixture raises (no network).
  - Commit: `feat(infra): add LLMClient port with offline replay mode`

- [ ] **C067** `feat(infra): FakeLLM and record client (deferred live)`
  - Files: add `FakeLLM` (canned outputs) for unit tests;
    `RecordingClient` stub (live wired later, free-tier).
  - Verify: FakeLLM returns structured output in a unit test.
  - Commit: `feat(infra): add FakeLLM and recording client scaffold`

- [ ] **C068** `feat(infra): repositories (twin, log)`
  - Files: `app/infrastructure/db/repos/twin_repo.py`, `log_repo.py`
    (implement domain ports; writes via single-writer).
  - Verify: append KPIs/events + read back in a test.
  - Commit: `feat(infra): add twin and log repositories`

- [ ] **C069** `feat(infra): remaining repositories`
  - Files: `workflow_repo.py`, `memory_store.py`, `policy_store.py`, registry glue.
  - Verify: unit tests per repo.
  - Commit: `feat(infra): add workflow, memory, and policy repositories`

- [ ] **C070** `feat(infra): sim scheduler`
  - Files: `app/infrastructure/sim/scheduler.py`
    (emits `SIM_TICK`, start/pause/step, gate), test with a manual clock.
  - Commit: `feat(infra): add simulation tick scheduler`

> **Gate G3:** infra unit tests pass; DB creates + seeds a temp DB; replay LLM works offline.

---

## Phase 4 — SEL + Twin service

- [ ] **C080** `feat(sel): service registry`
  - Files: `app/application/sel/registry.py`
    (register descriptors, persist to `services`, discover/list), test.
  - Commit: `feat(sel): add service registry with persistence`

- [ ] **C081** `feat(sel): policy engine with PLC-1..6`
  - Files: `app/application/sel/policy_engine.py` (pure predicates),
    `app/infrastructure/db/seed.py` (seed built-in policies), tests for each policy.
  - Verify: PLC-1 (never zero NRF) and PLC-2 (healthy target) unit-tested.
  - Commit: `feat(sel): add deterministic policy engine (PLC-1..6)`

- [ ] **C082** `feat(sel): invoker pipeline`
  - Files: `app/application/sel/invoker.py`
    (validate → policy → dispatch → emit → persist), test.
  - Verify: a blocked action yields `POLICY_BLOCKED` + a `service_calls` row, no state change.
  - Commit: `feat(sel): add service invoker pipeline`

- [ ] **C083** `feat(sel): tool adapter (services as JSON-schema tools)`
  - Files: `app/application/sel/tools.py`, test (schema derived from a Pydantic input).
  - Commit: `feat(sel): expose services as JSON-schema agent tools`

- [ ] **C084** `feat(twin): twin service on_tick/snapshot/apply_command`
  - Files: `app/application/twin_service/service.py`, test with manual clock.
  - Verify: tick advances state, persists KPIs (write-behind) + events (write-through).
  - Commit: `feat(twin): add twin service (tick, snapshot, apply_command)`

- [ ] **C085** `feat(twin): scenarios and fault injection`
  - Files: `app/application/twin_service/scenarios.py`, `faults.py`,
    `data/scenarios/baseline_healthy.json`.
  - Commit: `feat(twin): add scenario loading and fault injection`

- [ ] **C086** `feat(sel): Scenario-A services`
  - Files: `app/application/sel/services/{nrf,aimle,nwdaf,twin_read}.py`
    (descriptors + input/output models + handlers wired to twin).
  - Services: `nrf.discover`, `aimle.model.deploy`, `nwdaf.analytics.congestion.subscribe`,
    `twin.snapshot`.
  - Verify: each callable through the invoker; deploy declares a compensation.
  - Commit: `feat(sel): add Scenario A service set`

- [ ] **C087** `test(determinism): golden-trajectory test`
  - Files: `tests/determinism/test_golden_trajectory.py`, `baselines/`.
  - Verify: 50 ticks at seed 42 → stable hash.
  - Commit: `test(determinism): add golden-trajectory determinism test`

> **Gate G4:** golden-trajectory passes; one action flows through the invoker with events + persistence.

---

## Phase 5 — Prompts, Agents, Workflow engine

- [ ] **C090** `feat(prompts): shared preamble + partials + registry`
  - Files: `app/application/agents/prompts/_preamble.md.j2`,
    `_tool_protocol.md.j2`, `_output_contract.md.j2`, `_guardrails.md.j2`,
    `registry.py`, deterministic `render()`.
  - Commit: `feat(prompts): add shared prompt partials and registry`

- [ ] **C091** `feat(agents): BaseAgent + AgentContext`
  - Files: `app/application/agents/base.py`, test with FakeLLM.
  - Commit: `feat(agents): add BaseAgent and AgentContext`

- [ ] **C092** `feat(agents): Observer and Planner (read-only)`
  - Files: `observer.py`, `planner.py`, prompts `observer.md.j2`/`planner.md.j2`,
    tests with FakeLLM/replay.
  - Commit: `feat(agents): add Observer and Planner agents`

- [ ] **C093** `feat(agents): Executor`
  - Files: `executor.py`, prompt, test (calls a service via invoker, records compensation).
  - Commit: `feat(agents): add Executor agent`

- [ ] **C094** `feat(agents): Documentation and Memory`
  - Files: `documentation.py`, `memory_agent.py`, prompts, tests.
  - Commit: `feat(agents): add Documentation and Memory agents`

- [ ] **C095** `feat(workflow): WorkflowState + node functions`
  - Files: `app/application/workflow/state.py`,
    `nodes.py` (observe/reason/plan/execute/validate/complete first).
  - Commit: `feat(workflow): add WorkflowState and core node functions`

- [ ] **C096** `feat(workflow): routing guards + LangGraph engine`
  - Files: `routing.py`, `engine.py` (build_graph + WorkflowEngine.start).
  - Add `langgraph` to deps in `pyproject.toml`.
  - Commit: `feat(workflow): add routing guards and LangGraph engine`

- [ ] **C097** `feat(workflow): checkpointer + orchestrator binding`
  - Files: `checkpoint.py`, `app/application/agents/orchestrator.py`.
  - Commit: `feat(workflow): add checkpointer and agent orchestrator`

- [ ] **C098** `test(integration): Scenario A completes under replay`
  - Files: `tests/integration/test_scenario_a.py`,
    `tests/fixtures/llm/planner@v1/...` (record once via free-tier or hand-author).
  - Verify: 8 stages, steps+compensations, trace, deployed model, `WORKFLOW_COMPLETED`.
  - Commit: `test(integration): Scenario A completes end-to-end under replay`

> **Gate G5 (Day 1 target):** Scenario A green end-to-end under replay LLM. This is the milestone.

---

## Phase 6 — API + WebSocket + DI

- [ ] **C100** `feat(api): common schemas + error envelope + middleware`
  - Files: `app/api/schemas/common.py`, `app/api/errors.py`, `app/api/middleware.py`
    (correlation id, CORS localhost).
  - Commit: `feat(api): add common schemas, error envelope, middleware`

- [ ] **C101** `feat(api): DI container + composition root`
  - Files: `app/infrastructure/container.py`, `app/api/deps.py`,
    wire into `main.py` lifespan (start writer/bus/scheduler; init+seed DB).
  - Verify: `/health` still ok with real container; background tasks start/stop cleanly.
  - Commit: `feat(api): add DI container and lifespan wiring`

- [ ] **C102** `feat(api): services, twin, topology, simulation routers`
  - Files: `app/api/routers/{services,twin,topology,simulation}.py`.
  - Verify: `GET /services`, `GET /twin`, `POST /simulation/start` work.
  - Commit: `feat(api): add services, twin, topology, simulation routers`

- [ ] **C103** `feat(api): workflows router (async create + trace + control)`
  - Files: `app/api/routers/workflows.py`.
  - Verify: `POST /workflows` returns 201 immediately; `/trace` returns trace.
  - Commit: `feat(api): add workflows router with async create and trace`

- [ ] **C104** `feat(api): WebSocket hub`
  - Files: `app/api/ws/hub.py`, `envelope.py`, mount `/ws`.
  - Verify: connect, receive HELLO + streamed events.
  - Commit: `feat(api): add WebSocket hub and event streaming`

- [ ] **C105** `feat(api): remaining routers`
  - Files: `app/api/routers/{analytics,models,memory,knowledge,logs,policies,settings}.py`.
  - Commit: `feat(api): add analytics, models, memory, logs, policies routers`

- [ ] **C106** `build(frontend): generate API types from OpenAPI`
  - Files: `frontend/lib/api/types.gen.ts`
    (via `npx openapi-typescript http://localhost:8000/openapi.json -o lib/api/types.gen.ts`),
    `package.json` `gen:types` script.
  - Verify: `npm run typecheck` clean.
  - Commit: `build(frontend): generate API types from OpenAPI`

> **Gate G6:** `/openapi.json` valid; `POST /workflows` async + WS progress; type-gen clean.

---

## Phase 7 — Frontend (Day 2 AM)

- [ ] **C110** `feat(fe): app shell — nav rail + top bar + intent input`
  - Files: `frontend/app/layout.tsx`, `components/shell/*`, providers (React Query, theme).
  - Commit: `feat(fe): add app shell with nav and intent bar`

- [ ] **C111** `feat(fe): API client + React Query + WS store`
  - Files: `lib/api/client.ts`, `lib/api/endpoints.ts`, `lib/query/*`,
    `lib/ws/{store,use-ws,envelope}.ts`.
  - Verify: WS connects; store updates on events.
  - Commit: `feat(fe): add typed API client, React Query, and WS store`

- [ ] **C112** `feat(fe): shared components with loading/empty/error`
  - Files: `components/{stat-card,panel,data-table,status-badge,time-series-chart,
    event-feed,timeline-stepper,reasoning-trace,json-viewer,states/*}.tsx`.
  - Commit: `feat(fe): add shared component library`

- [ ] **C113** `feat(fe): Dashboard page`
  - Files: `app/dashboard/page.tsx`, `features/dashboard/*`.
  - Commit: `feat(fe): add Dashboard page`

- [ ] **C114** `feat(fe): Agent Console page (live)`
  - Files: `app/agent-console/page.tsx`, `features/agents/*`
    (WorkflowList + WorkflowDetail: TimelineStepper + ReasoningTrace).
  - Verify: submit intent → console shows stages advancing live.
  - Commit: `feat(fe): add live Agent Console`

- [ ] **C115** `feat(fe): Topology page (React Flow)`
  - Files: `app/topology/page.tsx`, `features/topology/*`,
    custom NF nodes colored by live status.
  - Commit: `feat(fe): add Topology page with live node status`

- [ ] **C116** `feat(fe): Digital Twin + Simulation pages`
  - Files: `app/digital-twin/page.tsx`, `app/simulation/page.tsx`, features.
  - Verify: load scenario + start/step; fault injection.
  - Commit: `feat(fe): add Digital Twin and Simulation pages`

- [ ] **C117** `feat(fe): remaining pages`
  - Files: service-registry, logs, analytics, models, memory, knowledge-graph,
    settings, workflow-builder (split across 2–3 commits if large).
  - Commit: `feat(fe): add remaining feature pages`

> **Gate G7:** all routes render; intent → live Agent Console; one fault updates Dashboard+Topology+Logs via one WS.

---

## Phase 8 — Autonomy & Recovery (Day 2 PM)

- [ ] **C120** `feat(agents): Optimizer agent`
  - Files: `optimizer.py`, prompt, test.
  - Commit: `feat(agents): add Optimizer agent`

- [ ] **C121** `feat(sel): mitigation services`
  - Files: `app/application/sel/services/{upf,pcf,dcf}.py`
    (`upf.loadbalance.apply`, `pcf.policy.apply`, `dcf.data.history`).
  - Commit: `feat(sel): add user-plane and policy mitigation services`

- [ ] **C122** `feat(workflow): autonomous triggering`
  - Files: `app/application/workflow/triggers.py`
    (Observer bus subscription + de-dup registry).
  - Commit: `feat(workflow): add Observer-driven autonomous triggering`

- [ ] **C123** `feat(scenario): mumbai_congestion + Scenario B integration test`
  - Files: `data/scenarios/mumbai_congestion.json`,
    `tests/integration/test_scenario_b.py`.
  - Verify: breach → autonomous workflow → recovery.
  - Commit: `feat(scenario): add Scenario B (autonomous mitigation)`

- [ ] **C124** `feat(agents): Recovery agent + rollback`
  - Files: `recovery.py`, prompt, `nodes.py` rollback wiring, test.
  - Commit: `feat(agents): add Recovery agent and rollback`

- [ ] **C125** `feat(scenario): nrf_failure + Scenario C integration test`
  - Files: `data/scenarios/nrf_failure.json`,
    `tests/integration/test_scenario_c.py`.
  - Verify: NRF fail → recovery via standby (PLC-1 respected).
  - Commit: `feat(scenario): add Scenario C (failure and recovery)`

> **Gate G8:** Scenarios A/B/C all pass at integration.

---

## Phase 9 — Tests, safety, demo, CI

- [ ] **C130** `test(safety): SEL-only, policy blocks, secret-scan, no-PII`
  - Files: `tests/safety/*.py`.
  - Commit: `test(safety): add golden-rule invariant tests`

- [ ] **C131** `test(determinism): golden-workflow test`
  - Files: `tests/determinism/test_golden_workflow.py`.
  - Commit: `test(determinism): add golden-workflow traversal test`

- [ ] **C132** `test(fe): WS store reducer + component states`
  - Files: `frontend/**/*.test.tsx` (Vitest).
  - Commit: `test(fe): add WS store and component tests`

- [ ] **C133** `test(e2e): Playwright Scenarios A/B/C (replay)`
  - Files: `frontend/e2e/scenario-{a,b,c}.spec.ts`.
  - Commit: `test(e2e): add Playwright scenario tests`

- [ ] **C134** `chore: CI gate script`
  - Files: `scripts/ci.ps1`
    (ruff, mypy, import-linter, pytest, tsc, vitest, e2e, coverage).
  - Verify: `scripts\ci.ps1` green offline.
  - Commit: `chore: add offline CI gate script`

- [ ] **C135** `chore: demo setup + reset scripts`
  - Files: `scripts/{seed,reset,backup,prune,demo-setup}.ps1`.
  - Commit: `chore: add demo/ops scripts`

> **Gate G9 (Day 2 target):** full suite green offline (replay); demo runs deterministically at $0.

---

## Progress tracker

| Phase | Commits | Status |
|-------|---------|--------|
| Phase 0: Git bootstrap | C001–C002 | ✅ Done |
| Phase 1: Backend scaffold | C010–C030 | ✅ All done — Gate G1 PASSED |
| Phase 2: Domain models | C040–C050 | ✅ All done — **Gate G2 PASSED** |
| Phase 3: Infrastructure | C060–C070 | ✅ All done — **Gate G3 PASSED** |
| Phase 4: SEL + Twin | C080–C087 | ✅ All done — **Gate G4 PASSED** |
| Phase 5: Agents + Engine | C090–C098 | ✅ All done — **Gate G5 PASSED** |
| Phase 6: API + WS | C100–C106 | ✅ All done — **Gate G6 PASSED** |
| Phase 7: Frontend | C110–C117 | ✅ All done — **Gate G7 PASSED** |
| Phase 8: Autonomy + Recovery | C120–C125 | ⬜ Pending (Gate G8) |
| Phase 9: Tests + Demo + CI | C130–C135 | ⬜ Pending (**Day 2 milestone** — Gate G9) |

**Golden rules while committing:** never commit on a red state · keep each commit to a few files · run the relevant verify before committing · LLM stays in `replay` (offline, $0) · never commit `.env`, `data/*.db`, or `planning/`.
