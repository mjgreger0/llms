# LLM Serve - Architecture Overview

## Document Information
- **Related PRD**: [llms-prd.md](./llms-prd.md)
- **Created**: 2025-12-23
- **Status**: Draft
- **Version**: 1.0

---

## System Context

LLM Serve provides a unified inference layer for applications consuming LLM APIs. Applications send OpenAI-compatible requests to the Dashboard's router endpoint, which handles model placement, loading, and request forwarding transparently.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Applications                                    │
│                         (OpenAI-compatible clients)                          │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │ HTTPS (OpenAI API format)
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           LLM Serve System                                   │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                      Dashboard / Control                               │  │
│  │                        (Single Instance)                               │  │
│  └───────────────────────────────┬───────────────────────────────────────┘  │
│                                  │                                           │
│            ┌─────────────────────┼─────────────────────┐                    │
│            ▼                     ▼                     ▼                    │
│  ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐           │
│  │   GPU Machine   │   │   GPU Machine   │   │   GPU Machine   │    ...    │
│  │   + Daemon      │   │   + Daemon      │   │   + Daemon      │           │
│  └─────────────────┘   └─────────────────┘   └─────────────────┘           │
└─────────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
                    ┌───────────────────────┐
                    │     NFS Storage       │
                    │  (HuggingFace layout) │
                    └───────────────────────┘
```

---

## Component Architecture

### Component Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           Dashboard Container                                 │
│                                                                               │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────────────────────┐  │
│  │   Svelte UI    │  │    Router      │  │       Control API              │  │
│  │  (static via   │  │  (async FIFO   │  │       (FastAPI)                │  │
│  │   FastAPI)     │  │   queues)      │  │                                │  │
│  └───────┬────────┘  └───────┬────────┘  └───────────────┬────────────────┘  │
│          │                   │                           │                    │
│          └───────────────────┴───────────────────────────┘                    │
│                              │                                                │
│                    ┌─────────┴─────────┐                                      │
│                    │   TimescaleDB     │                                      │
│                    │ (metrics, config) │                                      │
│                    └───────────────────┘                                      │
└──────────────────────────────┬───────────────────────────────────────────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │ WebSocket          │ WebSocket          │ WebSocket
          │ (JSON-RPC 2.0)     │                    │
          ▼                    ▼                    ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  Daemon Container │  │  Daemon Container │  │  Daemon Container │
│                   │  │                   │  │                   │
│  ┌─────────────┐  │  │  ┌─────────────┐  │  │  ┌─────────────┐  │
│  │  FastAPI    │  │  │  │  FastAPI    │  │  │  │  FastAPI    │  │
│  │  + pynvml   │  │  │  │  + pynvml   │  │  │  │  + pynvml   │  │
│  │  + podman-py│  │  │  │  + podman-py│  │  │  │  + podman-py│  │
│  └──────┬──────┘  │  │  └──────┬──────┘  │  │  └──────┬──────┘  │
│         │         │  │         │         │  │         │         │
│         ▼         │  │         ▼         │  │         ▼         │
│  ┌─────────────┐  │  │  ┌─────────────┐  │  │  ┌─────────────┐  │
│  │ LLM Container│  │  │ │ LLM Container│  │  │ │ LLM Container│  │
│  │ (vLLM/etc)  │  │  │ │ (vLLM/etc)  │  │  │ │ (vLLM/etc)  │  │
│  └─────────────┘  │  │  └─────────────┘  │  │  └─────────────┘  │
│                   │  │                   │  │                   │
│  Machine A        │  │  Machine B        │  │  Machine C        │
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

### Component Summary

| Component | Purpose | Technology | Deployment |
|-----------|---------|------------|------------|
| Dashboard | Web UI, request routing, cluster management | FastAPI + SvelteKit + TimescaleDB | Single Podman container |
| Daemon | Stats collection, container lifecycle | FastAPI + pynvml + podman-py | Podman container per GPU machine |
| LLM Container | Model inference | vLLM / SGLang / llama.cpp | Managed by Daemon, one or more per machine |
| NFS Storage | Model files | HuggingFace directory layout | Shared mount across all machines |

---

## Inter-Component Communication

### Dashboard ↔ Daemon (WebSocket + JSON-RPC 2.0)

Daemons initiate persistent WebSocket connections to Dashboard. All communication uses JSON-RPC 2.0 format.

**Connection Flow:**
1. Daemon starts, connects to `ws://<dashboard>:8080/ws/daemon`
2. Dashboard accepts, registers machine
3. Daemon sends stats every 6 seconds
4. Dashboard sends commands (start/stop containers)
5. On disconnect, Dashboard marks machine offline
6. Daemon reconnects with exponential backoff + jitter (1s → 60s cap)

**Message Types:**

| Direction | Method | Purpose |
|-----------|--------|---------|
| Daemon → Dashboard | `stats.report` | CPU/GPU/memory metrics, container status |
| Dashboard → Daemon | `container.start` | Start LLM container with config |
| Dashboard → Daemon | `container.stop` | Stop/evict LLM container |
| Daemon → Dashboard | `container.status` | Container lifecycle events (starting, ready, failed) |

**Example Messages:**

```json
// Daemon → Dashboard: Stats report (notification, no response expected)
{
  "jsonrpc": "2.0",
  "method": "stats.report",
  "params": {
    "machine_id": "gpu-server-b",
    "timestamp": "2025-01-15T10:30:00Z",
    "cpu": {"cores": 32, "load_percent": 15.2},
    "memory": {"total_gb": 256, "used_gb": 45},
    "gpus": [
      {"index": 0, "uuid": "GPU-abc123", "memory_used_gb": 22, "utilization": 85}
    ],
    "containers": [
      {"id": "vllm-qwen72b", "model": "qwen2.5-72b-instruct-awq", "status": "running"}
    ]
  }
}

// Dashboard → Daemon: Start container (request, expects response)
{
  "jsonrpc": "2.0",
  "method": "container.start",
  "params": {
    "model": "qwen2.5-72b-instruct-awq",
    "runtime": "vllm",
    "gpus": [0, 1],
    "config": {
      "context_length": 32768,
      "max_parallel_requests": 8
    }
  },
  "id": 42
}

// Daemon → Dashboard: Response
{
  "jsonrpc": "2.0",
  "result": {"container_id": "vllm-qwen72b-xyz789", "status": "starting"},
  "id": 42
}
```

### Dashboard → LLM Container (HTTP/SSE)

Dashboard routes inference requests directly to LLM containers (Daemon not in request path).

**Flow:**
1. Dashboard knows container endpoint from Daemon status reports
2. Request arrives at Dashboard router
3. Dashboard forwards to `http://<machine>:<port>/v1/chat/completions`
4. Response streams back via SSE
5. Dashboard streams to original client

**Health Checks:**
- Dashboard polls container `/health` endpoint at 1s intervals during startup
- Container considered ready when health returns 200

---

## Request Routing Architecture

### Queue Model

```
                         Incoming Requests
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Parse model+quant │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
     ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
     │ Queue:      │  │ Queue:      │  │ Queue:      │
     │ qwen-72b-awq│  │ llama-70b-q4│  │ mistral-7b  │
     │ (FIFO)      │  │ (FIFO)      │  │ (FIFO)      │
     └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
            │                │                │
            └────────────────┴────────────────┘
                             │
                    ┌────────┴────────┐
                    │  Async Workers  │
                    │  (per model)    │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  LLM Containers │
                    └─────────────────┘
```

### Queue Rules

1. **One queue per model+quant combination** - Created on first request, destroyed when model unloaded
2. **FIFO ordering** - Requests processed in arrival order within each queue
3. **Concurrent model access** - Multiple requests can be in-flight to same model
4. **Cross-queue independence** - Requests to different models don't block each other

### Eviction Rules

1. **Only evict models with empty queues** - Never evict a model with pending requests
2. **LRU among idle models** - Choose least-recently-used from models with empty queues
3. **Request protection** - Model that just loaded must process at least the triggering request
4. **Queue blocking on eviction** - Once eviction starts, queue blocks until model reloaded

### Request Lifecycle

```
Request arrives for model X (not loaded)
    │
    ├─► Add to Queue X (or create if doesn't exist)
    │
    ├─► Check GPU capacity
    │       │
    │       ├─► Capacity available: Start loading model X
    │       │
    │       └─► Need capacity: Evict LRU model(s) with empty queues
    │               │
    │               └─► Mark machines as "busy" during eviction+loading
    │
    ├─► Send keepalive to client while loading
    │
    ├─► Model X ready: Process queued requests in FIFO order
    │
    └─► Response streams back to client
```

### Multi-Machine Model Loading

For models requiring multiple machines (e.g., 405B across 8 GPUs on 2 machines):

1. Dashboard identifies required GPUs across machines
2. Both machines marked "busy" immediately
3. Eviction proceeds on each machine independently
4. When all machines ready, coordinated container start:
   - Machine A: Master node (ranks 0-3)
   - Machine B: Worker node (ranks 4-7)
5. Master coordinates distributed inference
6. All requests route to master node

---

## Data Flow

### Stats Collection (6-second intervals)

```
GPU Machine                    Dashboard
    │                              │
    │  [pynvml] Read GPU stats     │
    │  [psutil] Read CPU/memory    │
    │  [podman-py] List containers │
    │                              │
    │────── stats.report ─────────►│
    │                              │  Store in TimescaleDB
    │                              │  Update in-memory state
    │                              │
```

### Inference Request

```
Client          Dashboard           LLM Container
   │                │                     │
   │── POST /v1/chat/completions ───────►│
   │                │                     │
   │                │─── Check queue ────►│
   │                │                     │
   │◄── keepalive ──│   (if loading)      │
   │                │                     │
   │                │─── Forward ────────►│
   │                │                     │
   │◄────────────── SSE tokens ──────────│
   │                │                     │
```

---

## Deployment Topology

### Network Layout

```
┌─────────────────────────────────────────────────────────────────┐
│                     Local Network (192.168.0.0/24)              │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ Dashboard   │  │ GPU Server A│  │ GPU Server B│    ...       │
│  │ 192.168.0.10│  │ 192.168.0.20│  │ 192.168.0.21│              │
│  │ :8080       │  │             │  │             │              │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │
│         │                │                │                      │
│         └────────────────┴────────────────┘                      │
│                          │                                       │
│                          ▼                                       │
│                   ┌─────────────┐                                │
│                   │ NFS Server  │                                │
│                   │ 192.168.0.5 │                                │
│                   └─────────────┘                                │
└─────────────────────────────────────────────────────────────────┘
```

### Port Assignments

| Service | Port | Protocol | Purpose |
|---------|------|----------|---------|
| Dashboard Web UI | 8080 | HTTP | Web interface + API |
| Dashboard WebSocket | 8080 | WS | Daemon connections (same port, `/ws/daemon` path) |
| LLM Container | 8000+ | HTTP | Model inference (dynamic, reported by Daemon) |
| TimescaleDB | 5432 | TCP | Internal to Dashboard container |

### Container Mounts

**Dashboard Container:**
```
/data/config     → Configuration, container definitions (persistent)
/data/db         → TimescaleDB data (persistent)
/data/logs       → Application logs (persistent)
```

**Daemon Container:**
```
/host/proc       → Host /proc (read-only, for system stats)
/host/sys        → Host /sys (read-only, for device info)
/run/podman      → Podman socket (for container management)
```

**LLM Container:**
```
/models          → NFS: /data/projects/ai/models (read-only)
```

---

## Failure Modes & Recovery

| Failure | Detection | Impact | Recovery |
|---------|-----------|--------|----------|
| Dashboard crash | N/A | New requests fail, running models continue | Restart, reconnect daemons, rebuild state from daemons |
| Daemon crash | WebSocket disconnect | Machine marked offline, its models unavailable | Daemon auto-restarts, reconnects, reports current state |
| LLM container crash | Daemon health check | Requests to that model fail | Daemon auto-restarts container, requests queue until ready |
| Network partition | WebSocket timeout | Affected machines marked offline | Automatic reconnection when network restores |
| NFS unavailable | Container start fails | Cannot load new models | Models already loaded continue working |

---

## Security Boundaries

### Current (Phase 1)
- **Network**: Local network only (192.168.0.0/24)
- **Authentication**: None (trusted network assumption)
- **Daemon verification**: None (trusted network)
- **Credentials**: AES-256 encrypted, key from environment variable

### Future Auth Hooks (documented for Phase 2+)
- **Router API**: Add bearer token validation middleware
- **Dashboard UI**: Add session-based auth with login page
- **Daemon WebSocket**: Upgrade to mTLS with per-daemon certificates
- **Inter-container**: Service mesh or mTLS for Dashboard→Container

---

## Technology Stack Summary

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Frontend** | SvelteKit + adapter-static | Modern DX, static build, served by FastAPI |
| **Backend** | FastAPI (async) | Native async, OpenAPI docs, WebSocket support |
| **Database** | TimescaleDB | Time-series for metrics, PostgreSQL for config |
| **Container Runtime** | Podman | Daemonless, rootless-capable, OCI-compatible |
| **LLM Inference** | vLLM (primary) | Fastest, best model support |
| **GPU Monitoring** | pynvml | Low overhead, direct NVML access |
| **Container SDK** | podman-py | Pythonic interface to Podman |
| **IPC Protocol** | JSON-RPC 2.0 over WebSocket | Standard, debuggable, bidirectional |

---

## Related Documents

- [Product Requirements](./llms-prd.md)
- [Dashboard Architecture](./architecture-dashboard.md)
- [Daemon Architecture](./architecture-daemon.md)
- [Container Library](./architecture-containers.md)
