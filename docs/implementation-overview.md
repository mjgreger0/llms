# LLM Serve - Implementation Plan Overview

## Document Information
- **Related PRD**: [llms-prd.md](./llms-prd.md)
- **Related Architecture**: [architecture-overview.md](./architecture-overview.md), [architecture-dashboard.md](./architecture-dashboard.md), [architecture-daemon.md](./architecture-daemon.md), [architecture-containers.md](./architecture-containers.md)
- **Created**: 2025-12-23
- **Status**: Draft
- **Version**: 1.0

---

## Executive Summary

This implementation plan breaks the LLM Serve project into 8 sequential phases, building incrementally from development environment through full integration. Each phase produces working, testable artifacts using production-ready containers from day one.

The approach prioritizes:
- **Incremental delivery**: Each phase produces verifiable results
- **Production parity**: Same containers for development and production
- **Simplicity first**: Manual testing initially, automated tests added for critical paths later
- **Component isolation**: Build and test components independently before integration

---

## Phase Summary

| Phase | Name | Goal | Dependencies | Status |
|-------|------|------|--------------|--------|
| 1 | Dev Environment Setup | Production-ready Containerfiles, project structure | None | Not Started |
| 2 | Daemon Core | Stats collection, Podman integration, configuration | Phase 1 | Not Started |
| 3 | Dashboard Backend | FastAPI app, TimescaleDB schema, Control API skeleton | Phase 1 | Not Started |
| 4 | WebSocket Communication | Dashboard↔Daemon JSON-RPC 2.0 protocol | Phases 2, 3 | Not Started |
| 5 | Request Router | Queue management, routing logic, LLM forwarding | Phase 4 | Not Started |
| 6 | Dashboard Frontend | SvelteKit UI (Cluster Overview, Machine Detail, Chat) | Phase 3 | Not Started |
| 7 | Container Library | vLLM configs, command generation, launch configs | Phase 5 | Not Started |
| 8 | Integration & E2E | Full request flow, eviction, multi-GPU, production validation | All | Not Started |

---

## Phase Details

### Phase 1: Dev Environment Setup
**Goal**: Establish project structure and production-ready container configurations

**Success Criteria**:
- [ ] Project directory structure matches architecture docs
- [ ] Dashboard Containerfile builds successfully with Python + Node.js + TimescaleDB
- [ ] Daemon Containerfile builds successfully with Python + pynvml
- [ ] Both containers can start and run basic health checks
- [ ] pyproject.toml and package.json configured with dependencies

**Scope**:
- **Included**: Containerfiles, directory structure, dependency manifests, basic entrypoints
- **Excluded**: Application logic, database schema, frontend build

**Dependencies**: None

**Key Risks**:
- TimescaleDB integration in single container may require custom setup
- nvidia-container-toolkit configuration varies by host

**Detailed Plan**: [implementation-phase-1-dev-setup.md](./implementation-phase-1-dev-setup.md)

---

### Phase 2: Daemon Core
**Goal**: Implement stats collection and container management on GPU machines

**Success Criteria**:
- [ ] Daemon collects CPU, memory, network stats from host
- [ ] Daemon collects GPU stats via pynvml (VRAM, utilization, temperature)
- [ ] Daemon can start/stop Podman containers via podman-py
- [ ] Stats output matches schema from architecture docs
- [ ] Configuration via environment variables works

**Scope**:
- **Included**: StatsCollector, ContainerManager, HealthMonitor, data models, config
- **Excluded**: WebSocket client (Phase 4), Dashboard communication

**Dependencies**: Phase 1 (Containerfile)

**Key Risks**:
- pynvml requires NVIDIA drivers accessible from container
- Podman socket access permissions

**Detailed Plan**: [implementation-phase-2-daemon-core.md](./implementation-phase-2-daemon-core.md)

---

### Phase 3: Dashboard Backend
**Goal**: Create FastAPI application with database schema and Control API

**Success Criteria**:
- [ ] FastAPI app starts with uvicorn
- [ ] TimescaleDB initialized with schema from architecture docs
- [ ] Control API endpoints return placeholder data
- [ ] Database migrations work (Alembic)
- [ ] Structured logging configured

**Scope**:
- **Included**: FastAPI app structure, database models, Control API endpoints, config, logging
- **Excluded**: WebSocket handlers, Router logic, Frontend

**Dependencies**: Phase 1 (Containerfile)

**Key Risks**:
- TimescaleDB hypertable setup within container
- asyncpg connection pool configuration

**Detailed Plan**: [implementation-phase-3-dashboard-backend.md](./implementation-phase-3-dashboard-backend.md)

---

### Phase 4: WebSocket Communication
**Goal**: Establish bidirectional communication between Dashboard and Daemons

**Success Criteria**:
- [ ] Daemon connects to Dashboard WebSocket endpoint
- [ ] Dashboard accepts and registers daemon connections
- [ ] Stats reports flow from Daemon to Dashboard (JSON-RPC 2.0)
- [ ] Commands flow from Dashboard to Daemon
- [ ] Reconnection with exponential backoff works
- [ ] Dashboard stores stats in TimescaleDB

**Scope**:
- **Included**: WebSocket handlers, JSON-RPC protocol, DaemonManager, connection lifecycle
- **Excluded**: Actual container.start/stop execution (uses stubs)

**Dependencies**: Phases 2, 3

**Key Risks**:
- WebSocket connection stability under load
- Message ordering and request/response correlation

**Detailed Plan**: [implementation-phase-4-websocket.md](./implementation-phase-4-websocket.md)

---

### Phase 5: Request Router
**Goal**: Implement OpenAI-compatible API with queue management and model routing

**Success Criteria**:
- [ ] `/v1/chat/completions` endpoint accepts OpenAI-format requests
- [ ] Per-model FIFO queues created and managed
- [ ] Requests route to running LLM containers
- [ ] Streaming responses (SSE) work
- [ ] Keepalive sent while model loading
- [ ] Basic capacity checking (is model running?)

**Scope**:
- **Included**: Router endpoints, QueueManager, ModelRouter, request forwarding, SSE streaming
- **Excluded**: Eviction logic, multi-machine coordination

**Dependencies**: Phase 4 (Dashboard-Daemon communication)

**Key Risks**:
- Async queue management complexity
- SSE streaming through proxy

**Detailed Plan**: [implementation-phase-5-router.md](./implementation-phase-5-router.md)

---

### Phase 6: Dashboard Frontend
**Goal**: Build SvelteKit UI for cluster monitoring and testing

**Success Criteria**:
- [ ] Cluster Overview page shows machines, GPUs, running models
- [ ] Machine Detail page shows per-machine stats and GPU details
- [ ] Chat interface can send requests and display streaming responses
- [ ] Logs page shows system logs
- [ ] Real-time updates via WebSocket
- [ ] Static build served by FastAPI

**Scope**:
- **Included**: SvelteKit pages, components, API client, WebSocket updates
- **Excluded**: Model Inventory, Container Config, Credentials pages (Phase 2 features per PRD)

**Dependencies**: Phase 3 (Control API endpoints)

**Key Risks**:
- Real-time updates synchronization
- Static build integration with FastAPI

**Detailed Plan**: [implementation-phase-6-frontend.md](./implementation-phase-6-frontend.md)

---

### Phase 7: Container Library
**Goal**: Implement container configuration and command generation for vLLM

**Success Criteria**:
- [ ] Database tables for model configs, quantizations, launch configs
- [ ] vLLM container command generation works
- [ ] GPU memory requirements tracked
- [ ] Container launch with correct arguments
- [ ] Health check polling until ready
- [ ] Container labels for tracking

**Scope**:
- **Included**: Database schema, ContainerCommandGenerator, vLLM configs, launch flow
- **Excluded**: SGLang, llama.cpp (later), HuggingFace download (Phase 2 per PRD)

**Dependencies**: Phase 5 (Router needs to trigger container starts)

**Key Risks**:
- vLLM argument compatibility across versions
- GPU device mapping with nvidia-container-toolkit

**Detailed Plan**: [implementation-phase-7-container-library.md](./implementation-phase-7-container-library.md)

---

### Phase 8: Integration & End-to-End
**Goal**: Full request flow working with eviction, multi-GPU, production validation

**Success Criteria**:
- [ ] Request → model loads → response streams back (full flow)
- [ ] LRU eviction when GPUs needed
- [ ] Multi-GPU models start correctly
- [ ] Dashboard restart recovers state from daemons
- [ ] Daemon reconnection works
- [ ] Real cluster deployment validated

**Scope**:
- **Included**: Eviction logic, multi-GPU coordination, state recovery, production testing
- **Excluded**: Multi-machine (405B models), training support

**Dependencies**: All previous phases

**Key Risks**:
- Eviction timing and race conditions
- State recovery completeness

**Detailed Plan**: [implementation-phase-8-integration.md](./implementation-phase-8-integration.md)

---

## Implementation Guidelines

### Development Practices
- **Testing**: Manual testing initially; add automated tests for critical paths as needed
- **Containers**: Use production Containerfiles throughout (no separate dev containers)
- **Logging**: Structured JSON logging from day one
- **Configuration**: Environment variables for all settings

### Code Organization
```
llms/
├── docs/                    # Documentation (PRD, architecture, implementation)
├── dashboard/
│   ├── Containerfile        # Production container
│   ├── pyproject.toml
│   ├── backend/             # FastAPI application
│   └── frontend/            # SvelteKit application
├── daemon/
│   ├── Containerfile        # Production container
│   ├── pyproject.toml
│   └── src/                 # Daemon application
└── containers/              # LLM container configs (reference only)
```

### Database
- TimescaleDB runs embedded in Dashboard container
- Schema managed via Alembic migrations
- Data persisted via volume mount to host

---

## Definition of Done

A phase is complete when:
1. All success criteria checkboxes are satisfied
2. Code is committed to repository
3. Containers build and run successfully
4. Manual testing confirms functionality
5. Any blockers or open questions are documented

---

## Detailed Phase Documents

| Phase | Document | Tasks | Status |
|-------|----------|-------|--------|
| 1 | [implementation-phase-1-dev-setup.md](./implementation-phase-1-dev-setup.md) | 31 | Ready |
| 2 | [implementation-phase-2-daemon-core.md](./implementation-phase-2-daemon-core.md) | 47 | Ready |
| 3 | [implementation-phase-3-dashboard-backend.md](./implementation-phase-3-dashboard-backend.md) | 30 | Ready |
| 4 | [implementation-phase-4-websocket.md](./implementation-phase-4-websocket.md) | 33 | Ready |
| 5 | [implementation-phase-5-router.md](./implementation-phase-5-router.md) | 30 | Ready |
| 6 | [implementation-phase-6-frontend.md](./implementation-phase-6-frontend.md) | 31 | Ready |
| 7 | [implementation-phase-7-container-library.md](./implementation-phase-7-container-library.md) | 31 | Ready |
| 8 | [implementation-phase-8-integration.md](./implementation-phase-8-integration.md) | 28 | Ready |

---

## Implementation Statistics

| Metric | Value |
|--------|-------|
| Total Phases | 8 |
| Total Tasks | 261 |
| Total Documents | 9 |
| PRD Phase Coverage | Phase 1 (Core Infrastructure) |
