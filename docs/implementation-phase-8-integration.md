# Phase 8: Integration & End-to-End - Implementation Plan

## Document Information
- **Related PRD**: [llms-prd.md](./llms-prd.md)
- **Related Architecture**: [architecture-overview.md](./architecture-overview.md), [architecture-dashboard.md](./architecture-dashboard.md), [architecture-daemon.md](./architecture-daemon.md), [architecture-containers.md](./architecture-containers.md)
- **Implementation Overview**: [implementation-overview.md](./implementation-overview.md)
- **Phase**: 8 of 8
- **Created**: 2025-12-23
- **Status**: Not Started
- **Version**: 1.0

---

## Phase Overview

### Goal
Complete end-to-end request flow with eviction, multi-GPU coordination, production deployment, and validation. This phase integrates all previous components into a working system that can handle real production workloads.

### Success Criteria
- [ ] Request → model loads → response streams back (full flow)
- [ ] LRU eviction when GPUs needed (only evicts idle models)
- [ ] Multi-GPU models start correctly with tensor parallelism
- [ ] Dashboard restart recovers state from daemon reports
- [ ] Daemon reconnection works with state re-registration
- [ ] Real cluster deployment validated on multiple machines

### Scope

**Included:**
- LRU eviction logic with idle-only constraint
- GPU capacity management and eviction triggering
- Multi-GPU model coordination (same machine)
- Dashboard state recovery on restart
- Daemon reconnection and re-registration
- End-to-end test scenarios
- Production deployment validation
- Monitoring and health validation
- Known limitations documentation

**Excluded:**
- Multi-machine models (405B spanning 2+ machines) - Future
- Model download from HuggingFace - Phase 2 feature
- Grafana/historical metrics - Phase 3 feature
- Advanced eviction strategies (cost-based, priority) - Future

### Dependencies
- Phase 1: Dev Environment Setup
- Phase 2: Daemon Core
- Phase 3: Dashboard Backend
- Phase 4: WebSocket Communication
- Phase 5: Request Router
- Phase 6: Dashboard Frontend
- Phase 7: Container Library

### Timeline Estimate
- Integration tasks: 2-3 days
- Testing and validation: 2-3 days
- Production deployment: 1-2 days
- **Total: 5-8 days**

---

## Task Breakdown

### 1. LRU Eviction Logic

#### Task 1.1: Implement get_lru_idle_models
- [ ] **Status**: Not Started
- **Description**: Implement method to get idle models sorted by LRU
- **Acceptance Criteria**:
  - [ ] Returns only models with empty queues (no pending requests)
  - [ ] Sorted by last_used timestamp (oldest first)
  - [ ] Excludes models currently processing requests
  - [ ] Returns empty list if no idle models
- **Technical Approach**:
  - Use QueueManager's last_used tracking (updated on request completion)
  - Check QueueManager.is_idle() for each model
  - Filter running models from ClusterState
  - Sort by last_used ascending
- **Files/Components**:
  - [ ] `/data/home/mgreger/proj/llms/dashboard/backend/services/queue_manager.py` - Add get_lru_idle_models() method
  - [ ] `/data/home/mgreger/proj/llms/dashboard/backend/services/cluster_state.py` - Add get_running_models() helper
- **Dependencies**: Phase 5 (QueueManager)
- **Complexity**: M

#### Task 1.2: Implement evict_model method
- [ ] **Status**: Not Started
- **Description**: Safely evict a model from the cluster
- **Acceptance Criteria**:
  - [ ] Only evicts if model queue is empty (assert check)
  - [ ] Marks queue as "blocked" during eviction
  - [ ] Sends container.stop command to daemon with evicting=true flag
  - [ ] Waits for daemon confirmation before marking GPUs free
  - [ ] Queue remains blocked until model reloaded (prevents thrashing)
  - [ ] Logs eviction event to database
- **Technical Approach**:
  - Add "blocked" state to queue status
  - Send JSON-RPC container.stop with {"evicting": true}
  - Update ClusterState to mark GPUs as "transitioning"
  - Wait for daemon container.status notification
  - Keep queue structure alive (don't destroy)
- **Files/Components**:
  - [ ] `/data/home/mgreger/proj/llms/dashboard/backend/services/model_router.py` - Add evict_model() method
  - [ ] `/data/home/mgreger/proj/llms/dashboard/backend/services/queue_manager.py` - Add block_queue()/unblock_queue()
  - [ ] `/data/home/mgreger/proj/llms/dashboard/backend/api/websocket.py` - Handle container.status for eviction
- **Dependencies**: Task 1.1
- **Complexity**: L

#### Task 1.3: Add eviction protection for newly loaded models
- [ ] **Status**: Not Started
- **Description**: Prevent eviction of models that just loaded and haven't processed the triggering request
- **Acceptance Criteria**:
  - [ ] Model marked as "protected" when loading starts
  - [ ] Protection removed after first request completes
  - [ ] Protected models excluded from get_lru_idle_models()
  - [ ] Protection timeout (5 min) in case request fails
- **Technical Approach**:
  - Add "protected_until" timestamp to model state
  - Set protection when container.start sent
  - Remove protection on first request completion
  - Timeout protection after 5 minutes
  - Filter protected models in get_lru_idle_models()
- **Files/Components**:
  - [ ] `/data/home/mgreger/proj/llms/dashboard/backend/services/cluster_state.py` - Add protection tracking
  - [ ] `/data/home/mgreger/proj/llms/dashboard/backend/services/model_router.py` - Set/clear protection
- **Dependencies**: Task 1.2
- **Complexity**: M

### 2. GPU Capacity Management

#### Task 2.1: Implement ensure_capacity method
- [ ] **Status**: Not Started
- **Description**: Ensure sufficient GPU capacity available, evicting LRU models if needed
- **Acceptance Criteria**:
  - [ ] Calculates total VRAM required from container config
  - [ ] Identifies machines with available GPUs
  - [ ] Prefers single machine when possible
  - [ ] Evicts LRU idle models until capacity met
  - [ ] Returns list of machines/GPUs allocated
  - [ ] Raises exception if capacity cannot be met (all models busy)
  - [ ] Marks GPUs as "reserved" during transition
- **Technical Approach**:
  - Query ClusterState for free GPUs (memory_used_gb < threshold)
  - Try single-machine allocation first
  - If insufficient, calculate eviction candidates via get_lru_idle_models()
  - Evict models one at a time until capacity met
  - Mark allocated GPUs as reserved
  - Return allocation plan (machine_id, gpu_indices)
- **Files/Components**:
  - [ ] `/data/home/mgreger/proj/llms/dashboard/backend/services/model_router.py` - Add ensure_capacity() method
  - [ ] `/data/home/mgreger/proj/llms/dashboard/backend/models/schemas.py` - Add AllocationPlan schema
- **Dependencies**: Task 1.1, Task 1.2
- **Complexity**: XL

#### Task 2.2: Add capacity timeout and error handling
- [ ] **Status**: Not Started
- **Description**: Handle cases where capacity cannot be met
- **Acceptance Criteria**:
  - [ ] Timeout after configurable period (default 5 min)
  - [ ] Return error to client if timeout exceeded
  - [ ] Log capacity wait events
  - [ ] Provide helpful error messages (e.g., "All GPUs busy, try again later")
  - [ ] Clean up reserved state on timeout
- **Technical Approach**:
  - Add wait loop in ensure_capacity with timeout
  - Poll for capacity every 10s
  - Track wait time and log
  - Raise CapacityTimeoutError after timeout
  - Handle error in router, return 503 to client
- **Files/Components**:
  - [ ] `/data/home/mgreger/proj/llms/dashboard/backend/services/model_router.py` - Add timeout logic
  - [ ] `/data/home/mgreger/proj/llms/dashboard/backend/api/router.py` - Handle CapacityTimeoutError
- **Dependencies**: Task 2.1
- **Complexity**: M

### 3. Multi-GPU Coordination

#### Task 3.1: Implement GPU selection for multi-GPU models
- [ ] **Status**: Not Started
- **Description**: Select appropriate GPUs for multi-GPU models on same machine
- **Acceptance Criteria**:
  - [ ] Selects contiguous GPU indices when possible (better NCCL performance)
  - [ ] Verifies all selected GPUs have sufficient VRAM
  - [ ] Prefers GPUs with similar specs (memory, model)
  - [ ] Returns GPU indices in order
  - [ ] Handles case where contiguous GPUs unavailable
- **Technical Approach**:
  - Query ClusterState for machine's GPUs
  - Sort by index, filter by available memory
  - Attempt contiguous range first (e.g., [0,1,2,3])
  - Fall back to non-contiguous if needed
  - Verify total VRAM meets requirement
- **Files/Components**:
  - [ ] `/data/home/mgreger/proj/llms/dashboard/backend/services/model_router.py` - Add select_gpus_for_model() method
- **Dependencies**: Task 2.1
- **Complexity**: M

#### Task 3.2: Implement tensor parallel container startup
- [ ] **Status**: Not Started
- **Description**: Start multi-GPU container with tensor parallelism
- **Acceptance Criteria**:
  - [ ] Generates vLLM command with correct --tensor-parallel-size
  - [ ] Sets CUDA_VISIBLE_DEVICES to selected GPUs
  - [ ] Sets NCCL environment variables for multi-GPU communication
  - [ ] Waits for health check on single endpoint
  - [ ] Verifies all GPUs loaded via daemon stats
- **Technical Approach**:
  - Use ContainerCommandGenerator with TP config
  - Pass gpu_indices to daemon in container.start
  - Daemon sets CUDA_VISIBLE_DEVICES, NCCL_DEBUG
  - vLLM initializes TP across specified GPUs
  - Health monitor polls until ready
- **Files/Components**:
  - [ ] `/data/home/mgreger/proj/llms/dashboard/backend/services/model_router.py` - Multi-GPU start logic
  - [ ] `/data/home/mgreger/proj/llms/daemon/src/services/container_manager.py` - Multi-GPU device setup
- **Dependencies**: Task 3.1, Phase 7 (Container Library)
- **Complexity**: L

#### Task 3.3: Add multi-GPU eviction coordination
- [ ] **Status**: Not Started
- **Description**: Evict multi-GPU models cleanly, freeing all GPUs
- **Acceptance Criteria**:
  - [ ] Single evict_model() call handles multi-GPU models
  - [ ] All GPUs freed atomically
  - [ ] Container stop waits for all GPU memory released
  - [ ] Stats reflect all GPUs freed after eviction
- **Technical Approach**:
  - Track which GPUs assigned to each model in ClusterState
  - On eviction, mark all GPUs as transitioning
  - Container stop releases all GPU assignments
  - Daemon reports updated GPU stats with freed memory
- **Files/Components**:
  - [ ] `/data/home/mgreger/proj/llms/dashboard/backend/services/model_router.py` - Multi-GPU eviction
  - [ ] `/data/home/mgreger/proj/llms/dashboard/backend/services/cluster_state.py` - Track GPU assignments
- **Dependencies**: Task 3.2, Task 1.2
- **Complexity**: M

### 4. Dashboard State Recovery

#### Task 4.1: Implement state rebuild from daemon reports
- [ ] **Status**: Not Started
- **Description**: Rebuild ClusterState on Dashboard restart from daemon stats
- **Acceptance Criteria**:
  - [ ] Dashboard waits for daemon connections on startup
  - [ ] Processes daemon.register messages with current state
  - [ ] Rebuilds running_models map from container reports
  - [ ] Recreates GPU assignments from container labels
  - [ ] Marks machines online as they reconnect
  - [ ] Queues start empty (in-flight requests lost, clients retry)
- **Technical Approach**:
  - On startup, ClusterState starts empty
  - WebSocket handler accepts daemon.register notifications
  - Parse container stats from registration payload
  - Rebuild running_models from container labels
  - Update GPU states from stats
  - Log recovery progress
- **Files/Components**:
  - [ ] `/data/home/mgreger/proj/llms/dashboard/backend/services/cluster_state.py` - Add rebuild_from_daemon() method
  - [ ] `/data/home/mgreger/proj/llms/dashboard/backend/api/websocket.py` - Handle daemon.register
  - [ ] `/data/home/mgreger/proj/llms/dashboard/backend/main.py` - Startup sequence
- **Dependencies**: Phase 4 (WebSocket)
- **Complexity**: L

#### Task 4.2: Add graceful queue handling during restart
- [ ] **Status**: Not Started
- **Description**: Handle in-flight requests gracefully during Dashboard restart
- **Acceptance Criteria**:
  - [ ] In-flight requests receive connection error
  - [ ] Queue state not persisted (intentional - clients retry)
  - [ ] New requests after restart work immediately
  - [ ] No zombie queues left from pre-restart requests
- **Technical Approach**:
  - QueueManager.queues starts empty on restart
  - Client connections drop during restart (SSE closes)
  - Clients retry requests (standard HTTP behavior)
  - New queues created on demand for new requests
  - Document expected behavior in PRD appendix
- **Files/Components**:
  - [ ] `/data/home/mgreger/proj/llms/dashboard/backend/services/queue_manager.py` - Reset on startup
  - [ ] Document restart behavior in `/data/home/mgreger/proj/llms/docs/llms-prd.md` appendix
- **Dependencies**: Task 4.1
- **Complexity**: S

#### Task 4.3: Add state recovery validation
- [ ] **Status**: Not Started
- **Description**: Validate recovered state matches reality
- **Acceptance Criteria**:
  - [ ] Compare recovered GPU assignments to actual container GPU usage
  - [ ] Log any mismatches as warnings
  - [ ] Provide manual reconciliation command if needed
  - [ ] Test with pre-existing containers running
- **Technical Approach**:
  - After rebuild, compare ClusterState to latest daemon stats
  - Check container GPU labels vs reported GPU memory usage
  - Log discrepancies
  - Add /api/admin/reconcile endpoint for manual fix
- **Files/Components**:
  - [ ] `/data/home/mgreger/proj/llms/dashboard/backend/services/cluster_state.py` - Add validate() method
  - [ ] `/data/home/mgreger/proj/llms/dashboard/backend/api/control.py` - Add /api/admin/reconcile
- **Dependencies**: Task 4.1
- **Complexity**: M

### 5. Daemon Reconnection Handling

#### Task 5.1: Implement daemon re-registration protocol
- [ ] **Status**: Not Started
- **Description**: Handle daemon reconnection with state re-registration
- **Acceptance Criteria**:
  - [ ] Daemon sends daemon.register on every connection
  - [ ] Registration includes current container state
  - [ ] Dashboard merges new state with existing ClusterState
  - [ ] Old connection for same machine_id replaced
  - [ ] Reconnection logged with duration offline
- **Technical Approach**:
  - Daemon sends daemon.register as first message (already in Phase 4)
  - Dashboard DaemonManager checks for existing machine_id
  - Close old WebSocket connection if exists
  - Register new connection
  - Call ClusterState.update_machine() with new stats
  - Log "machine_reconnected" event
- **Files/Components**:
  - [ ] `/data/home/mgreger/proj/llms/dashboard/backend/services/daemon_manager.py` - Handle re-registration
  - [ ] `/data/home/mgreger/proj/llms/daemon/src/services/websocket_client.py` - Ensure register on connect
- **Dependencies**: Phase 4 (WebSocket), Task 4.1
- **Complexity**: M

#### Task 5.2: Add offline detection and marking
- [ ] **Status**: Not Started
- **Description**: Detect daemon disconnections and mark machines offline
- **Acceptance Criteria**:
  - [ ] WebSocket disconnect marks machine as offline
  - [ ] Timeout (30s no stats) also marks offline
  - [ ] Offline machines excluded from routing decisions
  - [ ] Models on offline machines marked unavailable
  - [ ] UI shows offline status clearly
- **Technical Approach**:
  - WebSocket handler catches disconnect events
  - Set machine.connected = false in ClusterState
  - Background task checks last_seen timestamps
  - Mark offline if no stats for 30s
  - ModelRouter skips offline machines
- **Files/Components**:
  - [ ] `/data/home/mgreger/proj/llms/dashboard/backend/services/daemon_manager.py` - Disconnect handling
  - [ ] `/data/home/mgreger/proj/llms/dashboard/backend/services/cluster_state.py` - Offline tracking
  - [ ] `/data/home/mgreger/proj/llms/dashboard/backend/main.py` - Add timeout check task
- **Dependencies**: Task 5.1
- **Complexity**: M

#### Task 5.3: Test daemon restart scenarios
- [ ] **Status**: Not Started
- **Description**: Validate daemon restart and reconnection works correctly
- **Acceptance Criteria**:
  - [ ] Daemon restart with running containers preserves state
  - [ ] Dashboard sees containers still running after daemon reconnect
  - [ ] New requests route to pre-existing containers
  - [ ] Daemon crash and auto-restart works (systemd)
- **Technical Approach**:
  - Start model on daemon
  - Restart daemon container
  - Verify Dashboard shows machine offline then back online
  - Verify container still appears in stats
  - Send new request, verify routing works
- **Files/Components**:
  - [ ] Test script: `/data/home/mgreger/proj/llms/tests/integration/test_daemon_reconnect.sh`
- **Dependencies**: Task 5.2
- **Complexity**: M

### 6. End-to-End Test Scenarios

#### Task 6.1: Test single-GPU model flow
- [ ] **Status**: Not Started
- **Description**: Validate complete flow for single-GPU model
- **Acceptance Criteria**:
  - [ ] Request received for model not loaded
  - [ ] Model auto-loads on available GPU
  - [ ] Response streams back to client
  - [ ] Model stays loaded for subsequent requests
  - [ ] Multiple concurrent requests handled correctly
- **Technical Approach**:
  - Send request to /v1/chat/completions for single-GPU model
  - Monitor Dashboard logs for load sequence
  - Verify container starts via daemon
  - Capture SSE stream
  - Send second request, verify no reload
  - Send 5 concurrent requests, verify all succeed
- **Files/Components**:
  - [ ] Test script: `/data/home/mgreger/proj/llms/tests/integration/test_single_gpu_flow.py`
  - [ ] Test client: `/data/home/mgreger/proj/llms/tests/utils/llm_client.py`
- **Dependencies**: All previous phases
- **Complexity**: M

#### Task 6.2: Test multi-GPU model flow
- [ ] **Status**: Not Started
- **Description**: Validate complete flow for multi-GPU model with tensor parallelism
- **Acceptance Criteria**:
  - [ ] Request for 2-GPU model allocates both GPUs
  - [ ] vLLM starts with correct tensor-parallel-size
  - [ ] Model loads across both GPUs (verified in stats)
  - [ ] Response streams correctly
  - [ ] Both GPUs show memory usage in Dashboard
- **Technical Approach**:
  - Configure 2-GPU model (e.g., Qwen 72B AWQ)
  - Send request
  - Monitor GPU stats for both GPUs
  - Verify container command includes --tensor-parallel-size 2
  - Check response quality (tokens look correct)
- **Files/Components**:
  - [ ] Test script: `/data/home/mgreger/proj/llms/tests/integration/test_multi_gpu_flow.py`
- **Dependencies**: Task 3.2
- **Complexity**: L

#### Task 6.3: Test eviction flow
- [ ] **Status**: Not Started
- **Description**: Validate LRU eviction when GPUs needed
- **Acceptance Criteria**:
  - [ ] Load models until all GPUs full
  - [ ] Request for new model triggers eviction of LRU idle model
  - [ ] New model loads on freed GPUs
  - [ ] Evicted model can be re-requested (reloads)
  - [ ] Models with pending requests not evicted
- **Technical Approach**:
  - Load 4 single-GPU models on 4-GPU machine
  - Wait for all idle
  - Send request for 5th model
  - Verify LRU model evicted (check logs)
  - Verify new model loads
  - Send request for evicted model, verify reload
  - Send concurrent requests to 2 models, request 3rd
  - Verify only truly idle model evicted
- **Files/Components**:
  - [ ] Test script: `/data/home/mgreger/proj/llms/tests/integration/test_eviction.py`
- **Dependencies**: Task 1.2, Task 2.1
- **Complexity**: L

#### Task 6.4: Test Dashboard restart
- [ ] **Status**: Not Started
- **Description**: Validate state recovery after Dashboard restart
- **Acceptance Criteria**:
  - [ ] Models running before restart still available after
  - [ ] Dashboard rebuilds state from daemon reports
  - [ ] New requests route correctly after restart
  - [ ] In-flight requests during restart receive errors
- **Technical Approach**:
  - Start 2 models
  - Restart Dashboard container
  - Verify Dashboard logs show state rebuild
  - Send requests to both models, verify routing works
  - Check UI shows correct state
- **Files/Components**:
  - [ ] Test script: `/data/home/mgreger/proj/llms/tests/integration/test_dashboard_restart.py`
- **Dependencies**: Task 4.1
- **Complexity**: M

#### Task 6.5: Test capacity timeout
- [ ] **Status**: Not Started
- **Description**: Validate timeout when capacity unavailable
- **Acceptance Criteria**:
  - [ ] Request for model when all GPUs busy receives timeout error
  - [ ] Error message is helpful
  - [ ] Request queued for short period before timeout
  - [ ] Subsequent request succeeds when capacity available
- **Technical Approach**:
  - Fill all GPUs with models processing long requests
  - Send request for new model
  - Verify waits for capacity
  - After timeout, verify 503 error returned
  - Complete long requests, send new request
  - Verify succeeds
- **Files/Components**:
  - [ ] Test script: `/data/home/mgreger/proj/llms/tests/integration/test_capacity_timeout.py`
- **Dependencies**: Task 2.2
- **Complexity**: M

### 7. Production Deployment

#### Task 7.1: Create production deployment guide
- [ ] **Status**: Not Started
- **Description**: Document production deployment steps
- **Acceptance Criteria**:
  - [ ] Step-by-step deployment instructions
  - [ ] Prerequisites checklist (NVIDIA drivers, Podman, etc.)
  - [ ] Network configuration requirements
  - [ ] Firewall rules documented
  - [ ] Systemd service files provided
  - [ ] Troubleshooting section
- **Technical Approach**:
  - Document in /data/home/mgreger/proj/llms/docs/deployment-guide.md
  - Cover Dashboard deployment
  - Cover Daemon deployment on each GPU machine
  - Include verification steps
  - Provide sample configurations
- **Files/Components**:
  - [ ] `/data/home/mgreger/proj/llms/docs/deployment-guide.md` - New deployment guide
  - [ ] `/data/home/mgreger/proj/llms/systemd/llm-serve-dashboard.service` - Systemd service
  - [ ] `/data/home/mgreger/proj/llms/systemd/llm-serve-daemon.service` - Systemd service
- **Dependencies**: None
- **Complexity**: M

#### Task 7.2: Deploy to first production machine
- [ ] **Status**: Not Started
- **Description**: Deploy Dashboard and first Daemon to production hardware
- **Acceptance Criteria**:
  - [ ] Dashboard container running on control machine
  - [ ] Daemon container running on first GPU machine
  - [ ] WebSocket connection established
  - [ ] Stats flowing from daemon to dashboard
  - [ ] UI accessible on local network
  - [ ] Test request succeeds
- **Technical Approach**:
  - Build Dashboard container image
  - Deploy to control machine with systemd
  - Build Daemon container image
  - Deploy to GPU machine with systemd
  - Configure NFS mounts
  - Test connectivity
  - Send test inference request
- **Files/Components**:
  - Production machines, systemd services, containers
- **Dependencies**: Task 7.1, all previous phases
- **Complexity**: L

#### Task 7.3: Deploy to remaining machines
- [ ] **Status**: Not Started
- **Description**: Roll out Daemon to all GPU machines
- **Acceptance Criteria**:
  - [ ] Daemon running on all 3+ machines
  - [ ] All machines visible in Dashboard UI
  - [ ] Stats from all machines displayed
  - [ ] Models can be routed to any machine
  - [ ] Multi-machine deployment working
- **Technical Approach**:
  - Deploy Daemon container to each machine
  - Configure unique MACHINE_ID for each
  - Verify all connect to Dashboard
  - Check UI shows all machines
  - Test model loading on each machine
- **Files/Components**:
  - Production machines
- **Dependencies**: Task 7.2
- **Complexity**: M

#### Task 7.4: Load production models
- [ ] **Status**: Not Started
- **Description**: Configure and load production LLM models
- **Acceptance Criteria**:
  - [ ] At least 3 models configured (small, medium, large)
  - [ ] Models downloaded to NFS storage
  - [ ] Container configs created in database
  - [ ] Test requests to each model succeed
  - [ ] Models appear in UI inventory
- **Technical Approach**:
  - Download models to /data/projects/ai/models (e.g., Qwen 7B, 32B, 72B)
  - Register models in database
  - Create launch configs
  - Test each model via router
  - Verify in UI
- **Files/Components**:
  - NFS storage, database
- **Dependencies**: Task 7.3
- **Complexity**: M

### 8. Monitoring and Validation

#### Task 8.1: Add monitoring endpoints
- [ ] **Status**: Not Started
- **Description**: Expose Prometheus-compatible metrics
- **Acceptance Criteria**:
  - [ ] /metrics endpoint returns Prometheus format
  - [ ] Metrics include: active models, GPU utilization, request counts, latencies
  - [ ] Daemon exposes local /metrics
  - [ ] Dashboard aggregates cluster metrics
- **Technical Approach**:
  - Add prometheus_client library
  - Expose metrics in FastAPI
  - Track request counters, histograms
  - Expose GPU stats as gauges
  - Document metrics in deployment guide
- **Files/Components**:
  - [ ] `/data/home/mgreger/proj/llms/dashboard/backend/services/metrics.py` - Prometheus metrics
  - [ ] `/data/home/mgreger/proj/llms/dashboard/backend/main.py` - Add /metrics endpoint
  - [ ] `/data/home/mgreger/proj/llms/daemon/src/main.py` - Add /metrics endpoint
- **Dependencies**: None
- **Complexity**: M

#### Task 8.2: Create validation test suite
- [ ] **Status**: Not Started
- **Description**: Automated test suite for production validation
- **Acceptance Criteria**:
  - [ ] Script validates all components running
  - [ ] Checks WebSocket connections
  - [ ] Sends test inference requests
  - [ ] Validates response quality
  - [ ] Reports health status
  - [ ] Can be run on schedule (e.g., hourly)
- **Technical Approach**:
  - Create validation.py script
  - Check /health on Dashboard and all Daemons
  - Verify stats collection working
  - Send test requests to representative models
  - Parse responses, check for errors
  - Exit 0 if all pass, 1 if any fail
- **Files/Components**:
  - [ ] `/data/home/mgreger/proj/llms/scripts/validate_cluster.py` - Validation script
- **Dependencies**: Task 7.3
- **Complexity**: M

#### Task 8.3: Monitor production deployment
- [ ] **Status**: Not Started
- **Description**: Monitor production system for 48 hours
- **Acceptance Criteria**:
  - [ ] No crashes or unexpected restarts
  - [ ] Eviction works as expected
  - [ ] Response times acceptable
  - [ ] Memory usage stable
  - [ ] No errors in logs
  - [ ] All machines stay connected
- **Technical Approach**:
  - Deploy to production
  - Run validation suite every hour
  - Monitor Dashboard and Daemon logs
  - Send periodic inference requests
  - Check GPU stats for stability
  - Document any issues found
- **Files/Components**:
  - Production monitoring
- **Dependencies**: Task 7.4, Task 8.2
- **Complexity**: S (passive monitoring)

### 9. Known Limitations Documentation

#### Task 9.1: Document Phase 1 limitations
- [ ] **Status**: Not Started
- **Description**: Document known limitations of Phase 1 MVP
- **Acceptance Criteria**:
  - [ ] Clear list of limitations
  - [ ] Workarounds provided where applicable
  - [ ] Future enhancement roadmap referenced
  - [ ] Performance characteristics documented
- **Technical Approach**:
  - Create limitations.md document
  - List features explicitly NOT included
  - Document performance baselines
  - Note edge cases and workarounds
  - Link to Phase 2/3 plans
- **Files/Components**:
  - [ ] `/data/home/mgreger/proj/llms/docs/limitations-phase1.md` - New limitations doc
- **Dependencies**: None
- **Complexity**: S

#### Task 9.2: Document known issues
- [ ] **Status**: Not Started
- **Description**: Track and document any known issues or bugs
- **Acceptance Criteria**:
  - [ ] Known issues listed with severity
  - [ ] Reproduction steps provided
  - [ ] Workarounds documented
  - [ ] Issues linked to GitHub issues (if applicable)
- **Technical Approach**:
  - Create known-issues.md
  - Document issues found during testing
  - Include workarounds
  - Update as issues resolved
- **Files/Components**:
  - [ ] `/data/home/mgreger/proj/llms/docs/known-issues.md` - New known issues doc
- **Dependencies**: Task 8.3
- **Complexity**: S

---

## Technical Design Details

### LRU Eviction Algorithm

```python
class QueueManager:
    def get_lru_idle_models(self) -> list[str]:
        """
        Get idle models sorted by LRU.

        A model is idle if:
        - Queue exists (model has been loaded)
        - Queue is empty (no pending requests)
        - Active count is 0 (no requests being processed)
        - Model is not protected (has processed at least one request)
        """
        idle_models = []

        for model_quant, queue in self.queues.items():
            if self.is_idle(model_quant):
                # Check if protected
                if not cluster_state.is_protected(model_quant):
                    idle_models.append((model_quant, self.last_used[model_quant]))

        # Sort by last_used ascending (oldest first)
        idle_models.sort(key=lambda x: x[1])

        return [model for model, _ in idle_models]

    def is_idle(self, model_quant: str) -> bool:
        """True if queue empty and no requests in-flight."""
        if model_quant not in self.queues:
            return False
        return (
            self.queues[model_quant].empty() and
            self.active_counts.get(model_quant, 0) == 0
        )
```

### Capacity Allocation Algorithm

```python
class ModelRouter:
    async def ensure_capacity(
        self,
        vram_required_gb: float,
        gpu_count: int,
        prefer_machine: str | None = None
    ) -> AllocationPlan:
        """
        Ensure GPU capacity available, evicting if needed.

        Returns:
            AllocationPlan with machine_id and gpu_indices

        Raises:
            CapacityTimeoutError if capacity cannot be met
        """
        start_time = time.time()
        timeout = config.capacity_timeout_seconds

        while time.time() - start_time < timeout:
            # Try to find free GPUs
            allocation = self._find_free_gpus(vram_required_gb, gpu_count, prefer_machine)
            if allocation:
                # Mark GPUs as reserved
                await cluster_state.reserve_gpus(allocation)
                return allocation

            # No capacity - try eviction
            idle_models = queue_manager.get_lru_idle_models()
            if not idle_models:
                # All models busy, wait and retry
                await asyncio.sleep(10)
                continue

            # Evict LRU model
            lru_model = idle_models[0]
            logger.info("evicting_lru_model", model=lru_model, reason="capacity_needed")
            await self.evict_model(lru_model)

            # Retry after eviction
            continue

        # Timeout exceeded
        raise CapacityTimeoutError(
            f"Could not allocate {gpu_count} GPUs with {vram_required_gb}GB VRAM "
            f"after {timeout}s. All models busy."
        )

    def _find_free_gpus(
        self,
        vram_required_gb: float,
        gpu_count: int,
        prefer_machine: str | None
    ) -> AllocationPlan | None:
        """Find free GPUs meeting requirements."""
        machines = cluster_state.get_online_machines()

        # Try preferred machine first
        if prefer_machine:
            machine = cluster_state.get_machine(prefer_machine)
            if machine:
                gpus = self._select_gpus_on_machine(machine, vram_required_gb, gpu_count)
                if gpus:
                    return AllocationPlan(machine_id=machine.id, gpu_indices=gpus)

        # Try all machines
        for machine in machines:
            gpus = self._select_gpus_on_machine(machine, vram_required_gb, gpu_count)
            if gpus:
                return AllocationPlan(machine_id=machine.id, gpu_indices=gpus)

        return None

    def _select_gpus_on_machine(
        self,
        machine: MachineState,
        vram_required_gb: float,
        gpu_count: int
    ) -> list[int] | None:
        """Select GPUs on a specific machine."""
        # Filter GPUs with sufficient free VRAM
        free_gpus = [
            gpu for gpu in machine.gpus
            if (gpu.memory_total_gb - gpu.memory_used_gb) >= vram_required_gb / gpu_count
        ]

        if len(free_gpus) < gpu_count:
            return None

        # Prefer contiguous indices
        free_gpus.sort(key=lambda g: g.index)
        indices = [g.index for g in free_gpus]

        # Check for contiguous range
        for i in range(len(indices) - gpu_count + 1):
            if indices[i:i+gpu_count] == list(range(indices[i], indices[i] + gpu_count)):
                return indices[i:i+gpu_count]

        # Fall back to non-contiguous
        return indices[:gpu_count]
```

### State Recovery Flow

```
Dashboard Startup:
1. Load configuration from database
2. Initialize ClusterState (empty)
3. Start WebSocket server
4. Wait for daemon connections

Daemon Connection:
1. Daemon connects to /ws/daemon
2. Sends daemon.register with current stats
3. Dashboard processes:
   - Update machines table
   - Parse container stats
   - Rebuild running_models map
   - Update GPU assignments
4. Dashboard sends acknowledgment
5. Normal stats reporting begins

State Validation:
1. After 30s (all daemons likely connected)
2. Compare ClusterState to database
3. Log any discrepancies
4. Ready for requests
```

---

## Testing Strategy

### Integration Tests

1. **Single-GPU Flow** - Basic request to single-GPU model
2. **Multi-GPU Flow** - Request to model spanning 2 GPUs
3. **Eviction Flow** - Fill GPUs, trigger eviction, verify LRU evicted
4. **Concurrent Requests** - Multiple simultaneous requests to different models
5. **Dashboard Restart** - Restart with models running, verify recovery
6. **Daemon Restart** - Restart daemon, verify reconnection
7. **Capacity Timeout** - Request when all GPUs busy, verify timeout

### Manual Testing Checklist

- [ ] Load single-GPU model, send request, verify response
- [ ] Load multi-GPU model, verify both GPUs used
- [ ] Fill all GPUs, request new model, verify eviction
- [ ] Restart Dashboard, verify models still available
- [ ] Restart Daemon, verify reconnects and models preserved
- [ ] Check UI shows all machines and models
- [ ] Send concurrent requests, verify all succeed
- [ ] Monitor logs for errors
- [ ] Check GPU memory usage in UI matches nvidia-smi
- [ ] Verify metrics endpoint returns data

### Performance Validation

- [ ] Routing overhead <20ms (log timestamp at each stage)
- [ ] Model loading completes in expected time (varies by size)
- [ ] Eviction completes within 30s
- [ ] Stats collection every 6s (verify in logs)
- [ ] WebSocket reconnection <5s

---

## Deployment Checklist

### Prerequisites (Each Machine)

- [ ] Fedora 43 installed
- [ ] NVIDIA drivers installed (525+)
- [ ] nvidia-container-toolkit installed and configured
- [ ] Podman installed (4.0+)
- [ ] Podman socket enabled (systemd)
- [ ] NFS client installed
- [ ] NFS mount configured (/data/projects/ai/models)
- [ ] Network connectivity to Dashboard
- [ ] Firewall allows port 8080 (Dashboard)

### Dashboard Machine

- [ ] TimescaleDB accessible (or embedded)
- [ ] Dashboard container built
- [ ] Configuration file created
- [ ] Environment variables set
- [ ] Systemd service installed
- [ ] Dashboard started and healthy
- [ ] UI accessible on http://192.168.0.x:8080

### GPU Machines

- [ ] Daemon container built
- [ ] Configuration file created
- [ ] Environment variables set (DASHBOARD_URL)
- [ ] Systemd service installed
- [ ] Daemon started and healthy
- [ ] WebSocket connected to Dashboard
- [ ] Stats appearing in Dashboard UI

### Post-Deployment

- [ ] All machines visible in UI
- [ ] GPU stats updating every 6s
- [ ] Test model loaded successfully
- [ ] Test request completed successfully
- [ ] Logs clean (no errors)
- [ ] Metrics endpoint accessible
- [ ] Validation script passes

---

## Known Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Race condition in eviction | Medium | High | Careful state locking, extensive testing |
| State recovery incomplete | Low | Medium | Validation checks, manual reconciliation endpoint |
| Multi-GPU NCCL errors | Medium | Medium | Proper NCCL configuration, network verification |
| Capacity thrashing | Low | Medium | Protection periods, queue blocking |
| Production hardware issues | Low | High | Incremental rollout, validation suite |

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Request success rate | >99% | Monitoring logs |
| Eviction correctness | 100% | Never evict busy model |
| State recovery completeness | 100% | All running models recovered |
| Routing latency | <20ms | Log timestamps |
| Uptime | >99.9% | 48-hour monitoring |
| Zero unexpected crashes | 100% | Log monitoring |

---

## Task Summary

| Category | Task Count | Complexity Breakdown |
|----------|------------|---------------------|
| LRU Eviction Logic | 3 | S:0, M:2, L:1, XL:0 |
| GPU Capacity Management | 2 | S:0, M:1, L:0, XL:1 |
| Multi-GPU Coordination | 3 | S:0, M:2, L:1, XL:0 |
| Dashboard State Recovery | 3 | S:1, M:1, L:1, XL:0 |
| Daemon Reconnection | 3 | S:0, M:3, L:0, XL:0 |
| End-to-End Tests | 5 | S:0, M:3, L:2, XL:0 |
| Production Deployment | 4 | S:0, M:3, L:1, XL:0 |
| Monitoring & Validation | 3 | S:1, M:2, L:0, XL:0 |
| Documentation | 2 | S:2, M:0, L:0, XL:0 |
| **TOTAL** | **28** | **S:4, M:17, L:6, XL:1** |

---

## Related Documents

- [Product Requirements](./llms-prd.md)
- [Architecture Overview](./architecture-overview.md)
- [Dashboard Architecture](./architecture-dashboard.md)
- [Daemon Architecture](./architecture-daemon.md)
- [Container Library](./architecture-containers.md)
- [Implementation Overview](./implementation-overview.md)
