# Dashboard / Control - Architecture Document

## Document Information
- **Related PRD**: [llms-prd.md](./llms-prd.md)
- **Component**: Dashboard / Control
- **Created**: 2025-12-23
- **Status**: Draft
- **Version**: 1.0

---

## Overview

The Dashboard is the central control plane for LLM Serve. It serves three primary functions:

1. **Web UI** - Cluster monitoring, model management, and testing interface
2. **Request Router** - OpenAI-compatible API that routes inference requests to appropriate LLM containers
3. **Control API** - Backend for UI operations and daemon coordination

All three functions run within a single FastAPI application, deployed as one Podman container. The frontend is built with SvelteKit and served as static assets by FastAPI.

---

## High-Level Design

### Responsibilities

- Serve web UI for cluster monitoring and management
- Accept and route OpenAI-compatible inference requests
- Maintain WebSocket connections with all GPU daemons
- Orchestrate model loading, eviction, and multi-machine deployments
- Store metrics, configuration, and container definitions
- Manage HuggingFace credentials and model downloads (Phase 2)

### Boundaries

**Owns:**
- Request queue management and routing decisions
- Cluster state aggregation and display
- Container configuration definitions
- Model inventory and download orchestration
- Credential storage

**Does NOT own:**
- Direct GPU monitoring (delegated to Daemons)
- Container lifecycle execution (delegated to Daemons)
- Model file storage (NFS)
- LLM inference (delegated to LLM containers)

### Key Abstractions

| Concept | Description |
|---------|-------------|
| **Machine** | A GPU-equipped server running a Daemon |
| **Model** | A base LLM (e.g., qwen2.5-72b-instruct) |
| **Quantization** | A specific quantized version (e.g., awq, q4_k_m) |
| **Model+Quant** | Unique identifier for routing (e.g., qwen2.5-72b-instruct-awq) |
| **Container Config** | Runtime configuration for a model+quant |
| **Queue** | Per-model+quant FIFO queue for pending requests |

---

## Technology Stack

### Language & Framework

- **Python 3.11+** - Async support, type hints, modern features
- **FastAPI** - Async web framework with OpenAPI, WebSocket support
- **Uvicorn** - ASGI server

### Frontend

- **SvelteKit** - Frontend framework with file-based routing
- **adapter-static** - Builds to static files
- **Vite** - Dev server with HMR (development only)

### Database

- **TimescaleDB** - PostgreSQL extension for time-series data
- **asyncpg** - Async PostgreSQL driver
- **SQLAlchemy 2.0** - ORM with async support

### Key Dependencies

```
# Backend
fastapi>=0.104
uvicorn[standard]>=0.24
asyncpg>=0.29
sqlalchemy[asyncio]>=2.0
pydantic>=2.5
websockets>=12.0
httpx>=0.25          # For forwarding requests to LLM containers
cryptography>=41.0   # For credential encryption

# Frontend (build-time)
@sveltejs/kit
@sveltejs/adapter-static
```

---

## Application Structure

### Directory Layout

```
dashboard/
├── Containerfile
├── pyproject.toml
├── backend/
│   ├── main.py                 # FastAPI app entry point
│   ├── config.py               # Environment-based configuration
│   ├── api/
│   │   ├── __init__.py
│   │   ├── router.py           # OpenAI-compatible inference endpoints
│   │   ├── control.py          # UI backend API endpoints
│   │   └── websocket.py        # Daemon WebSocket handler
│   ├── services/
│   │   ├── __init__.py
│   │   ├── queue_manager.py    # Request queue management
│   │   ├── cluster_state.py    # In-memory cluster state
│   │   ├── model_router.py     # Routing logic and eviction
│   │   ├── daemon_manager.py   # Daemon connection management
│   │   └── credentials.py      # Encrypted credential storage
│   ├── models/
│   │   ├── __init__.py
│   │   ├── database.py         # SQLAlchemy models
│   │   └── schemas.py          # Pydantic schemas
│   └── db/
│       ├── __init__.py
│       ├── session.py          # Async session management
│       └── migrations/         # Alembic migrations
└── frontend/
    ├── package.json
    ├── svelte.config.js
    ├── vite.config.js
    ├── src/
    │   ├── routes/
    │   │   ├── +layout.svelte
    │   │   ├── +page.svelte           # Cluster Overview
    │   │   ├── machine/[id]/+page.svelte  # Machine Detail
    │   │   ├── logs/+page.svelte
    │   │   └── chat/+page.svelte      # Test Interface
    │   ├── lib/
    │   │   ├── components/
    │   │   ├── stores/
    │   │   └── api.ts
    │   └── app.html
    └── static/
```

---

## API Design

### OpenAI-Compatible Router Endpoints

These endpoints match OpenAI's API format for drop-in compatibility.

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v1/chat/completions` | POST | Chat completions (primary) |
| `/v1/completions` | POST | Text completions |
| `/v1/models` | GET | List available models |
| `/v1/models/{model}` | GET | Model details |

**Request Format (chat completions):**
```json
{
  "model": "qwen2.5-72b-instruct-awq",
  "messages": [
    {"role": "user", "content": "Hello, world!"}
  ],
  "stream": true,
  "max_tokens": 1000,
  "temperature": 0.7
}
```

**Model Naming:**
- Format: `{model-name}-{quantization}` (e.g., `qwen2.5-72b-instruct-awq`)
- If no quantization specified, system uses smallest available quant
- `/v1/models` returns all available model+quant combinations

### Control API Endpoints

Backend for the web UI.

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/cluster/status` | GET | Cluster overview (machines, GPUs, models) |
| `/api/machines` | GET | List all machines |
| `/api/machines/{id}` | GET | Machine details with GPU info |
| `/api/machines/{id}/logs` | GET | Machine logs (from daemon) |
| `/api/models` | GET | Model inventory |
| `/api/models/{id}/start` | POST | Manually start a model |
| `/api/models/{id}/stop` | POST | Manually stop a model |
| `/api/containers` | GET | Container configurations |
| `/api/containers/{id}` | GET/PUT | Container config details |
| `/api/logs` | GET | System logs (filterable) |
| `/api/settings` | GET/PUT | System settings |

### WebSocket Endpoints

| Endpoint | Purpose |
|----------|---------|
| `/ws/daemon` | Daemon connections (JSON-RPC 2.0) |
| `/ws/ui` | Real-time UI updates (cluster state changes) |

---

## Request Router Design

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Router Service                            │
│                                                                  │
│  ┌──────────────┐    ┌──────────────────┐    ┌───────────────┐  │
│  │   Endpoint   │───►│   QueueManager   │───►│  ModelRouter  │  │
│  │  /v1/chat/   │    │                  │    │               │  │
│  │ completions  │    │  Per-model FIFO  │    │  Placement &  │  │
│  └──────────────┘    │  queues          │    │  eviction     │  │
│                      └──────────────────┘    └───────┬───────┘  │
│                                                      │          │
│                                              ┌───────▼───────┐  │
│                                              │ DaemonManager │  │
│                                              │               │  │
│                                              │ Send commands │  │
│                                              └───────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### QueueManager

Manages per-model+quant request queues using `asyncio.Queue`.

```python
class QueueManager:
    """Manages FIFO queues for each model+quant combination."""

    # model+quant -> asyncio.Queue
    queues: dict[str, asyncio.Queue]

    # model+quant -> count of requests in queue or being processed
    active_counts: dict[str, int]

    # model+quant -> last request completion timestamp
    last_used: dict[str, datetime]

    async def enqueue(self, model_quant: str, request: InferenceRequest) -> None:
        """Add request to queue, create queue if needed."""

    async def dequeue(self, model_quant: str) -> InferenceRequest:
        """Get next request from queue (blocks until available)."""

    def is_idle(self, model_quant: str) -> bool:
        """True if queue is empty and no requests in-flight."""

    def get_lru_idle_models(self) -> list[str]:
        """Return idle models sorted by last_used (oldest first)."""
```

### ModelRouter

Handles model placement, loading, and eviction decisions.

```python
class ModelRouter:
    """Routes requests to appropriate LLM containers."""

    async def route_request(self, request: InferenceRequest) -> AsyncIterator[str]:
        """
        Route request to LLM container, loading model if needed.

        1. Parse model+quant from request
        2. Check if model running -> route directly
        3. If not running:
           a. Look up GPU requirements
           b. Find capacity (evict LRU idle models if needed)
           c. Send start command to daemon(s)
           d. Poll health until ready
        4. Forward request to container
        5. Stream response back
        """

    async def ensure_capacity(self, required_gpus: list[GPURequirement]) -> list[Machine]:
        """
        Ensure required GPU capacity is available.

        - Identify machines with available GPUs
        - If insufficient, evict LRU idle models
        - Mark machines as "busy" during transition
        - Return list of machines ready for loading
        """

    async def evict_model(self, model_quant: str) -> None:
        """
        Evict a model from the cluster.

        - Only callable if model is idle (queue empty)
        - Send stop command to daemon(s)
        - Block queue until eviction complete
        """
```

### Request Flow (Detailed)

```python
async def handle_chat_completion(request: ChatCompletionRequest):
    model_quant = parse_model_quant(request.model)

    # Get or create queue for this model+quant
    queue = queue_manager.get_or_create_queue(model_quant)

    # Create async event for this request's completion
    response_event = asyncio.Event()
    request_context = RequestContext(request, response_event)

    # Enqueue the request
    await queue_manager.enqueue(model_quant, request_context)

    # Start worker if model not being processed
    if not model_router.is_processing(model_quant):
        asyncio.create_task(model_router.process_queue(model_quant))

    # Return streaming response (yields keepalive until model ready)
    async def generate():
        while not response_event.is_set():
            yield ": keepalive\n\n"
            await asyncio.sleep(1)

        async for chunk in request_context.response_stream:
            yield f"data: {chunk}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
```

### Timeout Scaling

Request timeout scales with model size to account for loading time:

| Model Size | Base Timeout | Loading Buffer | Total Timeout |
|------------|--------------|----------------|---------------|
| < 10B | 60s | +30s | 90s |
| 10-30B | 60s | +60s | 120s |
| 30-70B | 60s | +120s | 180s |
| 70B+ | 60s | +180s | 240s |
| Multi-machine | 60s | +300s | 360s |

---

## Cluster State Management

### In-Memory State

The Dashboard maintains real-time cluster state in memory, updated by daemon stats reports.

```python
@dataclass
class ClusterState:
    """Real-time cluster state (in-memory)."""

    machines: dict[str, MachineState]      # machine_id -> state
    running_models: dict[str, ModelState]  # model_quant -> state
    pending_operations: dict[str, Operation]  # operation_id -> state

@dataclass
class MachineState:
    machine_id: str
    hostname: str
    connected: bool
    last_seen: datetime
    cpu: CPUStats
    memory: MemoryStats
    gpus: list[GPUState]
    containers: list[ContainerState]

@dataclass
class GPUState:
    index: int
    uuid: str
    name: str
    memory_total_gb: float
    memory_used_gb: float
    utilization_percent: int
    temperature_c: int
    assigned_model: str | None
```

### State Recovery on Restart

When Dashboard restarts:

1. Load configuration from database (container configs, settings)
2. Wait for daemons to reconnect (they initiate)
3. Each daemon reports current state on connect
4. Rebuild in-memory cluster state from daemon reports
5. Rebuild queue state (empty - clients retry failed requests)
6. Resume normal operation

**Note:** Requests in-flight during restart are lost. Clients receive connection errors and should retry.

---

## Data Architecture

### Database Schema

```sql
-- Time-series tables (TimescaleDB hypertables)

CREATE TABLE cpu_stats (
    time        TIMESTAMPTZ NOT NULL,
    machine_id  TEXT NOT NULL,
    cores       INTEGER,
    load_percent REAL,
    PRIMARY KEY (time, machine_id)
);
SELECT create_hypertable('cpu_stats', 'time');

CREATE TABLE gpu_stats (
    time            TIMESTAMPTZ NOT NULL,
    machine_id      TEXT NOT NULL,
    gpu_uuid        TEXT NOT NULL,
    gpu_index       INTEGER,
    gpu_name        TEXT,
    memory_total_gb REAL,
    memory_used_gb  REAL,
    utilization     INTEGER,
    temperature_c   INTEGER,
    model_loaded    TEXT,
    PRIMARY KEY (time, machine_id, gpu_uuid)
);
SELECT create_hypertable('gpu_stats', 'time');

CREATE TABLE memory_stats (
    time         TIMESTAMPTZ NOT NULL,
    machine_id   TEXT NOT NULL,
    total_gb     REAL,
    used_gb      REAL,
    available_gb REAL,
    PRIMARY KEY (time, machine_id)
);
SELECT create_hypertable('memory_stats', 'time');

-- Regular tables

CREATE TABLE machines (
    id          TEXT PRIMARY KEY,
    hostname    TEXT NOT NULL,
    ip_address  TEXT,
    first_seen  TIMESTAMPTZ DEFAULT NOW(),
    last_seen   TIMESTAMPTZ,
    cpu_model   TEXT,
    cpu_cores   INTEGER,
    memory_gb   REAL,
    notes       TEXT
);

CREATE TABLE models (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,  -- e.g., "qwen2.5-72b-instruct"
    provider        TEXT,                   -- e.g., "Qwen"
    huggingface_id  TEXT,                   -- e.g., "Qwen/Qwen2.5-72B-Instruct"
    base_parameters TEXT,                   -- e.g., "72B"
    added_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE model_quantizations (
    id              SERIAL PRIMARY KEY,
    model_id        INTEGER REFERENCES models(id),
    quantization    TEXT NOT NULL,          -- e.g., "awq", "q4_k_m", "fp16"
    file_path       TEXT,                   -- Path in NFS
    file_size_gb    REAL,
    vram_required_gb REAL,                  -- Estimated VRAM needed
    gpu_count       INTEGER DEFAULT 1,      -- Minimum GPUs required
    added_at        TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(model_id, quantization)
);

CREATE TABLE container_configs (
    id              SERIAL PRIMARY KEY,
    model_quant_id  INTEGER REFERENCES model_quantizations(id),
    runtime         TEXT NOT NULL DEFAULT 'vllm',  -- vllm, sglang, llamacpp
    context_length  INTEGER DEFAULT 8192,
    max_parallel    INTEGER DEFAULT 4,
    tensor_parallel INTEGER DEFAULT 1,      -- TP degree
    pipeline_parallel INTEGER DEFAULT 1,    -- PP degree
    extra_args      JSONB,                  -- Runtime-specific args
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE credentials (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,       -- e.g., "huggingface"
    encrypted   BYTEA NOT NULL,             -- AES-256 encrypted value
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE settings (
    key         TEXT PRIMARY KEY,
    value       JSONB NOT NULL,
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);
```

### Retention Policy

Default retention: 30 days at full resolution.

```sql
-- Set retention policy (configurable via settings table)
SELECT add_retention_policy('cpu_stats', INTERVAL '30 days');
SELECT add_retention_policy('gpu_stats', INTERVAL '30 days');
SELECT add_retention_policy('memory_stats', INTERVAL '30 days');
```

Storage estimate for 30 GPUs at 6-second intervals:
- GPU stats: ~30 GPUs × 14,400 samples/day × 30 days × ~200 bytes = ~2.5 GB
- CPU/Memory stats: ~10 machines × 14,400 × 30 × ~100 bytes = ~0.4 GB
- Total: ~3 GB for 30 days (configurable)

---

## WebSocket Protocol

### Daemon Connection Handler

```python
@app.websocket("/ws/daemon")
async def daemon_websocket(websocket: WebSocket):
    await websocket.accept()

    # First message must be registration
    registration = await websocket.receive_json()
    machine_id = registration["params"]["machine_id"]

    # Register machine
    daemon_manager.register(machine_id, websocket)

    try:
        async for message in websocket.iter_json():
            await handle_daemon_message(machine_id, message)
    finally:
        daemon_manager.unregister(machine_id)

async def handle_daemon_message(machine_id: str, message: dict):
    method = message.get("method")

    if method == "stats.report":
        await cluster_state.update_machine_stats(machine_id, message["params"])
        await store_stats_to_db(machine_id, message["params"])

    elif method == "container.status":
        await cluster_state.update_container_status(
            machine_id,
            message["params"]["container_id"],
            message["params"]["status"]
        )
```

### UI WebSocket

Real-time updates pushed to connected UI clients.

```python
@app.websocket("/ws/ui")
async def ui_websocket(websocket: WebSocket):
    await websocket.accept()
    ui_manager.add_client(websocket)

    try:
        # Send initial state
        await websocket.send_json({
            "type": "cluster_state",
            "data": cluster_state.to_dict()
        })

        # Keep alive, updates pushed via ui_manager
        async for message in websocket.iter_json():
            # Handle UI commands if any
            pass
    finally:
        ui_manager.remove_client(websocket)
```

---

## Security

### Credential Encryption

```python
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os

class CredentialManager:
    def __init__(self, encryption_key: str):
        # Derive Fernet key from provided key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"llm-serve-salt",  # Static salt (key is already secret)
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(encryption_key.encode()))
        self.fernet = Fernet(key)

    def encrypt(self, value: str) -> bytes:
        return self.fernet.encrypt(value.encode())

    def decrypt(self, encrypted: bytes) -> str:
        return self.fernet.decrypt(encrypted).decode()
```

**Environment variable:** `LLM_SERVE_ENCRYPTION_KEY`

### Future Auth Hooks

Document where authentication would be added:

1. **Router endpoints** (`/v1/*`): Add `Depends(verify_api_key)` to route definitions
2. **Control API** (`/api/*`): Add `Depends(verify_session)` middleware
3. **WebSocket UI** (`/ws/ui`): Verify session token on connect
4. **WebSocket Daemon** (`/ws/daemon`): Verify client certificate (mTLS)

---

## Configuration

All configuration via environment variables:

```bash
# Required
LLM_SERVE_ENCRYPTION_KEY=<secret-key-for-credentials>

# Database (defaults shown)
DATABASE_URL=postgresql+asyncpg://llmserve:llmserve@localhost:5432/llmserve

# Server
HOST=0.0.0.0
PORT=8080

# Network
ALLOWED_NETWORKS=192.168.0.0/24

# Storage
MODEL_PATH=/data/projects/ai/models

# Retention
METRICS_RETENTION_DAYS=30

# Timeouts
DEFAULT_REQUEST_TIMEOUT_SECONDS=60
HEALTH_CHECK_INTERVAL_SECONDS=1

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

---

## Logging

Structured JSON logging throughout:

```python
import structlog

logger = structlog.get_logger()

# Example log entry
logger.info(
    "request_routed",
    model=model_quant,
    machine_id=machine.id,
    latency_ms=latency,
    action="forward"
)
```

**Output:**
```json
{
  "timestamp": "2025-01-15T10:30:00.123Z",
  "level": "info",
  "event": "request_routed",
  "model": "qwen2.5-72b-instruct-awq",
  "machine_id": "gpu-server-b",
  "latency_ms": 15,
  "action": "forward"
}
```

---

## Development

### Dev Container

Single container with hot-reload for both frontend and backend:

```dockerfile
# dev/Containerfile
FROM python:3.11-slim

# Install Node.js for frontend
RUN apt-get update && apt-get install -y nodejs npm

# Python dependencies
COPY dashboard/pyproject.toml /app/dashboard/
RUN pip install -e /app/dashboard[dev]

# Frontend dependencies
COPY dashboard/frontend/package.json /app/dashboard/frontend/
RUN cd /app/dashboard/frontend && npm install

WORKDIR /app
CMD ["./dev/start-dev.sh"]
```

```bash
# dev/start-dev.sh
#!/bin/bash
# Start frontend dev server (background)
cd /app/dashboard/frontend && npm run dev &

# Start backend with reload
cd /app/dashboard && uvicorn backend.main:app --reload --host 0.0.0.0 --port 8080
```

### Testing

Unit tests with pytest, mocking external dependencies:

```bash
pytest dashboard/backend/tests/ -v
```

Mock targets:
- Database: Use `asyncpg` test fixtures or SQLite
- WebSocket connections: Mock `WebSocket` class
- HTTP requests to LLM containers: Mock `httpx.AsyncClient`

---

## Deployment

### Production Container

```dockerfile
# dashboard/Containerfile
FROM node:20-slim AS frontend-builder
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim
WORKDIR /app

# Install dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir .

# Copy backend code
COPY backend/ ./backend/

# Copy built frontend
COPY --from=frontend-builder /app/build ./static/

# Run
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### Container Launch

```bash
podman run -d \
  --name llm-serve-dashboard \
  --restart=always \
  -p 8080:8080 \
  -v /data/llm-serve/config:/data/config \
  -v /data/llm-serve/db:/data/db \
  -v /data/llm-serve/logs:/data/logs \
  -e LLM_SERVE_ENCRYPTION_KEY=<key> \
  -e DATABASE_URL=postgresql+asyncpg://llmserve:llmserve@localhost:5432/llmserve \
  -e MODEL_PATH=/data/projects/ai/models \
  llm-serve-dashboard:latest
```

---

## Related Documents

- [Architecture Overview](./architecture-overview.md)
- [Daemon Architecture](./architecture-daemon.md)
- [Container Library](./architecture-containers.md)
- [Product Requirements](./llms-prd.md)
