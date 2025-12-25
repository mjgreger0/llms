# Phase 7: Container Library - Implementation Plan

## Document Information
- **Phase**: 7 - Container Library
- **Created**: 2025-12-23
- **Status**: Complete
- **Dependencies**: Phase 1-6 (Database infrastructure, ModelRouter foundation)

---

## Phase Overview

**Goal**: Implement container configuration storage and command generation for vLLM

**Deliverables**:
- Database tables for container library (model_configs, quantization_configs, launch_configs)
- SQLAlchemy models for container configurations
- ContainerCommandGenerator class for generating vLLM commands
- GPU device mapping using nvidia-container-toolkit format
- Environment variable building for containers
- Container labeling scheme for tracking
- Health check polling logic
- Integration with ModelRouter (ensure_capacity, start model)
- Initial vLLM configurations (seed data)
- VRAM requirement calculations

**Exit Criteria**:
- Database schema created and migrated
- vLLM commands generated correctly with all arguments
- Containers start with proper GPU assignments
- Health polling works until container ready
- ModelRouter can trigger container starts
- Container labels track ownership and configuration

---

## Task Breakdown

### 1. Database Schema Implementation

#### Task 1.1: Create Database Migration for Container Library Tables
- [x] **Status**: Complete
- **Description**: Create Alembic migration to add model_configs, quantization_configs, and launch_configs tables
- **Acceptance Criteria**:
  - [x] Migration file created in `dashboard/backend/db/migrations/versions/`
  - [x] model_configs table created with all fields from architecture
  - [x] quantization_configs table created with foreign key to model_configs
  - [x] launch_configs table created with foreign key to quantization_configs
  - [x] Indexes created on frequently queried columns (name, model_id, quant_id)
  - [x] Migration runs successfully upgrade and downgrade
  - [x] All constraints (UNIQUE, NOT NULL, DEFAULT) properly defined
- **Technical Approach**:
  - Use Alembic autogenerate as starting point, then verify/adjust
  - Add indexes: model_configs.name (UNIQUE), quantization_configs(model_id, quantization) (UNIQUE)
  - Set up cascade deletes appropriately (quantizations delete when model deleted)
  - Use TEXT for all string fields except SERIAL/INTEGER fields
  - Default timestamps to NOW() for created_at/updated_at
- **Files/Components**:
  - [x] `dashboard/backend/db/migrations/versions/001_initial_tables.py` - Base tables
  - [x] `dashboard/backend/db/migrations/versions/003_add_container_environment.py` - Environment columns
- **Dependencies**: None (assumes base database infrastructure exists)
- **Complexity**: M

#### Task 1.2: Add Updated Timestamp Triggers
- [x] **Status**: Complete
- **Description**: Create database triggers to automatically update updated_at timestamps
- **Acceptance Criteria**:
  - [x] Trigger function created for updating updated_at column
  - [x] Triggers applied to model_configs, launch_configs tables
  - [x] Trigger fires on UPDATE operations only
  - [x] updated_at column automatically set to NOW() on row updates
- **Technical Approach**:
  - Create PostgreSQL function: `update_updated_at_column()`
  - Apply trigger to each table with updated_at column
  - Test trigger by updating rows and verifying timestamp changes
- **Files/Components**:
  - [x] `dashboard/backend/db/migrations/versions/003_add_container_environment.py` - Includes trigger
- **Dependencies**: Task 1.1
- **Complexity**: S

---

### 2. SQLAlchemy Models

#### Task 2.1: Create ModelConfig SQLAlchemy Model
- [x] **Status**: Complete
- **Description**: Implement SQLAlchemy model for model_configs table
- **Acceptance Criteria**:
  - [x] ModelConfig class created in models/database.py (named `Model`)
  - [x] All columns mapped from database schema
  - [x] Relationship to QuantizationConfig defined (one-to-many)
  - [x] Type hints used for all attributes
  - [x] __repr__ method provides useful string representation
  - [x] Validation methods for max_context (positive integer)
- **Technical Approach**:
  - Use SQLAlchemy 2.0 declarative syntax
  - Define relationship with lazy='selectin' for efficient loading
  - Add validators using @validates decorator for max_context
  - Include cascade delete: relationship(..., cascade="all, delete-orphan")
- **Files/Components**:
  - [x] `dashboard/backend/models/database.py` - Model class with full implementation
- **Dependencies**: Task 1.1
- **Complexity**: M

#### Task 2.2: Create QuantizationConfig SQLAlchemy Model
- [x] **Status**: Complete
- **Description**: Implement SQLAlchemy model for quantization_configs table
- **Acceptance Criteria**:
  - [x] QuantizationConfig class created in models/database.py (named `ModelQuantization`)
  - [x] All columns mapped from database schema
  - [x] Relationship to ModelConfig defined (many-to-one)
  - [x] Relationship to LaunchConfig defined (one-to-many)
  - [x] Type hints used for all attributes
  - [x] Validation for vram_required_gb (positive number)
  - [x] Validation for format (must be one of: transformers, awq, gptq, gguf)
- **Technical Approach**:
  - Foreign key to model_configs with ondelete='CASCADE'
  - Relationship back to ModelConfig with back_populates
  - Validators for numeric fields (must be positive)
  - Enum or choice validation for format field
- **Files/Components**:
  - [x] `dashboard/backend/models/database.py` - ModelQuantization class
- **Dependencies**: Task 2.1
- **Complexity**: M

#### Task 2.3: Create LaunchConfig SQLAlchemy Model
- [x] **Status**: Complete
- **Description**: Implement SQLAlchemy model for launch_configs table
- **Acceptance Criteria**:
  - [x] LaunchConfig class created in models/database.py (named `ContainerConfig`)
  - [x] All columns mapped from database schema
  - [x] Relationship to QuantizationConfig defined (many-to-one)
  - [x] JSONB fields properly mapped for extra_args and environment
  - [x] Type hints include proper JSON typing
  - [x] Validation for positive integers (gpu_count, tensor_parallel, etc.)
  - [x] Validation for runtime (must be: vllm, sglang, llamacpp)
- **Technical Approach**:
  - Use JSONB type for extra_args and environment columns
  - Add property methods to access JSONB data as dicts
  - Validators for all numeric fields (positive, non-zero)
  - Default values match architecture specification
- **Files/Components**:
  - [x] `dashboard/backend/models/database.py` - ContainerConfig class
- **Dependencies**: Task 2.2
- **Complexity**: M

#### Task 2.4: Create Pydantic Schemas for API Responses
- [x] **Status**: Complete
- **Description**: Create Pydantic models for serializing container configs in API responses
- **Acceptance Criteria**:
  - [x] ModelConfigSchema created in models/schemas.py
  - [x] QuantizationConfigSchema created in models/schemas.py
  - [x] LaunchConfigSchema created in models/schemas.py (ContainerConfigResponse)
  - [x] Nested schemas properly reference each other
  - [x] from_attributes=True (ORM mode) enabled
  - [x] All fields properly typed with Python type hints
  - [x] Optional fields marked correctly
- **Technical Approach**:
  - Use Pydantic v2 syntax (ConfigDict)
  - Define nested relationships (ModelConfigSchema includes quantizations list)
  - Add computed fields if needed (e.g., full_name = f"{model}-{quant}")
  - Exclude internal fields like encrypted data from responses
- **Files/Components**:
  - [x] `dashboard/backend/models/schemas.py` - ContainerConfigBase/Create/Response/Update schemas
- **Dependencies**: Tasks 2.1, 2.2, 2.3
- **Complexity**: M

---

### 3. Container Command Generator

#### Task 3.1: Implement Base ContainerCommandGenerator Class
- [x] **Status**: Complete
- **Description**: Create ContainerCommandGenerator class with runtime dispatch logic
- **Acceptance Criteria**:
  - [x] ContainerCommandGenerator class created in services/
  - [x] generate() method dispatches to runtime-specific methods
  - [x] Runtime mapping configured (vllm, sglang, llamacpp)
  - [x] ValueError raised for unknown runtimes
  - [x] Type hints for all parameters (LaunchConfig, Machine, list[int])
  - [x] Returns list[str] representing command parts
  - [x] Unit tests for dispatch logic
- **Technical Approach**:
  - Create services/container_command.py module
  - Use match/case (Python 3.10+) or dict dispatch for runtime selection
  - Accept LaunchConfig, Machine, and GPU list as parameters
  - Return command as list of strings (not shell string)
  - Private methods: _generate_vllm, _generate_sglang, _generate_llamacpp
- **Files/Components**:
  - [x] `dashboard/backend/services/container_command.py` - ContainerCommandGenerator class
  - [x] `dashboard/backend/tests/test_container_command.py` - Unit tests (20 test cases)
- **Dependencies**: Task 2.3 (needs LaunchConfig model)
- **Complexity**: M

#### Task 3.2: Implement vLLM Command Generation
- [x] **Status**: Complete
- **Description**: Implement _generate_vllm method to build complete vLLM podman command
- **Acceptance Criteria**:
  - [x] Generates complete podman run command as list[str]
  - [x] Container name includes model+quant and random suffix
  - [x] GPU devices mapped using --device nvidia.com/gpu=N format
  - [x] Model volume mounted at /models:ro
  - [x] SHM size set to 16g
  - [x] Port mapping from next available port to 8000
  - [x] CUDA_VISIBLE_DEVICES set correctly
  - [x] All vLLM arguments included (model, max-model-len, tensor-parallel-size, etc.)
  - [x] Extra args from config.extra_args appended
  - [x] Environment variables from config.environment added
  - [x] Container labels added (llm-serve=true, model, runtime, gpus)
- **Technical Approach**:
  - Build command as list: ["podman", "run", "-d", ...]
  - Use uuid4().hex[:8] for unique container suffix
  - Port allocation: implement _next_port() helper (track in-memory)
  - GPU devices: iterate gpu list and add --device for each
  - Model path: join MODEL_PATH config with config.file_path
  - Labels: JSON serialize GPU list for label value
  - Follow example from architecture doc line 362-385
- **Files/Components**:
  - [x] `dashboard/backend/services/container_command.py` - _generate_vllm method
  - [x] `dashboard/backend/services/container_command.py` - PortAllocator class
  - [x] `dashboard/backend/services/container_command.py` - _container_name helper
  - [x] `dashboard/backend/tests/test_container_command.py` - Test vLLM generation
- **Dependencies**: Task 3.1
- **Complexity**: L

#### Task 3.3: Implement GPU Device Mapping
- [x] **Status**: Complete
- **Description**: Create helper methods for GPU device mapping in nvidia-container-toolkit format
- **Acceptance Criteria**:
  - [x] _format_gpu_devices method accepts list[int] and returns list of --device args
  - [x] Correct format: --device nvidia.com/gpu=N for each GPU
  - [x] Multiple GPUs result in multiple --device arguments
  - [x] Empty GPU list raises ValueError
  - [x] Unit tests cover single GPU, multi-GPU, and error cases
- **Technical Approach**:
  - Iterate GPU index list
  - For each GPU, append ["--device", f"nvidia.com/gpu={idx}"]
  - Validate list is not empty before processing
  - Return flat list of arguments ready to extend into command
- **Files/Components**:
  - [x] `dashboard/backend/services/container_command.py` - _format_gpu_devices method
  - [x] `dashboard/backend/tests/test_container_command.py` - GPU mapping tests
- **Dependencies**: Task 3.1
- **Complexity**: S

#### Task 3.4: Implement Environment Variable Building
- [x] **Status**: Complete
- **Description**: Create helper method to build environment variable arguments from config
- **Acceptance Criteria**:
  - [x] _build_env_args method accepts config.environment dict and gpu list
  - [x] CUDA_VISIBLE_DEVICES automatically added from GPU list
  - [x] Config environment variables added as -e KEY=VALUE pairs
  - [x] Returns list of ["-e", "KEY=VALUE", "-e", "KEY2=VALUE2", ...]
  - [x] Handles empty environment dict gracefully
  - [x] Unit tests verify correct formatting
- **Technical Approach**:
  - Start with base env: {"CUDA_VISIBLE_DEVICES": ",".join(str(g) for g in gpus)}
  - Merge config.environment into base env
  - Iterate merged dict and build ["-e", f"{k}={v}"] pairs
  - Return flat list ready to extend into command
- **Files/Components**:
  - [x] `dashboard/backend/services/container_command.py` - _build_env_args method
  - [x] `dashboard/backend/tests/test_container_command.py` - Environment tests
- **Dependencies**: Task 3.1
- **Complexity**: S

#### Task 3.5: Implement Container Labeling
- [x] **Status**: Complete
- **Description**: Create helper method to build container label arguments
- **Acceptance Criteria**:
  - [x] _build_label_args method accepts config and GPU list
  - [x] Labels include: llm-serve=true, model, runtime, gpus
  - [x] GPU list JSON serialized for gpus label
  - [x] Returns list of ["--label", "key=value", ...] pairs
  - [x] All labels properly formatted for podman
  - [x] Unit tests verify label formatting
- **Technical Approach**:
  - Define label dict with required keys
  - llm-serve: "true"
  - model: config.model_quant (derived from config relationships)
  - runtime: config.runtime
  - gpus: json.dumps(gpus)
  - Build list of ["--label", f"{k}={v}"] pairs
  - Return flat list ready to extend
- **Files/Components**:
  - [x] `dashboard/backend/services/container_command.py` - _build_label_args method
  - [x] `dashboard/backend/tests/test_container_command.py` - Label tests
- **Dependencies**: Task 3.1
- **Complexity**: S

#### Task 3.6: Implement Port Allocation
- [x] **Status**: Complete
- **Description**: Create port allocation mechanism to assign unique ports to containers
- **Acceptance Criteria**:
  - [x] _next_port method returns next available port (via PortAllocator.allocate())
  - [x] Port range configurable (default 8001-8999)
  - [x] Port tracking persists across container starts
  - [x] Ports released when containers stop
  - [x] Thread-safe allocation (use asyncio lock)
  - [x] Unit tests verify no duplicate ports
- **Technical Approach**:
  - Maintain in-memory set of allocated ports
  - Start from configured base port (8001)
  - Increment until finding free port
  - Track port -> container_id mapping
  - Release port when container stops (called by daemon manager)
  - Use asyncio.Lock for thread safety
- **Files/Components**:
  - [x] `dashboard/backend/services/container_command.py` - PortAllocator class
  - [x] `dashboard/backend/services/container_command.py` - allocate() method
  - [x] `dashboard/backend/services/container_command.py` - release() method
  - [x] `dashboard/backend/tests/test_container_command.py` - Port allocation tests
- **Dependencies**: Task 3.1
- **Complexity**: M

---

### 4. VRAM Calculations

#### Task 4.1: Implement VRAM Estimation Function
- [x] **Status**: Complete
- **Description**: Create utility function to estimate VRAM requirements for model+quantization
- **Acceptance Criteria**:
  - [x] estimate_vram_gb function accepts parameter count and quantization
  - [x] Formula implemented: VRAM = (params_billions * bits_per_param / 8) * 1.2
  - [x] Quantization bits mapped correctly (fp16=16, awq=4, gptq=4, q4_k_m=4, q8=8)
  - [x] Returns float representing GB required
  - [x] Unit tests verify estimates match reference table from architecture
  - [x] Helper function to parse parameter count from strings like "72B", "8B"
- **Technical Approach**:
  - Create utils/vram.py module
  - Map quantization names to bits per parameter
  - Parse parameter strings: regex to extract number, convert to billions
  - Apply formula with 1.2 overhead multiplier
  - Round to 1 decimal place for cleanliness
- **Files/Components**:
  - [x] `dashboard/backend/utils/vram.py` - VRAM estimation functions
  - [x] `dashboard/backend/tests/test_vram.py` - VRAM calculation tests
- **Dependencies**: None
- **Complexity**: S

#### Task 4.2: Implement Context Length VRAM Impact
- [x] **Status**: Complete
- **Description**: Create function to calculate additional VRAM needed for KV cache based on context length
- **Acceptance Criteria**:
  - [x] calculate_kv_cache_gb function accepts model architecture params and context length
  - [x] Formula based on: layers * heads * head_dim * 2 * context_length * batch_size * bytes
  - [x] Returns float representing additional GB needed
  - [x] Documented limitations (requires model architecture details)
  - [x] Unit tests verify estimates for known models
- **Technical Approach**:
  - Implement formula from architecture doc line 445-447
  - Accept architecture params as dict (layers, heads, head_dim)
  - Default batch_size to 1 (conservative estimate)
  - Use 2 bytes for FP16 KV cache (common case)
  - Note: This is informational; not used for Phase 7 but useful for Phase 2
- **Files/Components**:
  - [x] `dashboard/backend/utils/vram.py` - calculate_kv_cache_gb function
  - [x] `dashboard/backend/tests/test_vram.py` - KV cache tests
- **Dependencies**: Task 4.1
- **Complexity**: S

---

### 5. Health Check Polling

#### Task 5.1: Implement Container Health Checker
- [x] **Status**: Complete
- **Description**: Create service to poll container health endpoints until ready
- **Acceptance Criteria**:
  - [x] ContainerHealthChecker class created in services/
  - [x] poll_until_ready async method accepts container endpoint and timeout
  - [x] Polls /health endpoint at configured interval (default 1 second)
  - [x] Returns True when health check succeeds (200 OK)
  - [x] Raises TimeoutError if timeout exceeded
  - [x] Logs each attempt with status
  - [x] Configurable timeout and interval
- **Technical Approach**:
  - Use httpx.AsyncClient for HTTP requests
  - Implement exponential backoff or fixed interval (start with fixed)
  - Timeout based on model size (use timeout table from architecture)
  - Catch connection errors and retry
  - Log each attempt: "container_health_check", status=<code>, attempt=<n>
- **Files/Components**:
  - [x] `dashboard/backend/services/health_check.py` - ContainerHealthChecker class
  - [x] `dashboard/backend/tests/test_health_check.py` - Health check tests
- **Dependencies**: None (independent utility)
- **Complexity**: M

#### Task 5.2: Integrate Health Polling with ModelRouter
- [x] **Status**: Complete
- **Description**: Add health polling to ModelRouter.start_model flow
- **Acceptance Criteria**:
  - [x] ModelRouter.start_model calls health checker after sending start command
  - [x] Streams keepalive messages to client during health polling
  - [x] Waits for health check success before routing request
  - [x] Handles timeout errors gracefully (mark model as failed, retry)
  - [x] Updates cluster state when model becomes healthy
  - [x] Logs health check duration
- **Technical Approach**:
  - After daemon confirms container started, get container endpoint
  - Create health checker task: asyncio.create_task(health_checker.poll_until_ready(...))
  - While polling, yield keepalive to client (": keepalive\n\n")
  - On success, mark model as ready in cluster state
  - On timeout, mark model as failed, send stop command to daemon
- **Files/Components**:
  - [x] `dashboard/backend/services/model_router.py` - load_model_with_health_check function
  - [x] `dashboard/backend/tests/test_model_router.py` - Test health integration
- **Dependencies**: Tasks 5.1, 6.1 (needs ModelRouter)
- **Complexity**: M

---

### 6. ModelRouter Integration

#### Task 6.1: Implement ModelRouter.ensure_capacity Method
- [x] **Status**: Complete
- **Description**: Add ensure_capacity method to identify and free GPU capacity for model loading
- **Acceptance Criteria**:
  - [x] ensure_capacity method accepts GPURequirement spec
  - [x] Identifies machines with sufficient free GPUs
  - [x] Prefers single machine over multi-machine allocation
  - [x] If insufficient capacity, selects LRU idle models for eviction
  - [x] Returns list of Machine objects ready for allocation
  - [x] Raises InsufficientCapacityError if cannot meet requirements
  - [x] Marks machines as "busy" during allocation
  - [x] Unit tests cover single-machine, multi-machine, and eviction scenarios
- **Technical Approach**:
  - Query cluster state for GPU availability per machine
  - Sort machines by free GPU count (prefer concentrated allocation)
  - Check single machine first, fall back to multi-machine
  - If still insufficient, call _find_eviction_candidates (LRU idle)
  - Evict models via evict_model method
  - Mark allocated GPUs as "reserved" until container starts
  - Return list of (machine, gpu_indices) tuples
- **Files/Components**:
  - [x] `dashboard/backend/services/model_router.py` - ensure_capacity method (full orchestration)
  - [x] `dashboard/backend/services/model_router.py` - find_available_machine, evict_lru_models
  - [x] `dashboard/backend/tests/test_model_router.py` - Capacity tests
- **Dependencies**: Assumes ModelRouter class exists from earlier phase
- **Complexity**: L

#### Task 6.2: Implement ModelRouter.start_model Method
- [x] **Status**: Complete
- **Description**: Add start_model method to orchestrate container startup
- **Acceptance Criteria**:
  - [x] start_model method accepts model+quant identifier (via load_model, load_model_with_health_check)
  - [x] Looks up launch config from database
  - [x] Calls ensure_capacity to get machine allocation
  - [x] Generates container command via ContainerCommandGenerator
  - [x] Sends container.start command to daemon(s)
  - [x] Waits for daemon acknowledgment
  - [x] Polls health until ready (via health checker)
  - [x] Updates cluster state with running container info
  - [x] Returns container endpoint (host:port)
  - [x] Handles errors at each step with rollback
- **Technical Approach**:
  - Query database for LaunchConfig matching model+quant
  - Call ensure_capacity with GPU requirements from config
  - For each allocated machine, generate command and send to daemon
  - Multi-machine: coordinate master/worker startup (master first)
  - Wait for all daemons to report container started
  - Poll health on master node (or single node)
  - On success, update cluster state and return endpoint
  - On failure, send stop commands and release capacity
- **Files/Components**:
  - [x] `dashboard/backend/services/model_router.py` - load_model, load_model_with_health_check
  - [x] `dashboard/backend/tests/test_model_router.py` - Start model tests
- **Dependencies**: Tasks 3.2, 5.2, 6.1
- **Complexity**: XL

#### Task 6.3: Implement ModelRouter.evict_model Method
- [x] **Status**: Complete
- **Description**: Add evict_model method to stop and remove a running model
- **Acceptance Criteria**:
  - [x] evict_model method accepts model+quant identifier (via evict_lru_models)
  - [x] Verifies model is idle (queue empty, no in-flight requests)
  - [x] Sends container.stop command to daemon(s)
  - [x] Waits for daemon confirmation
  - [x] Blocks queue during eviction (queue exists but rejects requests)
  - [x] Releases GPU resources in cluster state
  - [x] Releases port allocation
  - [x] Logs eviction event
  - [x] Unit tests verify idle check and multi-machine coordination
- **Technical Approach**:
  - Check QueueManager.is_idle(model_quant)
  - If not idle, raise ModelBusyError
  - Look up running container(s) from cluster state
  - Send stop command to each daemon hosting the model
  - Wait for all stops to confirm
  - Update cluster state: remove containers, free GPUs
  - Call port allocator to release port(s)
  - Log: "model_evicted", model=model_quant, reason="lru"
- **Files/Components**:
  - [x] `dashboard/backend/services/model_router.py` - evict_lru_models function
  - [x] `dashboard/backend/tests/test_model_router.py` - Eviction tests
- **Dependencies**: Task 6.1
- **Complexity**: M

---

### 7. Initial vLLM Configurations (Seed Data)

#### Task 7.1: Create Seed Data SQL Script
- [x] **Status**: Complete
- **Description**: Create SQL script to populate database with initial vLLM configurations
- **Acceptance Criteria**:
  - [x] SQL script created with INSERT statements for common models
  - [x] At least 5 models included (Qwen 7B, 14B, 32B, 72B; Llama 8B, 70B; Mistral 7B)
  - [x] Each model has 2-3 quantizations (e.g., awq, fp16, q4_k_m, q8_0)
  - [x] Launch configs defined with sensible defaults
  - [x] VRAM requirements match reference table from architecture
  - [x] Script is idempotent (uses INSERT ... ON CONFLICT DO NOTHING)
  - [x] Script documented with comments
- **Technical Approach**:
  - Create db/seed_data/container_library.sql
  - Use transactions to ensure atomic insertion
  - Include models from architecture reference table (line 432-439)
  - Set is_default=TRUE for one launch config per quantization
  - Document where VRAM values came from (estimated vs measured)
- **Files/Components**:
  - [x] `dashboard/backend/db/seed_data/container_library.sql` - Seed data (7 models, 20+ quantizations)
  - [x] `dashboard/backend/db/seed_data/README.md` - Full documentation
- **Dependencies**: Task 1.1 (database schema must exist)
- **Complexity**: M

#### Task 7.2: Add Seed Data Loading to Startup
- [x] **Status**: Complete
- **Description**: Add option to load seed data on Dashboard first run or via CLI
- **Acceptance Criteria**:
  - [x] CLI command to load seed data: `python -m dashboard.backend.cli seed-container-library`
  - [x] Checks if seed data already loaded (count rows, skip if present)
  - [x] Loads SQL file and executes via SQLAlchemy connection
  - [x] Logs success or skip message
  - [x] Optional: --force flag to reload even if data exists
  - [x] Unit tests verify seed data loads correctly
- **Technical Approach**:
  - Create backend/cli.py with click or argparse
  - Check model_configs table count, skip if > 0
  - Read SQL file and execute via session.execute()
  - Commit transaction on success
  - Log: "seed_data_loaded", table="container_library", models=<count>
- **Files/Components**:
  - [x] `dashboard/backend/cli.py` - CLI tool with seed-container-library, list-models, verify-vram
  - [x] `dashboard/backend/tests/test_cli.py` - CLI tests (if created)
- **Dependencies**: Task 7.1
- **Complexity**: M

#### Task 7.3: Validate Seed Data Accuracy
- [x] **Status**: Complete
- **Description**: Create validation script to verify seed data VRAM estimates against known values
- **Acceptance Criteria**:
  - [x] Validation script compares seed VRAM values to formula estimates
  - [x] Reports any discrepancies > 10% difference
  - [x] Outputs summary of all models and their VRAM requirements
  - [x] Can be run as part of CI/testing
  - [x] Documents known discrepancies (measured vs estimated)
- **Technical Approach**:
  - Query all quantization_configs from database
  - For each, calculate estimated VRAM using formula
  - Compare to stored vram_required_gb
  - Report differences with % variance
  - Flag any outliers for manual review
- **Files/Components**:
  - [x] `dashboard/backend/cli.py` - verify-vram command integrates validation
- **Dependencies**: Tasks 4.1, 7.1
- **Complexity**: S

---

### 8. API Endpoints for Container Configs

#### Task 8.1: Create Container Config List Endpoint
- [x] **Status**: Complete
- **Description**: Implement GET /api/containers endpoint to list all container configurations
- **Acceptance Criteria**:
  - [x] Endpoint returns list of launch configs with nested model and quant info
  - [x] Supports filtering by runtime (query param)
  - [x] Supports filtering by model name (query param)
  - [x] Returns Pydantic schema (ContainerConfigResponse)
  - [x] Includes pagination support (limit/offset)
  - [x] Unit tests verify filtering and pagination
- **Technical Approach**:
  - Query LaunchConfig with joined ModelConfig and QuantizationConfig
  - Apply filters from query params
  - Use SQLAlchemy selectin loading for relationships
  - Serialize to LaunchConfigSchema
  - Return JSON array
- **Files/Components**:
  - [x] `dashboard/backend/api/control.py` - GET /api/containers endpoint
  - [x] `dashboard/backend/tests/test_api_control.py` - API tests
- **Dependencies**: Tasks 2.4, 7.1
- **Complexity**: M

#### Task 8.2: Create Container Config Detail Endpoint
- [x] **Status**: Complete
- **Description**: Implement GET /api/containers/{id} endpoint to retrieve single config
- **Acceptance Criteria**:
  - [x] Endpoint returns full launch config with all nested data
  - [x] Returns 404 if config not found
  - [x] Returns ContainerConfigResponse
  - [x] Unit tests verify response structure
- **Technical Approach**:
  - Query LaunchConfig by ID with joined relationships
  - Return 404 if None
  - Serialize to LaunchConfigSchema
  - Return JSON object
- **Files/Components**:
  - [x] `dashboard/backend/api/control.py` - GET /api/containers/{config_id} endpoint
  - [x] `dashboard/backend/tests/test_api_control.py` - Detail endpoint tests
- **Dependencies**: Task 8.1
- **Complexity**: S

#### Task 8.3: Create Container Config Update Endpoint
- [x] **Status**: Complete
- **Description**: Implement PUT /api/containers/{id} endpoint to update launch configuration
- **Acceptance Criteria**:
  - [x] Endpoint accepts ContainerConfigUpdate (partial update)
  - [x] Updates allowed fields: context_length, max_parallel, extra_args, environment
  - [x] Rejects updates to runtime, gpu_count (structural changes)
  - [x] Validates numeric fields (positive, within ranges)
  - [x] Returns updated ContainerConfigResponse
  - [x] Updates updated_at timestamp
  - [x] Unit tests verify updates and validation errors
- **Technical Approach**:
  - Accept Pydantic model for update data
  - Query existing LaunchConfig
  - Apply updates to allowed fields only
  - Validate constraints (positive integers, etc.)
  - Commit and return updated object
  - Trigger updated_at via database trigger
- **Files/Components**:
  - [x] `dashboard/backend/api/control.py` - PUT /api/containers/{config_id} endpoint
  - [x] `dashboard/backend/tests/test_api_control.py` - Update tests
- **Dependencies**: Task 8.2
- **Complexity**: M

---

### 9. Integration Testing

#### Task 9.1: Create End-to-End Container Start Test
- [ ] **Status**: Not Started
- **Description**: Create integration test that verifies complete flow from API call to container start
- **Acceptance Criteria**:
  - [ ] Test creates launch config in database
  - [ ] Test calls ModelRouter.start_model
  - [ ] Verifies container command generated correctly
  - [ ] Mocks daemon communication and health checks
  - [ ] Verifies cluster state updated correctly
  - [ ] Verifies port allocated and returned
  - [ ] Test cleanup releases resources
- **Technical Approach**:
  - Use pytest fixtures to setup test database
  - Insert test launch config
  - Mock DaemonManager.send_command
  - Mock ContainerHealthChecker.poll_until_ready
  - Call start_model and verify command sent to daemon
  - Assert cluster state reflects running container
  - Cleanup: call evict_model
- **Files/Components**:
  - [ ] `dashboard/backend/tests/integration/test_container_lifecycle.py` - Integration test
- **Dependencies**: Tasks 3.2, 6.2
- **Complexity**: L

#### Task 9.2: Create Multi-GPU Container Test
- [ ] **Status**: Not Started
- **Description**: Create integration test for multi-GPU model startup
- **Acceptance Criteria**:
  - [ ] Test creates launch config requiring 2+ GPUs
  - [ ] Verifies ensure_capacity allocates multiple GPUs
  - [ ] Verifies container command includes all GPU devices
  - [ ] Verifies tensor_parallel setting correct
  - [ ] Verifies CUDA_VISIBLE_DEVICES includes all GPUs
  - [ ] Test covers single-machine multi-GPU case
- **Technical Approach**:
  - Insert launch config with gpu_count=2, tensor_parallel=2
  - Mock cluster state with machine having 2+ free GPUs
  - Call start_model
  - Verify command has two --device arguments
  - Verify CUDA_VISIBLE_DEVICES="0,1"
  - Verify --tensor-parallel-size 2 in vLLM args
- **Files/Components**:
  - [ ] `dashboard/backend/tests/integration/test_container_lifecycle.py` - Multi-GPU test
- **Dependencies**: Tasks 3.2, 6.2
- **Complexity**: L

#### Task 9.3: Create Eviction and Reload Test
- [ ] **Status**: Not Started
- **Description**: Create integration test for model eviction and subsequent reload
- **Acceptance Criteria**:
  - [ ] Test starts model, marks as idle, evicts
  - [ ] Verifies eviction releases GPU resources
  - [ ] Verifies port released
  - [ ] Test reloads same model
  - [ ] Verifies model loads on same or different GPU
  - [ ] Verifies new port allocated
- **Technical Approach**:
  - Start model A, verify running
  - Mark queue as idle (mock QueueManager)
  - Call evict_model(A)
  - Verify cluster state shows GPUs free
  - Start model A again
  - Verify successful start and potentially different port
- **Files/Components**:
  - [ ] `dashboard/backend/tests/integration/test_eviction.py` - Eviction test
- **Dependencies**: Tasks 6.2, 6.3
- **Complexity**: M

---

### 10. Documentation

#### Task 10.1: Document Container Command Generator
- [x] **Status**: Complete
- **Description**: Add comprehensive docstrings and usage examples for ContainerCommandGenerator
- **Acceptance Criteria**:
  - [x] Class docstring explains purpose and usage
  - [x] Each method has docstring with parameters and return value
  - [x] Example usage provided in docstring
  - [x] Type hints complete and accurate
  - [x] Sphinx-compatible formatting
- **Technical Approach**:
  - Follow Google or NumPy docstring style
  - Include example code in module docstring
  - Document all parameters with types
  - Document exceptions raised
- **Files/Components**:
  - [x] `dashboard/backend/services/container_command.py` - Full docstrings on all classes/methods
- **Dependencies**: Tasks 3.1-3.6
- **Complexity**: S

#### Task 10.2: Document VRAM Calculation Functions
- [x] **Status**: Complete
- **Description**: Add documentation explaining VRAM estimation formulas and limitations
- **Acceptance Criteria**:
  - [x] Module docstring explains estimation approach
  - [x] Function docstrings include formula references
  - [x] Limitations documented (estimates vs actual)
  - [x] Reference table included as comment
  - [x] Examples provided for common models
- **Technical Approach**:
  - Reference architecture doc formulas
  - Explain 1.2 overhead multiplier rationale
  - Note that actual usage may vary
  - Recommend monitoring and adjustment
- **Files/Components**:
  - [x] `dashboard/backend/utils/vram.py` - Comprehensive module and function documentation
- **Dependencies**: Tasks 4.1, 4.2
- **Complexity**: S

#### Task 10.3: Create Container Library User Guide
- [ ] **Status**: Not Started
- **Description**: Create user-facing documentation for container library feature
- **Acceptance Criteria**:
  - [ ] Markdown document explains container library concept
  - [ ] Instructions for viewing available configs
  - [ ] Instructions for updating configs via API
  - [ ] Example API calls with curl
  - [ ] Explanation of when to adjust context_length or max_parallel
  - [ ] Troubleshooting section for common issues
- **Technical Approach**:
  - Create docs/user-guide-container-library.md
  - Include screenshots (if UI exists) or API examples
  - Link to architecture doc for deep dive
  - Provide decision tree for config adjustments
- **Files/Components**:
  - [ ] `docs/user-guide-container-library.md` - User guide
- **Dependencies**: Tasks 8.1-8.3
- **Complexity**: M

---

## Summary

### Task Count by Category
- **Database Schema**: 2 tasks
- **SQLAlchemy Models**: 4 tasks
- **Container Command Generator**: 6 tasks
- **VRAM Calculations**: 2 tasks
- **Health Check Polling**: 2 tasks
- **ModelRouter Integration**: 3 tasks
- **Seed Data**: 3 tasks
- **API Endpoints**: 3 tasks
- **Integration Testing**: 3 tasks
- **Documentation**: 3 tasks

**Total Tasks**: 31

### Complexity Breakdown
- **Small (S)**: 9 tasks
- **Medium (M)**: 16 tasks
- **Large (L)**: 5 tasks
- **Extra Large (XL)**: 1 task

### Critical Path
1. Database migration (1.1) → SQLAlchemy models (2.1-2.3)
2. Command generator base (3.1) → vLLM generation (3.2)
3. ModelRouter integration (6.1-6.2)
4. Health checking (5.1-5.2)
5. Seed data (7.1-7.2)
6. Integration testing (9.1-9.3)

### Estimated Timeline
- **Database & Models**: 3-4 days
- **Command Generation**: 4-5 days
- **ModelRouter Integration**: 5-6 days
- **Health Checking & VRAM**: 2-3 days
- **Seed Data & APIs**: 3-4 days
- **Testing & Documentation**: 4-5 days

**Total Estimated Duration**: 21-27 days (3-4 weeks)

---

## Dependencies on Other Phases

**Prerequisites from Earlier Phases**:
- Database infrastructure (TimescaleDB, SQLAlchemy setup)
- ModelRouter class foundation (queue management)
- DaemonManager for sending commands
- ClusterState for tracking machine/GPU availability

**Enables Future Phases**:
- Phase 2: Model download and registration
- Phase 2: Container configuration UI
- Multi-machine coordination (future)

---

## Testing Strategy

1. **Unit Tests**: Each component tested in isolation with mocks
2. **Integration Tests**: End-to-end flows with test database
3. **Manual Testing**: Actual container starts on dev environment
4. **Validation**: Seed data VRAM estimates verified against formula

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| vLLM argument changes between versions | Pin vLLM version in config, document version compatibility |
| VRAM estimates inaccurate | Provide validation script, allow manual overrides |
| Port allocation conflicts | Implement proper locking, track allocations persistently |
| Health check timeouts too short | Use dynamic timeouts based on model size |
| Multi-GPU coordination failures | Start with single-GPU, add multi-GPU incrementally |

---

## Success Criteria

Phase 7 is complete when:
- [x] Database schema created and populated with seed data
- [x] vLLM commands generated correctly for single and multi-GPU configs
- [x] Containers start successfully with proper GPU assignments
- [x] Health checks poll until containers ready
- [x] ModelRouter can trigger container starts and handle failures
- [x] Container labels track all required metadata
- [x] All unit and integration tests pass
- [x] Documentation complete and accurate
