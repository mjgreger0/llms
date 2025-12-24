# Implementation Plan - Phase 4: WebSocket Communication

## Document Information
- **Phase**: 4 - WebSocket Communication
- **Created**: 2025-12-23
- **Status**: Ready for Implementation
- **Version**: 1.0

---

## Phase Overview

**Goal**: Establish bidirectional communication between Dashboard and Daemons using WebSocket connections with JSON-RPC 2.0 protocol.

**Deliverables**:
- Dashboard WebSocket handler (`/ws/daemon` endpoint)
- Daemon WebSocket client with reconnection logic
- JSON-RPC 2.0 protocol implementation
- DaemonManager (Dashboard-side connection tracking)
- Stats storage to TimescaleDB
- ClusterState in-memory state management
- Container command stubs (start/stop)
- UI WebSocket endpoint (`/ws/ui`) for real-time updates

**Exit Criteria**:
- Daemon successfully connects to Dashboard
- Stats flow from Daemon and get stored in TimescaleDB
- Commands can be sent from Dashboard to Daemon (stub execution)
- Reconnection with exponential backoff + jitter works
- ClusterState updates in real-time from daemon reports
- UI clients receive real-time cluster state updates

---

## Task Breakdown

### 1. JSON-RPC 2.0 Protocol Implementation

#### Task 1.1: JSON-RPC Message Builders
- [ ] **Status**: Not Started
- **Description**: Create helper functions for building JSON-RPC 2.0 compliant messages (requests, responses, notifications, errors).
- **Acceptance Criteria**:
  - [ ] Request builder with method, params, and auto-incrementing ID
  - [ ] Response builder with result or error
  - [ ] Notification builder (no ID field)
  - [ ] Error response builder with standard error codes
  - [ ] All messages include `jsonrpc: "2.0"` field
  - [ ] Type hints and validation using Pydantic
- **Technical Approach**:
  - Create `dashboard/backend/protocol/jsonrpc.py` and `daemon/src/protocol/jsonrpc.py` (shared code)
  - Use Pydantic models for message structure validation
  - Standard error codes: -32700 (parse error), -32600 (invalid request), -32601 (method not found), -32603 (internal error)
  - Auto-incrementing request ID generator (thread-safe)
- **Files/Components**:
  - [ ] `dashboard/backend/protocol/__init__.py` - Package init
  - [ ] `dashboard/backend/protocol/jsonrpc.py` - JSON-RPC builders (Dashboard)
  - [ ] `daemon/src/protocol/__init__.py` - Package init
  - [ ] `daemon/src/protocol/jsonrpc.py` - JSON-RPC builders (Daemon)
- **Dependencies**: None
- **Complexity**: S

#### Task 1.2: JSON-RPC Message Parser
- [ ] **Status**: Not Started
- **Description**: Create parser to deserialize and validate incoming JSON-RPC messages.
- **Acceptance Criteria**:
  - [ ] Parses JSON string to Python dict
  - [ ] Validates JSON-RPC 2.0 format
  - [ ] Distinguishes between request, response, notification
  - [ ] Extracts method, params, id, result, error
  - [ ] Returns appropriate error for malformed messages
- **Technical Approach**:
  - Add `parse_message()` function to jsonrpc.py modules
  - Return discriminated union type (Request | Response | Notification | Error)
  - Handle parsing errors gracefully
- **Files/Components**:
  - [ ] `dashboard/backend/protocol/jsonrpc.py` - Add parser
  - [ ] `daemon/src/protocol/jsonrpc.py` - Add parser
- **Dependencies**: Task 1.1
- **Complexity**: S

---

### 2. Dashboard WebSocket Handler

#### Task 2.1: WebSocket Endpoint Setup
- [ ] **Status**: Not Started
- **Description**: Create WebSocket endpoint `/ws/daemon` in Dashboard that accepts daemon connections.
- **Acceptance Criteria**:
  - [ ] WebSocket endpoint at `/ws/daemon` accepts connections
  - [ ] Connection upgrade from HTTP to WebSocket works
  - [ ] Multiple concurrent daemon connections supported
  - [ ] Connection errors handled gracefully
  - [ ] Logging for connection events (connect, disconnect)
- **Technical Approach**:
  - Create FastAPI WebSocket route in `dashboard/backend/api/websocket.py`
  - Use `@app.websocket("/ws/daemon")` decorator
  - Accept connection with `await websocket.accept()`
  - Create async message loop: `async for message in websocket.iter_json()`
  - Handle `WebSocketDisconnect` exception
- **Files/Components**:
  - [ ] `dashboard/backend/api/__init__.py` - Package init
  - [ ] `dashboard/backend/api/websocket.py` - WebSocket handlers
- **Dependencies**: None
- **Complexity**: S

#### Task 2.2: Daemon Registration Handler
- [ ] **Status**: Not Started
- **Description**: Handle initial registration message from daemon when it connects.
- **Acceptance Criteria**:
  - [ ] First message from daemon must be `daemon.register` notification
  - [ ] Extracts machine_id and initial stats from registration
  - [ ] Rejects connections without valid registration
  - [ ] Registers daemon in DaemonManager
  - [ ] Logs successful registration
- **Technical Approach**:
  - First message validation in WebSocket handler
  - Parse `daemon.register` method with params: machine_id, hostname, stats
  - Call `daemon_manager.register(machine_id, websocket)` on success
  - Return error response if registration invalid
- **Files/Components**:
  - [ ] `dashboard/backend/api/websocket.py` - Add registration logic
- **Dependencies**: Task 2.1, Task 3.1
- **Complexity**: S

#### Task 2.3: Message Dispatcher
- [ ] **Status**: Not Started
- **Description**: Route incoming JSON-RPC messages to appropriate handlers based on method.
- **Acceptance Criteria**:
  - [ ] Dispatches to handler based on message method
  - [ ] Handles `stats.report` notifications
  - [ ] Handles `container.status` notifications
  - [ ] Responds to unknown methods with error
  - [ ] Logs all incoming messages (debug level)
- **Technical Approach**:
  - Create `handle_daemon_message(machine_id, message)` async function
  - Use dict mapping method names to handler functions
  - Call appropriate handler with parsed params
  - Send error response for unknown methods
- **Files/Components**:
  - [ ] `dashboard/backend/api/websocket.py` - Add dispatcher
- **Dependencies**: Task 2.2, Task 1.2
- **Complexity**: M

---

### 3. DaemonManager Service

#### Task 3.1: DaemonManager Core
- [ ] **Status**: Not Started
- **Description**: Create DaemonManager to track active daemon connections and send commands.
- **Acceptance Criteria**:
  - [ ] Tracks active daemon WebSocket connections by machine_id
  - [ ] Register/unregister daemons on connect/disconnect
  - [ ] Provides method to get daemon by machine_id
  - [ ] Provides method to list all connected daemons
  - [ ] Thread-safe connection tracking
- **Technical Approach**:
  - Create singleton DaemonManager class in `dashboard/backend/services/daemon_manager.py`
  - Store connections in `dict[str, WebSocket]`
  - Use asyncio locks for thread safety
  - Track connection timestamp and last_seen
- **Files/Components**:
  - [ ] `dashboard/backend/services/__init__.py` - Package init
  - [ ] `dashboard/backend/services/daemon_manager.py` - DaemonManager class
- **Dependencies**: None
- **Complexity**: M

#### Task 3.2: Send Command Methods
- [ ] **Status**: Not Started
- **Description**: Add methods to send JSON-RPC commands to specific daemons.
- **Acceptance Criteria**:
  - [ ] `send_request(machine_id, method, params)` - Send request, wait for response
  - [ ] `send_notification(machine_id, method, params)` - Send notification (no response)
  - [ ] Request timeout handling (30s default)
  - [ ] Tracks pending requests by ID
  - [ ] Returns error if daemon not connected
- **Technical Approach**:
  - Use asyncio.Future for request/response matching
  - Store pending requests: `dict[int, asyncio.Future]`
  - Auto-increment request ID
  - Implement timeout with `asyncio.wait_for()`
  - Send via `websocket.send_json(message)`
- **Files/Components**:
  - [ ] `dashboard/backend/services/daemon_manager.py` - Add send methods
- **Dependencies**: Task 3.1, Task 1.1
- **Complexity**: M

#### Task 3.3: Response Handler
- [ ] **Status**: Not Started
- **Description**: Handle responses from daemons to match with pending requests.
- **Acceptance Criteria**:
  - [ ] Matches response to pending request by ID
  - [ ] Resolves Future with result or error
  - [ ] Cleans up completed request from pending dict
  - [ ] Logs warning for responses with no matching request
- **Technical Approach**:
  - Called from WebSocket message dispatcher when response received
  - Extract ID from response message
  - Look up pending Future, set result
  - Remove from pending dict
- **Files/Components**:
  - [ ] `dashboard/backend/services/daemon_manager.py` - Add response handler
- **Dependencies**: Task 3.2
- **Complexity**: S

---

### 4. Stats Storage to TimescaleDB

#### Task 4.1: Database Schema Creation
- [ ] **Status**: Not Started
- **Description**: Create TimescaleDB hypertables for storing daemon stats.
- **Acceptance Criteria**:
  - [ ] `cpu_stats` hypertable with time, machine_id, cores, load_percent
  - [ ] `gpu_stats` hypertable with time, machine_id, gpu_uuid, gpu_index, memory, utilization, temperature
  - [ ] `memory_stats` hypertable with time, machine_id, total_gb, used_gb, available_gb
  - [ ] `machines` regular table with id, hostname, ip_address, first_seen, last_seen
  - [ ] All hypertables created with `create_hypertable()`
  - [ ] Indexes on machine_id and time
- **Technical Approach**:
  - Create Alembic migration in `dashboard/backend/db/migrations/`
  - Use SQLAlchemy ORM models with TimescaleDB support
  - Set time column as primary key for hypertables
  - Add retention policy (30 days default)
- **Files/Components**:
  - [ ] `dashboard/backend/db/__init__.py` - Package init
  - [ ] `dashboard/backend/db/session.py` - Database session management
  - [ ] `dashboard/backend/db/migrations/versions/001_create_stats_tables.py` - Migration
  - [ ] `dashboard/backend/models/__init__.py` - Package init
  - [ ] `dashboard/backend/models/database.py` - SQLAlchemy models
- **Dependencies**: None
- **Complexity**: M

#### Task 4.2: Stats Storage Service
- [ ] **Status**: Not Started
- **Description**: Service to store stats from daemon reports to TimescaleDB.
- **Acceptance Criteria**:
  - [ ] Parses stats.report params into DB models
  - [ ] Inserts CPU, GPU, memory stats into respective tables
  - [ ] Updates machine last_seen timestamp
  - [ ] Handles database errors gracefully (log and continue)
  - [ ] Batch inserts for efficiency (multiple GPUs)
- **Technical Approach**:
  - Create `StatsStorage` service in `dashboard/backend/services/stats_storage.py`
  - Use async SQLAlchemy session for inserts
  - Parse MachineStats from daemon report
  - Create batch insert for GPU stats (all GPUs in one transaction)
  - Update machine record with upsert (insert or update)
- **Files/Components**:
  - [ ] `dashboard/backend/services/stats_storage.py` - StatsStorage service
- **Dependencies**: Task 4.1
- **Complexity**: M

#### Task 4.3: Stats Report Handler Integration
- [ ] **Status**: Not Started
- **Description**: Integrate stats storage into WebSocket message handler for `stats.report`.
- **Acceptance Criteria**:
  - [ ] WebSocket dispatcher calls StatsStorage on `stats.report`
  - [ ] Stats stored asynchronously (doesn't block WebSocket)
  - [ ] Errors logged but don't crash connection
  - [ ] Stats also sent to ClusterState for in-memory update
- **Technical Approach**:
  - Add handler for `stats.report` in WebSocket dispatcher
  - Call `stats_storage.store(machine_id, stats)` asynchronously
  - Also call `cluster_state.update_machine_stats(machine_id, stats)`
  - Use `asyncio.create_task()` to run storage without blocking
- **Files/Components**:
  - [ ] `dashboard/backend/api/websocket.py` - Add stats.report handler
- **Dependencies**: Task 4.2, Task 5.1
- **Complexity**: S

---

### 5. ClusterState In-Memory Management

#### Task 5.1: ClusterState Data Models
- [ ] **Status**: Not Started
- **Description**: Define Pydantic models for in-memory cluster state.
- **Acceptance Criteria**:
  - [ ] `ClusterState` model with machines dict and running_models dict
  - [ ] `MachineState` model with machine_id, hostname, connected, last_seen, CPU, memory, GPUs, containers
  - [ ] `GPUState` model with index, uuid, name, memory, utilization, temperature, assigned_model
  - [ ] `ContainerState` model with id, model, runtime, gpus, status, uptime
  - [ ] All models use Pydantic for validation
  - [ ] Models support serialization to dict for API responses
- **Technical Approach**:
  - Create dataclasses or Pydantic models in `dashboard/backend/models/schemas.py`
  - Use datetime for timestamps
  - Optional fields for nullable data
  - Add `to_dict()` method for serialization
- **Files/Components**:
  - [ ] `dashboard/backend/models/schemas.py` - Pydantic schemas
- **Dependencies**: None
- **Complexity**: M

#### Task 5.2: ClusterState Service
- [ ] **Status**: Not Started
- **Description**: Create ClusterState service to maintain real-time in-memory cluster state.
- **Acceptance Criteria**:
  - [ ] Singleton service with cluster-wide state
  - [ ] `update_machine_stats(machine_id, stats)` - Update from daemon report
  - [ ] `get_machine(machine_id)` - Get machine state
  - [ ] `get_all_machines()` - List all machines
  - [ ] `mark_machine_offline(machine_id)` - Mark disconnected
  - [ ] Thread-safe state updates
- **Technical Approach**:
  - Create `ClusterState` class in `dashboard/backend/services/cluster_state.py`
  - Use asyncio locks for thread-safe updates
  - Store state in memory (no persistence - rebuilt from daemon reports)
  - Update connected status based on WebSocket connection
- **Files/Components**:
  - [ ] `dashboard/backend/services/cluster_state.py` - ClusterState service
- **Dependencies**: Task 5.1
- **Complexity**: M

#### Task 5.3: Container Status Updates
- [ ] **Status**: Not Started
- **Description**: Handle container status updates from daemons in ClusterState.
- **Acceptance Criteria**:
  - [ ] `update_container_status(machine_id, container_id, status)` method
  - [ ] Updates container state in machine's container list
  - [ ] Supports statuses: starting, running, ready, failed, stopped
  - [ ] Triggers UI update notifications
- **Technical Approach**:
  - Find machine in ClusterState by machine_id
  - Update container in machine's containers list
  - If status is "ready", also update GPU assigned_model
  - Trigger UI notification via UIManager
- **Files/Components**:
  - [ ] `dashboard/backend/services/cluster_state.py` - Add container update method
- **Dependencies**: Task 5.2
- **Complexity**: S

---

### 6. Daemon WebSocket Client

#### Task 6.1: WebSocket Client Core
- [ ] **Status**: Not Started
- **Description**: Create WebSocket client in Daemon to connect to Dashboard.
- **Acceptance Criteria**:
  - [ ] Connects to Dashboard URL from environment variable
  - [ ] Sends initial registration message on connect
  - [ ] Maintains persistent connection
  - [ ] Handles incoming messages from Dashboard
  - [ ] Detects disconnection and triggers reconnection
- **Technical Approach**:
  - Create `WebSocketClient` class in `daemon/src/services/websocket_client.py`
  - Use `websockets` library for client connection
  - Async context manager for connection lifecycle
  - Message loop: `async for message in websocket`
  - Handle `ConnectionClosed` exception
- **Files/Components**:
  - [ ] `daemon/src/services/__init__.py` - Package init
  - [ ] `daemon/src/services/websocket_client.py` - WebSocket client
- **Dependencies**: Task 1.1
- **Complexity**: M

#### Task 6.2: Reconnection with Backoff
- [ ] **Status**: Not Started
- **Description**: Implement exponential backoff with jitter for reconnection attempts.
- **Acceptance Criteria**:
  - [ ] Initial backoff: 1 second
  - [ ] Exponential increase: backoff *= 2
  - [ ] Maximum backoff: 60 seconds
  - [ ] Jitter: +/- 0.5 seconds random
  - [ ] Resets backoff to 1s on successful connection
  - [ ] Infinite reconnection attempts (never give up)
- **Technical Approach**:
  - Wrap connection logic in infinite while loop
  - Catch connection errors, sleep for backoff duration
  - Add `random.uniform(-0.5, 0.5)` jitter to backoff
  - Double backoff on each failure, cap at 60s
  - Reset backoff to 1.0 on successful connect
- **Files/Components**:
  - [ ] `daemon/src/services/websocket_client.py` - Add reconnection logic
- **Dependencies**: Task 6.1
- **Complexity**: M

#### Task 6.3: Registration Message
- [ ] **Status**: Not Started
- **Description**: Send daemon.register notification on connection with machine_id and initial stats.
- **Acceptance Criteria**:
  - [ ] Collects current stats before sending registration
  - [ ] Sends `daemon.register` notification (not request)
  - [ ] Includes machine_id, hostname, stats in params
  - [ ] Logs successful registration
- **Technical Approach**:
  - Call `stats_collector.collect()` before registration
  - Build JSON-RPC notification with method="daemon.register"
  - Include full stats in params
  - Send immediately after WebSocket connection established
- **Files/Components**:
  - [ ] `daemon/src/services/websocket_client.py` - Add registration
- **Dependencies**: Task 6.1, Task 7.1
- **Complexity**: S

#### Task 6.4: Command Handler Dispatcher
- [ ] **Status**: Not Started
- **Description**: Dispatch incoming commands from Dashboard to appropriate handlers.
- **Acceptance Criteria**:
  - [ ] Routes `container.start` to start handler
  - [ ] Routes `container.stop` to stop handler
  - [ ] Sends response back to Dashboard for requests (with ID)
  - [ ] Handles unknown methods with error response
  - [ ] Logs all incoming commands
- **Technical Approach**:
  - Create `_dispatch_command(method, params)` method
  - Use dict mapping methods to handler functions
  - Distinguish requests (have ID) from notifications (no ID)
  - Send response only for requests
  - Log at info level for all commands
- **Files/Components**:
  - [ ] `daemon/src/services/websocket_client.py` - Add dispatcher
- **Dependencies**: Task 6.1, Task 1.2
- **Complexity**: M

---

### 7. Daemon Stats Collection

#### Task 7.1: Stats Collector Service
- [ ] **Status**: Not Started
- **Description**: Create StatsCollector service to gather system metrics.
- **Acceptance Criteria**:
  - [ ] Collects CPU stats (cores, model, load) from /host/proc
  - [ ] Collects memory stats (total, used, available) from /host/proc
  - [ ] Collects GPU stats using pynvml (memory, utilization, temperature, power)
  - [ ] Collects container stats using podman-py
  - [ ] Returns MachineStats object with all metrics
  - [ ] Handles errors gracefully (log and return partial stats)
- **Technical Approach**:
  - Create `StatsCollector` class in `daemon/src/services/stats_collector.py`
  - Read from /host/proc/cpuinfo for CPU details
  - Read from /host/proc/meminfo for memory
  - Use pynvml library for GPU metrics
  - Use podman-py to list containers with label `llm-serve=true`
  - Initialize pynvml once in constructor
- **Files/Components**:
  - [ ] `daemon/src/services/stats_collector.py` - StatsCollector class
  - [ ] `daemon/src/models/__init__.py` - Package init
  - [ ] `daemon/src/models/stats.py` - Stats data models
- **Dependencies**: None
- **Complexity**: L

#### Task 7.2: Network Interface Stats
- [ ] **Status**: Not Started
- **Description**: Collect network interface statistics including link speed and traffic rates.
- **Acceptance Criteria**:
  - [ ] Collects stats for all physical network interfaces (skip virtual/loopback)
  - [ ] Includes interface name, MAC address, IP addresses, link speed, MTU, operational state
  - [ ] Computes bytes sent/received rates from deltas
  - [ ] Handles interfaces without speed info gracefully
  - [ ] Filters out IPv6 link-local addresses
- **Technical Approach**:
  - Read from /sys/class/net/{iface}/ for interface details
  - Use psutil for traffic counters and IP addresses
  - Store previous sample in instance variable for rate calculation
  - Skip interfaces starting with: lo, veth, docker, br-, virbr
- **Files/Components**:
  - [ ] `daemon/src/services/stats_collector.py` - Add network collection
  - [ ] `daemon/src/models/stats.py` - Add NetworkInterfaceStats model
- **Dependencies**: Task 7.1
- **Complexity**: M

#### Task 7.3: GPU Card Manufacturer Detection
- [ ] **Status**: Not Started
- **Description**: Identify GPU card manufacturer (eVGA, MSI, ASUS, etc.) from PCI subsystem vendor.
- **Acceptance Criteria**:
  - [ ] Reads PCI subsystem vendor ID from /sys/bus/pci/devices/
  - [ ] Maps vendor ID to manufacturer name
  - [ ] Supports common manufacturers: eVGA, MSI, ASUS, Gigabyte, PNY, etc.
  - [ ] Returns "Unknown" for unrecognized vendors
  - [ ] Includes vendor ID in unknown case for debugging
- **Technical Approach**:
  - Read from /sys/bus/pci/devices/{pci_bus_id}/subsystem_vendor
  - Create dict mapping vendor IDs to names (0x3842 -> eVGA, etc.)
  - Fall back to "Unknown ({vendor_id})" for unmapped IDs
- **Files/Components**:
  - [ ] `daemon/src/services/stats_collector.py` - Add manufacturer lookup
- **Dependencies**: Task 7.1
- **Complexity**: S

#### Task 7.4: Stats Report Loop
- [ ] **Status**: Not Started
- **Description**: Background task to collect and send stats every 6 seconds.
- **Acceptance Criteria**:
  - [ ] Collects stats every 6 seconds (configurable)
  - [ ] Sends via WebSocket as `stats.report` notification
  - [ ] Continues even if WebSocket disconnected (queues if needed)
  - [ ] Handles collection errors (log and skip interval)
  - [ ] Runs as background asyncio task
- **Technical Approach**:
  - Create `stats_loop()` async function in `daemon/src/main.py`
  - Use `asyncio.sleep(6)` for interval timing
  - Check `websocket_client.connected` before sending
  - Call `stats_collector.collect()` and `websocket_client.send_notification()`
  - Wrap in try/except to handle errors
- **Files/Components**:
  - [ ] `daemon/src/main.py` - Add stats loop
- **Dependencies**: Task 7.1, Task 6.1
- **Complexity**: S

---

### 8. Container Command Stubs

#### Task 8.1: Container Manager Setup
- [ ] **Status**: Not Started
- **Description**: Create ContainerManager service to manage LLM containers via Podman.
- **Acceptance Criteria**:
  - [ ] Initializes podman-py client with socket path
  - [ ] Tracks running containers by model_quant
  - [ ] Provides method to get container by model_quant
  - [ ] Handles Podman socket connection errors gracefully
- **Technical Approach**:
  - Create `ContainerManager` class in `daemon/src/services/container_manager.py`
  - Use `PodmanClient(base_url=f"unix://{socket_path}")`
  - Store running containers: `dict[str, Container]`
  - Initialize in main.py as singleton
- **Files/Components**:
  - [ ] `daemon/src/services/container_manager.py` - ContainerManager class
- **Dependencies**: None
- **Complexity**: S

#### Task 8.2: Container Start Command (Stub)
- [ ] **Status**: Not Started
- **Description**: Implement stub for container.start command that logs params but doesn't actually start container.
- **Acceptance Criteria**:
  - [ ] Receives container.start request with model, runtime, gpus, config params
  - [ ] Logs all parameters at info level
  - [ ] Returns success response with stub container_id and status="starting"
  - [ ] Does NOT actually create/start container (stub only)
  - [ ] Sends container.status notification with status="ready" after 2 seconds
- **Technical Approach**:
  - Create `_handle_start(params)` in WebSocketClient
  - Parse params into ContainerConfig model
  - Log: "Would start container: {model_quant} on GPUs {gpus}"
  - Return `{"container_id": "stub-{model_quant}", "status": "starting"}`
  - Use `asyncio.create_task()` to send "ready" status after 2s delay
- **Files/Components**:
  - [ ] `daemon/src/services/websocket_client.py` - Add start handler
  - [ ] `daemon/src/models/commands.py` - ContainerConfig model
- **Dependencies**: Task 6.4, Task 8.1
- **Complexity**: S

#### Task 8.3: Container Stop Command (Stub)
- [ ] **Status**: Not Started
- **Description**: Implement stub for container.stop command that logs params but doesn't actually stop container.
- **Acceptance Criteria**:
  - [ ] Receives container.stop request with model and evicting params
  - [ ] Logs all parameters at info level
  - [ ] Returns success response with status="stopped"
  - [ ] Does NOT actually stop container (stub only)
- **Technical Approach**:
  - Create `_handle_stop(params)` in WebSocketClient
  - Parse model and evicting flag from params
  - Log: "Would stop container: {model_quant}, evicting={evicting}"
  - Return `{"status": "stopped"}`
- **Files/Components**:
  - [ ] `daemon/src/services/websocket_client.py` - Add stop handler
- **Dependencies**: Task 6.4, Task 8.1
- **Complexity**: S

---

### 9. UI WebSocket Endpoint

#### Task 9.1: UI WebSocket Handler
- [ ] **Status**: Not Started
- **Description**: Create WebSocket endpoint `/ws/ui` for real-time Dashboard UI updates.
- **Acceptance Criteria**:
  - [ ] WebSocket endpoint at `/ws/ui` accepts connections
  - [ ] Supports multiple concurrent UI client connections
  - [ ] Sends initial cluster state snapshot on connect
  - [ ] Keeps connection alive with periodic pings
  - [ ] Handles client disconnect gracefully
- **Technical Approach**:
  - Create WebSocket route in `dashboard/backend/api/websocket.py`
  - Use `@app.websocket("/ws/ui")` decorator
  - Send initial state from ClusterState service
  - Add client to UIManager on connect
  - Remove from UIManager on disconnect
- **Files/Components**:
  - [ ] `dashboard/backend/api/websocket.py` - Add UI WebSocket handler
- **Dependencies**: Task 5.2
- **Complexity**: M

#### Task 9.2: UIManager Service
- [ ] **Status**: Not Started
- **Description**: Service to manage UI client connections and broadcast updates.
- **Acceptance Criteria**:
  - [ ] Tracks all connected UI WebSocket clients
  - [ ] `add_client(websocket)` - Register new UI client
  - [ ] `remove_client(websocket)` - Unregister on disconnect
  - [ ] `broadcast(message)` - Send to all connected clients
  - [ ] Handles errors in client send (remove dead connections)
- **Technical Approach**:
  - Create `UIManager` singleton in `dashboard/backend/services/ui_manager.py`
  - Store clients in list: `list[WebSocket]`
  - Broadcast by iterating clients and calling `websocket.send_json()`
  - Catch send errors and remove failed clients
- **Files/Components**:
  - [ ] `dashboard/backend/services/ui_manager.py` - UIManager service
- **Dependencies**: None
- **Complexity**: M

#### Task 9.3: Update Notifications
- [ ] **Status**: Not Started
- **Description**: Trigger UI updates when cluster state changes.
- **Acceptance Criteria**:
  - [ ] ClusterState notifies UIManager on state changes
  - [ ] UIManager broadcasts updates to all UI clients
  - [ ] Update types: machine_connected, machine_disconnected, stats_updated, container_status_changed
  - [ ] Updates include timestamp and relevant data
- **Technical Approach**:
  - Add callback to ClusterState for state changes
  - Call `ui_manager.broadcast()` with update message
  - Message format: `{"type": "update_type", "data": {...}, "timestamp": "..."}`
  - Throttle stats updates to max 1/second per machine
- **Files/Components**:
  - [ ] `dashboard/backend/services/cluster_state.py` - Add UI notifications
  - [ ] `dashboard/backend/services/ui_manager.py` - Receive and broadcast
- **Dependencies**: Task 9.2, Task 5.2
- **Complexity**: M

---

### 10. Integration and Testing

#### Task 10.1: Dashboard Application Integration
- [ ] **Status**: Not Started
- **Description**: Wire all Dashboard components together in main.py.
- **Acceptance Criteria**:
  - [ ] Initialize all services on startup (DaemonManager, ClusterState, StatsStorage, UIManager)
  - [ ] Register WebSocket routes in FastAPI app
  - [ ] Configure database connection
  - [ ] Set up structured logging
  - [ ] Handle shutdown gracefully (close connections)
- **Technical Approach**:
  - Update `dashboard/backend/main.py` with service initialization
  - Use FastAPI `lifespan` context manager for startup/shutdown
  - Initialize database session pool
  - Create service singletons and store in app.state
- **Files/Components**:
  - [ ] `dashboard/backend/main.py` - Application setup
  - [ ] `dashboard/backend/config.py` - Configuration from environment
- **Dependencies**: All Dashboard tasks
- **Complexity**: M

#### Task 10.2: Daemon Application Integration
- [ ] **Status**: Not Started
- **Description**: Wire all Daemon components together in main.py.
- **Acceptance Criteria**:
  - [ ] Initialize all services on startup (StatsCollector, ContainerManager, WebSocketClient)
  - [ ] Start background tasks (stats loop, health monitoring)
  - [ ] Connect to Dashboard and maintain connection
  - [ ] Handle shutdown gracefully (close WebSocket)
  - [ ] Set up structured logging
- **Technical Approach**:
  - Create `daemon/src/main.py` with async main()
  - Initialize services as globals/singletons
  - Use `asyncio.create_task()` for background tasks
  - Run `websocket_client.connect()` as main blocking task
  - Handle KeyboardInterrupt for clean shutdown
- **Files/Components**:
  - [ ] `daemon/src/main.py` - Application entry point
  - [ ] `daemon/src/config.py` - Configuration from environment
- **Dependencies**: All Daemon tasks
- **Complexity**: M

#### Task 10.3: End-to-End Connection Test
- [ ] **Status**: Not Started
- **Description**: Verify Daemon can connect to Dashboard and exchange messages.
- **Acceptance Criteria**:
  - [ ] Dashboard accepts Daemon connection on `/ws/daemon`
  - [ ] Daemon sends registration and gets registered
  - [ ] Daemon sends stats reports every 6 seconds
  - [ ] Stats appear in Dashboard logs
  - [ ] Stats stored in TimescaleDB
  - [ ] ClusterState shows connected machine
  - [ ] Disconnect/reconnect works with backoff
- **Technical Approach**:
  - Start Dashboard with `uvicorn backend.main:app`
  - Start Daemon with `python -m src.main`
  - Observe logs for connection and stats flow
  - Query database to verify stats storage
  - Kill Dashboard and verify Daemon reconnects
- **Files/Components**:
  - [ ] Manual testing with logs
- **Dependencies**: Task 10.1, Task 10.2
- **Complexity**: M

#### Task 10.4: Command Execution Test
- [ ] **Status**: Not Started
- **Description**: Test sending container start/stop commands from Dashboard to Daemon.
- **Acceptance Criteria**:
  - [ ] Dashboard can send container.start request to Daemon
  - [ ] Daemon receives command and logs params
  - [ ] Daemon sends back success response
  - [ ] Daemon sends container.status notification after delay
  - [ ] Dashboard receives response and status update
  - [ ] Same flow works for container.stop
- **Technical Approach**:
  - Add test endpoint in Dashboard: POST /api/test/start-container
  - Endpoint calls `daemon_manager.send_request(machine_id, "container.start", {...})`
  - Verify response received and logged
  - Verify status notification received
  - Repeat for stop command
- **Files/Components**:
  - [ ] `dashboard/backend/api/control.py` - Add test endpoints
  - [ ] Manual testing with curl/httpie
- **Dependencies**: Task 10.3
- **Complexity**: M

#### Task 10.5: UI WebSocket Test
- [ ] **Status**: Not Started
- **Description**: Test UI WebSocket receives real-time cluster updates.
- **Acceptance Criteria**:
  - [ ] UI client can connect to `/ws/ui`
  - [ ] Receives initial cluster state on connect
  - [ ] Receives updates when daemon connects/disconnects
  - [ ] Receives updates when stats arrive
  - [ ] Multiple UI clients receive same updates
- **Technical Approach**:
  - Create simple HTML/JS test client for WebSocket
  - Connect to `/ws/ui` and log all messages
  - Verify initial state message
  - Start/stop daemon and verify update messages
  - Open multiple browser tabs and verify all receive updates
- **Files/Components**:
  - [ ] `dashboard/backend/static/test-websocket.html` - Test client
- **Dependencies**: Task 9.1, Task 9.2, Task 9.3
- **Complexity**: S

---

## Configuration Requirements

### Dashboard Environment Variables
```bash
# Database
DATABASE_URL=postgresql+asyncpg://llmserve:llmserve@localhost:5432/llmserve

# Server
HOST=0.0.0.0
PORT=8080

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### Daemon Environment Variables
```bash
# Required
DASHBOARD_URL=ws://192.168.0.10:8080/ws/daemon
MACHINE_ID=gpu-server-b   # Auto-generated from hostname if not set

# Paths (for containerized access to host)
PROC_PATH=/host/proc
SYS_PATH=/host/sys
PODMAN_SOCKET=/run/podman/podman.sock

# Intervals
STATS_INTERVAL_SECONDS=6

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

---

## Dependencies

### Dashboard Backend
```
fastapi>=0.104
uvicorn[standard]>=0.24
asyncpg>=0.29
sqlalchemy[asyncio]>=2.0
pydantic>=2.5
websockets>=12.0
alembic>=1.13
structlog>=23.2
```

### Daemon
```
fastapi>=0.104
uvicorn[standard]>=0.24
websockets>=12.0
pynvml>=11.5
psutil>=5.9
podman-py>=4.8
structlog>=23.2
pydantic>=2.5
httpx>=0.25
```

---

## Summary

**Total Tasks**: 33

**By Complexity**:
- Small (S): 14 tasks
- Medium (M): 18 tasks
- Large (L): 1 task
- Extra Large (XL): 0 tasks

**By Category**:
1. JSON-RPC Protocol: 2 tasks
2. Dashboard WebSocket: 3 tasks
3. DaemonManager: 3 tasks
4. Stats Storage: 3 tasks
5. ClusterState: 3 tasks
6. Daemon WebSocket: 4 tasks
7. Stats Collection: 4 tasks
8. Container Commands: 3 tasks
9. UI WebSocket: 3 tasks
10. Integration/Testing: 5 tasks

**Estimated Timeline**: 2-3 weeks for full implementation and testing

**Critical Path**:
1. JSON-RPC helpers (1.1, 1.2)
2. Basic WebSocket endpoints (2.1, 6.1)
3. Connection management (3.1, 6.2, 6.3)
4. Stats flow (7.1, 7.4, 4.2, 4.3, 5.1, 5.2)
5. Command flow (6.4, 8.2, 8.3, 3.2, 3.3)
6. Integration testing (10.1-10.5)

**Risk Areas**:
- TimescaleDB setup and performance (Task 4.1, 4.2)
- WebSocket connection stability under load (Task 6.2)
- Thread safety in concurrent state updates (Task 5.2, 3.1)
- Stats collection performance from /proc and pynvml (Task 7.1)
