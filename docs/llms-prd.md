# LLM Serve - Product Requirements Document

## Document Information
- **Author**: mgreger
- **Created**: 2025-12-23
- **Status**: Draft
- **Version**: 1.0

---

## Executive Summary

LLM Serve is a self-hosted infrastructure platform for managing Large Language Model inference across a cluster of GPU-equipped machines. The system automates model deployment, request routing, and resource management, enabling efficient utilization of distributed GPU resources without manual intervention.

The platform consists of three components: a centralized Dashboard/Control web application, GPU Daemons running on each machine, and a curated Container Library for LLM runtimes. Applications send inference requests to a single endpoint, and the system automatically routes them to available GPUs—loading models on-demand and evicting least-recently-used models when resources are constrained.

This project addresses the pain of manual LLM management: tracking which models run where, creating containers from scratch, and underutilizing hardware due to management overhead. The goal is to make 30 GPUs as easy to use as one.

---

## Problem Statement

### Current State
- **Manual management**: LLMs are started, stopped, and monitored by hand across multiple machines
- **No visibility**: Difficult to remember which models are running on which machines
- **Container chaos**: Custom containers created from scratch or copied from working ones without standardization
- **Underutilization**: 30 GPUs available, but only 8 are practical to manage manually
- **Context switching**: Applications must know which machine hosts which model

### Desired State
- **Automatic routing**: Applications request a model; the system handles placement
- **Full utilization**: All 30 GPUs manageable from a single interface
- **Standardized containers**: Curated, tested container configurations for each model
- **Unified visibility**: Single dashboard showing cluster state, resource usage, and model status

---

## Goals & Success Metrics

### Primary Goals
1. Run applications without thinking about which machine hosts the model
2. Utilize all available GPUs (30) when needed
3. Eliminate manual container creation and configuration
4. Provide at-a-glance cluster visibility

### Success Metrics
| Metric | Target |
|--------|--------|
| GPU accessibility | All 30 GPUs manageable from single interface |
| Request routing | Automatic model loading and routing with no manual intervention |
| Model startup | Request → model loaded → response, fully automated |
| Management overhead | Near-zero manual intervention for day-to-day operations |

---

## Target Users

### Primary User
- **Single operator** (owner) managing personal GPU cluster
- Technical background, comfortable with containers and command line
- Wants automation, not hand-holding

### Future Consideration
- System designed for potential multi-user growth
- Architecture should not preclude adding authentication/authorization later

---

## System Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Applications                            │
│                    (LLM API consumers)                          │
└─────────────────────────┬───────────────────────────────────────┘
                          │ HTTP/WebSocket
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Dashboard / Control                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Web UI    │  │   Router    │  │   Control API           │  │
│  │  (Svelte)   │  │   (FIFO)    │  │   (FastAPI)             │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
│                         Podman Container                        │
└─────────────────────────┬───────────────────────────────────────┘
                          │ WebSocket (stats, commands)
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   GPU Daemon    │ │   GPU Daemon    │ │   GPU Daemon    │
│   Machine A     │ │   Machine B     │ │   Machine C     │
│  (FastAPI)      │ │  (FastAPI)      │ │  (FastAPI)      │
│    Podman       │ │    Podman       │ │    Podman       │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  LLM Container  │ │  LLM Container  │ │  LLM Container  │
│  (vLLM/SGLang)  │ │  (vLLM/SGLang)  │ │  (vLLM/SGLang)  │
│    Podman       │ │    Podman       │ │    Podman       │
└─────────────────┘ └─────────────────┘ └─────────────────┘
         │                   │                   │
         └───────────────────┴───────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │     NFS Storage       │
              │  /data/projects/ai/   │
              │    models/            │
              │    training/          │
              └───────────────────────┘
```

### Component 1: Dashboard / Control

**Deployment**: Podman container

**Responsibilities**:
- Web UI for cluster monitoring and management
- Request router for LLM inference
- Container library management
- Credential storage (HuggingFace)
- Model download orchestration

**Technology Stack**:
- Backend: Python + FastAPI
- Frontend: Svelte + SvelteKit
- Database: TimescaleDB (metrics/state)
- Communication: WebSocket (daemon) + REST (config)

#### Dashboard Pages

| Page | Purpose | Priority |
|------|---------|----------|
| **Cluster Overview** | Overall status: used/free/broken GPUs, active models, health | P1 - Phase 1 |
| **Machine Detail** | Per-machine: CPU/GPU load, memory, specs, running models, GPU mapping | P1 - Phase 1 |
| **Logs** | Filterable logs: errors, warnings, info | P1 - Phase 1 |
| **Model Inventory** | List models, details, download new, check updates | P2 - Phase 2 |
| **Container Config** | Configure: GPU allocation, context size, parallel requests | P2 - Phase 2 |
| **Chat/Test Interface** | Interact with models, send text/images/files, health checks | P1 - Phase 1 |
| **Notifications** | Alerts for missing models, errors, action items | P2 - Phase 2 |
| **Credentials** | Manage HuggingFace token, secure storage | P2 - Phase 2 |
| **Historical Metrics** | Grafana integration for trends/graphs | P3 - Phase 3 |

#### Request Router

**Model Naming Convention**:
- Requests include quantization suffix: `qwen2.5-72b-instruct-awq` or `qwen2.5-72b-instruct-q4_k_m`
- If no quantization specified, system uses smallest available quant for that model
- System tracks all available quantizations per model

**Routing Logic**:
1. Request arrives for model X (with or without quant suffix)
2. Parse model name and quantization (default to smallest available if not specified)
3. Check if model X with quant Q is running → route to it
4. If not running, look up GPU requirements for model+quant (may require multiple GPUs/machines)
5. Find available GPU(s) that meet requirements (prefer single machine, fall back to multi-machine)
6. If insufficient GPUs free, evict LRU model(s) until requirements met (coordinated across machines)
7. Start container(s) for model X with quant Q (single or multi-machine)
8. Route request once ready

**Multi-GPU / Multi-Machine Allocation**:
- Each model+quant has known GPU memory requirements (stored in container config)
- Allocation prefers single-machine when possible (lower latency)
- Large models (e.g., 70B+) may span multiple machines using tensor parallelism
- Eviction considers total GPU memory needed, may evict multiple smaller models
- Multi-machine models require coordinated startup across daemons
- Dashboard orchestrates multi-machine bring-up, waits for all nodes ready

**Parallelism Strategies** (vLLM):
- **Tensor Parallelism (TP)**: Splits layers across GPUs - requires uniform VRAM, lowest latency
- **Pipeline Parallelism (PP)**: Splits model into stages - allows mixed VRAM sizes, higher latency
- Container config specifies TP and PP settings per model+quant
- For heterogeneous clusters, PP may be required for largest models

**Queue Management**:
- One FIFO queue per model+quant combination
- Queue created when model+quant first requested
- FIFO ordering when backed up
- Configurable timeout → error if capacity unavailable

**Eviction Rules**:
- Only evict models with **empty queues** (no pending requests)
- Never evict a model that has requests waiting or in-flight
- LRU policy applies only among models with empty queues
- A model that just loaded must process at least the triggering request before becoming eviction-eligible
- Once eviction begins, the queue **blocks** (not destroyed) until model reloads
- This prevents thrashing: load model → serve one request → evict → someone else requests → reload

**Streaming**:
- All responses support streaming (SSE/WebSocket)
- Keepalive/heartbeat while model loading
- Tokens streamed as generated

**Concurrency**:
- Multiple concurrent requests to router (dozens+)
- Multiple concurrent requests to single model
- Responses routed back to correct caller

**Request Path**:
- Dashboard routes inference requests **directly to LLM containers** (not through Daemons)
- Daemons are for monitoring, stats reporting, and container lifecycle only
- Dashboard learns container endpoints from Daemon status reports

### Component 2: GPU Daemon

**Deployment**: Podman container on each GPU machine, started at boot

**Responsibilities**:
- Report machine stats to Dashboard
- Execute commands (start/stop LLM containers)
- Monitor local GPU/CPU/memory
- Manage local container lifecycle

**Technology Stack**:
- Python + FastAPI
- WebSocket client (connects to Dashboard)

**Stats Reporting**:
- Frequency: Every 6 seconds (10/minute)
- Metrics: CPU load, GPU load, memory usage (system + GPU), running containers, GPU mapping

**Communication Protocol**:
- Primary: WebSocket (bidirectional, real-time)
- Daemon initiates connection to Dashboard (zero-config machine addition)
- Dashboard accepts connection, registers machine automatically
- If connection drops, Dashboard marks machine as offline
- Reconnection handled automatically by Daemon

**Container Host Access**:

The daemon runs inside a container but must access host system metrics. Required container configuration:

| Resource | Access Method | Purpose |
|----------|---------------|---------|
| CPU info | `-v /proc:/host/proc:ro` | CPU type, core count, load average |
| Memory | `-v /proc:/host/proc:ro` | Total/available system memory |
| System info | `-v /sys:/host/sys:ro` | Device information |
| GPUs | `--device nvidia.com/gpu=all` | GPU stats via nvidia-smi |
| Podman socket | `-v /run/podman/podman.sock:/run/podman/podman.sock` | Manage LLM containers |

**Prerequisites on each GPU machine**:
- `nvidia-container-toolkit` installed and configured for Podman
- Podman socket enabled (`systemctl --user enable podman.socket` or system-level)
- NFS mount available at configured model path

**Example daemon container launch**:
```bash
podman run -d \
  --name llm-serve-daemon \
  --restart=always \
  -v /proc:/host/proc:ro \
  -v /sys:/host/sys:ro \
  -v /run/podman/podman.sock:/run/podman/podman.sock \
  --device nvidia.com/gpu=all \
  -e DASHBOARD_URL=ws://192.168.0.x:8080/ws/daemon \
  -e PROC_PATH=/host/proc \
  llm-serve-daemon:latest
```

### Component 3: Container Library

**Purpose**: Curated, tested Podman container configurations for LLM inference

**Supported Runtimes** (in preference order):
1. **vLLM** (preferred) - Latest version (0.12.x), fastest, best new model support
2. **SGLang** - When vLLM won't work, near-vLLM performance
3. **llama.cpp** - For GGUF models only, last resort

**Quantization Preference**:
- 4-bit preferred for large models
- 8-bit or 16-bit acceptable for smaller models

**Container Configuration**:
- GPU allocation (which GPUs, how many)
- Context size (token limit)
- Parallel request limit
- Model-specific parameters

**Model Storage**:
- Location: NFS `/data/projects/ai/models` (configurable)
- Structure: Standard HuggingFace directory layout (`provider/model-name`)
- User-trained models: `username/model-name`

---

## Data Architecture

### Storage Locations

| Data Type | Location | Notes |
|-----------|----------|-------|
| Models | NFS: `/data/projects/ai/models` | HuggingFace structure, shared across cluster |
| Training data | NFS: `/data/projects/ai/training` | Future use |
| Metrics DB | Local SSD (outside container) | TimescaleDB, per-Dashboard instance |
| Logs | Local SSD (outside container) | Retained long-term |
| Configuration | Local SSD (outside container) | Container definitions, settings |
| Credentials | Local SSD (outside container) | Encrypted, secure storage |

**Rule**: Anything >100MB or growing unbounded lives outside containers.

### Database Schema (High-Level)

**TimescaleDB Tables**:
- `machine_stats` - Time-series CPU/GPU/memory metrics
- `model_events` - Load/unload/request events
- `request_log` - Router request history (optional, for debugging)

**Regular Tables**:
- `machines` - Registered machines, specs, status
- `models` - Known models (base model info)
- `model_quantizations` - Available quantizations per model, file paths, sizes
- `containers` - Container definitions, runtime configs (per model+quant)
- `credentials` - Encrypted credential storage

---

## Infrastructure Requirements

### Current Environment

| Aspect | Value |
|--------|-------|
| **Machines** | 3 active, capacity for more |
| **GPUs** | 8 active, 30 total available |
| **OS** | Fedora Linux 38-43 (will standardize to 43 if needed) |
| **Network - WAN** | 2.5 Gbps |
| **Network - LAN** | 1-25 Gbps (average 10 Gbps) |
| **Storage** | NFS server with U.2/U.3 SSDs, faster than network |
| **Container runtime** | Podman + nvidia-container-toolkit (to be installed on all machines) |

### Network Configuration

- Dashboard accessible on local network only: `192.168.0.x`
- No authentication initially
- No VPN/external access required

### Model Source

- Primary: HuggingFace Hub
- Download method: Fastest available (huggingface-cli, hf_transfer)
- Credentials: HuggingFace token used for all downloads when available (faster rates, gated model access)

---

## Development Requirements

### Containerized Development

**All development must occur inside containers**. No packages/tools installed directly on the development machine.

Development containers should include:
- Python 3.11+
- Node.js 20+ (for Svelte frontend)
- Required Python packages (FastAPI, uvicorn, etc.)
- Development tools (pytest, ruff, etc.)

### Code Organization

```
llms/
├── docs/
│   └── llms-prd.md
├── dashboard/
│   ├── Containerfile
│   ├── backend/          # FastAPI application
│   │   ├── api/
│   │   ├── router/
│   │   ├── models/
│   │   └── services/
│   └── frontend/         # Svelte application
│       ├── src/
│       └── static/
├── daemon/
│   ├── Containerfile
│   └── src/
├── containers/           # LLM container definitions
│   ├── vllm/
│   ├── sglang/
│   └── llamacpp/
└── dev/                  # Development container configs
    └── Containerfile
```

---

## Architecture Documents

The following architecture documents provide detailed technical design for this product:

| Document | Description |
|----------|-------------|
| [architecture-overview.md](./architecture-overview.md) | System-wide architecture, component interactions, deployment topology |
| [architecture-dashboard.md](./architecture-dashboard.md) | Dashboard/Control design: router, queues, DB schema, API endpoints |
| [architecture-daemon.md](./architecture-daemon.md) | GPU Daemon design: stats collection, container lifecycle, WebSocket protocol |
| [architecture-containers.md](./architecture-containers.md) | Container Library: runtime configs, GPU requirements, command generation |

These documents should be read alongside this PRD for complete product specifications.

---

## Non-Functional Requirements

### Security
- Local network access only (192.168.0.x)
- No authentication in initial release
- Credentials (HuggingFace) stored encrypted
- Future: Design should not preclude adding auth

### Reliability
- **Dashboard failure**: GPU Daemons keep models running
- **Dashboard restart**: Auto-recovers state from database, reconnects to daemons
- **Daemon failure**: Dashboard detects, marks machine as unavailable
- **Acceptable data loss**: Router state during Dashboard restart (apps see temporary errors)

### Performance
- Router overhead: <20ms acceptable
- Stats collection: 6-second intervals (10/minute)
- Model loading: As fast as hardware allows
- Streaming latency: Minimal buffering

### Scalability
- Support 30+ GPUs across 10+ machines
- Dozens of concurrent requests through router
- Per-model FIFO prevents head-of-line blocking

---

## Phased Delivery

### Phase 1: Core Infrastructure (MVP)

**Goal**: End-to-end request handling—send request, model loads, get response

**Deliverables**:
1. Dashboard container with:
   - Cluster Overview page (mockup first, then implement)
   - Machine Detail page (mockup first, then implement)
   - Basic request router
   - Chat/Test interface
   - Basic logging
2. GPU Daemon container with:
   - Stats reporting (WebSocket)
   - Container start/stop commands
   - Boot startup configuration
3. Initial vLLM container configuration
4. Development container for all work

**Approach**:
- Front page mockup → feedback → implement
- Machine detail mockup → feedback → implement
- Then router and daemon integration

**Exit Criteria**:
- Can see cluster status in Dashboard
- Can see individual machine details
- Can send chat request through router
- Model auto-loads on available GPU
- Response streams back to chat interface

### Phase 2: Container Library & Model Management

**Goal**: Full model and container lifecycle management

**Deliverables**:
1. Model Inventory page
2. Container Configuration page
3. Model download from HuggingFace
4. Credentials management (HuggingFace token)
5. Notifications for missing models
6. Additional container configs (SGLang, llama.cpp)

**Exit Criteria**:
- Can download new models from Dashboard
- Can configure container parameters (context, parallelism)
- Can create container config for new model
- Notifications appear when unknown model requested

### Phase 3: Observability

**Goal**: Historical metrics and detailed monitoring

**Deliverables**:
1. Grafana integration
2. Historical metrics dashboards
3. Enhanced logging (retention, search)
4. Alerting (optional)

**Exit Criteria**:
- Can view historical GPU/CPU/memory trends
- Can correlate request patterns with resource usage
- Logs searchable and retained

### Phase 4: Training Support (Deferred)

**Goal**: Run training jobs through the same infrastructure

**Deliverables**:
1. Training job API
2. Training container configs (Unsloth, Axolotl, HuggingFace Trainer)
3. Job monitoring
4. Output model management

**Status**: Deferred until specific need arises. Design should not preclude future addition.

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Podman version incompatibility across Fedora versions | Medium | Medium | Standardize to Fedora 43; test on oldest supported |
| vLLM container complexity | Medium | High | Start with known-working model; iterate |
| WebSocket connection stability | Low | Medium | Implement reconnection logic, heartbeats |
| NFS latency under load | Low | Medium | Monitor; NFS server has SSD backing |
| Model loading time frustrating users | Medium | Low | Streaming keepalive; clear status in UI |

---

## Assumptions

1. All machines have stable network connectivity to NFS and Dashboard
2. Podman can be installed and configured uniformly across all machines
3. User has HuggingFace account for accessing gated models
4. NFS performance is sufficient (validated: SSD-backed, fast)
5. Local network (192.168.0.x) is trusted; no auth needed initially
6. Single user; no concurrent administrative access conflicts

---

## Open Questions

None at this time. All requirements have been clarified.

---

## Glossary

| Term | Definition |
|------|------------|
| **vLLM** | High-performance LLM inference engine with PagedAttention |
| **SGLang** | LLM inference framework with structured generation support |
| **llama.cpp** | CPU/GPU inference for GGUF quantized models |
| **GGUF** | File format for quantized LLM models |
| **LoRA** | Low-Rank Adaptation, efficient fine-tuning method |
| **LRU** | Least Recently Used (eviction policy) |
| **FIFO** | First In, First Out (queue ordering) |
| **NFS** | Network File System |
| **Pipeline Parallelism** | Splitting model into sequential stages across GPUs; allows mixed VRAM sizes |
| **Podman** | Daemonless container runtime (Docker alternative) |
| **Tensor Parallelism** | Splitting individual layers across GPUs; requires uniform VRAM, lowest latency |
| **TimescaleDB** | PostgreSQL extension for time-series data |

---

## Appendix

### A. Example Request Flow (Single Machine)

```
1. Application sends: POST /v1/chat/completions
   {"model": "qwen2.5-32b-instruct-awq", "messages": [...]}

2. Router receives request
   - Parses model: "qwen2.5-32b-instruct", quant: "awq"
   - Looks up requirements: 2 GPUs, ~40GB VRAM, single machine OK
   - Checks: Is qwen2.5-32b-instruct-awq running? No.
   - Checks: Machine B has 2 GPUs free with sufficient VRAM
   - Sends to Daemon B: Start vLLM container for qwen2.5-32b-instruct-awq on GPUs 0,1

3. Daemon B:
   - Pulls container config from library for model+quant
   - Starts Podman container with model mounted from NFS
   - Reports: Container starting, health checking...

4. Router:
   - Sends keepalive/heartbeat to application (streaming)
   - Waits for healthy signal

5. Daemon B reports: Model ready

6. Router:
   - Forwards original request to vLLM container on Machine B
   - Streams response tokens back to application

7. Application receives streamed response

8. Model+quant stays loaded for future requests (until LRU evicted)
```

### A2. Example Request Flow (Multi-Machine)

```
1. Application sends: POST /v1/chat/completions
   {"model": "llama3.1-405b-instruct-fp8", "messages": [...]}

2. Router receives request
   - Parses model: "llama3.1-405b-instruct", quant: "fp8"
   - Looks up requirements: 8 GPUs, ~400GB VRAM, multi-machine required
   - Checks: Is llama3.1-405b-instruct-fp8 running? No.
   - Checks available capacity:
     - Machine A: 2 GPUs free (not enough alone)
     - Machine B: 4 GPUs free
     - Machine C: 4 GPUs free
   - Eviction needed: Evict LRU models on A to free 2 more GPUs
   - Allocation plan: Machine A (4 GPUs) + Machine B (4 GPUs) = 8 GPUs total

3. Router orchestrates multi-machine startup:
   - Sends to Daemon A: Evict models X, Y; prepare for tensor parallel rank 0-3
   - Sends to Daemon B: Prepare for tensor parallel rank 4-7
   - Both daemons acknowledge eviction complete

4. Router sends coordinated start command:
   - Daemon A: Start vLLM container as master node (rank 0-3)
   - Daemon B: Start vLLM container as worker node (rank 4-7), connect to master

5. Router:
   - Sends keepalive/heartbeat to application (streaming)
   - Waits for both daemons to report healthy

6. Both daemons report: Model ready (distributed inference active)

7. Router:
   - Forwards request to master node (Machine A)
   - Master coordinates inference across both machines
   - Streams response tokens back to application

8. Application receives streamed response

9. Model+quant stays loaded across both machines (until LRU evicted together)
```

### B. Daemon Stats Payload (Example)

```json
{
  "machine_id": "gpu-server-b",
  "hostname": "gpu-server-b.local",
  "timestamp": "2025-01-15T10:30:00Z",
  "cpu": {
    "manufacturer": "AMD",
    "model": "AMD Ryzen Threadripper PRO 5975WX 32-Cores",
    "cores": 32,
    "threads": 64,
    "load_percent": 15.2
  },
  "memory": {
    "total_gb": 256,
    "used_gb": 45,
    "available_gb": 211
  },
  "network": [
    {
      "interface": "enp5s0",
      "mac_address": "00:1a:2b:3c:4d:5e",
      "ip_addresses": ["192.168.0.21", "fd00::21"],
      "speed_mbps": 10000,
      "mtu": 9000,
      "is_up": true,
      "bytes_sent": 1234567890,
      "bytes_recv": 9876543210,
      "bytes_sent_rate": 125000000.0,
      "bytes_recv_rate": 500000000.0
    }
  ],
  "gpus": [
    {
      "index": 0,
      "uuid": "GPU-12345678-abcd-efgh-ijkl-mnopqrstuvwx",
      "chip_manufacturer": "NVIDIA",
      "chip_model": "NVIDIA GeForce RTX 4090",
      "card_manufacturer": "eVGA",
      "pci_bus_id": "0000:01:00.0",
      "serial": "1234567890",
      "memory_total_gb": 24,
      "memory_used_gb": 22,
      "utilization_percent": 85,
      "temperature_c": 72,
      "power_draw_w": 350.5,
      "power_limit_w": 450.0,
      "model_loaded": "qwen2.5-72b-instruct-awq"
    },
    {
      "index": 1,
      "uuid": "GPU-87654321-dcba-hgfe-lkji-xwvutsrqponm",
      "chip_manufacturer": "NVIDIA",
      "chip_model": "NVIDIA GeForce RTX 4090",
      "card_manufacturer": "eVGA",
      "pci_bus_id": "0000:02:00.0",
      "serial": "0987654321",
      "memory_total_gb": 24,
      "memory_used_gb": 0,
      "utilization_percent": 0,
      "temperature_c": 35,
      "power_draw_w": 25.0,
      "power_limit_w": 450.0,
      "model_loaded": null
    }
  ],
  "containers": [
    {
      "id": "vllm-qwen72b-abc123",
      "model": "qwen2.5-72b-instruct-awq",
      "runtime": "vllm",
      "gpus": [0],
      "status": "running",
      "uptime_seconds": 3600
    }
  ]
}
```

### C. Configuration Defaults

```yaml
# Dashboard configuration
dashboard:
  host: 0.0.0.0
  port: 8080
  allowed_networks:
    - 192.168.0.0/24

# Storage paths
storage:
  models: /data/projects/ai/models
  training: /data/projects/ai/training

# Router settings
router:
  timeout_seconds: 300
  keepalive_interval_ms: 1000

# Daemon settings
daemon:
  stats_interval_seconds: 6
  dashboard_url: ws://192.168.0.x:8080/ws/daemon

# Container defaults
containers:
  default_runtime: vllm
  runtime_preference:
    - vllm
    - sglang
    - llamacpp
```
