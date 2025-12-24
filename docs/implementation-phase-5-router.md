# Phase 5: Request Router - Implementation Plan

## Document Information
- **Phase**: Phase 5 - Request Router
- **Related Documents**:
  - PRD: [llms-prd.md](./llms-prd.md)
  - Dashboard Architecture: [architecture-dashboard.md](./architecture-dashboard.md)
  - Architecture Overview: [architecture-overview.md](./architecture-overview.md)
- **Created**: 2025-12-23
- **Status**: Planning

---

## Phase Overview

**Goal**: Implement OpenAI-compatible API with queue management and model routing

**Deliverables**:
- Router endpoints (/v1/chat/completions, /v1/completions, /v1/models)
- QueueManager (per-model FIFO queues)
- ModelRouter (routing decisions, model lookup)
- Request forwarding to LLM containers via httpx
- SSE streaming responses
- Keepalive during model loading
- Timeout scaling by model size

**Exit Criteria**:
- OpenAI-format requests accepted
- Requests routed to running containers
- Streaming responses work
- Keepalives sent while loading

---

## Task Breakdown

### 1. Foundation & Data Models

#### Task 1.1: OpenAI-Compatible Pydantic Models
- [ ] **Status**: Not Started
- **Description**: Create Pydantic models for OpenAI API compatibility (chat completions, completions, models list)
- **Acceptance Criteria**:
  - [ ] ChatCompletionRequest model with all required fields (model, messages, stream, max_tokens, temperature)
  - [ ] ChatCompletionResponse model with proper structure
  - [ ] ChatCompletionChunk model for streaming responses
  - [ ] CompletionRequest and CompletionResponse models
  - [ ] ModelInfo and ModelList response models
  - [ ] Message model with role/content validation
  - [ ] All models validated against OpenAI API specification
- **Technical Approach**:
  - Create `backend/models/openai_schemas.py` with Pydantic v2 models
  - Use Field(...) for required fields with descriptions
  - Add validators for enums (role: user/assistant/system)
  - Support optional fields (temperature, top_p, presence_penalty, etc.)
  - Include streaming-specific models (delta format)
- **Files/Components**:
  - [ ] `dashboard/backend/models/openai_schemas.py` - OpenAI-compatible Pydantic models
- **Dependencies**: None
- **Complexity**: M

#### Task 1.2: Internal Request/Response Models
- [ ] **Status**: Not Started
- **Description**: Create internal models for request queue management and routing state
- **Acceptance Criteria**:
  - [ ] InferenceRequest model wrapping OpenAI request + metadata (request_id, enqueue_time, timeout)
  - [ ] RequestContext model with response event, stream queue, and error state
  - [ ] ModelQuant class for parsing and representing model+quantization pairs
  - [ ] GPURequirement model (memory_gb, gpu_count, multi_machine flag)
  - [ ] ContainerEndpoint model (machine_id, host, port, health_url)
- **Technical Approach**:
  - Create `backend/models/internal_schemas.py`
  - ModelQuant.parse() method to extract quantization from model name
  - ModelQuant.default_quant() method to select smallest available
  - Use dataclasses for simpler internal models
  - Include helper methods for timeout calculation based on model size
- **Files/Components**:
  - [ ] `dashboard/backend/models/internal_schemas.py` - Internal request/routing models
- **Dependencies**: Task 1.1
- **Complexity**: M

---

### 2. Queue Management

#### Task 2.1: QueueManager Core Implementation
- [ ] **Status**: Not Started
- **Description**: Implement QueueManager class with per-model FIFO queues using asyncio.Queue
- **Acceptance Criteria**:
  - [ ] QueueManager class with dict[str, asyncio.Queue] for per-model queues
  - [ ] enqueue() method creates queue on first request for model+quant
  - [ ] dequeue() method blocks until request available
  - [ ] get_or_create_queue() helper method
  - [ ] Thread-safe queue access with proper async locking
  - [ ] Queue cleanup when model unloaded (destroy queue, reject pending requests)
- **Technical Approach**:
  - Use asyncio.Queue (unbounded for now, can add size limits later)
  - Lock per-model queue creation with asyncio.Lock
  - Store queues in dict keyed by model+quant string
  - Each queue item is RequestContext with event for response coordination
- **Files/Components**:
  - [ ] `dashboard/backend/services/queue_manager.py` - QueueManager class (queues dict, enqueue/dequeue methods)
- **Dependencies**: Task 1.2
- **Complexity**: M

#### Task 2.2: QueueManager Active Tracking
- [ ] **Status**: Not Started
- **Description**: Track active request counts and last-used timestamps per model+quant for eviction decisions
- **Acceptance Criteria**:
  - [ ] active_counts dict tracking in-queue + in-flight requests per model+quant
  - [ ] last_used dict tracking completion timestamp per model+quant
  - [ ] increment_active() called on enqueue
  - [ ] decrement_active() called on request completion
  - [ ] update_last_used() called on request completion
  - [ ] is_idle() method returns True when active_count == 0
  - [ ] get_lru_idle_models() returns list sorted by last_used (oldest first)
- **Technical Approach**:
  - Use dict[str, int] for active_counts (model+quant -> count)
  - Use dict[str, datetime] for last_used timestamps
  - Context manager for request tracking (auto increment/decrement)
  - LRU sorting filters is_idle() models, then sorts by last_used ascending
- **Files/Components**:
  - [ ] `dashboard/backend/services/queue_manager.py` - Add active_counts, last_used tracking
- **Dependencies**: Task 2.1
- **Complexity**: S

#### Task 2.3: QueueManager Metrics & Monitoring
- [ ] **Status**: Not Started
- **Description**: Add logging and metrics for queue state visibility
- **Acceptance Criteria**:
  - [ ] Log queue creation with model+quant name
  - [ ] Log enqueue with request_id, model, queue depth
  - [ ] Log dequeue with request_id, wait time
  - [ ] get_queue_status() method returning dict of all queues (depth, active_count, last_used)
  - [ ] Expose queue metrics via /api/router/status endpoint
- **Technical Approach**:
  - Use structlog for structured logging with model, request_id context
  - get_queue_status() iterates all queues, returns {model: {depth: N, active: M, last_used: timestamp}}
  - Add Control API endpoint to expose queue state for UI/debugging
- **Files/Components**:
  - [ ] `dashboard/backend/services/queue_manager.py` - Add logging and get_queue_status()
  - [ ] `dashboard/backend/api/control.py` - Add /api/router/status endpoint
- **Dependencies**: Task 2.2
- **Complexity**: S

---

### 3. Model Routing Logic

#### Task 3.1: ModelRouter Core Structure
- [ ] **Status**: Not Started
- **Description**: Create ModelRouter class skeleton with dependencies on ClusterState and DaemonManager
- **Acceptance Criteria**:
  - [ ] ModelRouter class initialized with ClusterState and DaemonManager references
  - [ ] route_request() method signature (accepts InferenceRequest, returns AsyncIterator[str])
  - [ ] Placeholder methods for ensure_capacity() and evict_model()
  - [ ] Integration with QueueManager instance
  - [ ] Proper async context usage
- **Technical Approach**:
  - Create `backend/services/model_router.py`
  - Store references to cluster_state, daemon_manager, queue_manager
  - route_request() will be async generator yielding SSE chunks
  - Use httpx.AsyncClient for forwarding requests to containers
- **Files/Components**:
  - [ ] `dashboard/backend/services/model_router.py` - ModelRouter class skeleton
- **Dependencies**: Task 2.1
- **Complexity**: S

#### Task 3.2: Model Name Parsing
- [ ] **Status**: Not Started
- **Description**: Implement model name parsing to extract base model and quantization suffix
- **Acceptance Criteria**:
  - [ ] parse_model_name() function extracts base model and quantization
  - [ ] Handles formats: "qwen2.5-72b-instruct-awq", "llama3.1-8b-q4_k_m", "mistral-7b-instruct"
  - [ ] Returns (base_model, quantization) tuple
  - [ ] If no quantization suffix, returns (model, None)
  - [ ] Known quantization suffixes: awq, q4_k_m, q8_0, fp8, fp16, gptq, etc.
  - [ ] Unit tests for various model name formats
- **Technical Approach**:
  - Define set of known quantization suffixes
  - Split model name on hyphens, check if last segment matches known quant
  - Return tuple of (base_model, quant_or_none)
  - Helper method resolve_default_quant() queries DB for smallest quant if None
- **Files/Components**:
  - [ ] `dashboard/backend/services/model_router.py` - Add parse_model_name() function
  - [ ] `dashboard/backend/tests/test_model_router.py` - Unit tests for parsing
- **Dependencies**: Task 3.1
- **Complexity**: S

#### Task 3.3: Container Lookup & Routing
- [ ] **Status**: Not Started
- **Description**: Implement logic to check if model+quant is running and get container endpoint
- **Acceptance Criteria**:
  - [ ] get_running_container() method queries ClusterState for model+quant
  - [ ] Returns ContainerEndpoint (machine_id, host, port) if running
  - [ ] Returns None if model not loaded
  - [ ] Handles multi-machine models (returns master node endpoint)
  - [ ] Validates container health status before returning
- **Technical Approach**:
  - Query ClusterState.running_models dict by model+quant key
  - Check ModelState.status == "ready" (not "loading" or "failed")
  - For multi-machine models, return master node (rank 0) endpoint
  - Construct endpoint URL: http://{host}:{port}/v1/chat/completions
- **Files/Components**:
  - [ ] `dashboard/backend/services/model_router.py` - Add get_running_container() method
- **Dependencies**: Task 3.2
- **Complexity**: M

#### Task 3.4: GPU Requirement Lookup
- [ ] **Status**: Not Started
- **Description**: Query database for GPU requirements (VRAM, count, parallelism) for model+quant
- **Acceptance Criteria**:
  - [ ] get_gpu_requirements() async method queries container_configs and model_quantizations tables
  - [ ] Returns GPURequirement with vram_required_gb, gpu_count, tensor_parallel, pipeline_parallel
  - [ ] Raises ModelNotFoundError if model+quant not in database
  - [ ] Calculates multi_machine flag based on gpu_count and tensor_parallel settings
- **Technical Approach**:
  - Join model_quantizations and container_configs tables
  - Calculate total VRAM needed = vram_required_gb * gpu_count
  - Set multi_machine = True if gpu_count > max_gpus_per_machine (configurable, default 8)
  - Use asyncpg/SQLAlchemy async session for DB query
- **Files/Components**:
  - [ ] `dashboard/backend/services/model_router.py` - Add get_gpu_requirements() method
- **Dependencies**: Task 3.3
- **Complexity**: M

#### Task 3.5: Capacity Planning (Single Machine)
- [ ] **Status**: Not Started
- **Description**: Find available GPU capacity on single machine for model loading
- **Acceptance Criteria**:
  - [ ] find_available_machine() method finds machine with sufficient free GPU memory
  - [ ] Checks each machine's GPUs for total free VRAM >= required
  - [ ] Prefers machines with exact GPU count match
  - [ ] Prefers machines with lowest utilization as tiebreaker
  - [ ] Returns None if no machine has capacity
  - [ ] Excludes machines marked as "busy" (mid-transition)
- **Technical Approach**:
  - Iterate ClusterState.machines, filter connected=True
  - For each machine, sum free VRAM across GPUs (total - used)
  - Check if free VRAM >= required and free GPU count >= required
  - Sort candidates by: exact GPU match, then lowest utilization
  - Return best match or None
- **Files/Components**:
  - [ ] `dashboard/backend/services/model_router.py` - Add find_available_machine() method
- **Dependencies**: Task 3.4
- **Complexity**: M

#### Task 3.6: Eviction Logic
- [ ] **Status**: Not Started
- **Description**: Implement LRU eviction of idle models to free GPU capacity
- **Acceptance Criteria**:
  - [ ] evict_lru_models() method frees GPU memory until requirement met
  - [ ] Only evicts models with empty queues (is_idle() == True)
  - [ ] Evicts oldest last_used models first (LRU policy)
  - [ ] Sends container.stop commands to daemons
  - [ ] Blocks model queues during eviction (don't destroy, pause)
  - [ ] Returns list of evicted model+quants
  - [ ] Raises InsufficientCapacityError if cannot free enough memory
- **Technical Approach**:
  - Call QueueManager.get_lru_idle_models() for eviction candidates
  - Calculate VRAM freed for each candidate from ClusterState
  - Greedily evict models until required VRAM freed
  - Mark queues as "blocked" (return 503 errors for new requests)
  - Send async container.stop commands via DaemonManager
  - Wait for container stop confirmation before considering VRAM freed
- **Files/Components**:
  - [ ] `dashboard/backend/services/model_router.py` - Add evict_lru_models() method
- **Dependencies**: Task 3.5, Task 2.2
- **Complexity**: L

#### Task 3.7: Model Loading Orchestration
- [ ] **Status**: Not Started
- **Description**: Orchestrate model loading on daemon (single machine), wait for ready state
- **Acceptance Criteria**:
  - [ ] load_model() method sends container.start command to daemon
  - [ ] Waits for container status == "ready" (polls health endpoint)
  - [ ] Yields keepalive messages during loading
  - [ ] Times out based on model size (see timeout scaling table)
  - [ ] Updates ClusterState with new container info
  - [ ] Raises ModelLoadError on failure or timeout
- **Technical Approach**:
  - Query container_configs table for runtime params
  - Build container.start JSON-RPC message with model, runtime, GPUs, config
  - Send via DaemonManager.send_command()
  - Poll container health at 1s intervals: GET {container_url}/health
  - Yield ": keepalive\n\n" SSE messages during polling
  - Timeout scales: <10B=90s, 10-30B=120s, 30-70B=180s, 70B+=240s
  - On ready, update ClusterState.running_models
- **Files/Components**:
  - [ ] `dashboard/backend/services/model_router.py` - Add load_model() method
- **Dependencies**: Task 3.6
- **Complexity**: L

#### Task 3.8: Request Forwarding to Container
- [ ] **Status**: Not Started
- **Description**: Forward inference request to LLM container and stream response back
- **Acceptance Criteria**:
  - [ ] forward_request() method uses httpx.AsyncClient to POST to container
  - [ ] Preserves all request parameters (messages, temperature, max_tokens, etc.)
  - [ ] Handles streaming responses (SSE format)
  - [ ] Yields chunks as "data: {json}\n\n" SSE format
  - [ ] Handles container errors gracefully (converts to OpenAI error format)
  - [ ] Times out based on max_tokens and model speed (configurable)
- **Technical Approach**:
  - Use httpx.AsyncClient with streaming enabled
  - POST request.dict() to {container_url}/v1/chat/completions
  - Set stream=True in request body
  - Iterate response.aiter_lines(), yield SSE-formatted chunks
  - Parse "data: {json}" lines, re-yield in OpenAI format
  - Catch httpx errors, convert to OpenAI error response format
- **Files/Components**:
  - [ ] `dashboard/backend/services/model_router.py` - Add forward_request() method
- **Dependencies**: Task 3.7
- **Complexity**: M

#### Task 3.9: Full route_request() Integration
- [ ] **Status**: Not Started
- **Description**: Implement complete route_request() flow tying all routing logic together
- **Acceptance Criteria**:
  - [ ] route_request() parses model name, resolves quantization
  - [ ] Checks if model+quant running, forwards directly if so
  - [ ] If not running: gets GPU requirements, checks capacity, evicts if needed, loads model
  - [ ] Yields keepalive during loading
  - [ ] Forwards request once container ready
  - [ ] Yields response chunks from container
  - [ ] Updates queue active counts and last_used on completion
  - [ ] Handles all error cases with proper logging
- **Technical Approach**:
  - Combine all previous methods into complete async generator
  - Use try/finally to ensure active_counts decremented
  - Log each step: parse, lookup, capacity check, eviction, loading, forward
  - Yield keepalive with estimated wait time if loading
  - Stream response chunks directly from container
- **Files/Components**:
  - [ ] `dashboard/backend/services/model_router.py` - Implement route_request() fully
- **Dependencies**: Tasks 3.2 through 3.8
- **Complexity**: XL

---

### 4. Router API Endpoints

#### Task 4.1: POST /v1/chat/completions Endpoint
- [ ] **Status**: Not Started
- **Description**: Implement OpenAI-compatible chat completions endpoint with streaming support
- **Acceptance Criteria**:
  - [ ] Accepts ChatCompletionRequest (validated by Pydantic)
  - [ ] Enqueues request to QueueManager
  - [ ] Returns StreamingResponse with SSE media type
  - [ ] Supports stream=true (default) and stream=false modes
  - [ ] Includes OpenAI-compatible response headers
  - [ ] Handles errors with proper HTTP status codes (400, 503, 500)
- **Technical Approach**:
  - Create `backend/api/router.py` with FastAPI router
  - Validate request with ChatCompletionRequest model
  - Create InferenceRequest with metadata (request_id, timeout)
  - Enqueue to QueueManager, get RequestContext
  - Return StreamingResponse wrapping ModelRouter.route_request()
  - For stream=false, collect all chunks and return single response
- **Files/Components**:
  - [ ] `dashboard/backend/api/router.py` - POST /v1/chat/completions endpoint
- **Dependencies**: Task 3.9, Task 2.1
- **Complexity**: L

#### Task 4.2: POST /v1/completions Endpoint
- [ ] **Status**: Not Started
- **Description**: Implement OpenAI-compatible text completions endpoint (non-chat format)
- **Acceptance Criteria**:
  - [ ] Accepts CompletionRequest (prompt as string, not messages)
  - [ ] Converts to internal format compatible with model router
  - [ ] Supports streaming and non-streaming modes
  - [ ] Returns CompletionResponse in OpenAI format
  - [ ] Shares routing logic with chat completions
- **Technical Approach**:
  - Similar flow to Task 4.1 but with CompletionRequest model
  - Convert prompt string to messages format internally if needed
  - Some models may require chat template wrapping
  - Forward to container's /v1/completions endpoint if supported
- **Files/Components**:
  - [ ] `dashboard/backend/api/router.py` - POST /v1/completions endpoint
- **Dependencies**: Task 4.1
- **Complexity**: M

#### Task 4.3: GET /v1/models Endpoint
- [ ] **Status**: Not Started
- **Description**: Return list of all available models (model+quant combinations) in OpenAI format
- **Acceptance Criteria**:
  - [ ] Returns ModelList response with all model+quant combinations
  - [ ] Queries model_quantizations table joined with models table
  - [ ] Each entry includes id (model+quant name), owned_by (provider), created timestamp
  - [ ] Includes running status for each model (from ClusterState)
  - [ ] Sorted alphabetically by model name
- **Technical Approach**:
  - Query database for all model+quant combinations
  - Format as OpenAI ModelList response: {object: "list", data: [{id, object, created, owned_by}]}
  - Augment with running status from ClusterState (extension field)
  - Cache results for 60s to reduce DB load
- **Files/Components**:
  - [ ] `dashboard/backend/api/router.py` - GET /v1/models endpoint
- **Dependencies**: Task 1.1
- **Complexity**: S

#### Task 4.4: GET /v1/models/{model} Endpoint
- [ ] **Status**: Not Started
- **Description**: Return details for specific model+quant
- **Acceptance Criteria**:
  - [ ] Returns ModelInfo response for requested model+quant
  - [ ] Returns 404 if model+quant not found
  - [ ] Includes GPU requirements, context length, runtime info
  - [ ] Includes current status (running/stopped)
- **Technical Approach**:
  - Query database for specific model+quant
  - Join with container_configs for detailed info
  - Return OpenAI ModelInfo format with extensions for GPU requirements
- **Files/Components**:
  - [ ] `dashboard/backend/api/router.py` - GET /v1/models/{model} endpoint
- **Dependencies**: Task 4.3
- **Complexity**: S

#### Task 4.5: Router Error Handling
- [ ] **Status**: Not Started
- **Description**: Implement comprehensive error handling with OpenAI-compatible error responses
- **Acceptance Criteria**:
  - [ ] ModelNotFoundError returns 404 with error detail
  - [ ] InsufficientCapacityError returns 503 with retry-after header
  - [ ] ModelLoadError returns 500 with error detail
  - [ ] Validation errors return 400 with field details
  - [ ] Timeout errors return 504 Gateway Timeout
  - [ ] All errors formatted as OpenAI error responses: {error: {message, type, code}}
- **Technical Approach**:
  - Define custom exception classes in `backend/models/exceptions.py`
  - Create FastAPI exception handlers for each exception type
  - Map to appropriate HTTP status codes
  - Format responses in OpenAI error format
  - Include request_id in error responses for tracing
- **Files/Components**:
  - [ ] `dashboard/backend/models/exceptions.py` - Custom exception classes
  - [ ] `dashboard/backend/api/router.py` - Exception handlers
- **Dependencies**: Tasks 4.1-4.4
- **Complexity**: M

---

### 5. SSE Streaming & Keepalive

#### Task 5.1: SSE Response Generator
- [ ] **Status**: Not Started
- **Description**: Create reusable SSE response generator that wraps async iterators
- **Acceptance Criteria**:
  - [ ] sse_generator() function wraps async iterator, yields SSE-formatted chunks
  - [ ] Formats data as "data: {json}\n\n"
  - [ ] Supports keepalive comments ": keepalive\n\n"
  - [ ] Sends "data: [DONE]\n\n" at end of stream
  - [ ] Handles errors mid-stream (sends error chunk, closes stream)
  - [ ] Sets proper headers: text/event-stream, no-cache, keep-alive
- **Technical Approach**:
  - Create `backend/services/sse_utils.py`
  - Accept async iterator yielding dict or str
  - For dict, json.dumps() and prefix with "data: "
  - For str starting with ":", pass through as comment
  - Yield "\n\n" after each chunk
  - Wrap in try/except to send error chunk on exception
- **Files/Components**:
  - [ ] `dashboard/backend/services/sse_utils.py` - SSE generator utility
- **Dependencies**: None
- **Complexity**: S

#### Task 5.2: Keepalive Generator During Model Loading
- [ ] **Status**: Not Started
- **Description**: Generate keepalive messages with loading status while model loads
- **Acceptance Criteria**:
  - [ ] keepalive_generator() yields SSE comments every 1 second
  - [ ] Includes estimated wait time: ": loading, estimated 45s remaining\n\n"
  - [ ] Decrements countdown based on elapsed time
  - [ ] Stops when loading complete (event set) or timeout
  - [ ] Interleaves with container response once ready
- **Technical Approach**:
  - Accept timeout duration and asyncio.Event for completion signal
  - Loop: yield comment, sleep 1s, check event
  - Calculate remaining = timeout - elapsed
  - Format as ": loading {model}, ~{remaining}s remaining\n\n"
  - Break when event.is_set()
- **Files/Components**:
  - [ ] `dashboard/backend/services/sse_utils.py` - Add keepalive_generator()
- **Dependencies**: Task 5.1
- **Complexity**: S

#### Task 5.3: Response Streaming Integration
- [ ] **Status**: Not Started
- **Description**: Integrate SSE generators into route_request() for seamless keepalive→response transition
- **Acceptance Criteria**:
  - [ ] route_request() uses keepalive_generator() during loading phase
  - [ ] Transitions to container response streaming once ready
  - [ ] No gap in SSE stream (continuous keepalive until first token)
  - [ ] Client receives uninterrupted stream from request to completion
  - [ ] Handles transition edge cases (model ready while sending keepalive)
- **Technical Approach**:
  - Use asyncio.create_task() for concurrent loading and keepalive
  - Yield keepalive chunks until loading complete
  - Once ready, cancel keepalive task and start forwarding chunks
  - Use asyncio.Queue to coordinate between tasks
- **Files/Components**:
  - [ ] `dashboard/backend/services/model_router.py` - Update route_request() to use SSE utils
- **Dependencies**: Task 5.2, Task 3.9
- **Complexity**: M

---

### 6. Timeout & Configuration

#### Task 6.1: Timeout Scaling by Model Size
- [ ] **Status**: Not Started
- **Description**: Implement dynamic timeout calculation based on model size and operation type
- **Acceptance Criteria**:
  - [ ] calculate_timeout() function takes model parameters, returns timeout in seconds
  - [ ] Scaling: <10B=90s, 10-30B=120s, 30-70B=180s, 70B+=240s, multi-machine=360s
  - [ ] Separate timeouts for loading vs inference
  - [ ] Inference timeout scales with max_tokens (e.g., 1s per 10 tokens)
  - [ ] Configurable via settings table or environment variable
- **Technical Approach**:
  - Extract parameter count from model name or database
  - Define timeout tiers in config
  - calculate_loading_timeout(params_b) returns base + loading buffer
  - calculate_inference_timeout(params_b, max_tokens) returns base + generation estimate
  - Load overrides from settings table
- **Files/Components**:
  - [ ] `dashboard/backend/services/timeout_calculator.py` - Timeout calculation logic
- **Dependencies**: Task 1.2
- **Complexity**: S

#### Task 6.2: Configuration Loading
- [ ] **Status**: Not Started
- **Description**: Load router configuration from environment variables and database settings
- **Acceptance Criteria**:
  - [ ] RouterConfig class with timeout defaults, capacity limits, keepalive interval
  - [ ] Loads from environment variables (DEFAULT_REQUEST_TIMEOUT_SECONDS, etc.)
  - [ ] Overrides with database settings table if present
  - [ ] Validates config on startup (fails fast if invalid)
  - [ ] Exposes /api/router/config endpoint for viewing current config
- **Technical Approach**:
  - Use Pydantic Settings for env var loading
  - Query settings table on startup, merge with defaults
  - Store in singleton or app state
  - Add Control API endpoint to expose read-only config
- **Files/Components**:
  - [ ] `dashboard/backend/config.py` - Add RouterConfig class
  - [ ] `dashboard/backend/api/control.py` - Add /api/router/config endpoint
- **Dependencies**: Task 6.1
- **Complexity**: S

#### Task 6.3: Timeout Enforcement
- [ ] **Status**: Not Started
- **Description**: Enforce timeouts on model loading and inference requests
- **Acceptance Criteria**:
  - [ ] Loading phase times out per model size timeout
  - [ ] Inference phase times out based on max_tokens estimate
  - [ ] Timeout raises asyncio.TimeoutError, converted to 504 response
  - [ ] Partial responses discarded on timeout (no incomplete streams)
  - [ ] Timeout logged with request_id, model, phase (loading/inference)
- **Technical Approach**:
  - Wrap load_model() with asyncio.wait_for(timeout=loading_timeout)
  - Wrap forward_request() with asyncio.wait_for(timeout=inference_timeout)
  - Catch TimeoutError, cleanup resources, raise custom TimeoutError
  - FastAPI handler converts to 504 Gateway Timeout response
- **Files/Components**:
  - [ ] `dashboard/backend/services/model_router.py` - Add timeout wrappers to load_model() and forward_request()
  - [ ] `dashboard/backend/api/router.py` - Add timeout error handler
- **Dependencies**: Task 6.2
- **Complexity**: M

---

### 7. Integration & Testing

#### Task 7.1: Router Service Initialization
- [ ] **Status**: Not Started
- **Description**: Wire up all router services (QueueManager, ModelRouter) in FastAPI app startup
- **Acceptance Criteria**:
  - [ ] Startup event creates QueueManager singleton
  - [ ] Startup event creates ModelRouter with dependencies
  - [ ] Services injected into endpoints via Depends()
  - [ ] Shutdown event cleanly closes queues and pending requests
  - [ ] All async resources properly initialized and cleaned up
- **Technical Approach**:
  - Use FastAPI lifespan context manager
  - Initialize services in startup, store in app.state
  - Create dependency functions for injection
  - Shutdown cancels pending tasks, closes queues gracefully
- **Files/Components**:
  - [ ] `dashboard/backend/main.py` - Add router service initialization
- **Dependencies**: Task 3.1, Task 2.1
- **Complexity**: M

#### Task 7.2: Unit Tests for QueueManager
- [ ] **Status**: Not Started
- **Description**: Comprehensive unit tests for queue management logic
- **Acceptance Criteria**:
  - [ ] Test enqueue/dequeue FIFO ordering
  - [ ] Test queue creation on first request
  - [ ] Test active_counts increment/decrement
  - [ ] Test last_used timestamp updates
  - [ ] Test is_idle() logic
  - [ ] Test get_lru_idle_models() sorting
  - [ ] Test concurrent access (multiple enqueues)
  - [ ] All tests pass with 100% coverage of queue_manager.py
- **Technical Approach**:
  - Use pytest with pytest-asyncio
  - Mock time for last_used testing
  - Test edge cases: empty queues, single item, many concurrent requests
- **Files/Components**:
  - [ ] `dashboard/backend/tests/test_queue_manager.py` - Unit tests
- **Dependencies**: Task 2.3
- **Complexity**: M

#### Task 7.3: Unit Tests for Model Router
- [ ] **Status**: Not Started
- **Description**: Unit tests for routing logic with mocked dependencies
- **Acceptance Criteria**:
  - [ ] Test parse_model_name() with various formats
  - [ ] Test get_running_container() lookup
  - [ ] Test find_available_machine() capacity logic
  - [ ] Test evict_lru_models() selection and execution
  - [ ] Test load_model() orchestration
  - [ ] Mock ClusterState, DaemonManager, httpx for isolation
  - [ ] All tests pass with >90% coverage of model_router.py
- **Technical Approach**:
  - Use pytest with unittest.mock
  - Create fixtures for ClusterState with test data
  - Mock DaemonManager.send_command() to verify calls
  - Mock httpx.AsyncClient for container forwarding tests
- **Files/Components**:
  - [ ] `dashboard/backend/tests/test_model_router.py` - Unit tests
- **Dependencies**: Task 3.9
- **Complexity**: L

#### Task 7.4: Integration Tests for Router Endpoints
- [ ] **Status**: Not Started
- **Description**: End-to-end tests for router API endpoints with test client
- **Acceptance Criteria**:
  - [ ] Test POST /v1/chat/completions with valid request
  - [ ] Test streaming response format (SSE)
  - [ ] Test non-streaming mode
  - [ ] Test GET /v1/models returns expected list
  - [ ] Test error cases: invalid model, timeout, capacity error
  - [ ] Tests use FastAPI TestClient with mocked dependencies
  - [ ] All endpoints tested with 200, 400, 404, 500, 503, 504 responses
- **Technical Approach**:
  - Use FastAPI TestClient (httpx-based)
  - Mock database, ClusterState, DaemonManager
  - Inject test dependencies via app.dependency_overrides
  - Test streaming with client.stream() context manager
  - Assert SSE format, headers, response structure
- **Files/Components**:
  - [ ] `dashboard/backend/tests/test_router_api.py` - Integration tests
- **Dependencies**: Tasks 4.1-4.5
- **Complexity**: L

#### Task 7.5: Manual Testing with Real LLM Container
- [ ] **Status**: Not Started
- **Description**: Manual end-to-end testing with actual vLLM container running
- **Acceptance Criteria**:
  - [ ] Start vLLM container manually with known model
  - [ ] Send request via router API, verify forwarding works
  - [ ] Test streaming response with real tokens
  - [ ] Test keepalive during model loading (stop/start container)
  - [ ] Test queue FIFO with multiple concurrent requests
  - [ ] Test timeout handling (slow model or network)
  - [ ] Document test scenarios and results
- **Technical Approach**:
  - Use curl or Python script to send requests
  - Monitor logs for routing decisions
  - Inspect SSE stream format
  - Test with small model (e.g., Qwen 0.5B) for fast iteration
- **Files/Components**:
  - [ ] `dashboard/backend/tests/manual/test_real_container.md` - Manual test documentation
- **Dependencies**: Task 7.4
- **Complexity**: M

---

## Summary

### Task Count by Category
- **Foundation & Data Models**: 2 tasks
- **Queue Management**: 3 tasks
- **Model Routing Logic**: 9 tasks
- **Router API Endpoints**: 5 tasks
- **SSE Streaming & Keepalive**: 3 tasks
- **Timeout & Configuration**: 3 tasks
- **Integration & Testing**: 5 tasks

**Total Tasks**: 30

### Critical Path
1. Foundation (Tasks 1.1-1.2)
2. Queue Management (Tasks 2.1-2.2)
3. Model Router Core (Tasks 3.1-3.9)
4. Router Endpoints (Tasks 4.1-4.5)
5. SSE Integration (Tasks 5.1-5.3)
6. Testing (Tasks 7.1-7.5)

### Estimated Complexity Distribution
- **S (Small)**: 9 tasks
- **M (Medium)**: 13 tasks
- **L (Large)**: 6 tasks
- **XL (Extra Large)**: 2 tasks

### Key Dependencies
- All routing logic depends on Queue Manager (2.1-2.2)
- All endpoints depend on Model Router completion (3.9)
- Testing depends on full implementation (7.x depends on all)
- SSE integration requires routing and keepalive generators (5.3 depends on 3.9, 5.2)

### Risk Areas
1. **Eviction logic complexity** (Task 3.6) - Multi-machine coordination, race conditions
2. **Model loading orchestration** (Task 3.7) - Timeouts, health check reliability
3. **Full routing integration** (Task 3.9) - Many moving parts, error handling
4. **Integration testing** (Task 7.4) - Requires mock coordination of many services

---

## Completion Checklist

Before marking Phase 5 complete, verify:

- [ ] All 30 tasks marked as completed
- [ ] Unit tests pass with >85% coverage
- [ ] Integration tests pass for all endpoints
- [ ] Manual testing completed with real container
- [ ] OpenAI API compatibility verified (can drop-in replace OpenAI client)
- [ ] Streaming responses work correctly
- [ ] Keepalive messages sent during loading
- [ ] Timeout scaling works for different model sizes
- [ ] Queue FIFO ordering verified
- [ ] LRU eviction works correctly
- [ ] Error handling tested for all error paths
- [ ] Logging provides sufficient visibility into routing decisions
- [ ] No memory leaks (queue cleanup, task cancellation)
- [ ] Documentation updated (API docs, deployment guide)
- [ ] Code review completed
- [ ] Phase exit criteria met (see Phase Overview)
